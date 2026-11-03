# MJON AI OS Native Foundation Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a single-source Debian Live KDE OS build candidate with the fork's own agent preinstalled and a private, native graphical-session launcher.

**Architecture:** The existing monorepo remains authoritative. The fork's Python wheel includes both upstream Dodaios and MJON additions; Debian live-build copies this wheel into the image, installs it at image construction time, and starts it as the graphical user through systemd. No independent OS repository or second assistant runtime.

**Tech Stack:** Python 3.13, setuptools, Debian 13, live-build, KDE Plasma, systemd --user, XDG autostart, GitHub Actions.

## Global Constraints

- Preserve upstream license, attribution and action authorization.
- Never ask the user to install or partition a device before the final verified release.
- The agent is a user process, never root; no automatic permission bypass.
- Use one Git repository and one release unit (the OS ISO).
- Do not report that a prepared image is bootable until the ISO actually boots in tests.

---

### Task 1: Package the native engine

**Files:**
- Modify: `setup.py`
- Modify: `dodaios/core/config.py`
- Create: `mjon_os/__init__.py`
- Create: `mjon_os/config_paths.py`
- Test: `mjon_os/tests/test_image_builder.py`

**Interfaces:**
- Consumes: upstream `setup.py:packages()`, `resolve_config_file(Path)`.
- Produces: wheel modules `mjon_jarvis`, `mjon_os`; `config_root(Path, Mapping) -> Path`.

- [x] Step 1: Specify that native config-root selection uses only an explicit absolute per-user override and otherwise preserves upstream behavior.
- [x] Step 2: Verify missing helper triggers test import failure (RED).
- [x] Step 3: Add both MJON packages to the upstream wheel list and adapt the upstream config-root selector.
- [x] Step 4: Run focused config tests in local Python.
- [x] Step 5: Confirm the generated wheel contains all native modules using CI (GitHub Actions run 41700515794).
- [ ] Step 6: Verify packaging with the full upstream regression suite before merge.

### Task 2: One safe first-boot agent instance

**Files:**
- Create: `mjon_os/first_boot.py`
- Create: `mjon_os/live/config/includes.chroot/usr/local/bin/mjon-session`
- Create: `mjon_os/live/config/includes.chroot/usr/lib/systemd/user/mjon-jarvis.service`
- Create: `mjon_os/live/config/includes.chroot/etc/xdg/autostart/mjon-ai-os.desktop`
- Test: `mjon_os/tests/test_first_boot.py`

**Interfaces:**
- Consumes: upstream `dodaios.toml.example` and `dodaios.ui.web.launcher`.
- Produces: private `~/.config/mjon-ai-os/dodaios.toml`; a per-user service that runs only after KDE login.

- [x] Step 1: Define tests for private 0600 creation, Spanish/Jarvis defaults, no overwrite and invalid templates.
- [x] Step 2: Verify missing first-boot provisioner fails tests (RED).
- [x] Step 3: Implement fail-closed one-time config creation and the KDE/systemd desktop bridge.
- [x] Step 4: Run first-boot tests locally.
- [ ] Step 5: Test actual KDE user-session startup with D-Bus and window display in a VM.
- [ ] Step 6: Verify no duplicate listeners and no unexpected writes outside user state.

### Task 3: Prepare and verify the OS image

**Files:**
- Create: `mjon_os/image_builder.py`
- Create: `mjon_os/live/config/package-lists/mjon.list.chroot`
- Create: `mjon_os/live/config/hooks/live/90-mjon-agent.hook.chroot`
- Create: `mjon_os/README.md`
- Test: `mjon_os/tests/test_image_builder.py`

**Interfaces:**
- Consumes: local reviewed `dodaios-*.whl`, the repository license files and upstream template.
- Produces: a new, atomic live-build tree including `auto/config`, image assets and `mjon-build.json` with SHA256.

- [x] Step 1: Test missing inputs, wheel metadata, anti-overwrite and expected image tree.
- [x] Step 2: Observe the failing import test (RED).
- [x] Step 3: Add prepare-only CLI, Debian 13 KDE package list and an image-time pip hook.
- [x] Step 4: Run Python unit tests and POSIX shell syntax checks locally.
- [x] Step 5: Build an actual Debian ISO in a disposable Linux builder (experimental run 41704101235: passed, artifact 13264574252; source 9229bf249; not VM-certified).
- [ ] Step 6: Boot the ISO under QEMU with UEFI and BIOS and capture health evidence.

### Task 4: Cross-platform checks and release gating

**Files:**
- Create: `.github/workflows/mjon-ai-os.yml`
- Create: `docs/specs/2026-11-03-mjon-ai-os-unified-design.md`
- Test: wheel validation and image preparation jobs.

**Interfaces:**
- Consumes: source commit, native unit tests, wheel and image builder.
- Produces: CI job status and verified build input manifest; no release artifact yet.

- [x] Step 1: Run unit tests on Windows and Linux with Python 3.13.
- [x] Step 2: Add GitHub CI workflow with a wheel contract check.
- [x] Step 3: Observe successful Windows/Linux CI and fix any failures (12 tests on each platform, followed by wheel/image-preparation contract).
- [ ] Step 4: Verify full upstream suite and bundle the desktop frontend.
- [ ] Step 5: Test voice, on-screen control, model fallback and 8 GB RAM on real Linux.
- [ ] Step 6: Release only when the complete ISO boot and safety criteria pass.

## Unresolved product decisions

- Whether the eventual offline model weights should be bundled with the ISO or offered as a separate signed optional image; bundling is heavier but avoids first-run downloads.
- Whether to offer dual-boot installation in the first public release; the current foundation intentionally builds a Live-only image.
- Whether the first branded desktop ships only KDE Plasma or adds a lighter Xfce edition after RAM profiling.
