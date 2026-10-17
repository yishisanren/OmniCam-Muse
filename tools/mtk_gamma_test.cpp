#include "mtk_gamma.h"
#include <cassert>
#include <iostream>
#include <limits>

int main() {
    std::vector<int32_t> raw;
    for (uint16_t x : kMtkGammaX) raw.push_back(int32_t(std::lround(std::sqrt(x / 65535.0) * 4095)));
    std::vector<float> gamma;
    assert(decodeMtkGamma(raw.data(), raw.size(), gamma));
    // The real hardware grid is very dense near black. Uniform i/256 would
    // return 64/256 here instead of 64/65535, over 250 times the actual light.
    assert(std::fabs(inverseMtkGamma(gamma, gamma[64]) - 64 / 65535.0) < 1e-9);
    for (size_t i = 0; i < gamma.size(); ++i) {
        auto low = std::lower_bound(gamma.begin(), gamma.end(), gamma[i]) - gamma.begin();
        auto high = std::upper_bound(gamma.begin(), gamma.end(), gamma[i]) - gamma.begin() - 1;
        double inverse = inverseMtkGamma(gamma, gamma[i]);
        // Quantised plateaus lose the original location: any point inside that
        // equal-code interval is valid. Strictly rising knots invert exactly.
        assert(inverse + 1e-6 >= kMtkGammaX[low] / 65535.0);
        assert(inverse - 1e-6 <= kMtkGammaX[high] / 65535.0);
    }
    assert(inverseMtkGamma(gamma, -1) == 0 && inverseMtkGamma(gamma, 2) == 1);
    assert(!decodeMtkGamma(raw.data(), 256, gamma));
    raw[100] = -1;
    assert(!decodeMtkGamma(raw.data(), raw.size(), gamma));
    raw[100] = raw[99] - 1;
    assert(!decodeMtkGamma(raw.data(), raw.size(), gamma));
    raw[100] = 5000;
    assert(!decodeMtkGamma(raw.data(), raw.size(), gamma));
    std::vector<float> srgb;
    for (uint16_t x : kMtkGammaX) {
        double linear = std::min(x / 65535.0 * 18, 1.0);
        double encoded = linear <= .0031308 ? 12.92 * linear : 1.055 * std::pow(linear, 1 / 2.4) - .055;
        srgb.push_back(float(encoded * 1023));
    }
    assert(std::abs(mtkExposureFromSrgb(srgb.data(), srgb.size()) - std::log2(18.0)) < .03);
    assert(std::isnan(mtkExposureFromSrgb(srgb.data(), 256)));
    srgb[100] = NAN;
    assert(std::isnan(mtkExposureFromSrgb(srgb.data(), srgb.size())));
    std::cout << "MtkGammaTest: PASS\n";
}
