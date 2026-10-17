#include "mtk_grain.h"
#include <array>
#include <cassert>
#include <cstdio>
#include <map>
#include <string>

struct Calls {
    std::map<std::string, float> values;
    int count{};
};
void high(void *c, float v) { auto &x = *static_cast<Calls *>(c); x.values["highlight"] = v; ++x.count; }
void size(void *c, float v) { auto &x = *static_cast<Calls *>(c); x.values["size"] = v; ++x.count; }
void rough(void *c, float v) { auto &x = *static_cast<Calls *>(c); x.values["roughness"] = v; ++x.count; }
void number(void *c, const char *key, float v) { auto &x = *static_cast<Calls *>(c); x.values[key] = v; ++x.count; }
void integer(void *c, const char *key, int v) { number(c, key, float(v)); }
void boolean(void *c, const char *key, bool v) { number(c, key, float(v)); }

int main() {
    void *api[9]{};
    api[0] = reinterpret_cast<void *>(high);
    api[1] = reinterpret_cast<void *>(size);
    api[3] = reinterpret_cast<void *>(rough);
    api[4] = reinterpret_cast<void *>(boolean);
    api[5] = reinterpret_cast<void *>(integer);
    api[8] = reinterpret_cast<void *>(number);
    mtkgrain::Params p{.5f, {.85f, .7f, .33f, .7f, .9f, .89f}, 2, true, true};
    std::array<uint8_t, 128> output;
    output.fill(0xa5);
    const auto before = output;
    Calls calls;
    assert(mtkgrain::apply(p, api, &calls, output.data()));
    assert(calls.count == 9 && calls.values.size() == 9);
    assert(calls.values.at("Grain Type") == 2 && calls.values.at("size") == .7f);
    assert(calls.values.at("Grain Midtones") == .9f && calls.values.at("Grain Shadows") == .89f);
    assert(calls.values.at("Grain Color Ratio") == .7f && calls.values.at("highlight") == .85f);
    assert(calls.values.at("roughness") == .33f && calls.values.at("Grain Is Colored") == 1);
    assert(calls.values.at("Grain Render Finally") == 1);
    float amount;
    std::memcpy(&amount, output.data() + 0x44, sizeof(amount));
    assert(amount == .5f && output[0x40] == 1);
    for (size_t i = 0; i < output.size(); ++i)
        if (i != 0x40 && (i < 0x44 || i >= 0x48)) assert(output[i] == before[i]);
    auto expectRejected = [&](const mtkgrain::Params &invalid, void **table, void *handle, void *out) {
        calls = {};
        output = before;
        assert(!mtkgrain::apply(invalid, table, handle, out));
        assert(calls.count == 0 && output == before);
    };
    expectRejected(p, nullptr, &calls, output.data());
    expectRejected(p, api, nullptr, output.data());
    expectRejected(p, api, &calls, nullptr);
    for (int slot : {0, 1, 3, 4, 5, 8}) {
        void *saved = api[slot]; api[slot] = nullptr;
        expectRejected(p, api, &calls, output.data()); api[slot] = saved;
    }
    for (float amount : {0.f, -.5f, 1.1f, NAN, INFINITY}) {
        auto bad = p; bad.amount = amount; expectRejected(bad, api, &calls, output.data());
    }
    for (int i = 0; i < 6; ++i) for (float value : {-.1f, 1.1f, NAN, INFINITY}) {
        auto bad = p; bad.values[i] = value; expectRejected(bad, api, &calls, output.data());
    }
    auto wrongType = p; wrongType.type = -1; expectRejected(wrongType, api, &calls, output.data());
    for (float edge : {0.f, 1.f}) {
        auto boundary = p;
        boundary.amount = 1.f;
        boundary.values[1] = edge;
        calls = {};
        output = before;
        assert(mtkgrain::apply(boundary, api, &calls, output.data()));
        assert(calls.count == 9 && calls.values.at("size") == edge);
        std::memcpy(&amount, output.data() + 0x44, sizeof(amount));
        assert(amount == 1.f && output[0x40] == 1);
    }
    std::puts("MtkGrainTest: PASS (native fields, all 9 parameter calls, rejected inputs preserve output)");
}
