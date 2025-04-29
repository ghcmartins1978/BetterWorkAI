# Rust Helper Binaries

Place the compiled Rust helper binaries for each platform in this directory:

- `betterman_helper.exe` - Windows binary
- `betterman_helper` - macOS/Linux binary

## Building the Rust Helper

The Rust helper should be built separately for each target platform using the Rust toolchain:

```bash
# For Windows
cargo build --release --target x86_64-pc-windows-msvc
# For macOS
cargo build --release --target x86_64-apple-darwin
# For Linux
cargo build --release --target x86_64-unknown-linux-gnu
```

## Installation during Build

The Electron builder will package these binaries with the application during the build process.