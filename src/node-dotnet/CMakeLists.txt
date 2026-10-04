# node-dotnet: a C ABI over Node.js's public C++ embedding API, for P/Invoke from .NET (see node-dotnet.h).
# Each node job builds it right after Node, with the same compiler, against that build's headers and library:
#
#   cmake -S src/node-dotnet -B out/node-dotnet -G Ninja -DCMAKE_BUILD_TYPE=Release
#         -DLIBNODE_INCLUDE_DIR=<tools/install.py --headers-only include dir> -DLIBNODE_DIR=<dir with the built libnode>
#   cmake --build out/node-dotnet

cmake_minimum_required(VERSION 3.20)

# Node.js 26's own deployment target (common.gypi).
set(CMAKE_OSX_DEPLOYMENT_TARGET "13.5" CACHE STRING "")

project(node-dotnet LANGUAGES CXX)

set(LIBNODE_INCLUDE_DIR "" CACHE PATH "Node.js headers, as installed by tools/install.py --headers-only (contains node/node.h)")
set(LIBNODE_DIR "" CACHE PATH "Directory containing the built libnode")

if(WIN32)
  set(_libnode_name "libnode.lib")
elseif(APPLE)
  set(_libnode_name "libnode.*.dylib")
else()
  set(_libnode_name "libnode.so.*")
endif()
file(GLOB LIBNODE_LIBRARY "${LIBNODE_DIR}/${_libnode_name}")
if(NOT LIBNODE_LIBRARY)
  message(FATAL_ERROR "No ${_libnode_name} in LIBNODE_DIR (${LIBNODE_DIR})")
endif()

add_library(node-dotnet SHARED node-dotnet.cc)
target_compile_features(node-dotnet PRIVATE cxx_std_20)
target_include_directories(node-dotnet PRIVATE "${LIBNODE_INCLUDE_DIR}/node")
# A consumer of a shared libnode: NODE_EXTERN, V8_EXPORT and UV_EXTERN become imports.
target_compile_definitions(node-dotnet PRIVATE
  BUILDING_NODE_EXTENSION USING_V8_SHARED USING_V8_PLATFORM_SHARED USING_UV_SHARED NODE_DOTNET_EXPORTS)
target_link_libraries(node-dotnet PRIVATE "${LIBNODE_LIBRARY}")
set_target_properties(node-dotnet PROPERTIES CXX_VISIBILITY_PRESET hidden)

# libnode ships beside it, in the same runtimes/<rid>/native directory.
if(APPLE)
  set_target_properties(node-dotnet PROPERTIES BUILD_WITH_INSTALL_RPATH TRUE INSTALL_RPATH "@loader_path")
elseif(UNIX)
  set_target_properties(node-dotnet PROPERTIES BUILD_WITH_INSTALL_RPATH TRUE INSTALL_RPATH "$ORIGIN")
endif()
