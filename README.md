# libnode-dotnet

Builds [Node.js](https://github.com/nodejs/node) as a shared library (`libnode`) for every
supported runtime identifier and packages the results for NuGet, for use by
[node-api-dotnet](https://github.com/alethic/node-api-dotnet) when .NET hosts a Node.js runtime.

Node is **not patched**. `ext/node` is a submodule pinned to an upstream release tag; upgrading
Node is moving that pointer. The build is Node's own (`configure` + gyp).

## How it is built

[`.github/workflows/build.yml`](.github/workflows/build.yml):

1. **node**: one job per RID runs Node's own build commands natively on its OS (Windows:
   `python configure --shared … --clang-cl=…` then `msbuild node.sln` with the ClangCL toolset;
   Linux/macOS: `./configure --shared --ninja …` then `ninja`) and uploads the binaries as an
   artifact named after the RID.
2. **pack**: downloads every artifact into `out/libnode/<rid>/`, installs the headers from the
   submodule into `out/libnode/include/` with Node's `tools/install.py`, and runs `dotnet build`.
   Each project under `src/` is a NoTargets project whose `<None Pack="true">` items pick up
   its files.
3. **publish**: pushes the packages to the alethic GitHub Packages NuGet registry (`main` and tags).

## Packages

```
Alethic.LibNode.runtime.<rid>                   one per RID
  runtimes/<rid>/native/                          libnode.dll | libnode.so.<abi> | libnode.<abi>.dylib
  build/native/lib/<rid>/libnode.lib              (Windows) import library
  buildTransitive/Alethic.LibNode.runtime.<rid>.props    LibNodeNativeDir_<rid>, LibNodeLibDir_<rid>
  buildTransitive/Alethic.LibNode.runtime.<rid>.targets  (Windows) .NET Framework: copies the
                                                  native library to the output as runtimes\<rid>\native\
Alethic.LibNode                                 depends on every RID package
  build/native/include/node/                      C++ embedding headers: node.h, v8, uv, cppgc, node-api
  buildTransitive/Alethic.LibNode.props           LibNodeIncludeDir
```

Version is `<node version>.<build number>`, e.g. `26.10.0.17`.

## Toolchain

| Platform | Needs |
|---|---|
| All | Python 3.10–3.14, Rust (`rustup`; Temporal), LLVM/Clang 19+ |
| Windows | Visual Studio 2026 (or 2022 17.14) "Desktop development with C++" plus the **MSBuild support for LLVM (clang-cl) toolset** component, pointed at the standalone LLVM via `LLVMInstallDir`; NASM. win-arm64 also needs `rustup target add aarch64-pc-windows-msvc` |
| Linux / macOS | ninja |

On Windows the msvs generator is used (Node 26's Rust crates step uses an MSBuild macro that
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
```

Then copy `libnode.dll` and `libnode.lib` to `out\libnode\win-x64\`, install the headers, and
build (each project needs its RID's files present):

```
python tools\install.py install --headers-only --root-dir . --config-gypi-path config.gypi --dest-dir ..\..\out\libnode --prefix /
cd ..\..
dotnet build src\Alethic.LibNode.runtime.win-x64 -c Release
```

A cold Node build takes about an hour per RID and roughly 10 GB under `ext/node/out`.
