#include "../src/PreviewFramebuffer.hpp"

#include <iostream>
#include <memory>
#include <string>

namespace {

constexpr uint32_t SDR8 = 1, SDR10 = 2, FP16 = 3;
const auto SRGB = std::make_shared<int>(1);
const auto LINEAR_HDR = std::make_shared<int>(2);
const auto WIDE_GAMUT = std::make_shared<int>(3);

struct STexture {
    std::shared_ptr<int> description;
};

// Models Hyprland's allocation cache and texture metadata.
struct SFramebuffer {
    struct SSize {
        int x = 0, y = 0;
    } m_size;
    uint32_t format = 0;
    std::shared_ptr<STexture> texture;
    bool failAllocation = false;
    int allocations = 0;
    int descriptionUpdates = 0;

    bool alloc(int width, int height, uint32_t requestedFormat) {
        const bool changed = width != m_size.x || height != m_size.y || requestedFormat != format;
        if (texture && !changed)
            return true;
        m_size = {width, height};
        format = requestedFormat;
        texture.reset();
        ++allocations;
        if (failAllocation)
            return false;
        texture = std::make_shared<STexture>();
        return true;
    }

    void release() {
        texture.reset();
        m_size = {};
    }

    void setImageDescription(const std::shared_ptr<int>& description) {
        ++descriptionUpdates;
        if (texture)
            texture->description = description;
    }
};

int failures = 0;
void expect(bool condition, const std::string& label) {
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << label << '\n';
    }
}

void expectDescription(const SFramebuffer& framebuffer, const std::shared_ptr<int>& description, const std::string& label) {
    expect(framebuffer.texture && framebuffer.texture->description == description, label);
}

}

int main() {
    using Hyprexpo::Capture::prepareFramebuffer;

    for (const auto format : {SDR8, SDR10, FP16}) {
        SFramebuffer framebuffer;
        const auto description = format == FP16 ? LINEAR_HDR : SRGB;
        expect(prepareFramebuffer(framebuffer, 128, 72, format, description), "initial allocation succeeds");
        expect(framebuffer.format == format, "requested working precision is retained");
        expectDescription(framebuffer, description, "new texture has the captured color description");
        const auto texture = framebuffer.texture;
        expect(prepareFramebuffer(framebuffer, 128, 72, format, description), "unchanged capture can reuse allocation");
        expect(framebuffer.allocations == 1 && framebuffer.texture == texture, "unchanged dimensions and format keep texture storage");
        expectDescription(framebuffer, description, "reused texture remains tagged");
    }

    SFramebuffer framebuffer;
    expect(prepareFramebuffer(framebuffer, 128, 72, SDR10, SRGB), "initial SDR capture succeeds");
    const auto sdrTexture = framebuffer.texture;
    expect(prepareFramebuffer(framebuffer, 128, 72, FP16, LINEAR_HDR), "same-size HDR transition succeeds");
    expect(framebuffer.format == FP16 && framebuffer.texture != sdrTexture, "same-size FP16 transition replaces integer storage");
    expectDescription(framebuffer, LINEAR_HDR, "HDR replacement texture is tagged after allocation");
    const auto hdrTexture = framebuffer.texture;
    expect(prepareFramebuffer(framebuffer, 128, 72, FP16, WIDE_GAMUT), "color-only transition succeeds");
    expect(framebuffer.texture == hdrTexture, "color-only transition does not allocate storage");
    expectDescription(framebuffer, WIDE_GAMUT, "color-only transition refreshes metadata on reused texture");
    expect(prepareFramebuffer(framebuffer, 128, 72, SDR8, SRGB), "HDR to SDR transition succeeds");
    expect(framebuffer.format == SDR8, "HDR to SDR transition restores integer precision");
    expectDescription(framebuffer, SRGB, "HDR to SDR transition replaces color description");
    expect(prepareFramebuffer(framebuffer, 129, 72, FP16, LINEAR_HDR), "size and format transition succeeds");
    expect(framebuffer.m_size.x == 129 && framebuffer.format == FP16, "size and format both update");
    expectDescription(framebuffer, LINEAR_HDR, "resized texture receives its description");

    SFramebuffer failed;
    failed.failAllocation = true;
    expect(!prepareFramebuffer(failed, 128, 72, FP16, LINEAR_HDR), "allocation failure is propagated");
    expect(failed.descriptionUpdates == 0, "failed allocation does not publish metadata");
    expect(!prepareFramebuffer(failed, 128, 72, FP16, LINEAR_HDR), "same-size repeated failure never becomes success");
    failed.failAllocation = false;
    expect(prepareFramebuffer(failed, 128, 72, FP16, LINEAR_HDR), "same-size failed allocation is retried");
    expectDescription(failed, LINEAR_HDR, "recovered allocation is tagged");

    if (!failures)
        std::cout << "PreviewFramebufferTests passed\n";
    return failures ? 1 : 0;
}
