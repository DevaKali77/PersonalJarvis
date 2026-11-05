# Mac voice repairs on Dodaios 4.1.2

Base: `79830721f52932c9fd804ffbf09da6f329bc0e63` (v4.1.2), not the legacy
PersonalJarvis v3.1.1 branch. Existing local Mac source fixes are retained in
a separate parent commit. No user data, credentials, models or compiled desktop
bundle are committed.

## Repairs

- Piper's sherpa-onnx callback must return **1 to continue**, **0 to stop**.
  The reversed return truncated synthesis after the first callback. The test
  engine now honors the native contract; stream cancellation also releases a
  blocked producer and bounds pending queue-reader threads.
- Browser PCM speech now retains a bounded 60-second backlog instead of silently
  losing earlier words when generation gets over ten seconds ahead of playback.
  An overload is rejected before queue mutation and ends the call with a visible
  error. Intentional interruption, mute and cancellation still clear playback.
- A browser disconnect before the final hangup receipt no longer turns normal
  cleanup into a failed voice session. Other errors still propagate.
- The desktop starts with input muted. The visible microphone control enables
  listening deliberately; OS microphone permission remains a separate gate.
- The existing ChatGPT prompt transaction now sends typing and Enter through
  `ToolExecutor`, preserving approval, target-window and cancellation checks.
  Mutations are never retried after an uncertain result.

## Installation details

Rebuild the frontend with `npm ci --ignore-scripts` and `npm run build` from
`dodaios/ui/web/frontend`; deploy the resulting `dodaios/ui/web/dist` locally.
The generated bundle must not be committed. Close/reopen via the desktop's
normal user controls. Do not reset, pull or reinstall over existing live edits.

The retained Mac microphone bridge needs its local binary built from source:

```sh
clang -dynamiclib -fobjc-arc -framework Foundation \
  dodaios/ui/microphone_decision.m -o dodaios/ui/microphone_decision.dylib
```

This bridge only reuses an existing OS grant for the exact installed app's
loopback origin and main-frame, microphone-only request. It never grants camera,
other-origin or subframe access. Failure retains the system permission prompt.

Check the global `safety.approval_mode` explicitly. This version inherits
`bypass` when absent; use `ask` for consequential-action confirmation. Do not
weaken the self-mod forbidden-path protections to change it. A reviewed manual
config edit must preserve the complete TOML and retain a rollback copy.

Gemini Live voice is independently selected from the conversational brain.
`brain.policy.local_only` in the retained local patch limits that brain's
fallback chain; it is not an application-wide guarantee against cloud use.
Gemini voice, tool models and dictation polish require their own consent and
configuration checks. No cloud call is needed for the offline smoke tests.

## Validation

- 173 focused Python voice, realtime factory, computer-use and player tests.
- 153 safety, prompt-transaction and microphone-refusal tests.
- 89 Ollama and tool-model routing tests.
- 94 frontend audio, mute, startup, jitter and playback timeline tests.
- TypeScript compilation and production frontend build succeeded.
- Real native Piper callback comparison: truncated 1.440 s versus complete
  4.423 s for a fixed three-sentence sample.
- Real Piper → Nemotron round trip retained all three sentences.
- Native Mac speaker playback completed with no underflow warning in one run.
- Local Ollama selected `open_app`; `ToolExecutor` opened Calculator and a
  separate process check confirmed it running.
- An inert ask-tier probe was refused without an approval channel under Ask
  mode. No protected effect ran.

These tests do not certify acoustic microphone recognition, Gemini duplex
behavior in the user's room, long-session stability, or submission to an actual
ChatGPT chat. Those require a deliberate user voice test and explicit target.
Codex CLI subscription voice also remains incompatible with the installed
adapter's strict supported-version check; do not bypass that check or downgrade
an unrelated working Codex installation as part of these repairs.
