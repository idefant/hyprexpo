#pragma once

#include <cstdint>

namespace Hyprexpo::Capture {

template <typename Framebuffer, typename ImageDescription>
bool prepareFramebuffer(Framebuffer& framebuffer, int width, int height, uint32_t format, const ImageDescription& description) {
    // Hyprland handles storage reuse, format changes, and allocation retries.
    if (!framebuffer.alloc(width, height, format))
        return false;
    // Allocation may replace the texture; set its metadata afterwards.
    framebuffer.setImageDescription(description);
    return true;
}

}
