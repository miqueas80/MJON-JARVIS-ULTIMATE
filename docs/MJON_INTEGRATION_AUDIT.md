# MJON JARVIS — Native Dodaios integration audit

## Current implementation

The fork remains based on Dodaios 4.1.2. The canonical action execution path is **Dodaios**, not a parallel subprocess dispatcher.

| Layer | Existing upstream path | MJON change |
| --- | --- | --- |
| Voice / chat request | `dodaios.brain.manager.BrainManager` | No forked speech engine |
| Local classification | `dodaios.brain.local_action_gate.match_local_action` | Delegates supported Spanish commands to `mjon_jarvis.spanish_bridge` |
| App launch | Existing `open_app` tool | Emits `LocalToolCall(name="open_app", ...)` |
| Multi-step desktop control | Existing screenshot harness | Emits `LocalActionMode.COMPUTER_USE` |
| Authorization / execution | Upstream tool executor, approval workflow and platform adapters | No new executor; upstream policies remain authoritative |
| Unknown apps | Upstream brain / computer-use path | Do not invent an executable or arbitrary shell command |
| Coding work / pull requests | Agent/worker routing | Recognize desktop vs. project actions conservatively |

## Proven checks

- Local Python unit tests of the new Spanish parser were run in a development container (7 passed).
- GitHub Actions workflow `.github/workflows/mjon-jarvis-smoke.yml` runs 7 isolated integration checks on Windows and Linux runners.
- The smoke tests exercise the **real** `match_local_action` implementation and assert that Spanish text becomes native Dodaios plans.
- A green smoke suite does not prove a microphone, visual desktop control or an installed Windows release.

## Security and operational invariants

1. The Spanish parser **never executes** a system command.
2. No arbitrary shell strings or user-supplied executable paths are added.
3. Negated or instructional phrasing does not cause deterministic app execution.
4. Multi-step instructions are not shortened to a single opening action.
5. Existing user approvals and runtime safeguards must remain in force.
6. The branch is experimental; do not merge or distribute as a finished product on smoke-test evidence alone.

## Technical debt and compatibility

The initial `mjon_jarvis/commands.py` / `windows_actions.py` implementation is a separate demonstration. It must not become the production speech-action path. It can be removed after migrating any useful tests. The upstream API and permissions are authoritative.

## Final-release gates (not yet met)

- Real Windows 11 interactive UI automation test (screenshots, input and task verification).
- Argentine Spanish STT/TTS and wake phrase validation, including offline mode.
- CPU/RAM profiling for the target 8 GB Windows machine.
- Full upstream test suite and Windows installer verification.
- Destructive-action approval, cancellation, and recovery E2E tests.
- Signed or clearly attributed release builds and rollback/uninstall instructions.

**Release status:** development only.
