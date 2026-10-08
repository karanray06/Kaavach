# Snowflake Architecture & Integration: Kavach

This document details the active Snowflake architecture implemented in Kavach, as well as the design boundaries for external threat intelligence integrations.

---

## 1. Active Implementation

Kavach connects to Snowflake using `snowflake-connector-python` with credentials configured in `.env`. All live telemetry, campaign clustering, and indicator matching run on the `KAVACH` database under the `CORE` schema.

### Core Tables
- **`KAVACH.CORE.SCANS`**: Records incoming scam scans (UUID, timestamp, scam probability, primary tactic, raw/matched SimHash DNA, and language).
- **`KAVACH.CORE.INDICATORS`**: Stores Indicators of Compromise (IOCs) linked to scan records. **All IOC values are strictly HMAC-SHA256 hashed (`ioc_hash`)** before insertion to ensure zero raw PII is persisted.
- **`KAVACH.CORE.CAMPAIGNS`**: Tracks aggregated campaigns identified through SimHash distance matching. Updated using atomic `MERGE INTO` operations (`insert_or_update_campaign`).

### Analytics Views
All analytical views in `sql/02_views.sql` filter out synthetic test fixtures with `WHERE is_demo = FALSE`:
- **`V_TRENDING_TACTICS`**: Aggregates top scam tactics over the trailing 7 days with scan volume and average confidence.
- **`V_CAMPAIGN_GROWTH`**: Measures daily campaign propagation and velocity over trailing 14 days.
- **`V_SEEN_BEFORE`**: Enables fast sub-second lookups for previously reported IOC hashes.

### Background Persistence
Persistence to Snowflake occurs asynchronously via FastAPI `BackgroundTasks` in `app/pipeline.py`, ensuring user scan latency is decoupled from cloud database write operations.

---

## 2. External Intelligence & Cortex (Design / Concept Scope)

- **Marketplace Threat Feeds (e.g. Cybersixgill `DARKFEED.MALWARE_INSIGHTS_VIEW`)**:
  *Status*: Concept / Architectural Stub.
  *Details*: Explored as a method for enriching extracted malicious domains and malware hashes. The repository includes an architectural placeholder view (`V_CONTEXT_STUB`), but **the live codebase does not perform live joins against external marketplace databases at runtime**.
- **Snowflake Cortex Copilot (CoCo)**:
  *Status*: Design Exploration.
  *Details*: Evaluated during prototyping for natural language SQL query generation against threat intelligence tables. The active Kavach backend queries Snowflake directly using parameterized SQL queries in `app/snow.py`, rather than invoking Cortex APIs during scan execution.
