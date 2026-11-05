# MJON AI OS recovery audit — 2026-11-05

## Scope and baseline

This is the pre-correction audit of the real repository, not a new project.
Baseline: `feature/mjon-ai-os-native` at
`b61e9175bfc33de4f77b10ee91c8844a8de36348`. Default `main` was
`146fec095463eac56d984f1df1be3e58823c9857` when retrieved. Recovery work is
isolated on `recovery/mjon-ai-os-stability-20261105`; no merge into main is
authorized by this recovery task.

Reviewed the native distribution, its history against main, provider-related
changes, first boot, build hooks, release gates and CI logs. This is not a
line-by-line security audit of the entire inherited application.

## Evidence recovered

| Evidence | Result | What it establishes |
|---|---|---|
| [ISO run 41978693402](https://github.com/miqueas80/MJON-JARVIS-ULTIMATE/actions/runs/41978693402), source `70997acbb89b2b275f2d5fafb9b79915c2b4a533` | success | Real Debian image construction, BIOS/UEFI boot, Live account, Plasma process, stable user service, HTTP health endpoint |
| Job `127083475784`, decoded logs | BIOS and UEFI: `kernel=True, userspace=True, live_user=True, plasma=True, jarvis=True, api=True` | Boot and service evidence; no local model generation was required |
| Artifact `13393353931` | Uploaded experimental ZIP, 2,132,816,225 bytes | An artifact existed; ZIP size is not uncompressed ISO size or a verified release checksum |
| [Foundation run 42112006913](https://github.com/miqueas80/MJON-JARVIS-ULTIMATE/actions/runs/42112006913), source `b61e9175` | success | Linux/Windows native contracts, frontend/wheel/image staging; no new ISO boot |
| [Core run 42112006942](https://github.com/miqueas80/MJON-JARVIS-ULTIMATE/actions/runs/42112006942), source `b61e9175` | success | Python compilation and native unit tests |
| Local baseline: Python 3.12.14, `python -m unittest discover -s mjon_os/tests -p 'test_*.py' -v` | 112 tests passed | Simulated HTTP/streams, temporary-file and source/AST contracts, not real inference |

Neither an HTTP health endpoint nor successful model discovery establishes
that the assistant can answer or execute a tool with a real model offline.

## Findings before corrections

| Priority | Finding and evidence | Consequence / required action |
|---|---|---|
| P0 | `local_inference.OllamaClient` and `dodaios.plugins.brain.ollama.OllamaBrain` are separate implementations. Guards added in `e5f8f1a6`/`f9cdf32a` primarily protect the former. JARVIS still honors its own endpoint resolver and SDK environment proxies; automatic discovery only filters `:cloud` and `remote`, and an explicit model bypasses that filter. | Native offline policy must cover the actual brain before claiming offline safety. Preserve upstream configurable/LAN behavior outside native OS mode. |
| P0 | The tested ISO predates `1c6ac80b` (local first-boot brain defaults). Its template selects Gemini. The Center can generate locally without changing JARVIS's active brain. | Keep the new first-boot correction and guarded migration; do not describe `70997acb` as containing it. Test the configured brain path. |
| P1 | `OllamaClient.ask` accepts unknown model size under the 40% RAM budget, while `provider_health._choose_model` refuses it. It also accepts content without a completed `done` response. | Share selection rules and require completed response before ready. Bound context as well as output. |
| P1 | Center activation verifies its independent native client, then changes a config without pinning the verified endpoint/model. A successful Center test can still be followed by failure in JARVIS. | Verify through the real configured brain, report precisely what was tested, and prevent incompatible native endpoints. |
| P1 | Stream health previously succeeded on the first delta. Current draining fix catches empty/late-error streams, but needs integration coverage through the real plugin. Passive green cache invalidation is useful but does not bind evidence to model/endpoint/time. | Keep `aefc88ec`/`365f1ca1`/`de4ea11c`; extend executable tests, document remaining cache scope. |
| P1 | ISO construction intentionally bundles neither Ollama executable nor model weights. Startup preload is opt-in and cannot fix missing runtime/weights. | Add an explicit, checksummed offline payload path and an offline acceptance runner; never silently pull at login. |
| P1 | Personalized native template still inherits cloud STT/TTS defaults; wake models, voice weights and physical microphone operation are not proven. | Text inference work must not be described as complete offline voice. Preserve as a release blocker. |
| P1 | AppArmor/Bubblewrap are packages, not tested per-agent confinement. zram is compressed swap, not additional physical RAM. No actual 8 GiB desktop+model peak/latency measurements recovered. | Retain approvals and non-root runtime; require physical/security/resource acceptance. |
| P2 | README/runbook say VM validation is pending while CI already records successful boots. Release gate checks boot/API only. | Update evidence with source commit and separate boot candidate from offline AI acceptance. |

## Retain, replace or revert

- Retain Live-user/PAM and Verse packaging repairs, KDE Wi-Fi/audio packages,
  local Spanish action bridge, isolated user config, and the fork wheel build.
- Retain local brain defaults and opt-in private backup migration. `b61e9175`
  repaired the migration syntax after failed intermediate runs; do not revert
  the entire branch to an earlier, broken intermediate commit.
- Replace duplicated model-selection logic and native-brain policy gaps with
  narrow tested fixes. Do not reset history or revert all prior work.
- Withdraw any interpretation of green executable/server badges, boot proof,
  or unit-test success as proof of local offline reasoning.
- Do not publish a final ISO or auto-merge recovery into main.

## Original scope recovered and actual maturity

| Capability | Current evidence / remaining work |
|---|---|
| Debian 13 + KDE Live, BIOS/UEFI, no installer | Real VM boot evidence at `70997acb`; later corrections need a rebuilt image |
| JARVIS service, API and bundled desktop | Real process/API startup; interactive GUI actions still need physical validation |
| Local AI / model preload | Implementations and simulated tests; actual runtime/model and offline end-to-end acceptance pending at audit time |
| Agents, programming, automation | Substantial inherited Dodaios runtime plus MJON catalog; catalog detection is not tested integration of each optional engine |
| Voice and wake word | Inherited providers, cloud defaults and optional local engines; no complete offline audio acceptance |
| Vision | Inherited capability-aware providers; no demonstrated native offline vision model |
| Memory | User data directories exist; Live persistence, backups and reboot recovery not demonstrated |
| Optimization | Conservative model policy and zram baseline; no hardware performance guarantee |
| Security | User service and original approval path; actual confinement and destructive-action cancellation need acceptance |
| Offline-First | Deterministic local routes and diagnostics exist; enforce local policy on actual provider and test with Internet blocked |

## Doraimon attribution

Repository-wide search found only the prior diagnostic documentation mentioning
Doraimon, not a project, provider, endpoint or error log bearing that name.
Dodaios is the engine's actual package name. The cloud-default mismatch and
false-green mechanisms above are demonstrable defects, but they do not prove
the cause of the user's specific Doraimon incident. A redacted error and the
affected configuration/installation remain necessary for conclusive attribution.

## Acceptance required after repair

1. Reproduce policy/selection/stream failures with executable tests, then fix.
2. Exercise real Ollama weights through both the Center adapter and actual
   `OllamaBrain`, including missing model, stopped daemon and tool capability.
3. Run the real test with network isolation, not merely a loopback URL; record
   runtime version, model digest, completion, latency and limits honestly.
4. Rebuild and boot the corrected image before offering it as a new USB candidate.
5. On the Intel 8 GiB laptop test Wi-Fi, audio, voice, webcam, permissions,
   peak RAM, persistence and Windows return. No physical hardware evidence can
   be manufactured by this repository audit.
