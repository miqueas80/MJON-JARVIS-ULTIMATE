# MJON AI OS recovery: verification results

Read the [pre-correction audit](MJON_RECOVERY_AUDIT_2026-11-05.md) first.
Initial implementation snapshot: `ba1d39c12f6b18c0f8772f47a35b063ac2420324`.
Follow-up corrections in the same PR cover typed configuration and actual
manager/background fallback chains; consult the tested source hashes in the
latest real-model evidence.
The work remains on a recovery branch targeting the Linux feature branch,
with no changes to main and no final ISO publication.

## Verified repairs

- The actual native `OllamaBrain` now checks loopback routing, refuses cloud
  references and remote metadata, ignores environment proxies, and applies
  the same known-weight-size RAM filter as the Center adapter. The inherited
  application keeps its configurable LAN behavior outside native OS mode.
- Native CPU context is explicitly bounded to 2048 tokens and four threads.
  Oversized context requests fail explicitly; this profile does not promise
  to fit every inherited agent's system prompt or long conversation.
- The typed fallback key is `local_fallback`, not the legacy sample's
  `fallback`. Native first boot and opt-in repair set the actual fallback to
  Ollama, cap reply output at 256 tokens, and disable the optional flash/ack
  model when it was never configured. The actual manager and background
  resolver cannot append cloud families while the native primary is Ollama.
- A nonstream response must be completed (`done: true`) and contain text.
  Downloaded or merely loaded weights remain unverified.
- GUI and CLI migration verify the actual configured Ollama brain in a
  separate process before changing an eligible legacy Gemini profile. The
  private backup and refusal to replace customized providers are retained.
- Historical green evidence is invalidated when its endpoint, role/model
  configuration or primary brain changes. It remains historical proof at the
  displayed check time, not continuous monitoring of every request.
- The inherited 30-minute autostart cannot bypass MJON's opt-in preload service
  in native mode. The base image starts no optional inference engine.
- An explicit offline image payload can include reviewed Ollama CPU binaries,
  licenses and model blobs, all hashed. Writable per-user manifests link to
  immutable image weights instead of copying gigabytes into Live RAM.
  A failed bundled engine leaves the desktop available for diagnosis.

## Reproducible automated tests (simulated inputs)

| Command / environment | Result | Meaning |
|---|---|---|
| `python -m unittest discover -s mjon_os/tests -p 'test_*.py' -v`, runtime dependencies installed | 133 passed | File, configuration, source, transport and stream regressions; not model inference |
| Same native suite with the minimal host Python | 121 passed, 12 explicitly skipped | SDK-dependent tests are not silently counted as executed |
| Focused inherited pytest suites: Ollama, agent recovery, profiles, health checker, monitor, autostart, background/voice-key fallback chains | 174 passed | Existing non-native behavior and new shared behavior remain covered |
| Recovery regressions copied onto untouched `b61e9175` | See `regressions-before.txt` | Demonstrates failures before repair; never interpreted as passing tests |
| `compileall`, `sh -n` for native launch/VM scripts, workflow YAML parsing, `git diff --check` | passed | Syntax and formatting only |

Logs are in [evidence/mjon-recovery-2026-11-05](evidence/mjon-recovery-2026-11-05).
Expanded resolver tests need the fork installed (`pip install --no-deps -e .`)
so its provider entry points exist. The first source-only run had nine failures
in those metadata-dependent tests; after installation the same expanded set
passed all 174 tests. Both logs are preserved.

The inherited pytest invocation was:

```sh
python -m pytest \
  tests/unit/plugins/brain/test_ollama.py \
  tests/unit/plugins/brain/test_ollama_agent_recovery.py \
  tests/unit/brain/test_ollama_profiles.py \
  tests/unit/brain/test_healthcheck_request_compatibility.py \
  tests/unit/brain/test_healthcheck_off_loop.py \
  tests/unit/local_models/test_health_monitor.py \
  tests/unit/local_models/test_autostart.py \
  tests/unit/brain/test_resolver_quality_chain.py \
  tests/unit/brain/test_resolver_local_tail.py \
  tests/unit/brain/test_frontier_resolver.py \
  tests/unit/brain/test_manager_voice_key_chain.py -q
```

## Real offline inference, separate from the tests above

The runtime was downloaded from the official Ollama release `v0.40.14`.
Archive SHA256:
`993e83d08c3d13d17c55009a3e2664c8a25445e644aec3a68bef5abb6abce67d`.
Executed binary SHA256:
`4a525117528467da41be4188ef8efbc3dbbca9da420fb25cd61cf49d104732fd`.
The model was downloaded before isolation; acceptance performs no downloads.

`scripts/mjon_offline_acceptance.py` launches a new Linux user/network
namespace with only loopback, verifies that an external connect fails with
`ENETUNREACH`, runs Ollama with cloud disabled, and deliberately poisons the
client's HTTP proxy variables. The tests use real HTTP, the actual OpenAI SDK,
the production Ollama brain, and real quantized weights; no fake provider or
patched model output is involved.

| Run | Results and limitations |
|---|---|
| Qwen3 `0.6b`, Q4_K_M | Inference/restart plumbing passed, but it answered two plus two as seven. Rejected as the proposed payload. Its original JSON's `passed: true` only reflected the earlier infrastructure criteria; it is explicitly **not** a model-quality acceptance. |
| Qwen3 `1.7b`, Q4_K_M | Real adapter and configured brain completed responses offline; arithmetic smoke check passed. Model manifest digest `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`; reported weights 1,359,293,444 bytes. |
| Bundled runtime + initialized Live-style model store, Qwen3 `1.7b` | All ten infrastructure checks passed. Arithmetic and structured tool-schema smoke checks passed. The model produced `get_lab_status` with `{"lab":"chemistry"}`; the tool was **not executed**. |

In the bundled-store run, the short adapter answer took 1.139 seconds and the
configured brain probe took 3.2 seconds. Sampled peak aggregate daemon/runner
RSS was 1,733,926,912 bytes (about 1.61 GiB). This excludes KDE, desktop UI and
the separate provider-probe process and can double-count shared pages.
The host exposed about 9.73 GiB physical RAM; the adapter's selection policy
was constrained to 8 GiB. **This is not an 8 GiB laptop benchmark.**

The real checks also required: preload remains unverified, missing model is
refused, stopped daemon cannot report ready, and generation recovers after
daemon restart and startup preload.

Reproduce after obtaining the runtime and weights intentionally:

```sh
python scripts/mjon_offline_acceptance.py \
  --ollama /absolute/path/runtime/bin/ollama \
  --models /absolute/path/downloaded-models \
  --model qwen3:1.7b --output /absolute/path/new-evidence.json
```

Linux user namespaces must be available. On a disposable privileged CI host,
the workflow instead creates the network namespace with `sudo unshare -n`
and calls `--worker`. That CI privilege is for test isolation, not a grant of
root to production JARVIS.

## Image and USB boundary

[Recovery build 42121159781](https://github.com/miqueas80/MJON-JARVIS-ULTIMATE/actions/runs/42121159781)
passed real offline provider acceptance on GitHub, then failed staging because
the acceptance run wrote generated model aliases into the hashed payload.
No ISO was produced by that run. The corrected workflow uses a separate
writable manifest store, preserving the immutable payload. The follow-up build
result must be read from its Actions run; no final release is published.

The VM payload marker tests that the packaged daemon starts and discovers the
packaged model. It does **not** claim inference inside QEMU or full interaction
with the desktop assistant. The network-isolated provider acceptance is a
separate test on the builder. Exact ISO checksum and source commit must travel
with any artifact used for hardware testing.

The image profile remains Live with no Debian installer, no attached Windows
disk in VM tests and no automatic partitioning. Ordinary applications still
run with the Live user's permissions; no claim of disk-write isolation is made.
Use the [USB runbook](../mjon_os/USB_LIVE_TEST.md) and never select or format the
internal Windows disk.

## Work still required

- Physical Intel 8 GiB/KDE measurements and USB boot, firmware, Wi-Fi, audio,
  microphone, webcam, permission/cancellation and Windows-return tests.
- Complete offline STT, TTS and wake word: the inherited voice defaults remain
  cloud-oriented and their offline replacements have not passed acceptance.
- Full chat manager/agent orchestration, real tool execution through approval
  gates, long prompts and task quality. A successful provider and tool-schema
  probe do not establish those capabilities.
- Local vision model, persistent USB memory, reboot recovery, backups and
  audited per-agent confinement. Installing security packages is insufficient.
- Conclusive Doraimon incident attribution: the specific installation,
  redacted error and provider configuration are still unidentified.

## Rollback

The original Linux branch and main remain available. Do not reset or revert
their history. Recovery commits can be reviewed independently in the draft PR.
For a migrated user profile, stop JARVIS and restore its private `.bak` only
after preserving the current profile; never overwrite a user's later edits
silently. Disable opt-in preload with
`systemctl --user disable --now mjon-ollama-preload.service`; stop the bundled
daemon with `systemctl --user stop mjon-ollama.service`. A prior verified USB
image remains the rollback for an experimental new image.
