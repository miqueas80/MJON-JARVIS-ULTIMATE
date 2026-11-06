# Continuation: bundled daemon boot failure

Source under investigation: `0f7ab29c290422abd7990aea62b81d0c2e143946`.
[Build 42124742858](https://github.com/miqueas80/MJON-JARVIS-ULTIMATE/actions/runs/42124742858)
completed real network-isolated inference, immutable-payload staging, Debian ISO
construction and BIOS/UEFI boot-record inspection. Its BIOS VM reached the
Live account, Plasma and the stable JARVIS user service, but reported
`OLLAMA_PAYLOAD_FAILED`. UEFI was not attempted after that failure. No verified
ISO was uploaded or released.

The shell's API-health conditional was reached before testing Ollama, but it
emitted `JARVIS_API_READY` only after Ollama passed. The resulting `api=False`
summary therefore obscured the independent API result. The probe now records
JARVIS HTTP readiness separately and still rejects a required, failed payload.

The old artifact retained no Ollama user journal, exit code or startup result.
It cannot conclusively distinguish permission errors, service sandbox setup,
startup timeout or CPU/runtime incompatibility. No cause is asserted from the
single failure marker.

The next diagnostic build adds user-service state/journal and file-mode/memory
evidence to the serial log. The collector waits for required payload evidence
and retains failure diagnostics before exiting. A short-lived **UNVERIFIED**
image artifact is retained before boot checks so exact failing bytes can be
examined without rebuilding. It is not approved for USB hardware testing and
does not bypass the verified artifact or release gates.

Local contracts: 136 native tests, 124 executed and 12 SDK-dependent tests
explicitly skipped in the minimal environment; workflow policy reports zero
findings across 35 workflows. These are not new real-model or VM boot results.
The prior real-model evidence remains valid for its recorded source and scope.

## Stronger next-image acceptance

The diagnostic run at `7e8da8d` still tests model discovery, not generation in
the guest. The next source requires `JARVIS_LOCAL_INFERENCE_READY` from the
installed `mjon_os.jarvis_probe`, running as the Live user against that user's
actual configuration. QEMU has no NIC and no host disk. Discovery and HTTP
health cannot substitute for this marker in collection, CLI verdict or release
checks. The VM uses 4 GiB instead of 3 GiB: the actual 1.36 GB model would exceed
the conservative 40% weight budget at 3 GiB. This is a VM contract, not a
physical Intel 8 GiB desktop benchmark. The outer boot limit is 1200 seconds;
the installed provider probe still fails explicitly on its bounded timeout.

Payload staging now normalizes the image's read/execute modes rather than
copying private download-cache permissions into root-owned ISO files. A
regression test starts from a private 0600 weight and 0700 directory and checks
that staging is readable while the original cache stays private. This fixes a
potential packaging defect; it is not yet attributed as the VM failure cause.

Fresh native profiles now set the real typed global safety approval mode to
`ask`, instead of inheriting upstream `bypass`. Existing user profiles and
chat-owned policies are preserved. The inherited evaluator and approval tests
pass; this does not demonstrate complete agent confinement or approval of
every real external tool.

The Center launcher exposes the explicit bundled runtime in its PATH, like
the JARVIS session. Otherwise its installation catalog could report absent
while the bundled daemon was available. The catalog still reports only
installed/unverified; actual provider generation is independent.

## Additional historical source recovered

The user-provided `README(2).md` (2026-11-05) describes a separate v0.1 local
HTTP dashboard and an unbuilt Debian/Xfce recipe. It explicitly says that
agents, ANR integration and the ISO were unfinished. It is a historical
artifact, not a replacement for the real Debian/KDE branch and existing
Dodaios integration. No code from that parallel package replaces this branch.

## Automated checks for the follow-up source

140 native tests passed with actual SDK/config dependencies installed, zero
skipped. A minimal environment executes 128 and explicitly skips 12. Two
focused inherited safety invocations passed 36 and 19 tests. These use fixture
tools and mocked transports, not real agent side effects or model inference.
The generation gate regression first failed because discovery alone was
accepted, then passed with the stronger gate. Source hashes, commands, dirty
source scope and raw logs are retained in
[verification/mjon-recovery-2026-11-06](verification/mjon-recovery-2026-11-06).
The failed 0f7ab29 guest serial excerpt and build metadata are retained there.

## Diagnostic run outcome and targeted correction

[Run 42213768221](https://github.com/miqueas80/MJON-JARVIS-ULTIMATE/actions/runs/42213768221),
source `7e8da8dd1363e183bc04367ef0a25438a1c6caa9`, again passed real isolated
provider acceptance, ISO construction and boot-sector checks. BIOS proved
kernel, Live account, Plasma, JARVIS service and HTTP API. UEFI was not run.
The payload check failed, correctly blocking the verified artifact/release.

The retained service state was `ActiveState=activating`, `SubState=start-pre`.
`ExecStartPre` was the integrity-verification/model-store initializer with a
running PID and no stop time; `ExecStart` had no start time or PID. Root-owned
payload directory, manifest and executable modes were 0755/0644/0755. Guest
MemTotal was 2,983,764 kB and MemAvailable 1,610,652 kB at the observation.
This establishes that the daemon had not started when the one-shot catalog
request declared failure. It does not establish a permission error, illegal
instruction, OOM, completed initialization, or the exact verification duration.
The old journal query retained no entries and cannot prove an earlier timeout.

The correction retains full hash verification, increases the bounded startup
allowance from 120 to 600 seconds for cold squashfs under TCG. The session
queues the independent daemon without blocking JARVIS on cold verification;
queueing does not confer readiness. The guest waits up to
610 seconds for the independent daemon's expected model catalog. Missing
readiness still fails. The separate actual-brain generation gate then runs;
no success is synthesized from the service state. Diagnostics include both
process and user-manager journal fields. An outer 1200-second VM bound covers
boot, integrity verification, and the provider probe. These budgets must be
validated by the next image; longer native startup is not claimed necessary.

Diagnostic artifact 13501972095 had ZIP SHA256
`598aabd3d87a7614d2f945a86af2c2a63dac985f65fc637d44c76dfab171ac1b`.
Its serial excerpt and metadata are retained under the verification directory.
Artifact 13501880979 is a 3,462,715,018-byte quarantined ZIP, not a verified ISO.
Its size also means an eventual single-file GitHub Release may exceed the
existing 2 GiB gate; that gate is not relaxed and no release is authorized.

The explicitly enabled preload unit is ordered after, and requests, the bundled
daemon. Its payload condition preserves the unbundled/system-daemon case.
This avoids exhausting the preload's short HTTP retry window while a cold
bundled payload is still being verified. The service remains opt-in, never
pulls weights, and does not mark a warmed model as generation-verified.
