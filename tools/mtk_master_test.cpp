// Verify real PME110 frame input and its four original stock tables on a host.
#include "master_core.h"
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>

int main(int argc, char **argv) {
    assert(argc == 4);
    std::string error;
    assert(mastercolor::loadEngine(std::string(argv[1]) + "/hncs_engine.bin", &error));
    mastercolor::Key key;
    assert(mastercolor::readKeyFile(argv[3], key));
    assert(key.inputGamma.size() == 257);
    key.path = mastercolor::Path::Main;
    std::vector<float> look;
    assert(mastercolor::bake(key, look, 4));
    assert(!std::filesystem::exists(std::string(argv[2]) + "/LMTLut4"));
    for (float weight : {0.f, .5f, 1.f}) {
        key.toneWeight = key.colourWeight = weight;
        std::vector<std::vector<float>> tables;
        assert(mastercolor::blendWithStock(key, look, argv[2], tables, 4));
        assert(tables.size() == (weight == 1 ? 1 : 4));
        for (size_t i = 0; i < tables.size(); ++i) {
            for (float value : tables[i]) assert(std::isfinite(value) && value >= 0 && value <= 1);
            if (weight == 0) {
                std::ifstream file(std::string(argv[2]) + "/LMTLut" + std::to_string(i), std::ios::binary);
                std::vector<float> stock(tables[i].size());
                file.read(reinterpret_cast<char *>(stock.data()), std::streamsize(stock.size() * 4));
                assert(file && stock == tables[i]);
            }
        }
        if (weight == 1) assert(tables[0] == look);
        std::cout << "MTK blend " << weight << ": " << tables.size() << " tables PASS\n";
    }
}
