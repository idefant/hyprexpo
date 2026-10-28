# Shared desktops: idefant fork

This fork keeps hyprexpo's native grid, previews, wallpaper, rounding and animations.
It adds an opt-in frontend for **idefant/hyprland-virtual-desktops**. It is not
another virtual desktop manager. Ownership, window migration, external focus and
hotplug reconciliation remain in that plugin.

## Requirements and installation

- Build against the exact running Hyprland headers. Tested: Hyprland 0.56.2,
  commit efb50993780079460b0cbed1363e2166a2de1d9f.
- Load idefant/hyprland-virtual-desktops **2.2.8+multimonitor.3** or newer with
  `vdeskoverview` protocol v1, before this plugin.
- Build: `cmake -S . -B /tmp/hyprexpo-build -DCMAKE_BUILD_TYPE=Release`, then
  `cmake --build /tmp/hyprexpo-build --target hyprexpo -j2`.
- Install `libhyprexpo.so` to `~/.local/lib/hyprland-plugins/hyprexpo.so` using a
  temporary file and atomic rename. **Never overwrite a loaded library's inode.**
- Copy `examples/shared-desktops.lua` to `~/.config/hypr/overview.lua` and require
  `hypr.overview` after loading virtual-desktops. Bind Super+Tab to
  `function() require("hypr.overview").toggle() end`. Replace an existing binding
  through its owning configuration, rather than adding a duplicate.
- Reload and check `hyprctl configerrors`. A configuration reload alone does not
  replace an already loaded `.so`: explicitly replace that plugin or log in again.

The Lua example restores the previous grid styling used on this machine. Styling
options remain upstream hyprexpo options; `virtual_desktops=1` enables this bridge.
With the option off, normal upstream grid behavior is retained.

## Shared mode behavior

- A fixed 3×3 grid for logical desktops 1–9 on every enabled monitor, including
  empty monitors. The tile number is the **logical desktop**, not a workspace ID.
- Each output captures only that output's workspace belonging to the desktop.
- Hover/arrow focus is mirrored across grids. Click, digits 1–9 and Enter select
  one logical desktop for all monitors. Escape or Tab cancels all grids.
- Modal key input is consumed so typing cannot reach the application beneath.
  XKB symbols support both current language layouts and virtual keyboards.
- Existing surface commit listeners also recapture content updates in shared mode,
  preserving live previews. Workspaces remain on their own monitors during capture.
- Native dragging and `hl.plugin.hyprexpo.move_window("1 2 ADDRESS")` move windows
  between the corresponding per-output workspaces. Cross-output native dragging
  retains upstream behavior.
- Topology changes close the frozen overview before its mapping becomes stale.
  Reopening obtains the current mapping, including after repeated unplug/replug.
- The scratchpad controller, cursor redraw plugin, cursor visibility/warping and
  Mouse Modes are separate and retain their configuration.

Gesture-driven shared overviews are not configured or covered by acceptance tests;
leave `gesture_fingers=0` and do not register an expo gesture for shared mode.
The normal upstream scrolling overview is outside shared mode; use `overview_mode="grid"`.

## Bridge and diagnostics

There is no socket round trip, shell process or persistent Lua callback between
plugins. hyprexpo uses `HyprlandAPI::invokeHyprctlCommand` on the compositor thread:

```
vdeskoverview snapshot 9
vdeskoverview select 2
```

Snapshot prepares ownership of desks 1–9 without activating them or moving windows.
Its numeric text response is `vdesk-overview-v1`, `current N`, then lines of
`desktop monitorID workspaceID`. IDs come from actual layouts, not arithmetic.
Select delegates exactly once to the virtual-desktops manager. Missing or malformed
bridge data fails closed instead of displaying unrelated workspaces.

`hyprctl -j hyprexpostate` reports session monitor IDs, logical focus, tile workspace
IDs and window counts. It contains no window titles or content. It can establish
that the native overview is running; a config file or reload message cannot.

## Validation

```
ctest --test-dir /tmp/hyprexpo-build --output-on-failure
python3 tests/shared_desktops.py /tmp/hyprexpo-build/libhyprexpo.so /path/to/virtual-desktops.so [monitors|size|none]
```

The integration test uses an isolated nested compositor, synthetic terminal windows,
and `wtype` explicitly addressed to its Wayland socket. It refuses to inject into
the parent display. It covers per-monitor ownership/previews, all nine slots,
synchronized focus/selection, real keyboard events, cancellation, empty desktops,
window moves, reload, hotplug with 1–3 outputs and missing-bridge refusal.
Set `HYPREXPO_TEST_LIVE=1` to also compare pixels of an inactive animated
terminal preview (requires ImageMagick). This check passed in a separate nested run.
Screenshots and logs go under /tmp. No parent monitor is disconnected and no user
browser profile, clipboard or window content is inspected. Physical cable hotplug
and the final visual result on the user's actual screens require user testing.

## Rollback

Restore the previous Super+Tab action that toggled the saved QML overlay, remove
`require("hypr.overview")`, then reload/check errors. Unload this hyprexpo library
after removing its use. Keep virtual-desktops and the cursor plugin loaded.
The existing bar indicator can remain enabled with either overview.
