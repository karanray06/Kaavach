---
name: kavach-scam-triage
description: Explains how the Kavach pipeline runs and where the Snowflake hooks reside. Use this when extending the scam triage system.
---

# Kavach Scam Triage Pipeline

## Pipeline Overview

The pipeline (`app/pipeline.py`) executes five main loops over a single data spine:

1. **Scan loop (`app/extract.py`, `app/rules.py`)**: 
   Regex-based extraction of IOCs (phones, emails, UPI, crypto, URLs). Assigns a fast heuristic rule score.
2. **LLM Classification (`app/gemma.py`)**: 
   Passes the raw text to Google Gemini (Gemma 4 model structure via `gemini-3.1-pro-preview`). Uses `response_schema` to return structured JSON containing confidence score, tactics, and explanation.
3. **Memory loop (Snowflake `app/snow.py`)**: 
   Scans and indicators are ingested into Snowflake. The `insert_scan` function writes to the `KAVACH.CORE.SCANS` table. Note: Seen lookups currently fall back to memory but are designed to hit `KAVACH.CORE.INDICATORS` and the `V_SEEN_BEFORE` view.
4. **DNA loop (`app/dna.py`)**: 
   Calculates a 3-gram Simhash of the normalized text. A Hamming distance of <=12 groups the message into an existing `campaign_id`, tracking organized attacks.
5. **Radar & Drill loop**: 
   Exposed via the frontend (`web/radar.html`). Uses Snowflake views like `V_TRENDING_TACTICS` and the Cybersixgill Darkweb Malware Insights dataset (`DARKFEED.MALWARE_INSIGHTS_VIEW`) to provide threat intelligence.

## Extending the Pipeline
- **Adding new extraction rules**: Update `app/extract.py` regexes and `app/rules_data.json` weights.
- **Snowflake Context**: To integrate the Cybersixgill dataset deeply into the scan, update `app/snow.py` to query `V_CONTEXT_CYBERSIXGILL` during the "Blend" phase.

## Validation Script
Run `scripts/validate.py` to test the pipeline end-to-end on a dummy scam message.
