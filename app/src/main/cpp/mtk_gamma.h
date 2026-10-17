#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

// PME110 PostGamma::generateGamma, original HybridRaw SHA256 500d9d5a...94894b.
// The firmware samples densely near black; uniform i/256 is incorrect.
constexpr std::array<uint16_t, 257> kMtkGammaX = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
    32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,
    48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63,
    64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95,
    96, 97, 98, 99, 199, 299, 399, 499, 599, 699, 799, 899, 999, 1099, 1199, 1299,
    1399, 1499, 1599, 1699, 1799, 1899, 1999, 2099, 2199, 2299, 2399, 2499, 2599, 2699, 2799, 2899,
    2999, 3099, 3199, 3299, 3399, 3499, 3599, 3699, 3799, 3899, 3999, 4099, 4199, 4299, 4399, 4499,
    4599, 4699, 4799, 4899, 4999, 5099, 5199, 5299, 5399, 5499, 5599, 5699, 5799, 6396, 6993, 7591,
    8188, 8785, 9383, 9980, 10577, 11175, 11772, 12369, 12967, 13564, 14162, 14759, 15356, 15954, 16551, 17148,
    17746, 18343, 18940, 19538, 20135, 20733, 21330, 21927, 22525, 23122, 23719, 24317, 24914, 25511, 26109, 26706,
    27303, 27901, 28498, 29096, 29693, 30290, 30888, 31485, 32082, 32680, 33277, 33874, 34472, 35069, 35667, 36264,
    36861, 37459, 38056, 38653, 39251, 39848, 40445, 41043, 41640, 42237, 42835, 43432, 44030, 44627, 45224, 45822,
    46419, 47016, 47614, 48211, 48808, 49406, 50003, 50601, 51198, 51795, 52393, 52990, 53587, 54185, 54782, 55379,
    55977, 56574, 57171, 57769, 58366, 58964, 59561, 60158, 60756, 61353, 61950, 62548, 63145, 63742, 64340, 64937,
    65535,
};

inline bool validMtkGamma(const std::vector<float> &gamma) {
    if (gamma.size() != kMtkGammaX.size() || gamma.front() != 0 || gamma.back() < 0.1f) return false;
    float previous = 0;
    for (float v : gamma) {
        if (!std::isfinite(v) || v < previous || v > 1) return false;
        previous = v;
    }
    return true;
}

inline bool decodeMtkGamma(const int32_t *raw, size_t count, std::vector<float> &out) {
    out.clear();
    if (!raw || count != kMtkGammaX.size()) return false;
    for (size_t i = 0; i < count; ++i) out.push_back(raw[i] / 4095.0f);
    if (validMtkGamma(out)) return true;
    out.clear();
    return false;
}

inline double inverseMtkGamma(const std::vector<float> &gamma, double code) {
    if (code <= gamma.front()) return 0;
    if (code >= gamma.back()) return 1;
    size_t hi = std::upper_bound(gamma.begin(), gamma.end(), float(code)) - gamma.begin();
    size_t lo = hi - 1;
    double f = (code - gamma[lo]) / (gamma[hi] - gamma[lo]);
    return (kMtkGammaX[lo] + f * (kMtkGammaX[hi] - kMtkGammaX[lo])) / 65535.0;
}

inline float mtkExposureFromSrgb(const float *raw, size_t count) {
    if (!raw || count != kMtkGammaX.size()) return NAN;
    std::vector<float> gamma(count);
    for (size_t i = 0; i < count; ++i) gamma[i] = raw[i] / 1023.0f;
    if (!validMtkGamma(gamma)) return NAN;
    // The native ISP curve locates display 18% grey in sensor-linear space.
    // Sensor-normalised 0.18 itself is not a metered middle grey.
    constexpr double code18 = 0.46135612950044164;
    double grey = inverseMtkGamma(gamma, code18);
    double ev = std::log2(0.18 / grey);
    return grey > 0 && std::isfinite(ev) && std::abs(ev) <= 12 ? float(ev) : NAN;
}
