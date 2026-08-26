# Success Criteria

## 1. Purpose

This document defines how success will be measured for the Industrial Sound Anomaly Detection Pipeline. It covers the complete system—from ingesting the MIMII source archive through validation, audio feature extraction, anomaly scoring, storage, querying, reporting, and operations.

The criteria are acceptance gates, not aspirations. A stage is complete only when its required criteria have objective evidence.

## 2. Project objective

Build a reproducible AWS pipeline that:

1. Ingests industrial fan audio and its metadata without losing source lineage.
2. Detects invalid, corrupt, incomplete, or duplicate inputs.
3. Extracts consistent acoustic features from valid WAV files.
4. Assigns an unsupervised anomaly score to each recording or analysis window.
5. Stores analysis-ready records as partitioned Parquet.
6. Makes results queryable with Athena.
7. Produces scheduled operational and anomaly reports.
8. Exposes processing, data-quality, failure, and cost signals.

## 3. Scope of the first release

The first release uses:

- Dataset: MIMII.
- Machine type: fan.
- Source archive: `6_dB_fan.zip`.
- AWS Region: `us-west-2`.
- Training approach: unsupervised training using normal recordings only.
- Output granularity: one record per WAV file for the initial baseline; window-level records may be added later.

The first release does not claim to diagnose a specific mechanical fault, perform real-time streaming, or control production machinery.

## 4. Overall definition of done

The prototype is complete when all required conditions below are satisfied:

- The source archive is verified and retained in S3.
- Valid WAV files can pass through the pipeline without manual intervention.
- Invalid test files are quarantined with explicit reason codes.
- Feature and anomaly records are written as schema-compliant Parquet.
- Athena can query the results using partition pruning.
- A scheduled report summarizes volume, quality, failures, latency, and anomaly results.
- CloudWatch exposes actionable metrics and alarms.
- Infrastructure and processing code can be recreated from version-controlled definitions.
- Tests pass in CI for the supported development environment.

## 5. Acceptance criteria

### 5.1 Source ingestion and integrity

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| ING-01 | The selected MIMII archive is stored in the raw S3 zone | 1 verified archive | S3 object URI and successful `HeadObject` result |
| ING-02 | S3 object size matches the published source | `10,158,673,161` bytes | Source manifest and S3 `ContentLength` |
| ING-03 | Downloaded archive MD5 matches the published checksum | `0890f7d3c2fd8448634e69ff1d66dd47` | Checksum command output or ingestion log |
| ING-04 | Source provenance is recorded | 100% of source archives | Manifest includes source URL, record ID, license, checksum, size, and ingestion time |
| ING-05 | Raw source is protected from public access | 100% | S3 Block Public Access configuration |
| ING-06 | Raw objects are encrypted at rest | 100% | S3 encryption configuration or object metadata |
| ING-07 | A repeated ingestion does not silently overwrite a different source | 0 silent replacements | Versioning, checksum guard, or explicit idempotency test |
| ING-08 | Temporary transfer infrastructure is removed after verification | 100% | EC2 terminated and temporary EBS volume deleted |

Stage 1 passes only when ING-01 through ING-08 pass.

### 5.2 Extraction and reconciliation

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| EXT-01 | Every extracted WAV is traceable to its archive | 100% | `source_archive` and `source_member_path` populated |
| EXT-02 | Extraction does not alter the original ZIP | 0 mutations | Raw source object version/checksum unchanged |
| EXT-03 | Extracted file count reconciles with the archive manifest | 100% match | Archive inventory compared with S3 object inventory |
| EXT-04 | Failed members are recorded explicitly | 100% of failures | Failure manifest with member path and reason |
| EXT-05 | Extraction is safe to rerun | No duplicate logical recordings | Idempotency integration test |

### 5.3 Input and metadata validation

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| VAL-01 | Every discovered WAV receives a terminal validation status | 100% | `valid` or `invalid` record for every discovered WAV |
| VAL-02 | Valid MIMII audio meets the expected sample rate | `16,000 Hz` | Validation result and test fixtures |
| VAL-03 | Valid MIMII audio meets the expected sample width | `16 bit` | Validation result and test fixtures |
| VAL-04 | Required metadata is present and schema-valid | 100% of accepted files | Contract validation result |
| VAL-05 | Corrupt and unreadable WAV files are rejected | 100% of corrupt fixtures | Automated negative tests |
| VAL-06 | Missing required metadata is rejected | 100% of missing-field fixtures | Automated negative tests |
| VAL-07 | Invalid inputs are quarantined with one or more reason codes | 100% | Quarantine record and S3 URI |
| VAL-08 | Validation is deterministic | Same input and rules produce same result | Repeat-run test |
| VAL-09 | Duplicate deliveries do not create duplicate accepted records | 0 duplicates | Duplicate-event integration test |

### 5.4 Audio feature extraction

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| FEA-01 | Every accepted WAV produces a feature record or explicit failure | 100% | Reconciliation query |
| FEA-02 | Required baseline features are populated | 100% of successful records | Schema validation |
| FEA-03 | Numerical outputs contain no unexpected infinity values | 0 | Automated data-quality check |
| FEA-04 | Null feature values are limited to documented cases | 100% compliant | Null-rate query by column |
| FEA-05 | Feature extraction is deterministic within numeric tolerance | 100% of repeat test sample | Golden-file or tolerance-based test |
| FEA-06 | Feature definitions and code version are recorded | 100% | `feature_schema_version` and `pipeline_version` fields |
| FEA-07 | Processing a single file does not require loading the full dataset | Required | Code review and memory test |
| FEA-08 | At least 99% of valid files process successfully in a complete run | `>= 99%` | Batch/Parquet reconciliation report |

Required baseline features:

- RMS energy.
- Zero-crossing rate.
- Spectral centroid.
- Spectral bandwidth.
- Spectral roll-off.
- Spectral flatness.
- Configured frequency-band energy.
- MFCC summary statistics.
- Peak amplitude, clipping ratio, silence ratio, and duration.

### 5.5 Workflow reliability and performance

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| ORC-01 | Transient failures use bounded retries with backoff | 100% of retryable states | Step Functions definition and test execution |
| ORC-02 | Permanent failures enter a known terminal path | 100% | Failure-path integration tests |
| ORC-03 | Every execution has a correlation identifier | 100% | Logs and output records |
| ORC-04 | Duplicate events do not duplicate final records | 0 duplicates | Idempotency integration test |
| ORC-05 | Processing time is measured per file/job/execution | 100% | CloudWatch metric or structured log |
| ORC-06 | Initial prototype processes a representative sample end to end | At least 100 normal and 100 anomalous files when available | Execution report |

The full-run latency target will be established after the representative benchmark. The baseline must record file count, vCPU, memory, wall-clock duration, and estimated cost.

### 5.6 Anomaly detection

Model targets must be finalized after a leakage-free baseline run. Until then, the required acceptance gate is reproducibility and honest evaluation rather than a predetermined high score.

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| ML-01 | Only normal recordings are used to fit the unsupervised baseline | 100% | Training manifest |
| ML-02 | Train, validation, and test membership is reproducible | 100% | Versioned split manifest and random seed |
| ML-03 | Anomaly labels are excluded from feature fitting and model training | 0 label leakage | Code review and test |
| ML-04 | Every successfully processed record receives a finite anomaly score | 100% | Data-quality query |
| ML-05 | Evaluation is reported overall and by fan model ID | Required | Evaluation report |
| ML-06 | ROC-AUC and PR-AUC are reported | Required | Evaluation report |
| ML-07 | Threshold, false-positive rate, precision, recall, and confusion matrix are reported | Required | Evaluation report |
| ML-08 | Model, scaler, features, code, and threshold are versioned together | 100% | Model manifest |
| ML-09 | Baseline results are reproducible within documented tolerance | Required | Repeated evaluation run |

After the first baseline, numeric promotion targets should be added here. Any target must be specified overall and per machine model so that strong aggregate performance cannot hide a weak subgroup.

### 5.7 Parquet storage, Glue, and Athena

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| DAT-01 | Successful processed records conform to the approved data contract | 100% | Schema validation report |
| DAT-02 | Results use compressed Parquet | 100% | S3 object inspection |
| DAT-03 | Data is partitioned by approved low/medium-cardinality fields | 100% | S3 layout and Glue table definition |
| DAT-04 | Partition columns are queryable in Athena | 100% | Test queries |
| DAT-05 | Source-to-output counts reconcile | 100% accounted for | Athena reconciliation query |
| DAT-06 | Queries for one machine/date scan only relevant partitions | Required | Athena query statistics |
| DAT-07 | The pipeline avoids uncontrolled tiny-file creation | Required | File-count and average-size report |
| DAT-08 | Schema and feature versions are present in every processed record | 100% | Athena validation query |

### 5.8 Reporting and observability

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| OBS-01 | Scheduled report generation succeeds without manual action | 100% in acceptance test | Scheduler execution and report object |
| OBS-02 | Report includes received, accepted, rejected, processed, and failed counts | Required | Report review |
| OBS-03 | Report includes anomaly-score summary and top anomalous records | Required | Report review |
| OBS-04 | Report includes processing latency and data-quality rates | Required | Report review |
| OBS-05 | Pipeline errors produce structured logs | 100% of tested failures | CloudWatch Logs inspection |
| OBS-06 | Alarms exist for workflow failure and elevated validation-failure rate | Required | Alarm configuration and test |
| OBS-07 | Logs contain no secrets or private keys | 0 findings | Log review/security scan |

### 5.9 Security and cost

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| SEC-01 | Workloads use IAM roles instead of long-lived access keys | 100% | IAM/configuration review |
| SEC-02 | IAM policies follow least privilege for defined resources | Required | Policy review |
| SEC-03 | S3 public access is blocked | 100% of project buckets | S3 configuration |
| SEC-04 | Storage encryption is enabled | 100% of S3/EBS resources | Resource configuration |
| SEC-05 | Network access to temporary EC2 is restricted | Required | Security-group review |
| CST-01 | AWS Budget alerts are configured | Required | Budget configuration |
| CST-02 | Athena workgroup has cost controls | Required | Workgroup configuration |
| CST-03 | CloudWatch logs have explicit retention | 100% of project log groups | Log-group configuration |
| CST-04 | Temporary resources are tagged and removed after use | 100% | Resource inventory |
| CST-05 | A representative run records estimated service cost | Required | Benchmark report |

### 5.10 Testing and delivery

| ID | Criterion | Target | Required evidence |
|---|---|---:|---|
| TST-01 | Unit tests cover validation and core feature calculations | Required | CI test report |
| TST-02 | Valid, invalid, corrupt, duplicate, and missing-metadata fixtures exist | Required | Test fixture inventory |
| TST-03 | At least one end-to-end integration test succeeds | Required | CI or deployment test result |
| TST-04 | Terraform configuration validates successfully | 100% | CI output |
| TST-05 | Python dependencies and container base image are pinned | Required | Repository review |
| TST-06 | Deployment and rollback steps are documented | Required | Runbook review |

## 6. Stage exit gates

| Stage | Exit gate |
|---|---|
| Stage 0 — Definition | Scope, architecture, data contract, success criteria, risks, security approach, and cost controls are documented |
| Stage 1 — Ingestion | ING-01 through ING-08 pass |
| Stage 2 — Extraction | EXT-01 through EXT-05 pass |
| Stage 3 — Validation | VAL-01 through VAL-09 pass |
| Stage 4 — Orchestration | ORC-01 through ORC-06 pass |
| Stage 5 — Features | FEA-01 through FEA-08 pass |
| Stage 6 — Anomaly scoring | ML-01 through ML-09 pass and numeric promotion targets are agreed |
| Stage 7 — Storage/catalog | DAT-01 through DAT-08 pass |
| Stage 8 — Query | Required Athena acceptance queries pass with recorded scan statistics |
| Stage 9 — Reporting | OBS-01 through OBS-04 pass |
| Stage 10 — Operations | OBS-05 through OBS-07 and security/cost gates pass |
| Stage 11 — IaC/CI/CD | TST-01 through TST-06 pass |

## 7. Evidence and sign-off

Evidence should be stored in version control when it contains no sensitive information, or referenced by an S3/CloudWatch/AWS Console identifier when it is environment-specific.

For each stage, record:

- Review date.
- Environment and AWS Region.
- Pipeline and schema version.
- Criteria passed, failed, or waived.
- Links or identifiers for evidence.
- Known limitations.
- Reviewer/owner.

Any waived criterion must include a reason, risk, mitigation, owner, and review date.
