// Extra master grain on the original PME110 Meishe V2 path. The upstream
// Qualcomm instruction patches are deliberately not used on this firmware.
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <mutex>
#include <string>
#include "native_hooks.h"
#include "firmware_guard.h"
#include "mtk_grain.h"

namespace {
using ReadInt = int (*)(void *, const void *, int);
using ReadFloat = float (*)(void *, const void *, float);
using ReadBool = int (*)(void *, const void *, int);
using SetParams = uintptr_t (*)(void *, const void *, const void *, void *, void **, const int *);
ReadInt originalInt;
ReadFloat readFloat;
ReadBool readBool;
SetParams originalParams;
bool (*parameterApiReady)();
void **parameterApi;
uintptr_t gateReturn;
std::atomic<bool> ready{};
std::atomic<unsigned> frames{}, gates{}, applied{};
std::mutex statusMutex;
struct Capture { void *frame, *settings; float amount; };
thread_local const Capture *capture;

static_assert(sizeof(std::string) == 24, "Vendor libc++ string ABI changed");

bool apiAvailable() {
    return parameterApiReady && parameterApiReady() && mtkgrain::apiAvailable(parameterApi);
}

float number(void *settings, const char *key) {
    const std::string name(key);
    return readFloat(settings, &name, NAN);
}
int integer(void *settings, const char *key, int fallback) {
    const std::string name(key);
    return originalInt(settings, &name, fallback);
}
bool boolean(void *settings, const char *key) {
    const std::string name(key);
    return readBool(settings, &name, 0) != 0;
}
bool keyIsBlackSoft(const void *key) {
    // The call site constructs this 16-character key as a short libc++ string.
    const auto *p = static_cast<const uint8_t *>(key);
    return p && p[0] == 32 && std::memcmp(p + 1, "blacksoft_enable", 17) == 0;
}
int getInt(void *settings, const void *key, int fallback) {
    int result = originalInt(settings, key, fallback);
    // Admit the empty-filter node at its one verified gate read only. The
    // parameter mapper still reads the user's real soft-light setting.
    if (ready.load() && capture && capture->settings == settings && !result && keyIsBlackSoft(key) &&
        reinterpret_cast<uintptr_t>(__builtin_return_address(0)) == gateReturn) {
        ++gates;
        return 1;
    }
    return result;
}
void status(float amount, bool success, const mtkgrain::Params *parameters = nullptr) {
    std::lock_guard<std::mutex> lock(statusMutex);
    if (FILE *file = std::fopen("/data/user/0/com.oplus.camera/files/jiege/master-grain-status", "we")) {
        std::fprintf(file, "MTK V2 ready=%d frames=%u gate=%u applied=%u last=%d amount=%.6g\n",
                     int(ready.load()), frames.load(), gates.load(), applied.load(), int(success), double(amount));
        if (parameters) {
            std::fprintf(file, "grain type=%d highlight=%.6g size=%.6g roughness=%.6g colour=%.6g midtones=%.6g shadows=%.6g\n",
                         parameters->type, double(parameters->values[0]), double(parameters->values[1]),
                         double(parameters->values[2]), double(parameters->values[3]),
                         double(parameters->values[4]), double(parameters->values[5]));
        }
        std::fclose(file);
    }
}
uintptr_t setParams(void *frame, const void *type, const void *op, void *parameters, void **handle, const int *stage) {
    uintptr_t result = originalParams(frame, type, op, parameters, handle, stage);
    if (!capture || capture->frame != frame || !parameters || !handle || !*handle || !stage || *stage == 1) return result;
    bool success = false;
    mtkgrain::Params grain{};
    do {
        // Exact table layout, from this Build ID's generic film-grain branch:
        // +0 highlight, +8 size, +18 roughness, +20 named bool,
        // +28 named int, +40 named float. All other filter parameters stay intact.
        if (!apiAvailable()) break;
        const char *keys[] = {"filter_grain_highlight", "filter_grain_size", "filter_grain_roughness",
                              "filter_grain_color_ratio", "filter_grain_midtones", "filter_grain_shadows"};
        grain.amount = capture->amount;
        for (int i = 0; i < 6; ++i) {
            grain.values[i] = number(capture->settings, keys[i]);
        }
        grain.type = integer(capture->settings, "filter_grain_type", -1);
        grain.coloured = boolean(capture->settings, "filter_grain_color_enable");
        grain.finally = boolean(capture->settings, "filter_grain_finally_enable");
        success = mtkgrain::apply(grain, parameterApi, *handle, parameters);
        if (success) ++applied;
    } while (false);
    status(capture->amount, success, &grain);
    return result;
}
}

void installMasterGrain(HookFunction hook, void *base) {
    if (ready.load() || !hook || !hasBuildId(base, "d8bd771877bb9f58cb6ee198b68af51a")) return;
    auto at = [base](uintptr_t offset) { return static_cast<char *>(base) + offset; };
    readFloat = reinterpret_cast<ReadFloat>(at(0xa41650));
    readBool = reinterpret_cast<ReadBool>(at(0xa3a8d0));
    parameterApiReady = reinterpret_cast<decltype(parameterApiReady)>(at(0x1000a10));
    parameterApi = reinterpret_cast<void **>(at(0x3065428));
    gateReturn = reinterpret_cast<uintptr_t>(at(0x1006c98));
    if (!originalInt && hook(at(0xa252d0), reinterpret_cast<void *>(getInt), reinterpret_cast<void **>(&originalInt)) != 0) return;
    if (!originalParams && hook(at(0x1000cb0), reinterpret_cast<void *>(setParams), reinterpret_cast<void **>(&originalParams)) != 0) return;
    ready.store(originalInt && originalParams);
    status(0, false);
}

int processWithMasterGrain(void *frame, int stage, bool master, int (*original)(void *, int)) {
    if (!ready.load() || !frame || !master || !apiAvailable()) return original(frame, stage);
    void *settings = *reinterpret_cast<void **>(static_cast<char *>(frame) + 0x8110);
    if (!settings) return original(frame, stage);
    float marker = number(settings, "filter_grain_amount");
    if (!std::isfinite(marker) || marker >= 0 || marker < -1) return original(frame, stage);
    Capture context{frame, settings, -marker};
    struct Scope {
        const Capture *previous;
        ~Scope() { capture = previous; }
    } scope{capture};
    capture = &context;
    ++frames;
    return original(frame, stage);
}
