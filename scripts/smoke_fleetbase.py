import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fleetbase_backend import FleetbaseClient, LogisticsSessionState


async def main(*, commit: bool = False) -> None:
    load_dotenv(".env.fleetbase.local")
    client = FleetbaseClient()
    state = LogisticsSessionState()
    order = await client.lookup_waybill("LOG9113180438SG")
    availability = await client.list_delivery_slots("LOG9113180438SG")
    print(
        {
            "lookup_found": order.get("found"),
            "slots_found": len(availability.get("slots", [])),
        }
    )
    assert order["found"] and len(availability["slots"]) == 3
    if not commit:
        return

    proposal = await client.prepare_reschedule(
        state,
        "LOG9113180438SG",
        availability["slots"][0]["slot_id"],
        "user-prepare",
    )
    result = await client.commit_reschedule(
        state, proposal["proposal_id"], "user-confirm"
    )
    verified = await client.lookup_waybill("LOG9113180438SG")
    assert result["committed"] and verified["scheduled_at"] == proposal["scheduled_at"]
    print(
        {
            "lookup": order["waybill_number"],
            "slots": len(availability["slots"]),
            "committed": result["committed"],
            "scheduled_at": verified["scheduled_at"],
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate the Fleetbase adapter. The default mode is read-only."
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="submit a reschedule for the synthetic smoke-test order",
    )
    args = parser.parse_args()
    asyncio.run(main(commit=args.commit))
