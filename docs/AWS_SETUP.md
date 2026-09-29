# AWS setup and cost plan

Status: planned; no AWS account access or resources have been verified in this project.

## Known and unknown

User reports $100 signup credits. Current balance, expiry, account plan, region, permitted models, quotas, and eligible services are unknown. User explicitly deferred the optional hackathon credit request; continue local work.

## Stage A: before live calls

1. Inspect Billing for plan, usable balance, expiry, and credit restrictions.
2. Choose one region where a suitable Bedrock model is available to the account.
3. Verify that model supports the tool-calling flow we implement.
4. Configure local AWS authentication using the supported credential chain and scoped permissions. Prefer short-lived credentials; do not embed credentials in source or frontend code.
5. Configure cost tracking and alerts before repeated live testing. Alerts are notifications, not a guaranteed hard spending cap.
6. Record chosen model ID, region, pricing check date, and access test in DECISIONS.md.

## Stage B: smallest real integration

Run a single short Bedrock request, then one real tool-backed accounting request. Capture sanitized evidence: date, model/region, success/failure, token usage if available, and estimated charge. Do not capture secrets. Verify the installed Strands version against its current official documentation before using examples.

## Stage C: persistence

Introduce private S3 source storage and DynamoDB scenario persistence only when local storage contracts pass. Restrict permissions to the intended resources. Keep resource names in configuration and log identifiers sparingly. Document reproducible creation and cleanup commands after they are implemented.

## Configuration contract to implement

| Name | Meaning |
| --- | --- |
| AWS_PROFILE | Local authenticated profile, if used |
| AWS_REGION | Explicit chosen service region |
| BEDROCK_MODEL_ID | Verified model or inference-profile identifier |
| APP_MODE | Clearly distinguished local mock / live / demo behavior |
| STORAGE_BACKEND | Local or verified AWS adapter |
| S3_BUCKET_NAME | Private source bucket, when implemented |
| DYNAMODB_TABLE_NAME | Scenario/data table, when implemented |

These are proposed configuration names. Supply a matching `.env.example` only when the application actually reads them. Secret values never belong in `.env.example`.

## Development spending controls

Use mocks for unit tests and UI iteration; label mock mode visibly. Bound prompt length, output tokens, retries, agent steps, and concurrent calls. Cache reusable synthetic tool results where appropriate. Keep provider usage records. Avoid provisioned model throughput and always-on servers for this MVP. Set a personal testing budget after reviewing the account; no budget is assumed or authorized by this document.

For AWS Budgets, track service usage before credits as well as remaining credits so offsets do not hide consumption. Exact model costs depend on the chosen provider, region, tokens, and account terms. Record measured usage instead of a guaranteed dollar estimate.

## Credit offer

The competition advertises a $150 request for registered participants, while supplies last. See the official form and rules in RESOURCES.md. Credit availability, combination with signup offers, and covered charges must be verified. The user's request remains deferred. ROADMAP.md records the cutoff without scheduling a reminder.

## Judging and deployment

The organizer FAQ permits a locally runnable repository plus video. Keep clear live-mode and mock-mode instructions, real integration evidence, and a reviewer testing path free of charge. Do not require reviewers to share credentials with you. If live access needs hosting, settle that path before release and maintain it through judging. Mock mode supports reproducibility but does not prove AWS integration.

Sources: [AWS Free Tier](https://aws.amazon.com/free/), [credit terms](https://aws.amazon.com/awscredits/), [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html), [competition FAQ](https://amazonappdev2026.devpost.com/details/faqs). Recheck technical details when implementing.
