# MJON AI OS — USB Live Validation Runbook

**Do not flash or boot an experimental build until its SHA256, boot entries, VM boot, graphical session and agent startup are verified.** The presence of an `.iso` alone does not establish readiness.

## Scope

- Target: Intel/AMD x86-64 laptop with 8 GB RAM, Windows retained on its internal drive.
- USB Live **testing only**. The image builder explicitly disables the Debian installer.
- Bootable ISO may consume several gigabytes; choose a USB drive with capacity larger than the final ISO.
- Writing an ISO **erases the selected USB drive**. Confirm the removable drive twice; never select the Windows system disk.
- Hardware support (Wi-Fi chipset, GPU firmware, touchpad, audio, keyboard) requires live testing.

## Hardware finding: graphical login failed on 2026-11-03

The source `7b139ea9d510` ISO booted Debian 13 and presented SDDM, but the
physical Conectar Igualdad laptop reported `user (automatic login)` followed by
`Authentication failure` on tty3. The live-build configuration disabled APT
recommends and omitted `user-setup`, which Debian Live explicitly requires to
create its temporary account. **That pre-release must not be treated as a usable
USB login candidate.**

The replacement build now explicitly includes `live-config`,
`live-config-systemd`, `user-setup`, and `sudo`. Its QEMU boot gate refuses
success unless the expected `user` exists, has its home directory and its
password is not locked, then authenticates the known Live password through
PAM. It does **not** claim to simulate an interactive keyboard login; physical
testing is still necessary.

Use only a subsequently verified source commit and checksum. Replacing the
ISO on Ventoy does not format the internal Windows disk.

## Before the user's first USB test

1. CI must build an ISO with a documented source commit and both BIOS and UEFI boot records.
2. Run the ISO in a disposable VM with at least 4 GB RAM and no mounted host disks.
3. Verify KDE graphical login, an agent window, session service and safe open-app behavior.
4. Audit all distributed names/assets for the independent MJON brand and preserve upstream licensing.
5. Verify local speech and distinguish it from features that still need online models.
6. Publish the exact release SHA256 alongside the ISO. Never reuse a checksum for a rebuilt artifact.

## Check the downloaded ISO (only after a verified release)

On Windows PowerShell:

```powershell
Get-FileHash .\MJON-AI-OS-dev-amd64.iso -Algorithm SHA256
```

The output must match the published matching `.iso.sha256` entry. A mismatch means stop.

## Non-destructive hardware test

1. Back up important files on the Windows disk before any OS experimentation.
2. Use a trusted ISO writer after confirming the correct USB device; selecting the wrong target destroys data.
3. Use the machine's temporary boot-device menu to start from USB; do **not** partition or format the internal disk.
4. Choose the Live session, not an installer. The current build is designed not to include a Debian installer.
5. Check KDE desktop, keyboard layout, Wi-Fi, audio, microphone, webcam permissions and touchpad.
6. From the Live session terminal, inspect without elevated privileges:

```bash
mjon-doctor --json
systemctl --user status mjon-jarvis.service --no-pager
journalctl --user -u mjon-jarvis.service -b --no-pager -n 100
```

7. Test a harmless request: opening Calculator. Verify it opened, and distinguish spoken feedback from actual execution.
8. Disable Wi-Fi and repeat deterministic local tests. Do not claim offline LLM reasoning unless local model weights are present.
9. Shut down gracefully and remove the USB. Boot Windows normally from the internal drive.

## Failure conditions

- No boot menu, black screen, firmware refuses image, or unexpected installer prompt: stop and collect a photo/error.
- Missing frontend, failed service, or high memory use: run `mjon-doctor --json` and retain relevant logs, without exposing passwords/API keys.
- Unapproved disk modifications or requests for elevated permissions: stop the experiment.
- Hardware-specific changes remain out of scope until a VM and ISO build pass.

**Recorded status:** the `70997acb` experimental build passed BIOS/UEFI VM
boot, account, Plasma, user-service and HTTP API checks. It predates later
provider defaults and contains no Ollama weights. See the
[recovery results](../docs/MJON_RECOVERY_RESULTS_2026-11-05.md) for the corrected
payload profile and its separate real inference evidence. Check the exact new
build result and checksum before any hardware trial; no final ISO is approved.
