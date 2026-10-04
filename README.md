# libnode

Builds [Node.js](https://github.com/nodejs/node) as a shared library (`libnode`) for every
supported runtime identifier and packages the results for NuGet, for use by
[node-api-dotnet](https://github.com/alethic/node-api-dotnet) when .NET hosts a Node.js runtime.

Node is **not patched**. `ext/node` is a submodule pinned to an upstream release tag; upgrading
Node is moving that pointer. The build is Node's own (`configure` + gyp).

## How it is built

[`.github/workflows/build.yml`](.github/workflows/build.yml) has three stages:

1. **node** — a matrix with one job per RID, each running Node's own build commands natively on its
   OS (Windows: `python configure --shared … --clang-cl=…` then `msbuild node.sln` with the ClangCL
   toolset; Linux/macOS: `./configure --shared --ninja …` then `ninja`). No .NET involved. Each job
   uploads its raw outputs (`libnode.*`, `config.gypi`, `llvm-version.txt`) as an artifact.
2. **pack** — one Linux job downloads every artifact and runs the only .NET project in the repo,
   `src/LibNode.Pack/LibNode.Pack.proj`, which lays the files out and packs them. Headers come from
   the submodule via Node's `install.py`. It is just copying files.
3. **publish** — pushes the packages to the alethic GitHub Packages NuGet registry (`main` and tags).

## Packages

```
Alethic.LibNode.<rid>                           one per RID, natives only
  runtimes/<rid>/native/libnode.{dll,so,dylib}    .NET selects by RID via .deps.json (+ .pdb on Windows)
  build/native/<rid>/{config.gypi,libnode.lib}    per-RID build inputs for native consumers
  build/native/Alethic.LibNode.<rid>.props        paths for native consumers
  buildTransitive/net472/Alethic.LibNode.<rid>.targets   (Windows RIDs) .NET Framework fallback: copies the
                                                  natives into the output as runtimes\<rid>\native\
Alethic.LibNode                                 top-level; depends on every RID package (exact version)
  build/native/include/...                        C++ embedding headers: node.h, v8, uv, cppgc, node-api
  build/native/Alethic.LibNode.props              version, LLVM version, include dir
```

The C++ embedding headers and `config.gypi` are included so that consumers can compile code
against Node's C++ embedder API with a matching compiler and ABI.

Version is `<node version>.<build number>`, e.g. `26.10.0.17`.

## Toolchain

Node is compiled with a standalone LLVM/Clang install so that consumers compiling against the
C++ API can use the same compiler. Linking uses the platform linker.

| Platform | Needs |
|---|---|
| All | Python 3.10–3.14, Git, Rust toolchain (`rustup`; Temporal support), LLVM/Clang 19+ |
| Windows | Visual Studio 2026 (or 2022 17.14) "Desktop development with C++" workload for the MSVC STL, `link.exe` and the Windows SDK, plus the **MSBuild support for LLVM (clang-cl) toolset** component (its props are pointed at the standalone LLVM via `LLVMInstallDir`); NASM |
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

Then put the outputs where the pack project expects them and pack:

```
mkdir ..\..\out\libnode\win-x64
copy out\Release\libnode.dll ..\..\out\libnode\win-x64\   (and libnode.lib, libnode.pdb, config.gypi)
dotnet build ..\..\src\LibNode.Pack\LibNode.Pack.proj -t:PackAll
```

A cold build takes about an hour per RID and roughly 10 GB under `ext/node/out`.
