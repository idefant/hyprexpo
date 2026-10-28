-- Native hyprexpo design with shared desktops from virtual-desktops.
local M = {}
local library = (os.getenv("HOME") or "/home/idefant") .. "/.local/lib/hyprland-plugins/hyprexpo.so"
hl.plugin.load(library)
local function configure()
  if not hl.plugin.hyprexpo then return end
  hl.config({ plugin = { hyprexpo = {
    virtual_desktops = 1,
    overview_mode = "grid",
    columns = 3,
    rows = 3,
    dynamic_grid = 0,
    workspace_method = "first 1",
    skip_empty = 0,
    max_workspace = 9,
    cross_monitor = 0,
    gaps_in = 12,
    gaps_out = 24,
    tile_rounding = 16,
    wallpaper_bg = 1,
    label_enable = 1,
    label_text_mode = "id",
    label_position = "top-left",
    label_font_size = 24,
    label_bg_shape = "rounded",
    -- Shared mode handles its modal input directly; no extra Lua bind handles.
    keynav_enable = 0,
    keynav_wrap_h = 0,
    keynav_wrap_v = 0,
    number_key_mode = "workspace",
    gesture_fingers = 0,
  } } })
end
configure()
hl.on("config.reloaded", configure)
function M.toggle() hl.plugin.hyprexpo.expo("toggle all") end
return M
