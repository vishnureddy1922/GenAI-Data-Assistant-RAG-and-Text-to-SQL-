# Data platform policies

## Ownership

- The `analytics` schema and the nightly dbt build are owned by the Data Engineering team. Contact them in the #data-eng channel.
- Metric definitions are owned by the Analytics team. Changes need approval from the Head of Analytics.
- Source system issues (missing orders, wrong statuses) go to the Commerce Platform team.

## Refresh schedule and SLA

The warehouse refreshes every night. Source extracts land at 02:00 UTC, dbt runs at 03:00 UTC and the `analytics` tables are ready by 05:00 UTC. The SLA is 06:00 UTC on business days. If data is late, a notice is posted in #data-status.

Data for the current day is never complete. Dashboards show data through yesterday.

## PII and access

Customer email and full name are personally identifiable information (PII). PII must not be exported to spreadsheets or shared outside the company. Analysts can query PII columns for operational work, but reports and dashboards must aggregate or mask them. Access is reviewed every quarter.

## Retention

Order data is kept for 7 years for finance and tax reasons. Raw clickstream data is kept for 13 months. Customer accounts closed by request are anonymized within 30 days.

## Data quality

Every dbt model has tests for unique keys, not null keys and referential integrity. The nightly build fails, and tables are not published, if any of these tests fail. Revenue is reconciled against the finance ledger every month and must match within 0.5%.
