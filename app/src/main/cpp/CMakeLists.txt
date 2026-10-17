cmake_minimum_required(VERSION 3.22.1)
project(jiege_native CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# One LSPosed native module (see assets/native_init). native_entry.cpp owns the
# LSPosed entry point and routes library-load callbacks to the feature files.
add_library(jiege_native SHARED
    native_entry.cpp
    gr_basictone.cpp
    master_grain.cpp
    pop_path_remap.cpp
    natural_mode.cpp
    unlock25mp.cpp
    face200m.cpp
    master_color.cpp
    master_core.cpp
    master_dt.cpp
    master_canon.cpp
    soft_light.cpp
    master_lut_slots.cpp)

target_compile_options(jiege_native PRIVATE -O2 -fvisibility=hidden)
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/../assets/device_profile.json" MUSE_PROFILE)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../assets/device_profile.json")
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/../assets/device_profile.json" MUSE_PROFILE_SHA256)
string(JSON MUSE_MODEL GET "${MUSE_PROFILE}" model)
string(JSON MUSE_FIRMWARE GET "${MUSE_PROFILE}" firmware)
target_compile_definitions(jiege_native PRIVATE MUSE_MODEL="${MUSE_MODEL}" MUSE_FIRMWARE="${MUSE_FIRMWARE}" MUSE_PROFILE_SHA256="${MUSE_PROFILE_SHA256}")
target_link_libraries(jiege_native log dl camera2ndk android EGL GLESv3)
