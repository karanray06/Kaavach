# Kavach: An Immune System for Scams

## Elevator Pitch
Kavach is an immune system for messaging scams, combining Google Gemini's reasoning with Snowflake's data cloud to not just detect individual scams, but track and cluster organized campaigns across languages.

## The Problem
Scams on SMS, WhatsApp, and social media are growing exponentially, often using local languages and highly contextual cultural engineering (like fake KYC, electricity bill threats, or lottery promises). Traditional regex and static rules fail because the text mutates constantly. Furthermore, users fight scams alone; there is no "community immunity."

## The Solution (Kavach)
Kavach solves this through a five-loop architecture:
1. **Extraction & Rules**: Rapidly extracts URLs, phones, UPI IDs, and crypto wallets, applying a fast heuristic score.
2. **LLM Classification**: Uses **Google Gemini** (Gemma via the Gemini API) to perform deep semantic analysis of the text (and soon images) to detect the underlying tactic (e.g., `FAKE_KYC`, `OTP_THEFT`) and explain *why* it's a scam.
3. **DNA Clustering**: Uses Simhash to fingerprint the text and clusters it into larger "Campaigns", revealing the scale of the operation.
4. **Community Memory (Snowflake)**: Scans, indicators, and campaigns are continuously ingested into **Snowflake**. If one person reports a scam, the extracted indicators are instantly marked as suspicious for everyone else.
5. **Real-world Context**: Snowflake Cortex Copilot (CoCo) allows natural language querying of trending tactics, and Kavach integrates with Snowflake Marketplace datasets (like Cybersixgill Darkweb Malware Insights) to cross-reference extracted indicators with known threat actor data.

## Technologies Used
- **Backend**: FastAPI (Python)
- **AI/ML**: Google GenAI SDK (Gemini API for classification)
- **Data & Analytics**: Snowflake (Core storage, Views, Cortex Copilot, Cybersixgill Marketplace integration)
- **Frontend**: Vanilla HTML/CSS/JS (Swiss Poster Design System)

## How We Used Gemma 4 (Best Use of Gemma 4 Track)
We integrated Google's Generative AI via the `google-genai` SDK using `gemini-3.1-pro-preview` (standing in for the Gemma 4 / Gemini API structured outputs). 
Gemma handles the hardest part of the pipeline: unstructured, adversarial text. It uses structured JSON output (`response_schema`) to bypass brittle regex and extract a unified schema containing a confidence score, the specific social engineering tactics used, and a clear, short explanation for the user.

## How We Used Snowflake (Best Open-Source AI with Snowflake Track)
Snowflake acts as the central nervous system for Kavach:
- **Data Cloud**: All scans, indicators (redacted), and campaign clusters are stored in Snowflake, creating a shared global blocklist.
- **Marketplace**: We mounted the **Cybersixgill Deep and Darkweb Malware Insights** dataset to cross-reference our extracted indicators with known dark web activity.
- **Cortex Copilot (CoCo)**: We used CoCo to naturally query the Cybersixgill dataset, identifying threat patterns without writing complex SQL manually.

## Next Steps
- Integrate WhatsApp and Telegram bots directly.
- Expand the DNA clustering to use Gemma embeddings instead of just Simhash.
- Implement real-time automated reporting to authorities.
