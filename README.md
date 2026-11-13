<a href="https://livekit.io/">
  <img src="./.github/assets/livekit-mark.png" alt="LiveKit logo" width="100" height="100">
</a>

# LiveKit Agents starter for Python

A starter project for building voice AI apps with [LiveKit Agents for Python](https://github.com/livekit/agents) and [LiveKit Cloud](https://cloud.livekit.io/).

The starter includes:

- A simple [voice AI assistant](https://docs.livekit.io/agents/start/voice-ai/) to extend and customize.
- A voice pipeline built on [LiveKit Inference](https://docs.livekit.io/agents/models/inference/), which gives you access to [models](https://docs.livekit.io/agents/models/) from top labs with no extra configuration:
  - The default LLM is Gemma 4 31B, an open-weight model [hosted by LiveKit](https://docs.livekit.io/agents/models/llm/livekit/) and tuned for voice AI.
  - The default TTS is [Cartesia Sonic 3.5](https://docs.livekit.io/agents/models/tts/cartesia/), a low-latency streaming voice; Sonic 3 and Sonic 3.6 stay available as env-only A/B options, and [Fish Audio S2.1 Pro](https://docs.livekit.io/agents/models/tts/fishaudio/) as the rollback.
  - More than 50 other models are available from OpenAI, Cartesia, Deepgram, and other providers.
  - [Realtime models](https://docs.livekit.io/agents/models/realtime/) such as OpenAI GPT-Live. Many other models are available through the [plugin ecosystem](https://docs.livekit.io/agents/models/#plugins).
- [Expressive mode](https://docs.livekit.io/agents/models/tts/expressive/) support, disabled by default in this project so the agent's voice carries no model-inserted emotion or `<break>` markup; see [TTS configuration and rollback](#tts-configuration-and-rollback).
- [Keyterms](https://docs.livekit.io/agents/models/stt/keyterms/), on by default, so speech recognition gets your names, brands, and jargon right, including names it picks up during the conversation, like a caller's.
- Provider-aware turn handling: the default AssemblyAI STT supplies its own end-of-turn signal (`turn_detection="stt"` with no added endpointing delay), while the [LiveKit Turn Detector](https://docs.livekit.io/agents/logic/turns/turn-detector/) is retained for the Deepgram rollback and other models.
- [Adaptive interruption handling](https://docs.livekit.io/agents/logic/turns/adaptive-interruption-handling/) is supported by the installed SDK, but is not yet explicitly enabled for the local Console path; the next tuning round will compare intentional barge-ins with backchannels and background noise.
- [Background voice cancellation](https://docs.livekit.io/transport/media/noise-cancellation/).
- Session transcripts, traces, and recordings from LiveKit [Agent Observability](https://docs.livekit.io/testing/observability/).
- [Simulations](https://docs.livekit.io/testing/simulations/) that test full conversations with your agent, run in CI on every merge to `main`.
- A `Dockerfile` for [deploying to LiveKit Cloud](https://docs.livekit.io/deploy/agents/).

The starter works with any [custom web or mobile frontend](https://docs.livekit.io/frontends/) or with [telephony](https://docs.livekit.io/telephony/).

## Project case study

For a detailed Chinese engineering retrospective—including the production-style failure modes, safety design, A/B evidence, verification boundaries, resume-ready bullet points, and interview talking points—see [中文物流语音客服：问题、方案与工程复盘](docs/PROJECT_CASE_STUDY_ZH.md).

## Using coding agents

This project works with coding agents like [Claude Code](https://claude.com/product/claude-code), [Cursor](https://www.cursor.com/), and [Codex](https://openai.com/codex/).

LiveKit offers both a CLI and an [MCP server](https://docs.livekit.io/reference/developer-tools/docs-mcp/) for browsing and searching its documentation. Search returns short excerpts, so fetch the full page to read the details:

```console
lk docs search "testing my agent"
lk docs get-page /testing/unit-tests
```

The project also includes an [`AGENTS.md`](AGENTS.md) file, so your coding agent follows LiveKit's best practices for workflows, handoffs, and testing, and tries its changes with the [agent debugger](https://docs.livekit.io/testing/debugger/).

For more guidance at each stage of the work, from building and debugging to testing and deploying, install LiveKit's [agent skills](https://docs.livekit.io/intro/coding-agents/#agent-skills). The CLI installs them for the coding agents on your machine and adds the Docs MCP server to their config. `lk agent init` offers to do this when it creates your project, or you can run it yourself:

```console
lk skills install
```

Run `lk skills update` to get the latest skills, and commit `skills-lock.json` along with them. See the [coding agents guide](https://docs.livekit.io/intro/coding-agents/) for more details.

## Dev setup

Install the [LiveKit CLI](https://docs.livekit.io/intro/basics/cli/), version 2.18.8 or later:

- **macOS:** `brew install livekit-cli`
- **Linux:** `curl -sSL https://get.livekit.io/cli | bash`
- **Windows:** `winget install LiveKit.LiveKitCLI`

Check your version with `lk --version`. To update an existing install, see [Update the CLI](https://docs.livekit.io/reference/developer-tools/livekit-cli/#updates).

Then create a project from this template. The CLI clones the template and configures your environment:

```console
lk cloud auth
lk agent init my-agent --template agent-starter-python
```

<details>
<summary>Set up the project manually</summary>

Clone the repository and install dependencies into a virtual environment with [uv](https://docs.astral.sh/uv/):

```console
git clone https://github.com/livekit-examples/agent-starter-python.git
cd agent-starter-python
uv sync
```

Sign up for [LiveKit Cloud](https://cloud.livekit.io/), then copy `.env.example` to `.env.local` and fill it in. To have the CLI write your project's URL and API keys into the file instead, run:

```console
lk cloud auth
lk app env --write --destination .env.local
```

</details>

## Run the agent

The `lk agent console`, `lk agent dev`, and `lk agent debugger` commands run your agent on your own machine. To talk to it in your terminal:

```console
lk agent console
```

To connect it to LiveKit Cloud so a frontend, a phone call, or the [Agent Console](https://docs.livekit.io/testing/agent-console/) can reach it:

```console
lk agent dev
```

To let a coding agent or a script test it one text turn at a time, use the [agent debugger](https://docs.livekit.io/testing/debugger/). Each turn prints the agent's reply along with the tool calls and handoffs behind it:

```console
lk agent debugger start
lk agent debugger say "Hi, what can you do?"
lk agent debugger stop
```

### Test without a physical microphone

The project has two supported microphone-free paths:

```console
# Fast turn-by-turn logic checks; skips STT and TTS.
lk agent debugger start
lk agent debugger say "你好，我想查询运单状态。"
lk agent debugger stop

# Release-candidate audio smoke test; exercises STT, turn detection, tools, and TTS.
lk agent simulate audio --scenarios scenarios.audio.yaml --concurrency 1 --yes
```

The audio scenario uses only the unmistakably synthetic numeric waybill `12345678`.
It may be sent to LiveKit Cloud for simulation; do not replace it with customer data.
For the cheaper full behavior regression, run:

```console
lk agent simulate text --scenarios scenarios.yaml --concurrency 1 --yes
```

Validated on 2026-11-07, before the STT/TTS tuning documented below: 8 local
tests passed, the audio smoke test passed 1/1 (`SR_hudV2gQ6NfY5`), and the full
text suite passed 4/4 (`SR_UAzNgTjgZcSK`). The test suite has grown since; rerun
it rather than relying on that count.

In production, run the agent directly:

```console
uv run src/agent.py start
```

## Chinese STT configuration

Mandarin is transcribed through LiveKit Inference with **AssemblyAI
Universal-3.6 Pro** (`assemblyai/universal-3-6-pro`) and its accuracy profile.
`src/agent.py` builds the STT call from one pure function,
`stt_inference_kwargs()`; provider-specific options are gated by model prefix,
so AssemblyAI options are never sent to Deepgram and vice versa. Deepgram Nova-3
stays available as an env-only rollback/A-B option.

### Default: AssemblyAI Universal-3.6 Pro

The language switches to `zh` automatically, because that is AssemblyAI's code
for Mandarin. With the default `accuracy` profile it sends these
AssemblyAI-only options:

| Option | Value | Why |
|--------|-------|-----|
| `mode` | `max_accuracy` | Accuracy preset for Chinese contact-centre speech. |
| `prompt` | short Chinese logistics prompt | Domain context: waybill numbers, parcel status, delivery slots, rescheduling, and Latin letters or digits spoken one character at a time. |
| `keyterms_prompt` | same list as `STT_KEYTERMS` | One source of truth; the Inference SDK also merges `STTContextOptions.keyterms` into the same field. |
| `min_turn_silence` | 500 ms | A short mid-sentence pause, for example while spelling a waybill number, does not end the turn. |
| `max_turn_silence` | 1500 ms | Gives slowly dictated waybills room for short pauses without imposing a three-second forced-finalisation wait. |
| `continuous_partials` | `true` | Publishes interim hypotheses as they are revised, so the console or frontend shows partial text while the user is still speaking. |
| `interruption_delay` | 250 ms | Documented 0–1000 ms knob that allows an earlier first partial. 250 ms is a conservative start, not a tuned value. |

`voice_focus` is intentionally not set: RoomIO already applies AI acoustics
enhancement, and the microphone type is unknown. The two turn-silence values are
conservative starting points for A/B testing, not tuned values.

**Observed A/B evidence (2026-11-12):** on the same synthesized 8-digit waybill
samples, AssemblyAI produced a complete transcription for 3/3 samples and
Deepgram Nova-3 for 2/3. One AssemblyAI sample arrived in two transcript
segments, but the segments were combined correctly before the Fleetbase lookup,
so the split did not cause a miss. This is a small, synthesized run, not a
statistical proof; it is the reason the accuracy profile is the default again,
with Deepgram kept as a rollback for further comparison.

AssemblyAI notes: the installed `livekit-agents` 1.8.10 type hints mark `prompt`
as mutually exclusive with `keyterms_prompt`, while current Inference docs list
both. If a live session reports a gateway error for the combination, drop
`prompt` from `assemblyai_extra_kwargs` and keep `keyterms_prompt`.

The same 1.8.10 type stubs do not list `min_turn_silence`, `continuous_partials`
or `interruption_delay`; `extra_kwargs` is forwarded to the gateway as a plain
dict, so acceptance is decided server-side. If a live session fails at start with
an unknown-option error, remove only the rejected key(s) from
`assemblyai_extra_kwargs` and restart — the other accuracy options are
independent.

### Turn handling follows the STT provider

`src/agent.py` builds `TurnHandlingOptions` from one testable helper,
`turn_handling_options()`, which switches on the configured STT model:

| STT model | `turn_detection` | `endpointing.min_delay` | Why |
|-----------|------------------|-------------------------|-----|
| AssemblyAI Universal-3.6 Pro (default) | `"stt"` | `0` seconds | AssemblyAI already emits its own end-of-turn signal from the transcript it returns. STT turn detection lets that signal commit the turn, and a zero minimum delay stops LiveKit from adding a second wait on top of the provider's endpointing. |
| Deepgram Nova-3 rollback and other providers | `inference.TurnDetector()` | Session default (0.3 s for the streaming detector) | Preserves the previous LiveKit turn-detector behavior exactly. |

With `turn_detection="stt"`, LiveKit does not run the turn-detector model; it
commits the user turn when the STT reports `END_OF_SPEECH`. The AssemblyAI
`min_turn_silence` (500 ms) and `max_turn_silence` (1500 ms) options are
unchanged: they still decide when the provider finalises a transcript and emits
that end-of-turn event. Note the units differ — `endpointing.min_delay` is in
seconds, while the AssemblyAI silence options are in milliseconds.

Text simulations commit turns as text, so this setting only affects audio
sessions.

Unit tests pin the provider-to-mode selection. In a local audio-debugger A/B
with the same three synthesized, deliberately paused 8-digit waybill turns,
both configurations transcribed 3/3 completely. Provider-aware handling removed
the LiveKit EOT prediction and 2.5-second dynamic endpointing path, emitted no
late-transcript warning, and reduced observed end-to-end latency from roughly
3.05–4.50 seconds to 2.03–2.62 seconds. This is synthetic evidence; a real
microphone remains the final acceptance test.

### Rollback / A-B: Deepgram Nova-3

`LOGISTICS_STT_MODEL=deepgram/nova-3-general` switches to the mainstream LiveKit
voice-agent path: it streams interim and final results, supports `zh-CN`, and
needs no extra plugin or API key through Inference. The language switches to
`zh-CN` automatically.

| Option | Value | Why |
|--------|-------|-----|
| `language` | `zh-CN` | BCP-47 Mandarin locale for Nova-3. |
| `interim_results` | `true` | Streams interim hypotheses so the console or frontend shows text while the user is still speaking. |
| `no_delay` | `false` | Lets Smart Format wait for a spoken number to finish; Deepgram warns that forcing immediate finalization can skip entity formatting. |
| `smart_format` | `true` | Formats dates, times, numbers and similar entities for readability. |
| `numerals` | `true` | Renders spoken numbers as digits, which matters for waybill digits. |
| `punctuate` | `true` | Adds punctuation to transcripts. |
| `endpointing` | 800 ms | Silence before a final. Interim text still streams immediately, while the longer finalisation window avoids splitting slowly dictated waybill digits into separate tool calls. |
| `keyterm` | same list as `STT_KEYTERMS` | Biases logistics terms and the example waybill; the Inference SDK merges `STTContextOptions.keyterms` into the same field. |

Every provider option above except `language` exists in the installed
`livekit-agents` 1.8.10 `DeepgramOptions` type (`language` is an `inference.STT`
argument), so this profile carries no unknown-option risk. The model ID and
`zh-CN` support were checked against current LiveKit docs; the same 1.8.10 model
literal still lists only `deepgram/nova-3`. If the gateway rejects the model ID
at session start, set `LOGISTICS_STT_MODEL=deepgram/nova-3` — no code edit
needed.

These options change how transcripts are surfaced, not how LiveKit Inference
retries a provider WebSocket. A reset or retry still costs the reconnect time
and any audio the provider did not accept, so a single slow turn (the observed
11.2 s case) is not fixed by partial transcripts.

`LOGISTICS_STT_PROFILE=baseline` sends no provider extras at all: whichever
model is selected falls back to its provider's own defaults. It does not change
the model or the language.

### A/B without code edits

Everything below is read when the process starts, so restart the agent after
changing a variable. Windows PowerShell:

```powershell
# Default: AssemblyAI Universal-3.6 Pro with the accuracy profile above.
lk agent console

# Rollback / A-B to Deepgram Nova-3; no code edit.
$env:LOGISTICS_STT_MODEL = "deepgram/nova-3-general"
lk agent console

# Back to the default AssemblyAI model.
Remove-Item Env:\LOGISTICS_STT_MODEL
lk agent console

# Provider defaults for whichever model is selected (no extra_kwargs).
$env:LOGISTICS_STT_PROFILE = "baseline"
lk agent console
Remove-Item Env:\LOGISTICS_STT_PROFILE

# Let LiveKit choose the provider for Chinese; no provider extras are sent.
$env:LOGISTICS_STT_MODEL = "auto:zh"
lk agent console
```

A value set in `.env.local` also applies; `load_dotenv` does not override a
variable already set in the process environment, so a shell value wins.

### How to compare

Record one fixed set of 5–10 real-microphone utterances per model, including a
waybill number read digit by digit, a delivery-slot question, and a rescheduling
request. Run the same recordings against AssemblyAI and the Deepgram rollback,
then compare the Agent Console transcripts and note missed words, wrong digits
and premature fragments. **The 2026-11-12 result above comes from a small
synthesized sample and does not prove real-microphone accuracy**; keep using the
Deepgram rollback until a longer real-speaker comparison confirms the default.

## TTS configuration and rollback

The default voice pipeline uses **Cartesia Sonic 3.5** (`cartesia/sonic-3.5`)
through LiveKit Inference with `language="zh"` and Cartesia's official plugin
default voice `f786b574-daa5-4673-aa0c-cbe3e8534c02`. Sonic 3.5 is a streaming,
low-latency voice-agent model available through the gateway, and needs no
provider key or plugin. Sonic 3 (`cartesia/sonic-3`) and Sonic 3.6
(`cartesia/sonic-3.6`) remain available as env-only A/B options, and Fish Audio
S2.1 Pro (`fishaudio/s2.1-pro`) as the rollback, all with the same voice,
language and reliability settings.

`src/agent.py` builds the TTS call from one pure function,
`tts_inference_kwargs()`; provider-specific extras are gated by model prefix, so
Cartesia options are never sent to Fish Audio and vice versa. The voice is also
provider-aware (`resolve_tts_voice()`): it follows the selected model, and
`LOGISTICS_TTS_VOICE` overrides it for either provider.

### Default: Cartesia Sonic 3.5

| Option | Value | Why |
|--------|-------|-----|
| `language` | `zh` | Mandarin for Sonic's multilingual mode. |
| `voice` | `f786b574-daa5-4673-aa0c-cbe3e8534c02` | Cartesia's official plugin default voice, available through Inference. |
| `speed` | 1.0 | Natural speaking rate. |
| `volume` | 1.0 | Neutral level; loudness is handled downstream. |
| `max_buffer_delay_ms` | 300 ms | Caps how long Cartesia may buffer text before generating audio. Lower values cut latency at the cost of prosody context; 300 ms is an A/B starting point, not a tuned value. |

`emotion` and the timestamp options are deliberately not sent: expressive
markup stays off, and the model must not be encouraged to emit emotion tags.
All three keys exist in the installed `livekit-agents` 1.8.10 `CartesiaOptions`
type, and `cartesia/sonic-3.5` is in the installed 1.8.10 `inference.TTS` model
literal (as are `cartesia/sonic-3` and `cartesia/sonic-3-latest`), so the
default carries no unknown-model or unknown-option risk. `cartesia/sonic-3.6`
is **not** in that literal; it comes from current LiveKit docs and is kept as
an env-only A/B option. If the gateway rejects it at session start, remove
`LOGISTICS_TTS_MODEL` to return to the default, or use `cartesia/sonic-3` or
`cartesia/sonic-3.5`, both of which are in the literal — no code edit is
needed either way.

**Observed live evidence (2026-11-12):** in separate local runs, Sonic 3.5 was
the only Cartesia model that completed normally across consecutive turns — it
returned to listening and produced complete Chinese assistant speech with
observed TTS time-to-first-byte around 0.43–1.02 seconds. Its protective `flush
audio emitter due to slow audio generation` lines varied from one to many
without truncating those turns. Sonic 3 had a lower TTFB but stayed stuck in the
speaking state beyond 30 seconds and emitted no final assistant conversation
item in that run. These are single-run observations under the same local
conditions, not a statistical comparison or a real-speaker A/B; they are the
reason for choosing Sonic 3.5 as the default, not proof that it is generally
more reliable.

### What the `flush audio emitter` line means

`flush audio emitter due to slow audio generation` is a **debug-level** log
line from the LiveKit TTS emitter. When synthesis falls behind real-time
playback, the emitter releases the audio it has already buffered so the
downstream player does not underrun and stutter. It is a protective buffer
release, not an API error, and no server-side fallback triggers on it: it does
not cause LiveKit Inference or the gateway to switch models. Repeated
occurrences are the symptom to watch, because they mean generation is
consistently slower than playback; a single occurrence on one reply is not by
itself a failure.

### Rollback / A-B: Fish Audio

`LOGISTICS_TTS_MODEL=fishaudio/s2.1-pro` restores Fish Audio and, because the
voice is provider-aware, the previous Fish voice
`fa4c9eb3dccc4806b382b40d61c6b10a` and the `reliability` extras, with no code
edit:

| Option | Value | Why |
|--------|-------|-----|
| `expressive` (session) | off | Removes the markup guide from the LLM prompt, so the model stops inserting emotion, `<break>` and non-verbal tags. Those tags were the audible source of unnatural pauses and glitches. |
| `latency` | `balanced` | Provider default streaming mode. `low` trades generation quality for speed and could worsen artifacts, so it is not used. |
| `temperature` | 0.6 | Lower sampling variance than the provider default; repeats of the same sentence sound more consistent. |
| `top_p` | 0.7 | Together with temperature, keeps sampling away from unlikely token paths. |
| `normalize` | `true` | Normalises numbers, dates and abbreviations before synthesis. |
| `normalize_loudness` | `true` | Consistent output loudness (S2-Pro family). |
| `speed` | 1.0 | Natural speaking rate. 1.05 is the documented upper bound if replies need to finish sooner; the value is not changed without an A/B. |

`chunk_length` and `min_chunk_length` are deliberately left at provider
defaults: there is no official guidance tying them to these artifacts, and
changing chunk boundaries would confound the comparison.

`LOGISTICS_TTS_PROFILE=reliability` (default) sends the table for the selected
provider; `LOGISTICS_TTS_PROFILE=baseline` sends only model, voice and
language. It does not change expressive mode; that needs
`LOGISTICS_TTS_EXPRESSIVE` as well. All variables are read at process start, so
restart the agent after changing one.

### A/B and rollback without code edits (PowerShell)

```powershell
# Default: Cartesia Sonic 3.5 with the settings above.
lk agent console

# A/B the other Cartesia models; voice and extras stay identical.
$env:LOGISTICS_TTS_MODEL = "cartesia/sonic-3"
lk agent console

$env:LOGISTICS_TTS_MODEL = "cartesia/sonic-3.6"
lk agent console

# Roll back to Fish Audio; voice and extras switch automatically.
$env:LOGISTICS_TTS_MODEL = "fishaudio/s2.1-pro"
lk agent console

# Back to the Cartesia Sonic 3.5 default.
Remove-Item Env:\LOGISTICS_TTS_MODEL
lk agent console

# Try a different voice for the selected provider (it must belong to it).
$env:LOGISTICS_TTS_VOICE = "<voice-id>"
lk agent console
Remove-Item Env:\LOGISTICS_TTS_VOICE

# Provider defaults only, for whichever model is selected.
$env:LOGISTICS_TTS_PROFILE = "baseline"
lk agent console
Remove-Item Env:\LOGISTICS_TTS_PROFILE

# Expressive markup back on (Fish Audio) for a same-utterance A/B.
$env:LOGISTICS_TTS_EXPRESSIVE = "1"
lk agent console
Remove-Item Env:\LOGISTICS_TTS_EXPRESSIVE
```

`LOGISTICS_TTS_EXPRESSIVE` accepts `1/true/yes/on` and `0/false/no/off`
(case-insensitive); an unset or unrecognised value stays off, and a typo logs a
warning instead of silently re-enabling markup.

### What is and is not verified

Unit tests pin the configuration plumbing only. **Cartesia's Chinese
naturalness, the default voice's Mandarin pronunciation, and any broad
improvement in audio artifacts are unverified** — the live evidence above is a
small local comparison where Sonic 3.5 completed consecutive turns and Sonic 3
stalled once, but that is not a real-speaker A/B. Record the same 5–10
utterances (including a waybill read digit by digit), synthesize them through
Sonic 3.5, the Sonic 3 and Sonic 3.6 A/B options and the Fish Audio rollback,
and compare pronunciation, pauses, completion behaviour and artifacts. If the
default voice sounds accented or unsuitable for Mandarin, point
`LOGISTICS_TTS_VOICE` at a Cartesia multilingual or Chinese voice; no code edit
is needed.

If Sonic 3.5 ever shows the same stuck-speaking behaviour, switch with
`LOGISTICS_TTS_MODEL` to another Cartesia model or Fish Audio and compare
`lk agent logs`. Repeated `flush audio emitter` lines after a model switch
point at synthesis running behind playback (provider load or network) rather
than configuration.

## Frontends and telephony

### Waybill confirmation and typed input

Every waybill is confirmed before it is looked up. `prepare_waybill_lookup()`
normalizes the number, stores it with the id of the latest committed user
message (the same anchor the reschedule flow uses), and returns a read-back
payload; it never queries Fleetbase. The agent must read the candidate back
digit by digit and ask whether it is correct.
`lookup_waybill()` then refuses to run unless the same normalized candidate was
prepared in an **earlier** user message, so a lookup can never happen in the
turn that supplied the number. Saying the number is wrong, or dictating a new
one, simply prepares again and overwrites the candidate. A lookup clears the
candidate, so retrying always goes through one fresh read-back.
`list_delivery_slots()` is guarded the same way: it reads the order endpoint
internally, so it refuses any number that was not confirmed **and** found by a
successful lookup. Preparing a new number clears that authorization, so one
order can never unlock a slot query for another.

Validation stays exact. `FleetbaseClient.normalize_waybill()` applies NFKC
full-width folding, then strips whitespace and hyphens and uppercases the
result. A value made up only of Chinese digit characters
(`零〇○一二三四五六七八九幺`) is converted one character at a time, so
`幺二三四五六七八` becomes `12345678`. Values that mix Chinese digits with unit
words such as `十`, `百`, `千` or `万` are left untouched and fail the exact
match, because a unit reading is ambiguous; there is no fuzzy or
nearest-number matching anywhere in the path. Numbers shorter than eight
characters are rejected as incomplete before any request is made.

Typed input remains available but is only ever a suggestion. LiveKit
`AgentSession` accepts typed messages through the `lk.chat` text stream, and
the official Agent Embed Widget can expose that channel as a chat pane; enable
**Text chat** on the agent's **Embed → Settings** page in LiveKit Cloud. When a
number is incomplete or not found, the agent may offer the chat input as one
option, but it must keep accepting a repeated voice dictation: there is no
failure counter that forces the keyboard.

Official setup: [Agent Embed Widget](https://docs.livekit.io/agents/start/embed/)
and [text input](https://docs.livekit.io/agents/multimodality/text/).

Pair the agent with a prebuilt frontend starter, or add telephony:

| Platform | Link | Description |
|----------|----------|-------------|
| **Web** | [`livekit-examples/agent-starter-react`](https://github.com/livekit-examples/agent-starter-react) | Web voice AI assistant with React & Next.js |
| **iOS/macOS** | [`livekit-examples/agent-starter-swift`](https://github.com/livekit-examples/agent-starter-swift) | Native iOS, macOS, and visionOS voice AI assistant |
| **Flutter** | [`livekit-examples/agent-starter-flutter`](https://github.com/livekit-examples/agent-starter-flutter) | Cross-platform voice AI assistant app |
| **React Native** | [`livekit-examples/voice-assistant-react-native`](https://github.com/livekit-examples/voice-assistant-react-native) | Native mobile app with React Native & Expo |
| **Android** | [`livekit-examples/agent-starter-android`](https://github.com/livekit-examples/agent-starter-android) | Native Android app with Kotlin & Jetpack Compose |
| **Web Embed** | [`livekit-examples/agent-starter-embed`](https://github.com/livekit-examples/agent-starter-embed) | Voice AI widget for any website |
| **Telephony** | [Documentation](https://docs.livekit.io/telephony/) | Add inbound or outbound calling to your agent |

For more options, see the [frontend guide](https://docs.livekit.io/frontends/).

## Testing and debugging

Simulations run full multi-turn conversations between a simulated user and your agent on LiveKit Cloud, then judge each transcript. The scenarios live in [`scenarios.yaml`](scenarios.yaml). Run them locally with the CLI:

```console
lk agent simulate text --scenarios scenarios.yaml
```

The `Simulations` workflow in [`.github/workflows/simulations.yml`](.github/workflows/simulations.yml) runs the same file on every merge to `main`, and on demand from the Actions tab. It doesn't run on every pull request push because each run uses real inference. See the [simulations guide](https://docs.livekit.io/testing/simulations/) for how to write scenarios and read results.

To check a change turn by turn without a live session, use the [agent debugger](https://docs.livekit.io/testing/debugger/) shown in [Run the agent](#run-the-agent).

To debug a running agent, open it in the [Agent Console](https://docs.livekit.io/testing/agent-console/). It shows events, tool calls, and model timing as you talk to the agent. To stream logs from a deployed agent, run `lk agent logs`.

## Using this template for your own project

After you create your own project from this template:

- **Commit `uv.lock`.** The template doesn't track it, but your project should, for reproducible builds. If you deploy to LiveKit Cloud, commit `livekit.toml` too.
- **Add repository secrets.** Add `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` as [repository secrets](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/using-secrets-in-github-actions) so the simulations can run in CI.

## Deploying to production

To deploy the agent to LiveKit Cloud or another environment with the included `Dockerfile`, see the [deployment guide](https://docs.livekit.io/deploy/agents/).

## Self-hosted LiveKit

You can self-host LiveKit instead of using LiveKit Cloud. See the [self-hosting guide](https://docs.livekit.io/transport/self-hosting/local/). If you self-host, use [model plugins](https://docs.livekit.io/agents/models/#plugins) instead of LiveKit Inference, and remove the [LiveKit Cloud noise cancellation](https://docs.livekit.io/transport/media/noise-cancellation/) plugin.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
