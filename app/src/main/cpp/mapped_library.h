#pragma once
#include <cstdio>
#include <cstring>
#include <elf.h>
#include <fstream>
#include <string>
#include <vector>

// Android's SDK namespace can hide already-loaded vendor handles from dlopen.
// Resolve exported functions from the matching on-disk ELF and its mapped base.
inline void *mappedFunction(const std::string &path, void *base, const char *name) {
    FILE *f = std::fopen(path.c_str(), "rbe");
    if (!f) return nullptr;
    Elf64_Ehdr e{};
    void *result = nullptr;
    if (std::fread(&e, 1, sizeof(e), f) == sizeof(e) && !std::memcmp(e.e_ident, ELFMAG, SELFMAG) &&
        e.e_shentsize == sizeof(Elf64_Shdr) && e.e_shnum > 0 && e.e_shnum < 4096) {
        std::vector<Elf64_Shdr> sections(e.e_shnum);
        std::fseek(f, e.e_shoff, SEEK_SET);
        if (std::fread(sections.data(), sizeof(Elf64_Shdr), sections.size(), f) == sections.size()) {
            for (const auto &section : sections) {
                if (section.sh_type != SHT_DYNSYM || section.sh_link >= sections.size()) continue;
                const auto &strings = sections[section.sh_link];
                if (strings.sh_size > (64u << 20) || section.sh_size > (32u << 20)) continue;
                std::vector<char> table(strings.sh_size + 1);
                std::vector<Elf64_Sym> symbols(section.sh_size / sizeof(Elf64_Sym));
                std::fseek(f, strings.sh_offset, SEEK_SET);
                if (std::fread(table.data(), 1, strings.sh_size, f) != strings.sh_size) continue;
                std::fseek(f, section.sh_offset, SEEK_SET);
                if (std::fread(symbols.data(), sizeof(Elf64_Sym), symbols.size(), f) != symbols.size()) continue;
                for (const auto &s : symbols) {
                    if (s.st_shndx != SHN_UNDEF && ELF64_ST_TYPE(s.st_info) == STT_FUNC &&
                        s.st_name < strings.sh_size && !std::strcmp(table.data() + s.st_name, name)) {
                        result = static_cast<char *>(base) + s.st_value;
                        break;
                    }
                }
                if (result) break;
            }
        }
    }
    std::fclose(f);
    return result;
}

template <typename F> inline void mappedLibraries(F visit) {
    std::ifstream maps("/proc/self/maps");
    std::string line;
    while (std::getline(maps, line)) {
        unsigned long start, end, offset;
        char mode[5]{};
        size_t slash = line.find('/');
        if (slash == std::string::npos || std::sscanf(line.c_str(), "%lx-%lx %4s %lx", &start, &end, mode, &offset) != 4 ||
            offset != 0 || mode[0] != 'r' || line.find("(deleted)") != std::string::npos) continue;
        visit(line.substr(slash), reinterpret_cast<void *>(start));
    }
}
