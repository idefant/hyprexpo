#include "SharedDesktops.hpp"
#include "HyprlandConfigCompat.hpp"
#include "IOverviewSession.hpp"
#include "Overview.hpp"
#include "globals.hpp"
#include <algorithm>
#include <hyprland/src/config/shared/actions/ConfigActions.hpp>
#include <hyprland/src/debug/log/Logger.hpp>
#include <hyprland/src/managers/SeatManager.hpp>
#include <hyprland/src/output/Monitor.hpp>
#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/state/MonitorState.hpp>
#include <map>
#include <set>
#include <sstream>
#include <xkbcommon/xkbcommon.h>

namespace SharedDesktops {
static std::map<int64_t, std::vector<int64_t>> layouts;
bool enabled() {
  return CompatHyprlandAPI::intValue("plugin:hyprexpo:virtual_desktops") != 0;
}
bool handleKey(const IKeyboard::SKeyEvent &event) {
  if (!enabled() || !overviewOpen())
    return false;
  auto *ov = activeOverview();
  if (!ov || ov->closeCommitted() ||
      event.state != WL_KEYBOARD_KEY_STATE_PRESSED)
    return true;
  const auto keyboard = g_pSeatManager->m_keyboard.lock();
  if (!keyboard)
    return true;
  const auto symbol = [&](xkb_state *state) {
    return state ? xkb_state_key_get_one_sym(state, event.keycode + 8)
                 : XKB_KEY_NoSymbol;
  };
  auto key = symbol(keyboard->m_xkbState);
  const auto baseKey = symbol(keyboard->m_xkbSymState);
  if (baseKey >= XKB_KEY_1 && baseKey <= XKB_KEY_9)
    key = baseKey;
  switch (key) {
  case XKB_KEY_Escape:
  case XKB_KEY_Tab:
  case XKB_KEY_ISO_Left_Tab:
    closeOverviews(false);
    break;
  case XKB_KEY_Left:
    ov->onKbMoveFocus("left");
    break;
  case XKB_KEY_Right:
    ov->onKbMoveFocus("right");
    break;
  case XKB_KEY_Up:
    ov->onKbMoveFocus("up");
    break;
  case XKB_KEY_Down:
    ov->onKbMoveFocus("down");
    break;
  case XKB_KEY_Return:
  case XKB_KEY_KP_Enter:
    if (ov->onKbConfirm())
      closeOverviewsSelecting(ov);
    break;
  default:
    if (key >= XKB_KEY_1 && key <= XKB_KEY_9 &&
        ov->onKbSelectNumber(key - XKB_KEY_1 + 1))
      closeOverviewsSelecting(ov);
    break;
  }
  return true;
}
bool prepare(int count, std::string &error) {
  layouts.clear();
  std::istringstream input(HyprlandAPI::invokeHyprctlCommand(
      "vdeskoverview", "snapshot " + std::to_string(count)));
  std::string magic, current;
  int active;
  if (!(input >> magic >> current >> active) || magic != "vdesk-overview-v1" ||
      current != "current") {
    error = "virtual-desktops with vdeskoverview v1 is required";
    return false;
  }
  std::set<int64_t> owned;
  int desktop;
  int64_t monitor, workspace;
  while (input >> desktop >> monitor >> workspace) {
    if (desktop < 1 || desktop > count || workspace <= 0 ||
        !owned.insert(workspace).second) {
      error = "invalid or overlapping shared desktop layout";
      layouts.clear();
      return false;
    }
    auto &ids = layouts[monitor];
    ids.resize(count, -1);
    if (ids[desktop - 1] != -1) {
      error = "duplicate monitor/desktop";
      return false;
    }
    ids[desktop - 1] = workspace;
  }
  for (const auto &mon : State::monitorState()->monitors()) {
    const auto it = layouts.find(mon->m_id);
    if (it == layouts.end() ||
        std::ranges::find(it->second, -1) != it->second.end()) {
      error = "incomplete shared desktop layout";
      layouts.clear();
      return false;
    }
  }
  return true;
}
std::vector<int64_t> workspaces(const PHLMONITOR &monitor) {
  const auto it = monitor ? layouts.find(monitor->m_id) : layouts.end();
  return it == layouts.end() ? std::vector<int64_t>{} : it->second;
}
bool select(int desktop) {
  const auto result = HyprlandAPI::invokeHyprctlCommand(
      "vdeskoverview", "select " + std::to_string(desktop));
  if (result != "ok")
    Log::logger->log(Log::ERR, "[hyprexpo] shared desktop selection failed: {}",
                     result);
  return result == "ok";
}
void syncFocus(int index) {
  forEachOverview([index](IOverviewSession &session) {
    if (auto *grid = dynamic_cast<COverview *>(&session);
        grid && grid->sharedDesktops)
      grid->setKeyboardFocus(index);
  });
}
bool closeSelecting(IOverviewSession *selecting) {
  auto *source = dynamic_cast<COverview *>(selecting);
  if (!source || !source->sharedDesktops)
    return false;
  const int desktop = source->selectedDesktop();
  if (desktop < 1)
    return true;
  const auto monitor = source->monitor();
  // Arm every close animation before switching. Synchronous workspace events
  // can then never commit a second per-monitor selection.
  forEachOverview([desktop](IOverviewSession &session) {
    if (auto *grid = dynamic_cast<COverview *>(&session);
        grid && grid->sharedDesktops)
      grid->selectVisibleIndex(desktop - 1);
    session.close(false);
  });
  if (monitor)
    (void)Config::Actions::focusMonitor(monitor);
  select(desktop);
  forEachOverview([](IOverviewSession &session) {
    if (auto *grid = dynamic_cast<COverview *>(&session);
        grid && grid->sharedDesktops)
      grid->followSelectedDesktop();
  });
  return true;
}
void registerStatus() {
  SHyprCtlCommand command;
  command.name = "hyprexpostate";
  command.exact = true;
  command.fn = [](eHyprCtlOutputFormat, std::string) {
    std::string out = "{\"revision\":\"shared-desktops-v1\",\"sessions\":[";
    bool first = true;
    forEachOverview([&](IOverviewSession &session) {
      if (!first)
        out += ',';
      first = false;
      if (auto *grid = dynamic_cast<COverview *>(&session))
        out += grid->sharedStateJson();
      else
        out += "{}";
    });
    return out + "]}";
  };
  HyprlandAPI::registerHyprCtlCommand(PHANDLE, command);
}
} // namespace SharedDesktops
