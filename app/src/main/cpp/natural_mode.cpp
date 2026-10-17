// PME110's guided filter is an OpenCL kernel. Change only its epsilon argument.
#include <atomic>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <jni.h>
#include <mutex>
#include <string>
#include <unistd.h>
#include "native_hooks.h"
#include "firmware_guard.h"
#include "mapped_library.h"

namespace {
constexpr char kRoot[] = "/data/user/0/com.oplus.camera/files/jiege/natural";
constexpr char kStockJson[] = "/odm/etc/camera/conf_tuning_params.json";
constexpr char kKernel[] = "HDRtransform_gdf_mul5_float_c1_buf";
struct KernelArg { size_t size; const void *value; };
struct KernelArgs { KernelArg *begin, *end; };
using RunKernel = int (*)(void *, const char *, const std::string &, KernelArgs &, unsigned, const size_t *, const size_t *, const size_t *, bool);
struct ApiHook { RunKernel run{}; } apis[3];
std::atomic<unsigned> apiHooks{};
using FrameProcess = int (*)(void *);
FrameProcess originalFrameStages[6]{};
std::atomic<unsigned> photoScopes{}, otherScopes{}, scopedFrames{}, frameHooks{};
std::atomic<bool> compatible{}, modeEnabled{}, configServed{};
std::atomic<unsigned> calls{}, changed{}, totalArgs{};
std::atomic<float> stockEps{}, appliedEps{};
std::atomic<int> lastResult{-999};
std::mutex statusMutex, hookMutex;

void writeStatus() {
    std::lock_guard<std::mutex> lock(statusMutex);
    char path[256];
    std::snprintf(path, sizeof(path), "%s/status", kRoot);
    if (FILE *file = std::fopen(path, "we")) {
        std::fprintf(file, "tuning json: %s\nbackend: MTK-OpenCL ready=%d guard=%d hook=%d\nkernel calls=%u changed=%u mode=%d allArgs=%u result=%d\neps: stock=%.9g applied=%.9g\nframe hooks=%u count=%u photo=%u other=%u\n",
            configServed.load() ? "edited copy" : "stock", int(compatible.load() && apiHooks.load()),
            int(compatible.load()), int(apiHooks.load()), calls.load(), changed.load(), int(modeEnabled.load()), totalArgs.load(), lastResult.load(), double(stockEps.load()), double(appliedEps.load()), frameHooks.load(), scopedFrames.load(), photoScopes.load(), otherScopes.load());
        std::fclose(file);
    }
}

float wantedScale() {
    // Deferred work can finish after the UI switches modes. Scope the native
    // capture itself, including its workers, instead of trusting current UI mode.
    if (!photoScopes.load() || otherScopes.load()) return 1;
    char path[256];
    std::snprintf(path, sizeof(path), "%s/soften", kRoot);
    FILE *file = std::fopen(path, "re");
    if (!file) return 1;
    float epsilon = 0;
    bool ok = std::fscanf(file, "%f", &epsilon) == 1;
    std::fclose(file);
    // The UI maps 0..100% from 1e-7 to 1e-3. Preserve this firmware's actual
    // stock value, scaling its regularisation by 1..10000 instead of assuming it.
    return ok && std::isfinite(epsilon) && epsilon >= 1e-7f && epsilon <= 1.001e-3f ? epsilon / 1e-7f : 1;
}

template<int I>
int runKernel(void *object, const char *source, const std::string &name, KernelArgs &args, unsigned dim,
              const size_t *offset, const size_t *global, const size_t *local, bool wait) {
    ++totalArgs;
    // clSetKernelArg copies scalar values before runKernel returns. Restore the
    // builder even if the vendor implementation exits by throwing an exception.
    struct RestoreArg {
        KernelArg *arg{};
        const void *saved{};
        ~RestoreArg() { if (arg) arg->value = saved; }
    } restore;
    float stock = 0, applied = 0;
    int index = name == "tmc_upsample_merge_fastgdf" && I == 2 ? 7 : name == kKernel ? 4 : -1;
    int count = index == 7 ? 14 : 6;
    bool target = index >= 0 && args.end - args.begin == count && args.begin[index].size == 4 && args.begin[index].value;
    if (target) {
        std::memcpy(&stock, args.begin[index].value, 4);
        target = std::isfinite(stock) && stock > 0 && stock <= 1;
        if (target) {
            applied = std::fmin(stock * wantedScale(), 1.0f);
            restore.arg = &args.begin[index];
            restore.saved = args.begin[index].value;
            args.begin[index].value = &applied;
        }
    }
    int result = apis[I].run(object, source, name, args, dim, offset, global, local, wait);
    if (restore.arg) {
        lastResult.store(result);
        ++calls;
        if (result == 0 && applied != stock) ++changed;
        stockEps.store(stock); appliedEps.store(applied);
    }
    if (target || totalArgs.load() % 128 == 1) writeStatus();
    return result;
}

template<int I>
int frameStage(void *frame) {
    if (!frame) return originalFrameStages[I](frame);
    uint32_t mode = *reinterpret_cast<uint32_t *>(static_cast<char *>(frame) + 0x18);
    auto &scopes = mode == 0 ? photoScopes : otherScopes;
    ++scopes;
    ++scopedFrames;
    struct Exit { std::atomic<unsigned> &scopes; ~Exit() { --scopes; } } exit{scopes};
    return originalFrameStages[I](frame);
}
}

extern "C" JNIEXPORT void JNICALL
Java_local_jiege_hook_natural_NaturalMode_setSoftenMode(JNIEnv *, jclass, jboolean enabled) {
    modeEnabled.store(enabled == JNI_TRUE);
    writeStatus();
}

void onLibraryLoadedForNatural(HookFunction hook, const char *name, void *handle) {
    if (!name || !handle || !hook) return;
    if (std::strstr(name, "HDRTransform") || std::strstr(name, "HybridRaw"))
        activateLoadedLibrariesForNatural(hook);
    writeStatus();
}

void activateLoadedLibrariesForNatural(HookFunction hook) {
    if (!hook || (apiHooks.load() == 3 && frameHooks.load() == 6)) return;
    std::lock_guard<std::mutex> lock(hookMutex);
    mappedLibraries([&](const std::string &path, void *base) {
        if (path.find("libAlgoInterface.so") != std::string::npos && hasBuildId(base, "d8bd771877bb9f58cb6ee198b68af51a")) {
            const char *symbols[] = {
                "_ZN7android25hybridRawProcessStagePostEPNS_15AlgoProcessDataE",
                "_ZN7android24hybridRawProcessStageIPEEPNS_15AlgoProcessDataE",
                "_ZN7android22hybridRawPostProcessV3EPNS_15AlgoProcessDataE",
                "_ZN7android24hybridRawProcessStageOneEPNS_15AlgoProcessDataE",
                "_ZN7android28hybridRawProcessProfStageOneEPNS_15AlgoProcessDataE",
                "_ZN7android22hybridRawProcessAllItfEPNS_15AlgoProcessDataE"};
            void *replacements[] = {reinterpret_cast<void *>(frameStage<0>), reinterpret_cast<void *>(frameStage<1>), reinterpret_cast<void *>(frameStage<2>),
                                    reinterpret_cast<void *>(frameStage<3>), reinterpret_cast<void *>(frameStage<4>), reinterpret_cast<void *>(frameStage<5>)};
            for (int j = 0; j < 6; ++j) if (!originalFrameStages[j]) {
                void *target = mappedFunction(path, base, symbols[j]);
                if (target && hook(target, replacements[j], reinterpret_cast<void **>(&originalFrameStages[j])) == 0) ++frameHooks;
            }
            return;
        }
        int i = path.find("libOPAlgoCamHDRTransformCamera.so") != std::string::npos ? 0
              : path.find("libOPAlgoCamHDRTransformQuick.so") != std::string::npos ? 1
              : path.find("libOPAlgoCamHybridRaw.so") != std::string::npos ? 2 : -1;
        if (i < 0 || apis[i].run) return;
        const char *ids[] = {"f917c0db2a792cff118699767eeefee293cb1b4f", "b4e96c967b848c576c4dbae3b2143a0ebba4be14", "8dc491da1d0ffafc951778063c775b23b34c3000"};
        if (!hasBuildId(base, ids[i])) return;
        void *target = mappedFunction(path, base, "_ZN9framework3ocl8CLEngine9runKernelEPKcRKNSt6__ndk112basic_stringIcNS4_11char_traitsIcEENS4_9allocatorIcEEEERNS0_19CLKernelArgsBuilderEjPKmSG_SG_b");
        void *replacements[] = {reinterpret_cast<void *>(runKernel<0>), reinterpret_cast<void *>(runKernel<1>), reinterpret_cast<void *>(runKernel<2>)};
        if (target && hook(target, replacements[i], reinterpret_cast<void **>(&apis[i].run)) == 0) {
            compatible.store(true);
            ++apiHooks;
        }
    });
    writeStatus();
}

const char *naturalRemapPath(const char *path, char *buf, size_t n) {
    if (std::strcmp(path, kStockJson)) return nullptr;
    std::snprintf(buf, n, "%s/conf_tuning_params.json", kRoot);
    bool served = access(buf, R_OK) == 0;
    configServed.store(served);
    writeStatus();
    return served ? buf : nullptr;
}
