# libnode

Builds [Node.js](https://github.com/nodejs/node) as a shared library (`libnode`) for every
supported runtime identifier and packages the results for NuGet, for use by
[node-api-dotnet](https://github.com/alethic/node-api-dotnet) when .NET hosts a Node.js runtime.

Node is **not patched**. `ext/node` is a submodule pinned to an upstream release tag; upgrading
Node is moving that pointer. The build is Node's own (`configure` + gyp), driven from MSBuild by
`src/LibNode/LibNode.proj`, which builds in Node's standard `ext/node/out/<config>/` and harvests:

```
runtimes/<rid>/native/libnode.{dll,so,dylib}   shared library (+ .pdb on Windows)
lib/<rid>/libnode.lib                          Windows import library
include/node/...                               C++ embedding headers: node.h, v8, uv, cppgc, node-api
include/config.gypi                            V8/Node build defines the headers depend on
```

The C++ embedding headers and `config.gypi` are included so that consumers can compile code
against Node's C++ embedder API with a matching compiler and ABI.

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

```bash
git clone --recurse-submodules --shallow-submodules https://github.com/alethic/libnode.git
cd libnode
dotnet build src/LibNode/LibNode.proj -c Release
```

Properties: `LibNodeRuntimeIdentifier` (defaults to the host RID), `LlvmInstallDir`,
`LlvmVersion` (auto-detected), `NodeBuildConfig` (`Release`), `LibNodeUseNinja`.

A cold build takes about an hour per RID and roughly 10 GB under `ext/node/out`.
