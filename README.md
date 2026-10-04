# libnode-dotnet

Builds [Node.js](https://github.com/nodejs/node) as a shared library (`libnode`) for every
supported runtime identifier, plus `node-dotnet`, a small C shim over Node's C++ embedding API,
and packages both for NuGet, for use by [node-api-dotnet](https://github.com/alethic/node-api-dotnet)
when .NET hosts a Node.js runtime.

Node is **not patched**. `ext/node` is a submodule pinned to an upstream release tag; upgrading
Node is moving that pointer. The build is Node's own (`configure` + gyp).

## node-dotnet

[`src/node-dotnet`](src/node-dotnet) is a C ABI that mirrors Node's public C++ embedding API
(`node.h`) and the slice of `v8.h` an embedder needs, one function per C++ declaration, so .NET
can P/Invoke it (see [`node-dotnet.h`](src/node-dotnet/node-dotnet.h)). It is a CMake project
built against one specific libnode build, with the same compiler, and ships beside it:
`node-dotnet.dll`, `libnode-dotnet.so` or `libnode-dotnet.dylib`.

## How it is built

[`.github/workflows/build.yml`](.github/workflows/build.yml):

1. **node**: one job per RID runs Node's own build commands natively on its OS (Windows:
   `python configure --shared … --clang-cl=…` then `msbuild node.sln` with the ClangCL toolset;
   Linux/macOS: `./configure --shared --ninja …` then `ninja`). The result is cached per RID,
   keyed by the `ext/node` submodule commit, so Node is rebuilt only when the submodule moves
   (or the cache key's suffix is bumped). The job then installs the headers with Node's
   `tools/install.py`, builds `node-dotnet` with CMake against them, and uploads the binaries as
   an artifact named after the RID.
2. **pack**: downloads every artifact into `out/libnode/<rid>/`, installs the headers into
   `out/libnode/include/`, and runs `dotnet build`. Each project under `src/` is a NoTargets
   project whose `<None Pack="true">` items pick up its files.
3. **publish**: pushes the packages to the alethic GitHub Packages NuGet registry (`main` and tags).

## Packages

```
Alethic.LibNode.runtime.<rid>                   one per RID
  runtimes/<rid>/native/                          libnode.dll | libnode.so.<abi> | libnode.<abi>.dylib
                                                  node-dotnet.dll | libnode-dotnet.so | libnode-dotnet.dylib
  build/native/lib/<rid>/libnode.lib              (Windows) import library
  buildTransitive/Alethic.LibNode.runtime.<rid>.props    LibNodeNativeDir_<rid>, LibNodeLibDir_<rid>
  buildTransitive/Alethic.LibNode.runtime.<rid>.targets  (Windows) .NET Framework: copies the
                                                  native libraries to the output as runtimes\<rid>\native\
Alethic.LibNode                                 depends on every RID package
  build/native/include/node/                      C++ embedding headers: node.h, v8, uv, cppgc, node-api
  buildTransitive/Alethic.LibNode.props           LibNodeIncludeDir
```

Version is `<node version>.<build number>`, e.g. `26.10.0.17`.

## Toolchain

| Platform | Needs |
|---|---|
| All | Python 3.10–3.14, Rust (`rustup`; Temporal), LLVM/Clang 19+, CMake 3.20+, ninja |
| Windows | Visual Studio 2026 (or 2022 17.14) "Desktop development with C++" plus the **MSBuild support for LLVM (clang-cl) toolset** component, pointed at the standalone LLVM via `LLVMInstallDir`; NASM. win-arm64 also needs `rustup target add aarch64-pc-windows-msvc` |

On Windows Node uses the msvs generator (Node 26's Rust crates step uses an MSBuild macro that
the ninja generator cannot expand); elsewhere ninja.

## Building locally

Run the same commands the workflow does, from a Visual Studio developer prompt on Windows. For
example, win-x64 with a standalone LLVM at `C:\Program Files\LLVM`:

```
cd ext\node
set GYP_MSVS_VERSION=2026
set GYP_MSVS_OVERRIDE_PATH=%VSINSTALLDIR%
python configure --shared --dest-cpu=x64 --clang-cl=23.1.2
msbuild node.sln /m /p:Configuration=Release /p:Platform=x64 /p:LLVMInstallDir="C:\Program Files\LLVM" /p:LLVMToolsVersion=23.1.2
python tools\install.py install --headers-only --root-dir . --config-gypi-path config.gypi --dest-dir ..\..\out\libnode --prefix /
cd ..\..
cmake -S src/node-dotnet -B out/node-dotnet -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER="C:/Program Files/LLVM/bin/clang-cl.exe" -DLIBNODE_INCLUDE_DIR=out/libnode/include -DLIBNODE_DIR=ext/node/out/Release
cmake --build out/node-dotnet
```

To pack, copy `libnode.dll`, `libnode.lib` and `node-dotnet.dll` to `out\libnode\win-x64\` and
build that RID's project (each project needs its RID's files present):

```
dotnet build src\Alethic.LibNode.runtime.win-x64 -c Release
```

A cold Node build takes about an hour per RID and roughly 10 GB under `ext/node/out`.
