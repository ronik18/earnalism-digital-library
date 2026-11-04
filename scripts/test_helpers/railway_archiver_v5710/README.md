# Test-only Railway 5.71.0 archive helper

This package compiles only the byte-identical upstream `create_deploy_tarball` function. It contains no CLI command implementation, credential/config loader, HTTP client, upload function or provider endpoint. Its only output is a new local gzip archive file. It is never a release entrypoint.

`SOURCE-PINS.json` binds the upstream module, exact function and upstream Cargo.lock. The derived lock contains the complete 92-package registry dependency closure, retaining each upstream package version, source and checksum. Cargo must admit the lock without updating it (`--locked`). If Cargo requires a lock update, fail the job and review the exact closure; do not regenerate or upgrade silently.

Execute through ordinary reviewed CI, without provider secrets. Read the actual runner `rustc --version` and `cargo --version` first, admitting Rust >=1.85, not assuming image availability. Build the package with `cargo build --locked --release --manifest-path .../Cargo.toml`. Do not install a local toolchain or run Railway up.

Run the synthetic helper fixture checker, then use the existing paired-source exporter/qualifier on the exact controller checkout to prepare CLOSED B. Preflight the export for links/boundaries before calling the helper. Invoke `<binary> <export>/backend <export> <new-output.tgz>`; do not pass the parent `.gitignore` as an uploaded member. Verify the actual tar with `verify_railway_helper_archive.py`, passing the actual generated report SHA256 and controller checkout. It independently checks the local source against Git B blob identities/modes and verifies every archived regular file. Retain archive, report, source pins and actual toolchain/build logs as CI artifacts.

Expected current B export: 2164 regular backend members and 1966 measured runtime inputs. Directory entries are separately enumerated. Parent `.gitignore` is the 2165th export/filter input, not an archive member. Compression timestamps/UIDs can differ; archive bytes are observed and hashed, never predicted.

A passing job proves `EXACT_UPSTREAM_HELPER_EXECUTED`, not installed Railway binary capture, native upload, provider Git metadata, image/config/startup or recovery. Do not flip native archive flags on the existing offline report. Later actual operation/deployment/image/runtime evidence stays required.
