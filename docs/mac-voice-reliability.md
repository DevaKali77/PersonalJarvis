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

## Follow-up: voice app launch and Secure Input

The user's actual Gemini test heard the Calculator request but chose keyboard
computer-control actions, which were refused while Secure Input was active.
Native app launch was only exposed under a catalog alias (or discovery in a
deferred catalog). It is now declared directly as `open_app`, retained under
small model budgets, and explicitly preferred over Spotlight keystrokes for
application-launch requests. Normal supervisor gateway execution and approval
results are unchanged. A keyboard refusal is never worked around through
another input mechanism; Secure Input detection and enforcement are untouched.

The new regression failed three declaration checks before the change and
passed afterward. The focused live-session, subscription computer-control,
direct-computer and follow-up suite passed all 117 tests. On-disk changes need
the user's deliberate app quit/reopen; no automatic restart or listening was
performed. A new spoken Calculator request must confirm actual Gemini routing.

## Quit crash, Downloads and tracked ChatGPT work

The supplied macOS crash report records native AppKit termination on the main
thread while a background PySide/Shiboken import crashes during exit. Route
the native Quit delegate through the existing desktop cleanup owner, returning
NSTerminateCancel and stopping the Cocoa loop so `webview.start` returns. The
existing bounded cleanup and process-exit path retain ownership. This addresses
the observed quit-time race; it does not prove every possible crash resolved.

The supplied Downloads test passed an invented home directory to `open_app`.
Resolve `Downloads` and `~/` using the current user, refuse absent paths, and
await the system opener's bounded completion so a failed launch is not reported
as successful. A launch receipt is not proof that the window is visible. Native
voice now receives an unverified launch receipt with a fresh-screenshot step;
failed actions can never carry `verified=true`. Refresh frame IDs after launch.

`chatgpt_task` is an ask-tier, directly declared voice tool for an exact prompt
and named existing chat. It reuses the guarded single-submission transaction and
returns only after a verified completed reply or an explicit failure. The native
session's existing pending-task mechanism keeps long work tracked; `task_status`
follows it. It is task-scoped, not continuous screen or microphone recording.
An ambiguous chat, draft, foreground change, denied action, timeout or uncertain
submission must fail closed. A real named-chat delivery/readback test remains
required; do not describe this staged integration as certified.

Validation: 288 focused shutdown, launch, gateway, live-task, prompt-transaction
and safety tests passed. An isolated real Cocoa delegate test confirmed native
termination was cancelled and the cleanup owner invoked, without touching the
running app. A real Downloads launch through ToolExecutor succeeded; a separate
Finder front-window target check verified the actual user's Downloads folder.
