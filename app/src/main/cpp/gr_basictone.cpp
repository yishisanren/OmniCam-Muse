// GR port, native half.
//
// The GR mode reuses the professional (master) capture pipeline. GR frames are recognised by the
// gr_effect_size APS setting (63) and get:
//   * BasicTone: the GR LMT/SC/CWCM tree (staged by service.sh) instead of the host ODM tree;
//   * no artistic vignette from the V1 vignette parameters;
//   * the original MTK Meishe V2 hardware-buffer path (the V1 replacement produces zero planes).
// Master frames (capture mode 33) get the live master-colour LMT instead (master_color.cpp), unless
// files/jiege/mastercolor/off exists.
// PME110 MTK offsets are accepted only with the inspected ELF Build IDs.
#include <android/log.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <mutex>
#include <string>
#include <unordered_map>
#include <atomic>
#include <fstream>
#include <vector>

#include "native_hooks.h"
#include "firmware_guard.h"

namespace {

constexpr char kTag[] = "RicohGrPort";
constexpr char kGrLmtPath[] = "/data/user/0/com.oplus.camera/files/ricoh_gr/lmt";
constexpr char kHostLmtPath[] = "/odm/etc/camera/basictone/lmt";
constexpr uint32_t kMasterCaptureMode = 33;

// APS setting keys use libc++'s 24-byte short-string layout on this firmware.
struct alignas(8) SettingKey {
    uint8_t length;
    char text[23];
};
const SettingKey kGrSizeKey = {28, "gr_effect_size"};

int (*getSettingInt)(void *settings, const void *key, int fallback);
void (*originalGetLmtParams)(void *, void *, int);
void (*originalGetVigParams)(void *, void *, void *);
int (*originalFilterProcessV2)(void *, int);
uintptr_t (*originalProcessCore)(void *, void *, void *, void *, void *);
uintptr_t (*originalLoadLut)(void *, int);
std::mutex hookMutex;
void *algoBase;
std::atomic<unsigned> installedHooks{};
std::atomic<unsigned> grFrames{};
std::atomic<unsigned> grLutLoads{};
std::atomic<unsigned> grFilterCalls{};
std::atomic<int> lastGrResult{-999};

// getLmtParamsV1 runs per frame before BasicTone; remember which LUT tree belongs to each parameter
// block so processCore/loadLut (which no longer see the frame) can pick it.
enum Profile { kUnknown = -1, kHost = 0, kGr = 1, kMaster = 2 };
struct FrameProfile {
    Profile profile = kHost;
    bool master = false;  // a master capture, whatever LUT tree it uses
    MasterColorCapture capture;
};
std::mutex profileMutex;
std::unordered_map<void *, FrameProfile> frameProfiles;
thread_local int activeProfile = kUnknown;
thread_local bool activeMaster = false;
thread_local std::string activeMasterDir;

bool isGrFrame(void *frame) {
    if (!frame || !getSettingInt) return false;
    void *settings = *reinterpret_cast<void **>(static_cast<char *>(frame) + 0x8110);
    return settings && getSettingInt(settings, &kGrSizeKey, 0) == 63;
}

void rememberLmtParams(void *parameters, void *frame, int stage, int cct) {
    bool gr = isGrFrame(frame);
    if (gr) ++grFrames;
    FrameProfile profile;
    profile.profile = gr ? kGr : kHost;
    uint32_t mode = *reinterpret_cast<uint32_t *>(static_cast<char *>(frame) + 0x18);
    profile.master = !gr && mode == kMasterCaptureMode;
    std::string look;
    float exposureEv = 0, toneWeight = 1, colourWeight = 1;
    std::array<float, 4> param{NAN, NAN, NAN, NAN};
    std::array<float, 3> density{1, 1, 1};
    if (!gr && mode == kMasterCaptureMode && masterColorLook(look, exposureEv, toneWeight, colourWeight, density, param)) {
        if (masterColorCaptureInfo(frame, cct, profile.capture)) {
            profile.capture.look = look;
            profile.capture.exposureEv += exposureEv;
            profile.capture.toneWeight = toneWeight;
            profile.capture.colourWeight = colourWeight;
            profile.capture.density = density;
            profile.capture.param = param;
            profile.profile = kMaster;
        }
    }
    {
        std::lock_guard<std::mutex> lock(profileMutex);
        frameProfiles[parameters] = profile;
    }
    if (!gr) {
        if (FILE *status = std::fopen("/data/user/0/com.oplus.camera/files/jiege/mastercolor/frame-status", "we")) {
            std::fprintf(status, "mode=%u master=%d selected=%d\n", mode, int(profile.master), int(profile.profile));
            std::fclose(status);
        }
    }
}

void getLmtParams(void *parameters, void *frame, int stage) {
    originalGetLmtParams(parameters, frame, stage);
    // V1 ProcessParam +0x3c is CCT. The older layout instead uses frame metadata.
    rememberLmtParams(parameters, frame, stage,
        *reinterpret_cast<int32_t *>(static_cast<char *>(parameters) + 0x3c));
}


void getVigParams(void *parameters, void *frame, void *planes) {
    originalGetVigParams(parameters, frame, planes);
    if (isGrFrame(frame)) static_cast<uint8_t *>(parameters)[0x1a] = 0;
}

int filterProcessV2(void *frame, int stage) {
    bool gr = isGrFrame(frame);
    // Preserve the original MTK buffer lifecycle and request mode. On this firmware,
    // replacing V2 with V1 returns success but leaves zero YUV planes (a green JPEG).
    uint32_t mode = frame ? *reinterpret_cast<uint32_t *>(static_cast<char *>(frame) + 0x18) : 0;
    int result = processWithMasterGrain(frame, stage, !gr && mode == kMasterCaptureMode, originalFilterProcessV2);
    if (gr) {
        ++grFilterCalls;
        lastGrResult = result;
    }
    return result;
}

uintptr_t processCore(void *object, void *input, void *output, void *parameters, void *metadata) {
    int previous = activeProfile;
    bool previousMaster = activeMaster;
    std::string previousDir = activeMasterDir;
    activeProfile = kUnknown;
    activeMaster = false;
    FrameProfile profile;
    bool known = false;
    {
        std::lock_guard<std::mutex> lock(profileMutex);
        auto found = frameProfiles.find(parameters);
        if (found != frameProfiles.end()) {
            profile = found->second;
            known = true;
            frameProfiles.erase(found);
        }
    }
    if (known) {
        activeProfile = profile.profile;
        activeMaster = profile.master;
        if (profile.profile == kMaster) {
            // BasicTone_OGL::processCore logs Image +0 / +4 as the width and height.
            int width = *static_cast<int32_t *>(input), height = static_cast<int32_t *>(input)[1];
            activeMasterDir = masterColorCaptureDir(profile.capture, width, height);
            if (activeMasterDir.empty()) activeProfile = kHost;
        }
    }
    uintptr_t result = originalProcessCore(object, input, output, parameters, metadata);
    activeProfile = previous;
    activeMaster = previousMaster;
    activeMasterDir = previousDir;
    return result;
}

uintptr_t loadLut(void *object, int mode) {
    // Intermediate ODT passes carry no profile; they keep the object's current LUTs.
    if (activeProfile != kUnknown) {
        char *lmtPath = static_cast<char *>(object) + 0x008;  // 256-byte path buffer
        const char *desired = activeProfile == kGr ? kGrLmtPath
                            : activeProfile == kMaster ? activeMasterDir.c_str() : kHostLmtPath;
        if (std::strlen(desired) < 240 && std::strcmp(lmtPath, desired) != 0) {
            std::strcpy(lmtPath, desired);
            // The path is not part of the vendor cache key, so a profile switch forces a reload.
            *reinterpret_cast<int *>(static_cast<char *>(object) + 0xeb0) = -1;
            if (activeProfile == kGr) ++grLutLoads;
            __android_log_print(ANDROID_LOG_INFO, kTag, "BasicTone profile=%s path=%s",
                                activeProfile == kGr ? "GR" : activeProfile == kMaster ? "master-colour" : "host", desired);
        }
        if (activeProfile == kMaster) {
            if (FILE *status = std::fopen("/data/user/0/com.oplus.camera/files/jiege/mastercolor/applied-status", "we")) {
                std::fprintf(status, "LMT applied: %s\n", desired);
                std::fclose(status);
            }
        }
    }
    return originalLoadLut(object, mode);
}

bool installGrAddress(HookFunction hook, void *address, void *replacement, void **backup, unsigned flag) {
    if (!hook || !address || hook(address, replacement, backup) != 0) return false;
    installedHooks.fetch_or(flag);
    return true;
}

void hookAlgoBase(HookFunction hook, void *base) {
    std::lock_guard<std::mutex> lock(hookMutex);
    if (!hasBuildId(base, "d8bd771877bb9f58cb6ee198b68af51a")) return;
    algoBase = base;
    auto at = [base](uintptr_t offset) { return static_cast<char *>(base) + offset; };
    getSettingInt = reinterpret_cast<decltype(getSettingInt)>(at(0xa252d0));
    installMasterGrain(hook, base);
    if (!originalGetLmtParams) installGrAddress(hook, at(0x1598bc0), reinterpret_cast<void *>(getLmtParams),
        reinterpret_cast<void **>(&originalGetLmtParams), 1);
    if (!originalFilterProcessV2) installGrAddress(hook, at(0x1006bc0), reinterpret_cast<void *>(filterProcessV2),
        reinterpret_cast<void **>(&originalFilterProcessV2), 2);
    if (!originalGetVigParams) installGrAddress(hook, at(0x1597520), reinterpret_cast<void *>(getVigParams),
        reinterpret_cast<void **>(&originalGetVigParams), 4);
}

void hookBasicToneBase(HookFunction hook, void *base) {
    std::lock_guard<std::mutex> lock(hookMutex);
    if (!hasBuildId(base, "b125b367260781e1eee0aeec834b3dc91501a3aa")) return;
    auto at = [base](uintptr_t offset) { return static_cast<char *>(base) + offset; };
    if (!originalProcessCore) installGrAddress(hook, at(0x53b90), reinterpret_cast<void *>(processCore),
        reinterpret_cast<void **>(&originalProcessCore), 8);
    if (!originalLoadLut) installGrAddress(hook, at(0x51934), reinterpret_cast<void *>(loadLut),
        reinterpret_cast<void **>(&originalLoadLut), 16);
}

}  // namespace

bool basicToneMasterFrame() {
    return activeMaster;
}

void *resolveAlgoMetadata() {
    return algoBase ? static_cast<char *>(algoBase) + 0xa211b0 : nullptr;
}

void activateLoadedLibrariesForGr(HookFunction hook) {
    std::ifstream maps("/proc/self/maps");
    std::string line;
    while (std::getline(maps, line)) {
        if (line.find("libAlgoInterface.so") == std::string::npos &&
            line.find("libBasicTonePhoto") == std::string::npos) continue;
        unsigned long start, end, offset;
        char permissions[5]{};
        if (std::sscanf(line.c_str(), "%lx-%lx %4s %lx", &start, &end, permissions, &offset) != 4 ||
            offset != 0 || permissions[0] != 'r') continue;
        if (line.find("libAlgoInterface.so") != std::string::npos)
            hookAlgoBase(hook, reinterpret_cast<void *>(start));
        else hookBasicToneBase(hook, reinterpret_cast<void *>(start));
    }
}

unsigned grNativeHookStatus() { return installedHooks.load(); }
unsigned grNativeFrameCount() { return grFrames.load(); }
std::string grNativeDiagnostics() {
    return " lutLoads=" + std::to_string(grLutLoads.load()) +
           " backend=MTK-V2 calls=" + std::to_string(grFilterCalls.load()) +
           " filter=" + std::to_string(lastGrResult.load());
}

void onLibraryLoadedForGr(HookFunction hook, const char *name, void *handle) {
    if (std::strstr(name, "libAlgoInterface.so")) {
        if (!gAlgoInterfaceHandle) gAlgoInterfaceHandle = handle;
        Dl_info info{};
        void *address = dlsym(handle, "_ZN7android14getLmtParamsV1ER12ProcessParamPNS_15AlgoProcessDataEi");
        if (address && dladdr(address, &info)) hookAlgoBase(hook, info.dli_fbase);
    } else if (std::strstr(name, "libBasicTonePhotoX9.so") || std::strstr(name, "libBasicTonePhoto.so")) {
        Dl_info info{};
        void *address = dlsym(handle, "_ZN13BasicTone_OGL11processCoreEP5ImageS1_PvS2_");
        if (address && dladdr(address, &info)) hookBasicToneBase(hook, info.dli_fbase);
    }
}
