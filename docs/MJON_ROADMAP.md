# MJON JARVIS ULTIMATE — Windows-first roadmap

This fork builds on Dodaios; preserve upstream attribution, Apache-2.0 LICENSE and NOTICE, and maintain upstream compatibility.

## Verified baseline
- Upstream Python package: `dodaios` 4.1.2 (`pyproject.toml` on fork main at inspection).
- Python requirement: >=3.11,<3.15.
- Upstream README documents Windows installation, voice, agents, local Ollama support, and approvals for system-changing actions.
- Target: Windows 11, 8 GB RAM, CPU-first operation.

## Phase 0 — Establish a measurable baseline
1. Install in a Windows 11 test account or VM, after reviewing installer and dependencies.
2. Record idle/peak RAM, startup time, voice latency, task success, and CPU use.
3. Run upstream test suite and record exact commands, versions, failures, and environment.
4. Inventory existing voice, Windows UI automation, approvals, memory, and model adapters before extending them.

## Phase 1 — Jarvis identity and Spanish voice
- Configurable assistant display name and wake phrase (default `Jarvis`), without hard-coded renaming across upstream modules.
- Spanish speech input and output with clear offline/online fallback status.
- Explicit microphone on/off control and visible listening state.

## Phase 2 — Reliable Windows actions
- Use existing desktop automation and native accessibility APIs where available; prefer semantic UI actions to screen coordinates.
- Action planner with bounded retries, verification of result, cancellation, and audit log.
- File operations default to reversible workflows; do not silently delete, publish, spend, or send.
- Approvals for elevated permissions, credentials, external messages, destructive actions, and security-setting changes.

## Phase 3 — Local-first performance
- Benchmark small Ollama models under the 8 GB RAM constraint; never claim a model runs adequately without measurements.
- Distinguish deterministic OS commands from model-dependent reasoning.
- Degrade gracefully when offline or out of memory.

## Phase 4 — Extensible agent orchestration
- Capability registry, tool permissions, specialist agents, persistent memory with user controls.
- GitHub/Codex workflow: inspect -> propose -> test -> review -> commit/PR, with explicit approval before publishing.

## Release criteria
- Reproducible Windows installation and rollback.
- Test evidence for voice, automation, permissions, offline operation, resource consumption, and failure recovery.
- Upstream license and attribution preserved.
- No claim of unrestricted or infallible control: Windows protections and safety boundaries remain in place.

## Next engineering action
Audit the existing Dodaios Windows execution and speech pathways and add focused tests before implementing changes. Keep `main` untouched until review.
