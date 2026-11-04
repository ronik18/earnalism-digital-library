# Frozen executed-helper interface v1

This evidence is created only after the test helper actually executes in ordinary reviewed CI. It is not a native provider qualification or a release controller.

The consumer's paired-only approval binding is:

```json
{"schema":"earnalism.paired-content-input.v1","input_git_source_sha":"<B>","expected_archive_helper_report_sha256":"<canonical digest of entire executed receipt>","archive_member_manifest_sha256":"<canonical files digest>","archive_member_modes_sha256":"<canonical modes digest>","helper_archive_sha256":"<observed helper gzip SHA256>"}
```

All canonical digests use Python `hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()`, including its default ASCII escaping. Arrays retain their documented order.

* Member content digest: sorted by path array of objects containing exactly `path` (string), `bytes` (integer), `sha256` (lowercase hex SHA256 string). This equals the existing `digest(qualified_export_report.files)`.
* Member modes digest: sorted by path array of objects containing exactly `path`, `bytes`, `sha256`, and `mode` (integer archive permission bits). Expected Git100644 is decimal420 (0644), Git100755 is decimal493 (0755). File type bits are not included. Keys are sorted by canonical JSON serialization.
* Helper gzip digest: raw bytes actually produced by the helper. It is not stable across metadata-varying repacks and is NOT a checksum of the later Railway upload.
* Executed receipt digest: canonical digest of the entire `executed-helper-report.json` object. The separate `executed-helper-report-digests.json` records it as `expected_archive_helper_report_sha256`; `raw_report_file_sha256` is different and must not be substituted. No receipt self-hash is embedded in the receipt.

The executed receipt schema is `earnalism.executed_upstream_helper_archive.v1`, scope `EXACT_UPSTREAM_HELPER_EXECUTED_NOT_INSTALLED_CLI_UPLOAD_OR_NATIVE_RUNTIME`, with `helper_executed=true`. Its `input_git_source_sha` is the immutable Git input B. Its `controller_source_sha`, `ci_context.actual_controller_sha` and `offline_export_report_sha256` retain the ACTUAL producer checkout and actual input report bytes. Creation requires those producer/controller facts to agree. **Consumers must not rewrite them after merge or require them to equal a later merged operator/controller.**

Future reuse verifies the immutable executed receipt's canonical digest; the pinned module/function/lock/binary and executed status; actual producer source/tree or reviewed unchanged-component evidence; and stable B content/mode/runtime/filter bindings against a freshly qualified current operator export. Current top-level operator source/payload seal/protected approval remain independently bound. A whole-report hash that contains the old producer controller source is historical context, not a demand for a new helper run on every merge.

`runtime_expected_sha256` and `runtime_input_count` describe the bound input inventory, not measured serving runtime. Actual operation, deployment ID, image, config, measured runtime and recovery remain future native observations. `provider_git_sha=null` plus `provider_git_metadata_status=NOT_OBSERVED_NO_PROVIDER_CALL` reflects that the helper never calls a provider. It must never be filled from B. The later native observer must record actual provider metadata separately and leave it absent when absent.

The receipt keeps `native_archive_qualification=false`, `provider_upload_performed=false`, `runtime_qualification=false` and `provider_writes=0`. Neither the helper report nor its gzip hash grants dispatch authority or waives later actual source-delivery/runtime gates.
