{
  # Injected into Node's configure via `-I` (configure forwards unknown args to
  # gyp). Makes gyp's ninja generator compile with the standalone LLVM clang-cl
  # instead of cl.exe; linking stays with MSVC link.exe from the VS environment.
  # The same LLVM install is used by the IKVM.Clang shim project so both sides
  # of the C++ ABI are produced by one compiler.
  'make_global_settings': [
    ['CC',  'C:/Program Files/LLVM/bin/clang-cl.exe'],
    ['CXX', 'C:/Program Files/LLVM/bin/clang-cl.exe'],
  ],
}
