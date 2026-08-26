# Industrial Sound Anomaly Detection Pipeline

An end-to-end AWS data pipeline for ingesting, validating, processing, querying, and reporting on industrial machine audio. The initial use case is **unsupervised anomaly detection for industrial fans** using the [MIMII dataset](https://zenodo.org/records/3384388).

The intended outcome is a repeatable pipeline that identifies unusual fan sounds that may indicate contamination, leakage, rotational imbalance, damage, or another developing machine fault.

## Current project status

**Current stage: Stage 1 — Raw data ingestion**

Last updated: **2026-08-26**

| Item | Status | Notes |
|---|---|---|
| Create raw S3 bucket | Complete | Raw landing bucket created in `us-west-2` |
| Configure S3 lifecycle protection | Complete | Incomplete multipart uploads are cleaned up automatically |
| Create least-privilege EC2 IAM role | Complete | Grants the temporary transfer instance access to the raw bucket |
| Launch temporary EC2 instance | Complete | Ubuntu 24.04, `t3.small`, 30 GiB `gp3` |
| Configure secure EC2 access | Complete | EC2 Instance Connect and restricted SSH access configured |
| Download MIMII fan archive from Zenodo | Complete | `6_dB_fan.zip` downloaded to the temporary EC2 instance |
| Verify source size and MD5 checksum | In progress | Expected size: `10,158,673,161` bytes; expected MD5: `0890f7d3c2fd8448634e69ff1d66dd47` |
| Upload original archive to S3 | Pending verification | Target key: `source-archives/6_dB_fan.zip` |
| Verify uploaded S3 object | Pending | Confirm object size, encryption, and accessibility before terminating EC2 |

The temporary EC2 instance must not be terminated until the archive checksum is valid and the S3 object has been verified.

## Target architecture

```text
MIMII WAV archives + source metadata
                  |
                  v
        Amazon S3 raw zone
        - source-archives/
        - recordings/
        - metadata/
        - manifests/
                  |
                  v
            EventBridge
                  |
                  v
       Lambda intake validation
                  |
                  v
          AWS Step Functions
             /          \
            v            v
   AWS Batch/Fargate   S3 quarantine
   audio processing   rejected inputs
            |
            v
  S3 processed zone: partitioned Parquet
            |
            v
       AWS Glue Data Catalog
            |
            v
          Amazon Athena
            |
            v
 EventBridge Scheduler -> report generation

CloudWatch logs, metrics, dashboards, and alarms cover all stages.
Terraform manages cloud infrastructure, Docker packages processing jobs,
and GitHub Actions runs tests and deployment checks.
```

## Data zones and object structure

```text
s3://<raw-bucket>/
├── source-archives/
│   └── 6_dB_fan.zip
├── recordings/
│   └── machine_type=fan/
│       └── model_id=<id>/
│           └── condition=<normal|anomaly>/
│               └── *.wav
├── metadata/
│   └── *.json
├── manifests/
│   └── ingestion_date=YYYY-MM-DD/
│       └── manifest.json
└── quarantine/
    └── reason=<validation_reason>/

s3://<processed-bucket>/
└── audio_features/
    └── machine_type=fan/
        └── model_id=<id>/
            └── event_date=YYYY-MM-DD/
                └── part-*.parquet

s3://<report-bucket>/
└── reports/
    └── report_period=<daily|weekly>/
        └── report_date=YYYY-MM-DD/
```

The original ZIP is retained as an immutable source artifact. Processing jobs operate on extracted WAV files rather than reading audio repeatedly from inside the ZIP.

## Pipeline stages

### Stage 0 — Project definition and cost controls

**Purpose:** Define a narrow, measurable use case and prevent unexpected AWS spending.

Work:

- Use MIMII fan recordings at the `6 dB` signal-to-noise level.
- Detect anomalous fan behaviour without relying on anomaly labels during model training.
- Select `us-west-2` as the working AWS Region.
- Configure an AWS monthly budget and billing alerts.
- Define naming, tagging, encryption, and least-privilege IAM conventions.

Deliverables:

- Use-case statement and success criteria.
- Architecture decision record.
- AWS budget and alerts.
- Resource naming and tagging convention.

Status: **Complete for the initial prototype.**

### Stage 1 — Raw data ingestion

**Purpose:** Transfer the original MIMII archive to durable cloud storage without corrupting or silently changing it.

Work:

- Create the S3 raw-data bucket and prefixes.
- Configure encryption, public-access blocking, and lifecycle rules.
- Create a least-privilege IAM policy and EC2 role.
- Launch a temporary EC2 transfer instance in the same Region as S3.
- Download `6_dB_fan.zip` directly from Zenodo using resumable parallel transfer.
- Validate exact byte size and MD5 checksum.
- Upload the original archive to `source-archives/` using multipart upload.
- Verify the S3 object, then terminate the temporary EC2 instance.

Deliverables:

- Verified immutable source archive in S3.
- Source URL, license, byte size, checksum, and ingestion timestamp.
- Initial ingestion manifest.
- Transfer logs showing success or failure.

Status: **In progress — download complete; checksum and S3 upload verification remain.**

### Stage 2 — Extraction and raw-data organization

**Purpose:** Convert the source archive into individual WAV objects and machine-readable metadata.

Work:

- Build a Docker image for the extraction job.
- Run the job with AWS Batch on Fargate.
- Extract WAV files without modifying the original archive.
- Parse labels encoded in directory and file names.
- Write WAV files under deterministic S3 prefixes.
- Produce one metadata record per audio object.
- Produce a manifest containing counts, sizes, checksums, and source lineage.

Deliverables:

- Extracted WAV files in `recordings/`.
- Normalized JSON or Parquet metadata.
- Extraction manifest and reconciliation report.
- Repeatable Docker image and Batch job definition.

Status: **Not started.**

### Stage 3 — Intake and data-quality validation

**Purpose:** Reject or quarantine invalid inputs before expensive feature processing.

Validation checks:

- File extension and valid WAV container.
- Expected sample rate: `16 kHz`.
- Expected sample width: `16 bit`.
- Channel count and readable audio frames.
- Positive, reasonable duration.
- Non-empty file and non-silent/corrupt content checks.
- Required machine type, model ID, condition, source, and timestamp metadata.
- Duplicate object or checksum detection.
- Timestamp parsing and accepted time range.

Flow:

```text
S3 object-created event -> EventBridge -> Lambda validation
                                      ├── valid   -> Step Functions
                                      └── invalid -> S3 quarantine + metric
```

Deliverables:

- Lambda validation function.
- Validation schema using Pandera or Great Expectations where appropriate.
- Quarantine prefix and reason codes.
- Unit tests and representative valid/invalid fixtures.
- Data-quality metrics and alarms.

Status: **Not started.**

### Stage 4 — Workflow orchestration

**Purpose:** Make processing observable, retryable, and safe to rerun.

Work:

- Implement an AWS Step Functions Standard workflow.
- Pass S3 object references rather than audio bytes between states.
- Submit AWS Batch jobs for valid inputs.
- Configure retries with backoff for transient failures.
- Route permanent failures to quarantine or a failure prefix.
- Record execution ID, timestamps, status, and error details.
- Ensure idempotency so duplicate events do not create duplicate outputs.

Deliverables:

- Step Functions state machine.
- IAM execution roles with least privilege.
- Retry, timeout, catch, and failure-routing behaviour.
- Execution metrics and CloudWatch alarms.

Status: **Not started.**

### Stage 5 — Audio feature extraction

**Purpose:** Transform each WAV file into compact numerical features suitable for analysis and anomaly detection.

Planned features:

- RMS energy.
- Zero-crossing rate.
- Spectral centroid, bandwidth, roll-off, and flatness.
- Energy in configurable frequency bands.
- MFCCs and summary statistics.
- Duration, clipping ratio, peak amplitude, and silence ratio.

Processing principles:

- Process audio incrementally rather than loading the complete dataset into memory.
- Preserve the source S3 URI and checksum for lineage.
- Version feature definitions and processing code.
- Store one logical record per audio file or time window.

Deliverables:

- Python feature-extraction package using NumPy, SciPy, and librosa.
- Docker image suitable for AWS Batch.
- Unit and integration tests.
- Feature schema and version metadata.
- Processing-time and failure metrics.

Status: **Not started.**

### Stage 6 — Anomaly scoring

**Purpose:** Assign an anomaly score to each fan recording or time window.

Initial approach:

- Train only on normal fan recordings.
- Standardize features using statistics learned from the training set.
- Establish a baseline with Isolation Forest or a reconstruction-based model.
- Select thresholds from validation-score distributions.
- Evaluate using the hidden anomaly labels after scoring.
- Report ROC-AUC, precision-recall AUC, false-positive rate, and performance by model ID.

Deliverables:

- Reproducible training and inference code.
- Versioned model artifact and feature configuration.
- Evaluation report and chosen threshold.
- Anomaly score included in processed records.

Status: **Not started.**

### Stage 7 — Parquet storage and cataloguing

**Purpose:** Store analysis-ready results efficiently and make their schema discoverable.

Work:

- Write feature and anomaly records as compressed Parquet.
- Partition primarily by machine type, model ID, and event date.
- Avoid many tiny files by compacting output into appropriately sized objects.
- Register table definitions and partitions in AWS Glue Data Catalog.
- Track schema and feature versions.

Deliverables:

- Partitioned Parquet dataset in the processed S3 bucket.
- Glue database and table definitions.
- Schema-evolution policy.
- Row-count and source-to-output reconciliation checks.

Status: **Not started.**

### Stage 8 — Query and analytical validation

**Purpose:** Let users inspect quality, performance, and anomaly results using SQL.

Work:

- Configure an Athena workgroup and encrypted query-result location.
- Add scan limits and cost controls.
- Create saved queries for anomaly rates, machine/model comparisons, validation failures, and processing latency.
- Confirm partition pruning and compressed-columnar scans.

Deliverables:

- Athena workgroup and query-results prefix.
- Verified SQL queries and example outputs.
- Query-cost and scanned-byte checks.

Status: **Not started.**

### Stage 9 — Scheduled reporting

**Purpose:** Produce an operational summary without requiring manual queries.

Work:

- Use EventBridge Scheduler for daily or weekly execution.
- Query Athena for data quality, processing status, and anomaly summaries.
- Generate an HTML, CSV, or PDF report.
- Store reports in S3 and optionally publish a notification through SNS.

Report contents:

- Number of recordings received, accepted, quarantined, and processed.
- Missing metadata and validation-failure rates.
- Processing latency and failed executions.
- Highest anomaly scores and affected machine model IDs.
- Trends compared with the previous reporting period.

Deliverables:

- Scheduled report job.
- Versioned reports in S3.
- Optional email/SNS notification.

Status: **Not started.**

### Stage 10 — Observability and operations

**Purpose:** Detect failures quickly and understand pipeline health and cost.

Work:

- Use structured CloudWatch logs with execution and object identifiers.
- Publish custom metrics for files received, validation failures, quarantined files, processing duration, and feature-job failures.
- Create dashboards and alarms.
- Define log retention periods.
- Add operational runbooks for common failures and safe reprocessing.

Deliverables:

- CloudWatch dashboard.
- Alarms for pipeline failures and abnormal data-quality rates.
- Operational runbook.
- Cost-monitoring checklist.

Status: **Not started.**

### Stage 11 — Infrastructure as code and CI/CD

**Purpose:** Make the entire pipeline repeatable, testable, and safe to deploy.

Work:

- Define S3, IAM, EventBridge, Lambda, Step Functions, Batch, Glue, Athena, and CloudWatch resources in Terraform.
- Use separate development and production variables/state.
- Add Python formatting, linting, unit tests, schema tests, and Terraform validation to GitHub Actions.
- Build and scan Docker images before publishing them to ECR.
- Require review of infrastructure plans before deployment.

Deliverables:

- Terraform modules and environment configuration.
- GitHub Actions workflows.
- Dockerfile and pinned dependencies.
- Automated test suite and deployment documentation.

Status: **Not started.**

## Indicative timeline

| Week | Focus | Exit criterion |
|---|---|---|
| 1 | Stages 0–1: scope, cost controls, raw ingestion | Verified source archive and manifest in S3 |
| 2 | Stages 2–3: extraction and validation | WAV objects organized; invalid fixtures quarantined correctly |
| 3 | Stages 4–5: orchestration and features | End-to-end processing succeeds for a representative subset |
| 4 | Stage 6: anomaly baseline | Reproducible scores and evaluation metrics produced |
| 5 | Stages 7–8: Parquet, Glue, and Athena | Partitioned data is queryable with tested SQL |
| 6 | Stages 9–11: reporting, observability, IaC, CI/CD | Scheduled report, alarms, tests, and repeatable deployment work |

The timeline is a planning baseline. Processing a representative subset first is recommended before running the entire archive.

## Immediate next actions

1. Verify the downloaded archive size and MD5 checksum on EC2.
2. Upload it to `source-archives/6_dB_fan.zip` in the raw S3 bucket.
3. Confirm the S3 object has exactly `10,158,673,161` bytes.
4. Record the Zenodo URL, checksum, license, and ingestion timestamp in a manifest.
5. Terminate the temporary EC2 instance and confirm its root EBS volume was deleted.
6. Begin Stage 2 with a small extraction test before extracting the complete archive.

## Technology stack

- **Language and data:** Python, Polars or pandas, NumPy, SciPy, librosa, PyArrow, Parquet.
- **AWS ingestion and storage:** Amazon S3, EventBridge, Lambda.
- **Processing and orchestration:** AWS Batch on Fargate, Step Functions Standard.
- **Query:** AWS Glue Data Catalog and Amazon Athena.
- **Operations:** CloudWatch, EventBridge Scheduler, SNS.
- **Quality:** pytest, Pandera or Great Expectations.
- **Delivery:** Docker, Amazon ECR, Terraform, GitHub Actions.

## Cost-safety rules

- Keep compute resources in the same AWS Region as the S3 buckets.
- Use temporary EC2 only for the one-time source transfer, then terminate it.
- Confirm `Delete on termination` for temporary EBS volumes.
- Avoid NAT Gateway for the prototype unless private networking is a requirement.
- Use Batch only when work exists and start with a small dataset subset.
- Partition Parquet and compact small files to reduce Athena scanned bytes.
- Set Athena workgroup limits, CloudWatch retention, S3 lifecycle rules, and AWS Budget alerts.
