# Kavach: An Immune System for Scams

## Elevator Pitch
Kavach is an open-source scam triage and community early-warning system that combines Google Gemini's reasoning with Snowflake's data cloud to detect individual social engineering scams and cluster related fraud campaigns.

## The Problem
Scams delivered via SMS, WhatsApp, email, and social media are growing exponentially, leveraging regional languages and cultural engineering (such as fake KYC deactivations, electricity disconnection alerts, or task scams). Static regex rules fail against mutating payloads. Moreover, individuals fight scams in silos without shared threat intelligence.

## The Solution (Kavach)
Kavach implements a multi-stage triage pipeline:
1. **Extraction & Heuristics**: Rapidly parses suspicious phone numbers, UPI handles, URLs (including protocol-less shorteners), and wallets, assigning a deterministic risk score.
2. **AI Classification**: Leverages **Google Gemini** (`gemini-3.8-flash` via `google-genai`) with structured JSON schema outputs (`response_schema`) to evaluate intent, identify underlying social engineering tactics, and provide advisory user actions.
3. **Prompt Injection Hardening**: Fences untrusted user inputs inside `<UNTRUSTED_CONTENT>` boundaries and enforces system instructions to neutralize evasion attempts.
4. **Scam DNA (SimHash)**: Fingerprints message structures to measure Hamming distance and group related messages into campaigns.
5. **Community Memory & Analytics (Snowflake)**: Asynchronously persists scans, campaign clusters (via SQL `MERGE`), and HMAC-SHA256 hashed indicators into Snowflake (`KAVACH.CORE`). Analytical views (`V_TRENDING_TACTICS`, `V_CAMPAIGN_GROWTH`) power community radar dashboards without exposing raw PII.

## Technologies Used
- **Backend**: FastAPI, Uvicorn, Python
- **AI/ML**: Google GenAI SDK (`gemini-3.8-flash` / Gemini API)
- **Data & Analytics**: Snowflake (`snowflake-connector-python`, Views, MERGE persistence)
- **Security**: HMAC-SHA256 IOC hashing, `slowapi` rate limiting, magic-byte upload validation
- **Frontend**: Vanilla HTML/CSS/JavaScript (Swiss Poster Design System)

## AI Classification & Defense Posture
We integrated Google's Generative AI via the modern `google-genai` SDK using `gemini-3.8-flash`:
- **Structured Output**: Enforces strict Pydantic schemas (`is_scam`, `confidence`, `tactics`, `explanation`, `actions`) ensuring reliable JSON responses without markdown truncation.
- **Prompt Isolation**: Protects the triage model by segregating `system_instruction` and encapsulating untrusted input inside `<UNTRUSTED_CONTENT>` tags with explicit delimiter sanitization.
- **Multilingual Support**: Supports dynamic target translation for regional explanations (Hindi, Telugu, Tamil, Marathi, etc.).

## Snowflake Integration
Snowflake serves as the persistent analytics and threat correlation layer:
- **Zero Raw PII Storage**: All indicators (phone numbers, UPI IDs, emails, URLs) are hashed via HMAC-SHA256 (`ioc_hash`) using `KAVACH_HMAC_KEY` before entering `KAVACH.CORE.INDICATORS`.
- **Atomic Campaign Upserts**: `insert_or_update_campaign` uses SQL `MERGE INTO KAVACH.CORE.CAMPAIGNS` to record campaign velocity, volume, and tactics.
- **Production Analytics Views**: `V_TRENDING_TACTICS`, `V_CAMPAIGN_GROWTH`, and `V_SEEN_BEFORE` query live scan trends while filtering out synthetic fixtures (`WHERE is_demo = FALSE`).
- **Asynchronous Ingestion**: Ingestion runs via FastAPI `BackgroundTasks` to keep API response latencies minimal.

*(Note: External marketplace dataset joins such as Cybersixgill and Cortex Copilot NLQ integrations remain exploratory architecture concepts documented in `docs/SNOWFLAKE.md` rather than active runtime dependencies).*

## Next Steps
- Expand messaging integrations (WhatsApp Business API and Telegram bot webhooks).
- Explore vector embeddings alongside SimHash for semantic campaign clustering.
- Integrate automated reporting workflows for community cybercrime portals.
