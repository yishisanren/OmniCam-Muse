#pragma once
#include <cstring>
#include <elf.h>
#include <link.h>
#include <string>

// Offsets are only valid for the inspected original MTK binaries. Future OTA
// libraries must fail closed instead of silently reusing an old memory layout.
inline bool hasBuildId(void *base, const char *expected) {
    if (!base) return false;
    const auto *header = static_cast<const Elf64_Ehdr *>(base);
    if (memcmp(header->e_ident, ELFMAG, SELFMAG) || header->e_ident[EI_CLASS] != ELFCLASS64
        || header->e_phnum > 128 || header->e_phoff > 65536) return false;
    const auto *phdr = reinterpret_cast<const Elf64_Phdr *>(static_cast<const char *>(base) + header->e_phoff);
    for (size_t i = 0; i < header->e_phnum; ++i) {
        const auto &ph = phdr[i];
        if (ph.p_type != PT_NOTE || ph.p_memsz > 65536) continue;
        auto *p = static_cast<const unsigned char *>(base) + ph.p_vaddr;
        const auto *end = p + ph.p_memsz;
        while (p + sizeof(Elf64_Nhdr) <= end) {
            const auto *note = reinterpret_cast<const Elf64_Nhdr *>(p);
            size_t nameSize = (note->n_namesz + 3u) & ~3u;
            size_t descSize = (note->n_descsz + 3u) & ~3u;
            if (nameSize > size_t(end - p) || descSize > size_t(end - p)
                || sizeof(*note) + nameSize + descSize > size_t(end - p)) break;
            const auto *name = p + sizeof(*note);
            const auto *desc = name + nameSize;
            if (note->n_type == NT_GNU_BUILD_ID && note->n_namesz == 4 && !memcmp(name, "GNU", 4)) {
                std::string hex;
                const char digits[] = "0123456789abcdef";
                for (size_t n = 0; n < note->n_descsz; ++n) {
                    hex += digits[desc[n] >> 4]; hex += digits[desc[n] & 15];
                }
                return hex == expected;
            }
            p += sizeof(*note) + nameSize + descSize;
        }
    }
    return false;
}
