# ruff: noqa: RUF001

import pytest
from livekit.agents import inference

from agent import (
    ASSEMBLYAI_ENDPOINTING_MIN_DELAY,
    ASSEMBLYAI_STT_LANGUAGE,
    CARTESIA_TTS_MAX_BUFFER_DELAY_MS,
    CARTESIA_TTS_VOICE,
    DEEPGRAM_ENDPOINTING_MS,
    DEFAULT_STT_MODEL,
    DEFAULT_STT_PROFILE,
    DEFAULT_TTS_EXPRESSIVE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_PROFILE,
    FISH_AUDIO_TTS_VOICE,
    STT_CONTINUOUS_PARTIALS,
    STT_INTERRUPTION_DELAY_MS,
    STT_KEYTERMS,
    STT_LANGUAGE,
    STT_MAX_TURN_SILENCE_MS,
    STT_MIN_TURN_SILENCE_MS,
    STT_PROFILE_ACCURACY,
    STT_PROFILE_BASELINE,
    STT_PROMPT,
    TTS_LANGUAGE,
    TTS_PROFILE_BASELINE,
    TTS_PROFILE_RELIABILITY,
    Assistant,
    default_stt_language,
    inference_provider,
    resolve_stt_profile,
    resolve_tts_expressive,
    resolve_tts_profile,
    resolve_tts_voice,
    stt_inference_kwargs,
    stt_provider,
    tts_inference_kwargs,
    turn_handling_options,
)
from fleetbase_backend import (
    MIN_WAYBILL_LENGTH,
    FleetbaseClient,
    FleetbaseConflictError,
    LogisticsSessionState,
    WaybillCandidate,
)


class FakeFleetbase(FleetbaseClient):
    def __init__(self) -> None:
        super().__init__(
            api_key="fake", console_token="fake-console", company_uuid="company-1"
        )
        self.order = {
            "id": "order-1",
            "status": "created",
            "scheduled_at": "2026-11-09T02:00:00Z",
            "updated_at": "2026-11-08T10:00:00Z",
            "tracking_number": {
                "tracking_number": "LOG9113180438SG",
                "status": "Order Created",
            },
        }
        self.slots = [
            {
                "uuid": "slot-1",
                "subject_uuid": "company-1",
                "is_available": True,
                "reason": "customer_delivery",
                "start_at": "2026-11-09T05:00:00Z",
                "end_at": "2026-11-09T07:00:00Z",
                "notes": "下午第一时段",
            }
        ]
        self.patch_calls: list[dict] = []

    async def _request(self, method, path, *, internal=False, params=None, json=None):
        if method == "GET" and path == "/v1/orders":
            return (
                self.order.copy()
                if params["tracking_number"] == "LOG9113180438SG"
                else []
            )
        if method == "GET" and path == "/int/v1/schedule-availabilities":
            return {"schedule_availabilities": self.slots.copy()}
        if method == "PUT" and path == "/v1/orders/order-1":
            self.patch_calls.append(json)
            self.order.update(
                scheduled_at=json["scheduled_at"], updated_at="2026-11-08T11:00:00Z"
            )
            return self.order.copy()
        raise AssertionError((method, path, internal, params, json))


ASSEMBLYAI_MODEL = "assemblyai/universal-3-6-pro"
DEEPGRAM_MODEL = "deepgram/nova-3-general"


def test_uses_supported_chinese_speech_models() -> None:
    assert DEFAULT_STT_MODEL == "assemblyai/universal-3-6-pro"
    assert STT_LANGUAGE == "zh-CN"
    assert ASSEMBLYAI_STT_LANGUAGE == "zh"
    assert STT_KEYTERMS == [
        "物流",
        "运单号",
        "派送改约",
        "12345678",
        "LOG9113180438SG",
    ]
    assert DEFAULT_TTS_MODEL == "cartesia/sonic-3.5"
    assert TTS_LANGUAGE == "zh"
    assert CARTESIA_TTS_VOICE == "f786b574-daa5-4673-aa0c-cbe3e8534c02"
    assert FISH_AUDIO_TTS_VOICE == "fa4c9eb3dccc4806b382b40d61c6b10a"


def test_deepgram_rollback_configuration() -> None:
    options = stt_inference_kwargs(model=DEEPGRAM_MODEL, profile=STT_PROFILE_ACCURACY)
    assert options["model"] == "deepgram/nova-3-general"
    assert options["language"] == "zh-CN"

    extra = options["extra_kwargs"]
    assert set(extra) == {
        "interim_results",
        "no_delay",
        "smart_format",
        "numerals",
        "punctuate",
        "endpointing",
        "keyterm",
    }
    assert extra["interim_results"] is True
    assert extra["no_delay"] is False
    assert extra["smart_format"] is True
    assert extra["numerals"] is True
    assert extra["punctuate"] is True
    assert extra["endpointing"] == DEEPGRAM_ENDPOINTING_MS == 800
    assert extra["keyterm"] == STT_KEYTERMS
    # AssemblyAI-only keys must never reach Deepgram.
    for key in (
        "mode",
        "prompt",
        "keyterms_prompt",
        "min_turn_silence",
        "max_turn_silence",
        "continuous_partials",
        "interruption_delay",
        "voice_focus",
    ):
        assert key not in extra


def test_default_assemblyai_accuracy_configuration() -> None:
    assert DEFAULT_STT_MODEL == ASSEMBLYAI_MODEL
    options = stt_inference_kwargs(
        model=DEFAULT_STT_MODEL, profile=STT_PROFILE_ACCURACY
    )
    # AssemblyAI's Mandarin code differs from Deepgram's BCP-47 locale.
    assert options["language"] == ASSEMBLYAI_STT_LANGUAGE == "zh"

    extra = options["extra_kwargs"]
    assert extra["mode"] == "max_accuracy"
    assert extra["prompt"] == STT_PROMPT
    for phrase in ("运单号", "包裹状态", "派送时段", "改约", "英文字母", "数字"):
        assert phrase in extra["prompt"]
    assert extra["keyterms_prompt"] == STT_KEYTERMS
    assert extra["min_turn_silence"] == STT_MIN_TURN_SILENCE_MS == 500
    assert extra["max_turn_silence"] == STT_MAX_TURN_SILENCE_MS == 1500
    # Earlier interim transcripts for the console/frontend; documented 0-1000 ms.
    assert extra["continuous_partials"] == STT_CONTINUOUS_PARTIALS is True
    assert extra["interruption_delay"] == STT_INTERRUPTION_DELAY_MS == 250
    assert 0 <= extra["interruption_delay"] <= 1000
    # RoomIO already applies AI acoustics enhancement and the mic type is unknown.
    assert "voice_focus" not in extra
    assert "voice_focus_threshold" not in extra
    # Deepgram-only keys must never reach AssemblyAI.
    for key in ("interim_results", "no_delay", "keyterm", "endpointing"):
        assert key not in extra


def test_default_stt_language_is_provider_aware() -> None:
    assert default_stt_language("deepgram/nova-3-general") == "zh-CN"
    assert default_stt_language(ASSEMBLYAI_MODEL) == "zh"
    assert stt_inference_kwargs(model="auto:zh")["language"] == "zh-CN"
    # An explicit language always wins.
    overridden = stt_inference_kwargs(model="deepgram/nova-3-general", language="zh")
    assert overridden["language"] == "zh"


def test_provider_options_are_only_sent_to_the_matching_provider() -> None:
    assert stt_provider("assemblyai/universal-3-6-pro:zh") == "assemblyai"
    assert stt_provider("deepgram/nova-3-general:zh-CN") == "deepgram"
    assert stt_provider("auto:zh") == "auto"

    for model in ("auto:zh", "auto", "cartesia/ink-2"):
        options = stt_inference_kwargs(model=model, profile=STT_PROFILE_ACCURACY)
        assert options["model"] == model
        assert "extra_kwargs" not in options


def test_baseline_profile_keeps_provider_defaults() -> None:
    assemblyai = stt_inference_kwargs(
        model=DEFAULT_STT_MODEL, profile=STT_PROFILE_BASELINE
    )
    assert assemblyai == {"model": DEFAULT_STT_MODEL, "language": "zh"}

    deepgram = stt_inference_kwargs(model=DEEPGRAM_MODEL, profile=STT_PROFILE_BASELINE)
    assert deepgram == {"model": DEEPGRAM_MODEL, "language": "zh-CN"}


def test_assemblyai_uses_stt_turn_detection_without_added_delay() -> None:
    for model in (ASSEMBLYAI_MODEL, "assemblyai/universal-3-6-pro:zh"):
        options = turn_handling_options(model)
        assert options["turn_detection"] == "stt"
        # TurnHandlingOptions endpointing is in seconds, not milliseconds.
        assert options["endpointing"] == {"min_delay": ASSEMBLYAI_ENDPOINTING_MIN_DELAY}
    assert ASSEMBLYAI_ENDPOINTING_MIN_DELAY == 0.0


def test_other_stt_models_keep_the_turn_detector() -> None:
    for model in (DEEPGRAM_MODEL, "auto", "auto:zh", "cartesia/ink-2"):
        options = turn_handling_options(model)
        assert isinstance(options["turn_detection"], inference.TurnDetector)
        # No override: the session's own endpointing defaults apply unchanged.
        assert "endpointing" not in options


def test_profile_override_is_validated() -> None:
    assert DEFAULT_STT_PROFILE == STT_PROFILE_ACCURACY
    assert resolve_stt_profile("baseline") == STT_PROFILE_BASELINE
    assert resolve_stt_profile(" ACCURACY ") == STT_PROFILE_ACCURACY
    assert resolve_stt_profile("") == STT_PROFILE_ACCURACY
    assert resolve_stt_profile("bogus") == STT_PROFILE_ACCURACY


def test_default_tts_is_cartesia_multilingual() -> None:
    options = tts_inference_kwargs(
        model=DEFAULT_TTS_MODEL, voice="", profile=TTS_PROFILE_RELIABILITY
    )
    assert options["model"] == "cartesia/sonic-3.5"
    assert options["voice"] == CARTESIA_TTS_VOICE
    assert options["language"] == "zh"
    assert "voice" in options

    extra = options["extra_kwargs"]
    assert set(extra) == {"speed", "volume", "max_buffer_delay_ms"}
    # Neutral, natural delivery for voice replies.
    assert extra["speed"] == 1.0
    assert extra["volume"] == 1.0
    # Low-latency streaming start point; not tuned against real speech.
    assert extra["max_buffer_delay_ms"] == CARTESIA_TTS_MAX_BUFFER_DELAY_MS == 300
    # No expressive markup and no timestamp work for plain audio playback.
    for key in (
        "emotion",
        "add_timestamps",
        "add_phoneme_timestamps",
        "latency",
        "temperature",
        "top_p",
        "normalize",
        "normalize_loudness",
    ):
        assert key not in extra


def test_other_cartesia_models_remain_env_ab_options() -> None:
    default = tts_inference_kwargs(
        model=DEFAULT_TTS_MODEL, voice="", profile=TTS_PROFILE_RELIABILITY
    )
    assert DEFAULT_TTS_MODEL == "cartesia/sonic-3.5"
    # Both other Cartesia models are env-only A/B options; switching
    # LOGISTICS_TTS_MODEL changes only the model id, so voice, language and
    # reliability extras stay identical for a fair same-utterance comparison.
    for model in ("cartesia/sonic-3", "cartesia/sonic-3.6"):
        options = tts_inference_kwargs(
            model=model, voice="", profile=TTS_PROFILE_RELIABILITY
        )
        assert options["model"] == model
        assert options["voice"] == default["voice"] == CARTESIA_TTS_VOICE
        assert options["language"] == default["language"] == "zh"
        assert options["extra_kwargs"] == default["extra_kwargs"]


def test_fishaudio_rollback_keeps_voice_and_extras() -> None:
    options = tts_inference_kwargs(
        model="fishaudio/s2.1-pro", voice="", profile=TTS_PROFILE_RELIABILITY
    )
    assert options["model"] == "fishaudio/s2.1-pro"
    assert options["voice"] == FISH_AUDIO_TTS_VOICE
    assert options["language"] == "zh"

    extra = options["extra_kwargs"]
    assert extra["latency"] == "balanced"
    assert extra["normalize"] is True
    assert extra["normalize_loudness"] is True
    # Lower sampling variance than the provider defaults, without going to 0.
    assert 0 < extra["temperature"] <= 0.7
    assert 0 < extra["top_p"] <= 0.8
    # Natural speaking rate; 1.05 is the documented upper bound for an A/B.
    assert 0 < extra["speed"] <= 1.05
    # Only provider-supported Fish Audio knobs; no Cartesia keys.
    assert set(extra) == {
        "latency",
        "temperature",
        "top_p",
        "speed",
        "normalize",
        "normalize_loudness",
    }
    for key in ("volume", "max_buffer_delay_ms", "emotion"):
        assert key not in extra


def test_tts_voice_resolution_and_override() -> None:
    assert inference_provider("cartesia/sonic-3:zh") == "cartesia"
    assert inference_provider("fishaudio/s2.1-pro:zh") == "fishaudio"

    # The voice follows the model when no explicit override is set.
    assert resolve_tts_voice("cartesia/sonic-3", "") == CARTESIA_TTS_VOICE
    assert resolve_tts_voice("fishaudio/s2.1-pro", "") == FISH_AUDIO_TTS_VOICE
    # Unknown providers get no voice id; the gateway default applies.
    assert resolve_tts_voice("auto:zh", "") is None
    assert "voice" not in tts_inference_kwargs(model="auto:zh", voice="")

    # LOGISTICS_TTS_VOICE always wins, whichever model is selected.
    for model in (
        "cartesia/sonic-3.5",
        "cartesia/sonic-3",
        "cartesia/sonic-3.6",
        "fishaudio/s2.1-pro",
        "rime/coda",
    ):
        assert resolve_tts_voice(model, "custom-voice") == "custom-voice"
        assert (
            tts_inference_kwargs(model=model, voice="custom-voice")["voice"]
            == "custom-voice"
        )


def test_tts_provider_extras_are_gated_by_provider() -> None:
    cartesia = tts_inference_kwargs(
        model="cartesia/sonic-3", voice="", profile=TTS_PROFILE_RELIABILITY
    )
    assert "latency" not in cartesia["extra_kwargs"]
    assert "temperature" not in cartesia["extra_kwargs"]

    fish = tts_inference_kwargs(
        model="fishaudio/s2.1-pro", voice="", profile=TTS_PROFILE_RELIABILITY
    )
    assert "volume" not in fish["extra_kwargs"]
    assert "max_buffer_delay_ms" not in fish["extra_kwargs"]

    for model in ("auto", "auto:zh", "rime/coda"):
        options = tts_inference_kwargs(
            model=model, voice="", profile=TTS_PROFILE_RELIABILITY
        )
        assert options["model"] == model
        assert options["language"] == "zh"
        assert "extra_kwargs" not in options


def test_tts_baseline_profile_keeps_provider_defaults() -> None:
    cartesia = tts_inference_kwargs(
        model=DEFAULT_TTS_MODEL, voice="", profile=TTS_PROFILE_BASELINE
    )
    assert cartesia == {
        "model": DEFAULT_TTS_MODEL,
        "voice": CARTESIA_TTS_VOICE,
        "language": "zh",
    }

    fish = tts_inference_kwargs(
        model="fishaudio/s2.1-pro", voice="", profile=TTS_PROFILE_BASELINE
    )
    assert fish == {
        "model": "fishaudio/s2.1-pro",
        "voice": FISH_AUDIO_TTS_VOICE,
        "language": "zh",
    }


def test_tts_profile_and_expressive_overrides_are_validated() -> None:
    assert DEFAULT_TTS_PROFILE == TTS_PROFILE_RELIABILITY
    assert resolve_tts_profile("baseline") == TTS_PROFILE_BASELINE
    assert resolve_tts_profile(" RELIABILITY ") == TTS_PROFILE_RELIABILITY
    assert resolve_tts_profile("") == TTS_PROFILE_RELIABILITY
    assert resolve_tts_profile("bogus") == TTS_PROFILE_RELIABILITY

    assert DEFAULT_TTS_EXPRESSIVE is False
    for value in ("1", "true", " TRUE ", "yes", "on"):
        assert resolve_tts_expressive(value) is True
    for value in ("0", "false", "NO", "off", "", "maybe"):
        assert resolve_tts_expressive(value) is False


def test_assistant_requires_later_confirmation() -> None:
    instructions = Assistant(FakeFleetbase()).instructions
    assert "准备和提交绝不能发生在同一用户消息" in instructions
    assert "后续一轮明确确认" in instructions
    assert "提交失败或冲突时不得声称成功" in instructions
    assert "逐位复述" in instructions
    assert "准备和查询绝不能发生在同一用户消息" in instructions
    assert "键盘输入只是可选项" in instructions
    assert "语音重试始终有效" in instructions
    # The old two-strike keyboard fallback is gone.
    assert "连续两次" not in instructions
    assert {tool.id for tool in Assistant(FakeFleetbase()).tools} == {
        "prepare_waybill_lookup",
        "lookup_waybill",
        "list_delivery_slots",
        "prepare_reschedule",
        "commit_reschedule",
    }


@pytest.mark.asyncio
async def test_lookup_and_slots_come_from_fleetbase() -> None:
    client = FakeFleetbase()
    order = await client.lookup_waybill(" log-9113 180438-sg ")
    availability = await client.list_delivery_slots("LOG9113180438SG")
    assert order["found"] is True
    assert order["order_id"] == "order-1"
    assert availability["slots"] == [
        {
            "slot_id": "slot-1",
            "start_at": "2026-11-09T05:00:00Z",
            "end_at": "2026-11-09T07:00:00Z",
            "notes": "下午第一时段",
        }
    ]


@pytest.mark.asyncio
async def test_lookup_rejects_unrelated_order_returned_by_upstream() -> None:
    class UnfilteredFleetbase(FakeFleetbase):
        async def _request(
            self, method, path, *, internal=False, params=None, json=None
        ):
            if method == "GET" and path == "/v1/orders":
                return [self.order.copy()]
            return await super()._request(
                method, path, internal=internal, params=params, json=json
            )

    client = UnfilteredFleetbase()

    result = await client.lookup_waybill("DM012345")

    assert result == {"found": False, "waybill_number": "DM012345"}


@pytest.mark.asyncio
async def test_lookup_rejects_partial_spoken_waybill() -> None:
    result = await FakeFleetbase().lookup_waybill("1 2 3 4")

    assert result == {
        "found": False,
        "waybill_number": "1234",
        "incomplete": True,
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" log-9113 180438-sg ", "LOG9113180438SG"),
        ("ＬＯＧ－９１１３１８０４３８ＳＧ", "LOG9113180438SG"),
        ("１２３４５６７８", "12345678"),
        ("一二三四五六七八", "12345678"),
        ("幺二三四五六七八", "12345678"),
        ("零〇○一二三四五", "00012345"),
    ],
)
def test_normalize_waybill_folds_width_and_chinese_digits(raw, expected) -> None:
    assert FleetbaseClient.normalize_waybill(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        # Unit words make a dictation ambiguous; never reinterpret it.
        "一千二百三十四万五千六百七十八",
        "十二万三千四百五十六",
        "一二三四五六七八九十一",
        # Mixed ASCII and Chinese digits is likewise left alone.
        "1234五六七八",
    ],
)
def test_normalize_waybill_leaves_unit_and_mixed_numerals_alone(raw) -> None:
    assert FleetbaseClient.normalize_waybill(raw) == raw


@pytest.mark.asyncio
async def test_lookup_accepts_a_pure_chinese_digit_waybill() -> None:
    class ChineseDigitFleetbase(FakeFleetbase):
        async def _request(
            self, method, path, *, internal=False, params=None, json=None
        ):
            if method == "GET" and path == "/v1/orders":
                return (
                    self.order.copy() if params["tracking_number"] == "12345678" else []
                )
            return await super()._request(
                method, path, internal=internal, params=params, json=json
            )

    client = ChineseDigitFleetbase()
    client.order["tracking_number"]["tracking_number"] = "12345678"

    result = await client.lookup_waybill("幺二三四五六七八")

    assert result["found"] is True
    assert result["order_id"] == "order-1"


def test_prepare_waybill_reads_back_without_querying() -> None:
    state = LogisticsSessionState()

    payload = state.prepare_waybill_lookup("幺二三四 五六七八", "user-1")

    assert payload["candidate_waybill"] == "12345678"
    assert payload["digit_by_digit"] == "1 2 3 4 5 6 7 8"
    assert payload["confirmation_required"] is True
    assert state.pending_waybill == WaybillCandidate("12345678", "user-1")


def test_prepare_waybill_rejects_incomplete_number() -> None:
    state = LogisticsSessionState()

    with pytest.raises(FleetbaseConflictError, match="incomplete"):
        state.prepare_waybill_lookup("一 二 三 四", "user-1")

    assert state.pending_waybill is None
    assert MIN_WAYBILL_LENGTH == 8


def test_lookup_requires_an_earlier_prepared_candidate() -> None:
    with pytest.raises(FleetbaseConflictError, match="No waybill confirmation"):
        LogisticsSessionState().confirm_waybill_lookup("12345678", "user-1")


def test_lookup_requires_a_later_confirming_turn_and_the_same_number() -> None:
    state = LogisticsSessionState()
    state.prepare_waybill_lookup("12345678", "user-1")

    with pytest.raises(FleetbaseConflictError, match="later user turn"):
        state.confirm_waybill_lookup("12345678", "user-1")
    with pytest.raises(FleetbaseConflictError, match="does not match"):
        state.confirm_waybill_lookup("12345679", "user-2")

    confirmed = state.confirm_waybill_lookup("一 二 三 四 五 六 七 八", "user-2")
    assert confirmed == "12345678"


def test_replying_incorrect_overwrites_the_candidate() -> None:
    state = LogisticsSessionState()
    state.prepare_waybill_lookup("12345678", "user-1")
    state.confirmed_waybill = "12345678"

    payload = state.prepare_waybill_lookup("12345679", "user-2")

    assert payload["candidate_waybill"] == "12345679"
    assert state.pending_waybill == WaybillCandidate("12345679", "user-2")
    assert state.confirmed_waybill is None


def test_discarding_the_candidate_requires_a_fresh_read_back() -> None:
    state = LogisticsSessionState()
    state.prepare_waybill_lookup("12345678", "user-1")
    state.discard_waybill_candidate()

    assert state.pending_waybill is None
    with pytest.raises(FleetbaseConflictError, match="No waybill confirmation"):
        state.confirm_waybill_lookup("12345678", "user-2")


def test_slot_query_requires_an_already_confirmed_waybill() -> None:
    state = LogisticsSessionState()

    with pytest.raises(FleetbaseConflictError, match="not been confirmed"):
        state.require_confirmed_waybill("LOG9113180438SG")

    state.confirmed_waybill = "LOG9113180438SG"
    assert state.require_confirmed_waybill(" log-9113 180438-sg ") == "LOG9113180438SG"


def test_only_a_successful_lookup_authorizes_downstream_reads() -> None:
    state = LogisticsSessionState(confirmed_waybill="12345678")

    state.record_confirmed_waybill_result("12345679", {"found": False})
    assert state.confirmed_waybill is None

    state.record_confirmed_waybill_result("12345678", {"found": True})
    assert state.confirmed_waybill == "12345678"


@pytest.mark.asyncio
async def test_prepare_does_not_write_and_same_turn_commit_is_rejected() -> None:
    client = FakeFleetbase()
    state = LogisticsSessionState()
    proposal = await client.prepare_reschedule(
        state, "LOG9113180438SG", "slot-1", "user-1"
    )
    assert client.patch_calls == []
    with pytest.raises(FleetbaseConflictError, match="later user turn"):
        await client.commit_reschedule(state, proposal["proposal_id"], "user-1")
    assert client.patch_calls == []


@pytest.mark.asyncio
async def test_later_confirmation_commits_exactly_once() -> None:
    client = FakeFleetbase()
    state = LogisticsSessionState()
    proposal = await client.prepare_reschedule(
        state, "LOG9113180438SG", "slot-1", "user-1"
    )
    result = await client.commit_reschedule(state, proposal["proposal_id"], "user-2")
    assert result["committed"] is True
    assert result["scheduled_at"] == "2026-11-09T05:00:00Z"
    assert client.patch_calls == [{"scheduled_at": "2026-11-09T05:00:00Z"}]


@pytest.mark.asyncio
async def test_concurrent_order_change_blocks_commit() -> None:
    client = FakeFleetbase()
    state = LogisticsSessionState()
    proposal = await client.prepare_reschedule(
        state, "LOG9113180438SG", "slot-1", "user-1"
    )
    client.order["updated_at"] = "2026-11-08T10:30:00Z"
    with pytest.raises(FleetbaseConflictError, match="changed after review"):
        await client.commit_reschedule(state, proposal["proposal_id"], "user-2")
    assert client.patch_calls == []
