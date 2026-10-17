#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>

namespace mtkgrain {
struct Params {
    float amount;
    float values[6]; // highlight, size, roughness, colour ratio, midtones, shadows
    int type;
    bool coloured, finally;
};

inline bool apiAvailable(void *const *api) {
    return api && api[0] && api[1] && api[3] && api[4] && api[5] && api[8];
}

// The table and two output fields are from the guarded MTK generic film-grain
// branch. Keep this boundary portable so its writes and API calls can be tested.
inline bool apply(const Params &p, void *const *api, void *handle, void *output) {
    if (!handle || !output || !apiAvailable(api) || p.type != 2 ||
        !std::isfinite(p.amount) || p.amount <= 0 || p.amount > 1) return false;
    for (float v : p.values) if (!std::isfinite(v) || v < 0 || v > 1) return false;
    using Float = void (*)(void *, float);
    using NamedFloat = void (*)(void *, const char *, float);
    using NamedInt = void (*)(void *, const char *, int);
    using NamedBool = void (*)(void *, const char *, bool);
    reinterpret_cast<NamedInt>(api[5])(handle, "Grain Type", p.type);
    reinterpret_cast<Float>(api[0])(handle, p.values[0]);
    reinterpret_cast<Float>(api[1])(handle, p.values[1]);
    reinterpret_cast<Float>(api[3])(handle, p.values[2]);
    const char *uniforms[] = {"Grain Color Ratio", "Grain Midtones", "Grain Shadows"};
    for (int i = 0; i < 3; ++i) reinterpret_cast<NamedFloat>(api[8])(handle, uniforms[i], p.values[i + 3]);
    reinterpret_cast<NamedBool>(api[4])(handle, "Grain Is Colored", p.coloured);
    reinterpret_cast<NamedBool>(api[4])(handle, "Grain Render Finally", p.finally);
    static_cast<uint8_t *>(output)[0x40] = 1;
    std::memcpy(static_cast<char *>(output) + 0x44, &p.amount, sizeof(float));
    return true;
}
}
