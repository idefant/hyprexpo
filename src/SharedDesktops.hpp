#pragma once
#include <hyprland/src/desktop/DesktopTypes.hpp>
#include <hyprland/src/devices/IKeyboard.hpp>
#include <string>
#include <vector>
class IOverviewSession;
namespace SharedDesktops {
bool enabled();
bool handleKey(const IKeyboard::SKeyEvent &event);
bool prepare(int count, std::string &error);
std::vector<int64_t> workspaces(const PHLMONITOR &monitor);
bool select(int desktop);
void syncFocus(int index);
void initializeFocus();
bool closeSelecting(IOverviewSession *selecting);
void registerStatus();
} // namespace SharedDesktops
