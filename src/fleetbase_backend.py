from __future__ import annotations

import json as json_module
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp


class FleetbaseError(RuntimeError):
    pass


class FleetbaseConflictError(FleetbaseError):
    pass


@dataclass
class RescheduleProposal:
    proposal_id: str
    waybill_number: str
    order_id: str
    slot_id: str
    scheduled_at: str
    order_updated_at: str
    prepared_user_message_id: str


@dataclass
class LogisticsSessionState:
    proposals: dict[str, RescheduleProposal] = field(default_factory=dict)
    consecutive_waybill_lookup_failures: int = 0

    def record_waybill_lookup(self, result: dict[str, Any]) -> dict[str, Any]:
        """Track exact-lookup failures and expose when typed input should be offered."""

        if result.get("found"):
            self.consecutive_waybill_lookup_failures = 0
        else:
            self.consecutive_waybill_lookup_failures += 1

        fallback_recommended = self.consecutive_waybill_lookup_failures >= 2
        enriched = {
            **result,
            "consecutive_lookup_failures": self.consecutive_waybill_lookup_failures,
            "input_fallback_recommended": fallback_recommended,
        }
        if fallback_recommended:
            enriched["input_fallback"] = "chat_text_input"
        return enriched


class FleetbaseClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        console_token: str | None = None,
        company_uuid: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("FLEETBASE_URL", "http://localhost:8000")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("FLEETBASE_API_KEY", "")
        self.console_token = console_token or os.getenv("FLEETBASE_CONSOLE_TOKEN", "")
        self.company_uuid = company_uuid or os.getenv("FLEETBASE_COMPANY_UUID", "")
        self._session = session

    async def _request(
        self,
        method: str,
        path: str,
        *,
        internal: bool = False,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        token = self.console_token if internal else self.api_key
        if not token:
            raise FleetbaseError("Fleetbase credentials are not configured")
        headers = {"Authorization": f"Bearer {token}"}
        timeout = aiohttp.ClientTimeout(total=10)
        session = self._session or aiohttp.ClientSession(timeout=timeout)
        close_session = self._session is None
        try:
            async with session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                params=params,
                json=json,
            ) as response:
                body = await response.text()
                try:
                    data = json_module.loads(body) if body.strip() else {}
                except json_module.JSONDecodeError:
                    data = {"message": body}
                if response.status == 409:
                    raise FleetbaseConflictError(str(data))
                if response.status >= 400:
                    raise FleetbaseError(f"Fleetbase HTTP {response.status}: {data}")
                return data
        except aiohttp.ClientError as exc:
            raise FleetbaseError(f"Fleetbase request failed: {exc}") from exc
        finally:
            if close_session:
                await session.close()

    @staticmethod
    def normalize_waybill(value: str) -> str:
        return "".join(value.split()).replace("-", "").upper()

    @classmethod
    def _order_waybill(cls, order: dict[str, Any]) -> str:
        tracking = order.get("tracking_number") or {}
        value = (
            tracking.get("tracking_number", "")
            if isinstance(tracking, dict)
            else tracking
        )
        return cls.normalize_waybill(str(value))

    async def lookup_waybill(self, waybill_number: str) -> dict[str, Any]:
        normalized = self.normalize_waybill(waybill_number)
        if len(normalized) < 8:
            return {
                "found": False,
                "waybill_number": normalized,
                "incomplete": True,
            }
        data = await self._request(
            "GET", "/v1/orders", params={"tracking_number": normalized}
        )
        if isinstance(data, list):
            data = next(
                (
                    item
                    for item in data
                    if isinstance(item, dict)
                    and self._order_waybill(item) == normalized
                ),
                None,
            )
        if not isinstance(data, dict) or not data.get("id"):
            return {"found": False, "waybill_number": normalized}
        if self._order_waybill(data) != normalized:
            return {"found": False, "waybill_number": normalized}
        tracking = data.get("tracking_number") or {}
        return {
            "found": True,
            "waybill_number": tracking.get("tracking_number", normalized),
            "order_id": data["id"],
            "status": data.get("status"),
            "tracking_status": tracking.get("status"),
            "scheduled_at": data.get("scheduled_at"),
            "updated_at": data.get("updated_at"),
            "reschedule_allowed": data.get("status") in {"created", "scheduled"},
        }

    async def list_delivery_slots(self, waybill_number: str) -> dict[str, Any]:
        order = await self.lookup_waybill(waybill_number)
        if not order.get("found"):
            return {**order, "slots": []}
        if not order["reschedule_allowed"]:
            return {**order, "slots": []}
        data = await self._request(
            "GET", "/int/v1/schedule-availabilities", internal=True
        )
        records = data.get("schedule_availabilities", [])
        slots = []
        for record in records:
            if (
                record.get("subject_uuid") != self.company_uuid
                or not record.get("is_available")
                or record.get("reason") != "customer_delivery"
            ):
                continue
            slots.append(
                {
                    "slot_id": record["uuid"],
                    "start_at": record["start_at"],
                    "end_at": record["end_at"],
                    "notes": record.get("notes"),
                }
            )
        slots.sort(key=lambda item: item["start_at"])
        return {**order, "slots": slots}

    async def prepare_reschedule(
        self,
        state: LogisticsSessionState,
        waybill_number: str,
        slot_id: str,
        user_message_id: str,
    ) -> dict[str, Any]:
        availability = await self.list_delivery_slots(waybill_number)
        slot = next(
            (
                item
                for item in availability.get("slots", [])
                if item["slot_id"] == slot_id
            ),
            None,
        )
        if slot is None:
            raise FleetbaseConflictError(
                "The selected delivery slot is no longer available"
            )
        proposal = RescheduleProposal(
            proposal_id=str(uuid.uuid4()),
            waybill_number=availability["waybill_number"],
            order_id=availability["order_id"],
            slot_id=slot_id,
            scheduled_at=slot["start_at"],
            order_updated_at=availability["updated_at"],
            prepared_user_message_id=user_message_id,
        )
        state.proposals[proposal.proposal_id] = proposal
        return {
            "proposal_id": proposal.proposal_id,
            "waybill_number": proposal.waybill_number,
            "scheduled_at": proposal.scheduled_at,
            "slot_end_at": slot["end_at"],
            "requires_later_confirmation": True,
        }

    async def commit_reschedule(
        self,
        state: LogisticsSessionState,
        proposal_id: str,
        user_message_id: str,
    ) -> dict[str, Any]:
        proposal = state.proposals.get(proposal_id)
        if proposal is None:
            raise FleetbaseConflictError(
                "The reschedule proposal is missing or expired"
            )
        if user_message_id == proposal.prepared_user_message_id:
            raise FleetbaseConflictError("Confirmation must come in a later user turn")
        current = await self.lookup_waybill(proposal.waybill_number)
        if current.get("scheduled_at") == proposal.scheduled_at:
            state.proposals.pop(proposal_id, None)
            return {**current, "committed": True, "idempotent_replay": True}
        if current.get("updated_at") != proposal.order_updated_at:
            raise FleetbaseConflictError(
                "The order changed after review; review it again"
            )
        data = await self._request(
            "PUT",
            f"/v1/orders/{proposal.order_id}",
            json={"scheduled_at": proposal.scheduled_at},
        )
        state.proposals.pop(proposal_id, None)
        return {
            "committed": True,
            "idempotent_replay": False,
            "waybill_number": proposal.waybill_number,
            "order_id": data.get("id", proposal.order_id),
            "scheduled_at": data.get("scheduled_at", proposal.scheduled_at),
            "updated_at": data.get("updated_at"),
        }


def latest_user_message_id(history: Any) -> str:
    for item in reversed(history.items):
        if (
            getattr(item, "type", None) == "message"
            and getattr(item, "role", None) == "user"
        ):
            return item.id
    raise FleetbaseConflictError("No committed user message is available")


def iso_is_after(value: str, other: str) -> bool:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ) > datetime.fromisoformat(other.replace("Z", "+00:00"))
