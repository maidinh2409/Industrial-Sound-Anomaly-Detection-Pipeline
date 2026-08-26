# Data Contract

## 1. Purpose

This document defines the logical schemas, validation rules, identifiers, S3 layout, and compatibility policy for the Industrial Sound Anomaly Detection Pipeline.

The contract covers:

1. Source archive manifests.
2. Extracted audio metadata.
3. Validation results.
4. Quarantine records.
5. Processed audio features and anomaly scores stored in Parquet.

It does not prescribe a particular Python dataframe library. Implementations may use Polars, pandas, Pandera, Great Expectations, or PyArrow as long as the persisted data conforms to this contract.

## 2. Contract principles

- Every derived record must be traceable to an immutable source object.
- Timestamps use UTC and ISO 8601 in JSON; persisted analytical timestamps use a timezone-aware Parquet timestamp where supported.
- Durations are represented in seconds.
- Frequencies and sample rates are represented in hertz.
- Checksums are lowercase hexadecimal strings and include their algorithm in the field name.
- Controlled vocabulary values use lowercase snake case.
- Raw source metadata is never silently corrected; normalization is recorded separately.
- Unknown and missing are distinct from zero.
- Schema and processing versions are explicit in every persisted record.
- Dataset anomaly labels are evaluation metadata and must not be used to fit the unsupervised model.

## 3. Versioning

Initial versions:

```text
manifest_schema_version = 1.0.0
audio_metadata_schema_version = 1.0.0
validation_schema_version = 1.0.0
feature_schema_version = 1.0.0
```

Semantic versioning rules:

- **Patch:** clarification or implementation fix that does not change persisted meaning.
- **Minor:** backward-compatible optional field or allowed enum value.
- **Major:** renamed/removed field, changed data type, changed unit, or incompatible semantic change.

Readers must reject unsupported major versions. Readers should ignore unknown fields from compatible minor versions unless strict validation is explicitly required.

## 4. Common identifiers and fields

These fields are reused across record types.

| Field | Type | Required | Rule and meaning |
|---|---|---:|---|
| `recording_id` | string | Yes for WAV-derived records | Stable lowercase identifier derived from source lineage; recommended SHA-256 of `source_archive_sha256 + source_member_path` |
| `source_dataset` | string | Yes | Must be `mimii` for the initial release |
| `source_record_id` | string | Yes | Zenodo record identifier, initially `3384388` |
| `source_archive` | string | Yes | Original filename, initially `6_dB_fan.zip` |
| `source_archive_s3_uri` | string | Yes | Full `s3://` URI of the immutable ZIP object |
| `source_member_path` | string | Yes for extracted files | Exact case-sensitive path inside the source ZIP |
| `source_wav_s3_uri` | string | Yes after extraction | Full `s3://` URI of the extracted WAV object |
| `source_wav_sha256` | string | Yes after extraction | Exactly 64 lowercase hexadecimal characters |
| `pipeline_version` | string | Yes for derived records | Git commit SHA or immutable release identifier |
| `created_at` | timestamp | Yes | UTC processing timestamp |

Identifiers must not depend on the S3 upload time because reprocessing the same logical source must yield the same identity.

## 5. Controlled vocabularies

### 5.1 Machine type

Initial allowed value:

```text
fan
```

Future compatible values may include `pump`, `valve`, and `slide_rail` after their contracts and validation profiles are approved.

### 5.2 Condition

Allowed values:

```text
normal
anomaly
unknown
```

`condition` is dataset ground truth for evaluation. It must not be supplied to unsupervised model fitting.

### 5.3 Validation status

Allowed values:

```text
valid
invalid
```

### 5.4 Processing status

Allowed values:

```text
discovered
extracted
validated
quarantined
processed
failed
```

### 5.5 Baseline validation reason codes

| Code | Meaning |
|---|---|
| `missing_metadata` | One or more required metadata fields are missing |
| `invalid_metadata` | A field has an invalid type, format, range, or enum value |
| `unsupported_extension` | Input is not a supported `.wav` object |
| `empty_file` | Object contains zero bytes |
| `invalid_wav_container` | RIFF/WAVE structure cannot be parsed |
| `unreadable_audio` | Audio frames cannot be decoded |
| `unexpected_sample_rate` | Sample rate is not `16000 Hz` for the MIMII profile |
| `unexpected_sample_width` | Sample width is not `16 bit` for the MIMII profile |
| `unexpected_channel_count` | Channel count violates the selected ingestion profile |
| `invalid_duration` | Duration is zero, negative, non-finite, or outside the configured limit |
| `checksum_mismatch` | Calculated checksum differs from the manifest |
| `duplicate_recording` | Stable recording identifier already exists |
| `timestamp_parse_error` | Provided timestamp cannot be parsed as UTC/ISO 8601 |
| `timestamp_out_of_range` | Timestamp is outside configured acceptable bounds |
| `internal_validation_error` | Validator failed before making a content decision |

New reason codes are backward-compatible minor additions. Existing codes must not be repurposed.

## 6. Source archive manifest contract

One JSON manifest is required for each ingested source archive.

### 6.1 S3 location

```text
s3://<raw-bucket>/manifests/ingestion_date=YYYY-MM-DD/<archive-name>.manifest.json
```

### 6.2 Fields

| Field | Type | Required | Validation |
|---|---|---:|---|
| `manifest_schema_version` | string | Yes | Semantic version; initially `1.0.0` |
| `dataset_name` | string | Yes | `mimii` |
| `dataset_description` | string | No | Human-readable description |
| `source_record_id` | string | Yes | `3384388` for the selected Zenodo record |
| `source_url` | string | Yes | HTTPS URL |
| `license` | string | Yes | SPDX-style or source-published identifier/text; initially `CC-BY-SA-4.0` |
| `archive_filename` | string | Yes | `6_dB_fan.zip` |
| `archive_s3_uri` | string | Yes | Must use the `s3://` scheme |
| `archive_size_bytes` | int64 | Yes | Positive; expected `10158673161` |
| `archive_md5` | string | Yes | 32 lowercase hex characters; expected `0890f7d3c2fd8448634e69ff1d66dd47` |
| `archive_sha256` | string | Recommended | 64 lowercase hex characters |
| `ingested_at` | timestamp | Yes | UTC |
| `ingestion_method` | string | Yes | Initially `temporary_ec2_transfer` |
| `aws_region` | string | Yes | Initially `us-west-2` |
| `verification_status` | string | Yes | `verified` or `failed` |
| `verified_at` | timestamp | Conditional | Required when status is `verified` |
| `notes` | string | No | Non-sensitive operational notes |

### 6.3 Example

```json
{
  "manifest_schema_version": "1.0.0",
  "dataset_name": "mimii",
  "source_record_id": "3384388",
  "source_url": "https://zenodo.org/records/3384388/files/6_dB_fan.zip?download=1",
  "license": "CC-BY-SA-4.0",
  "archive_filename": "6_dB_fan.zip",
  "archive_s3_uri": "s3://<raw-bucket>/source-archives/6_dB_fan.zip",
  "archive_size_bytes": 10158673161,
  "archive_md5": "0890f7d3c2fd8448634e69ff1d66dd47",
  "archive_sha256": "<calculated-sha256>",
  "ingested_at": "2026-08-26T00:00:00Z",
  "ingestion_method": "temporary_ec2_transfer",
  "aws_region": "us-west-2",
  "verification_status": "verified",
  "verified_at": "2026-08-26T00:10:00Z"
}
```

Placeholders in examples must be replaced before persistence.

## 7. Extracted audio metadata contract

One metadata record is required per extracted WAV object.

### 7.1 Raw S3 layout

```text
s3://<raw-bucket>/recordings/
  machine_type=fan/
  model_id=<model-id>/
  condition=<normal|anomaly>/
  <recording-id>.wav
```

Dataset ground truth is permitted in the raw layout for controlled benchmark data. In a real production feed, `condition` should be `unknown` unless a trusted label is supplied later.

### 7.2 Fields

| Field | Type | Required | Validation |
|---|---|---:|---|
| `audio_metadata_schema_version` | string | Yes | Initially `1.0.0` |
| `recording_id` | string | Yes | Stable, non-empty, unique logical ID |
| `source_dataset` | string | Yes | `mimii` |
| `source_record_id` | string | Yes | `3384388` |
| `source_archive` | string | Yes | `6_dB_fan.zip` for initial scope |
| `source_archive_s3_uri` | string | Yes | Valid S3 URI |
| `source_archive_sha256` | string | Recommended | 64 lowercase hex characters |
| `source_member_path` | string | Yes | Exact ZIP member path; no path traversal after normalization |
| `source_wav_s3_uri` | string | Yes | Valid S3 URI in `recordings/` |
| `source_wav_size_bytes` | int64 | Yes | Greater than zero |
| `source_wav_sha256` | string | Yes | 64 lowercase hex characters |
| `machine_type` | string | Yes | Initially `fan` |
| `model_id` | string | Yes | Normalized source model identifier; non-empty |
| `condition` | string | Yes | `normal`, `anomaly`, or `unknown` |
| `domain` | string | No | Dataset domain value if present, such as source/target domain |
| `section_id` | string | No | Dataset section identifier if present |
| `sample_rate_hz` | int32 | Yes | Expected `16000` |
| `sample_width_bits` | int16 | Yes | Expected `16` |
| `channels` | int16 | Yes | Greater than zero; selected profile determines expected value |
| `frame_count` | int64 | Yes | Greater than zero |
| `duration_seconds` | float64 | Yes | Finite and greater than zero |
| `source_event_at` | timestamp | No | Real event time only if supplied by a trustworthy source |
| `ingested_at` | timestamp | Yes | UTC |
| `extracted_at` | timestamp | Yes | UTC |
| `pipeline_version` | string | Yes | Immutable code/release identifier |

### 7.3 Timestamp policy

MIMII filenames and archive paths must not be treated as real sensor timestamps unless the dataset documentation explicitly defines them that way.

- `source_event_at` may be null for MIMII.
- `ingested_at` records arrival into the project.
- `extracted_at` records extraction time.
- Partitioning benchmark data by `event_date` is allowed only when a legitimate event timestamp exists. Otherwise use `processing_date` or stable dataset dimensions.

## 8. Validation result contract

Every discovered WAV must receive exactly one current terminal validation result for a given `validation_run_id` and `validation_schema_version`.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `validation_schema_version` | string | Yes | Initially `1.0.0` |
| `validation_run_id` | string | Yes | UUID or Step Functions execution-derived identifier |
| `recording_id` | string | Yes | References audio metadata |
| `status` | string | Yes | `valid` or `invalid` |
| `reason_codes` | list<string> | Yes | Empty only when status is `valid` |
| `reason_details` | string | No | Sanitized diagnostic detail; no secrets |
| `validated_at` | timestamp | Yes | UTC |
| `validator_version` | string | Yes | Immutable release identifier |
| `observed_sample_rate_hz` | int32 | No | Populated when readable |
| `observed_sample_width_bits` | int16 | No | Populated when readable |
| `observed_channels` | int16 | No | Populated when readable |
| `observed_frame_count` | int64 | No | Populated when readable |
| `observed_duration_seconds` | float64 | No | Populated when readable |
| `quarantine_s3_uri` | string | Conditional | Required when invalid content is copied to quarantine |

Cross-field rules:

- `status = valid` requires an empty `reason_codes` list and all required observed audio properties.
- `status = invalid` requires at least one reason code.
- `internal_validation_error` must not be converted into `valid` automatically.
- Validation reruns preserve history or use a deterministic current-record selection rule.

## 9. Quarantine contract

Suggested S3 layout:

```text
s3://<raw-bucket>/quarantine/
  reason=<primary-reason-code>/
  processing_date=YYYY-MM-DD/
  <recording-id>/
```

Each quarantined item must have a sidecar JSON record containing:

- `recording_id` when it can be derived.
- Original S3 URI or archive member path.
- Quarantine S3 URI.
- All reason codes.
- Sanitized error detail.
- Validation run ID.
- Validation and pipeline versions.
- Quarantine timestamp.
- Retry eligibility: `true` or `false`.

Quarantine is a logical state, not an automatic deletion policy. Retention must be configured separately.

## 10. Processed feature and anomaly contract

### 10.1 Storage format

- File format: Apache Parquet.
- Compression: Snappy initially, unless benchmarks justify Zstandard.
- Character encoding: UTF-8 for strings.
- Numeric feature type: `float64` initially for reproducibility; selected fields may move to `float32` only through a documented schema revision.
- One logical record per WAV for feature schema `1.x`.

### 10.2 Suggested S3 layout

For MIMII, which may not contain a trustworthy event date:

```text
s3://<processed-bucket>/audio_features/
  feature_schema_version=1.0.0/
  machine_type=fan/
  model_id=<model-id>/
  processing_date=YYYY-MM-DD/
  part-*.parquet
```

Do not partition by `recording_id`, anomaly score, or other high-cardinality fields.

### 10.3 Identity and lineage fields

| Field | Parquet type | Nullable | Rule |
|---|---|---:|---|
| `recording_id` | string | No | Unique logical recording ID |
| `source_dataset` | string | No | `mimii` |
| `source_record_id` | string | No | `3384388` |
| `source_archive` | string | No | Original archive filename |
| `source_member_path` | string | No | Exact archive member path |
| `source_wav_s3_uri` | string | No | Extracted source object |
| `source_wav_sha256` | string | No | Source content identity |
| `machine_type` | string | No | Initially `fan` |
| `model_id` | string | No | Normalized model identifier |
| `condition` | string | No | Evaluation label; not a training feature |
| `feature_schema_version` | string | No | Initially `1.0.0` |
| `pipeline_version` | string | No | Immutable code/release identifier |
| `model_version` | string | No | Immutable anomaly model identifier |
| `processing_run_id` | string | No | Batch/workflow run identifier |
| `processed_at` | timestamp UTC | No | Processing completion time |
| `processing_date` | date | No | Derived from `processed_at`; partition field |

### 10.4 Audio property and quality fields

| Field | Parquet type | Nullable | Unit/rule |
|---|---|---:|---|
| `sample_rate_hz` | int32 | No | Hz; expected `16000` |
| `sample_width_bits` | int16 | No | Bits; expected `16` |
| `channels` | int16 | No | Greater than zero |
| `frame_count` | int64 | No | Greater than zero |
| `duration_seconds` | float64 | No | Seconds, finite, greater than zero |
| `peak_amplitude` | float64 | No | Normalized absolute peak in `[0, 1]` |
| `clipping_ratio` | float64 | No | Fraction in `[0, 1]` |
| `silence_ratio` | float64 | No | Fraction in `[0, 1]`; threshold configuration is versioned |

### 10.5 Baseline scalar features

For frame-based features, persist summary statistics instead of variable-length arrays in the primary Athena table.

| Field pattern/example | Parquet type | Nullable | Rule |
|---|---|---:|---|
| `rms_mean`, `rms_std`, `rms_min`, `rms_max` | float64 | No | Finite, non-negative |
| `zero_crossing_rate_mean`, `zero_crossing_rate_std` | float64 | No | Finite; mean in `[0, 1]` |
| `spectral_centroid_hz_mean`, `spectral_centroid_hz_std` | float64 | No | Finite, non-negative |
| `spectral_bandwidth_hz_mean`, `spectral_bandwidth_hz_std` | float64 | No | Finite, non-negative |
| `spectral_rolloff_hz_mean`, `spectral_rolloff_hz_std` | float64 | No | Finite, non-negative |
| `spectral_flatness_mean`, `spectral_flatness_std` | float64 | No | Finite, non-negative |
| `band_energy_<low>_<high>_hz_mean` | float64 | No | Finite, non-negative; band set defined in feature configuration |
| `mfcc_<nn>_mean`, `mfcc_<nn>_std` | float64 | No | Finite; zero-padded index such as `mfcc_01_mean` |

The initial MFCC count, FFT size, hop length, window, channel-reduction method, frequency bands, silence threshold, and aggregation statistics must be stored in a versioned feature configuration. Changing these parameters requires at least a new feature-schema minor version and a new model version.

### 10.6 Anomaly fields

| Field | Parquet type | Nullable | Rule |
|---|---|---:|---|
| `anomaly_score` | float64 | No | Finite; higher must consistently mean more anomalous |
| `anomaly_threshold` | float64 | No | Finite threshold associated with `model_version` |
| `is_anomaly_predicted` | boolean | No | `anomaly_score >= anomaly_threshold` unless model manifest specifies otherwise |
| `anomaly_score_method` | string | No | Example: `isolation_forest` or `autoencoder_reconstruction_error` |
| `model_version` | string | No | Immutable model/scaler/threshold bundle identifier |

The score scale may differ between model versions. Cross-version score comparisons require documented calibration.

### 10.7 Processing metrics

| Field | Parquet type | Nullable | Rule |
|---|---|---:|---|
| `feature_processing_ms` | int64 | No | Non-negative |
| `scoring_ms` | int64 | No | Non-negative |
| `retry_count` | int16 | No | Non-negative |

## 11. Null, NaN, and infinity policy

- Required identifiers, lineage, versions, partition fields, and anomaly fields must never be null.
- IEEE positive/negative infinity is prohibited in persisted feature columns.
- NaN is prohibited in the primary Athena feature table; use null only for a documented unavailable optional value.
- Zero must represent a measured zero, not missing data.
- A failed required feature calculation fails the record unless a schema-approved fallback exists.
- Null-rate metrics must be reported per optional field.

## 12. Duplicate and idempotency policy

The logical uniqueness key for schema `1.x` is:

```text
(recording_id, feature_schema_version, model_version)
```

Multiple physical Parquet rows with the same logical key are not allowed in the published table. Retries may write temporary output, but publication must use deterministic paths, a commit manifest, or a compaction/deduplication step.

A changed source checksum produces a new `recording_id` or an explicit source version; it must never silently replace the old logical input.

## 13. Schema enforcement points

| Boundary | Enforcement |
|---|---|
| Archive arrival | Manifest size/checksum and S3 object metadata validation |
| ZIP extraction | Safe path validation, member inventory, checksum generation |
| WAV intake | Container/audio/metadata validation in Lambda or validation job |
| Feature output | Python schema validation before Parquet write |
| Published dataset | PyArrow schema plus reconciliation and uniqueness checks |
| Athena | Glue table definition and acceptance queries |
| Model input | Exact ordered feature list from the model manifest |

## 14. Compatibility and change process

Any contract change must include:

1. Motivation and affected consumers.
2. Proposed schema-version change.
3. Migration or backfill plan.
4. Updates to validators, Glue tables, tests, and documentation.
5. Confirmation that existing Parquet partitions remain readable or are migrated.
6. Model impact analysis when feature semantics change.

Breaking changes require a new major version and a new S3 schema-version prefix or table. Historical raw audio and manifests remain immutable.

## 15. Security and privacy constraints

- No AWS access keys, session tokens, private keys, account credentials, or personal email addresses may appear in data records.
- Error details must be sanitized before persistence or logging.
- S3 URIs may identify project resources but should not contain secrets.
- Bucket names and account-specific identifiers in public documentation should use placeholders unless disclosure is intentional.
- Access is granted through least-privilege IAM roles.

## 16. Contract acceptance tests

The implementation must include automated tests for:

- A fully valid MIMII fan WAV and metadata record.
- Missing required metadata.
- Wrong sample rate.
- Wrong sample width.
- Zero-byte file.
- Corrupt WAV container.
- Invalid duration.
- Duplicate `recording_id`.
- Invalid checksum.
- Invalid enum value.
- Invalid timestamp.
- NaN or infinity in required output features.
- Missing schema or pipeline version.
- Cross-field inconsistency between anomaly score, threshold, and predicted flag.
- Parquet output matching the declared PyArrow schema.
- Glue/Athena reading a representative output partition.

Contract tests are part of the stage exit gates defined in [Success Criteria](success-criteria.md).
