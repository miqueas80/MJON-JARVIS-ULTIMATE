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
