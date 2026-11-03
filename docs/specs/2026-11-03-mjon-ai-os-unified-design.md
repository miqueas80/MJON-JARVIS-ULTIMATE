# MJON AI OS: Unified Native Distribution — Design

**Product decision:** MJON AI OS is **one operating system**, not a desktop app plus a separately branded OS. Its source, desktop integration, and agent runtime live in the existing `miqueas80/MJON-JARVIS-ULTIMATE` fork. We do not create a second GitHub repository.

## Product boundary

An amd64 Debian 13 (trixie) KDE Plasma Live ISO that embeds the maintained Dodaios-derived agent and the MJON desktop integration layer. KDE supplies ordinary windows and apps, while the bundled JARVIS agent provides conversational and tool-driven control with the same user permissions and the original approval mechanisms.

**Out of scope for this foundation:** rewriting the Linux kernel, claiming Windows binary compatibility, bypassing authentication, embedding an unlicensed model, or deploying to the user's actual computer.

## Architecture and data flow

1. `live-build` constructs an ISO from the official Debian archive and the repository's own Python wheel; dependency installation occurs inside the build environment, not on user startup.
2. KDE starts a graphical user session. The XDG autostart entry requests that `systemd --user` start `mjon-jarvis.service`; the service starts `/usr/local/bin/mjon-session` as the logged-in user.
3. `mjon_os.first_boot` creates one private, user-writable configuration, deriving it from the upstream sample without overwriting existing preferences. It chooses Spanish and `Jarvis` by default, prevents a duplicate upstream autostart, and uses an absolute per-user data directory.
4. `dodaios.ui.web.launcher` runs the existing desktop agent. `mjon_jarvis.spanish_bridge` emits existing `open_app` or Computer-Use plans, so commands go through the original tool execution and authorization path.
5. The agent can query local models or configured online providers. Without offline model weights it must report that an offline model is unavailable rather than claim full offline reasoning.
6. The OS image records the engine wheel hash and preserves the upstream `LICENSE` and `NOTICE`.

## Error and security behavior

- Build preparation refuses existing destination paths and missing or mismatched wheels; it does not overwrite user files.
- The OS build hook aborts when the reviewed engine cannot be installed. It must not silently fall back to a different PyPI release.
- Per-user configuration is created with mode 0600 and is not replaced after the first launch.
- JARVIS is not granted root, password, kernel or unrestricted device access. Sensitive actions remain subject to upstream permissions and user consent.
- If microphone, desktop portal or provider is unavailable, expose failure in the app rather than claiming an action happened.
- No background OS modification and no auto-installation on Windows are part of this work.

## Quality gates

**Implemented foundation:** package inclusion, config-root selection, first-run provisioner, native user-session assets, image workspace preparation, tests and CI checks.

**Required before a release:** full wheel build with frontend assets; actual ISO build; UEFI and legacy BIOS virtual boot; graphical session and service startup; persistent settings; file and GUI automation under KDE Wayland; Spanish voice plus reliable wake detection; offline and online behavior; 8 GB RAM profile; security/permission tests; release hashing/signing and rollback instructions.

**Status:** native distribution engineering, not a downloadable or final OS.
