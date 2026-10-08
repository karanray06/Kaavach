# 🛡️ Kaavach

> **An open-source AI-powered scam triage and community early-warning system.**

Kaavach analyzes social-engineering scams delivered through **SMS, WhatsApp, email, and fake web pages**. It combines rule-based extraction, AI analysis, scam fingerprinting, and Snowflake-powered threat intelligence to detect scams and identify related campaigns.

### 🎯 Threats in Scope

- Fake KYC / bank-block messages
- UPI collect-request and refund scams
- OTP theft
- Parcel and customs scams
- Fake job and task scams
- Investment scams
- Impersonation / "digital arrest" scams
- Suspicious or malicious links

### 🚫 Out of Scope

Kaavach does **not** block messages, access your inbox, visit suspicious links, or guarantee safety. Results are advisory and include a confidence value.

---

## 🧠 How It Works

```text
User Input
    ↓
Extraction & Rules
(URLs, phones, UPI IDs, wallets)
    ↓
AI Classification
(Gemini + structured analysis)
    ↓
Scam DNA
(SimHash + campaign similarity)
    ↓
Snowflake
(Scans, indicators, campaigns)
    ↓
Community Threat Intelligence
```

### Key Components

**Extraction & Rules**  
Fast detection of suspicious indicators and heuristic signals.

**AI Classification**  
Google GenAI / Gemini analyzes the meaning and social-engineering tactics behind suspicious content.

**Scam DNA**  
SimHash fingerprints similar scam messages and helps group them into larger campaigns.

**Community Memory**  
Snowflake stores scans, redacted indicators, and campaign information so previously observed threats can provide context for future detections.

**Threat Intelligence**  
The project integrates with Snowflake Marketplace threat-intelligence data such as the Cybersixgill Deep and Darkweb Malware Insights dataset.

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **AI:** Google GenAI / Gemini API
- **Data & Analytics:** Snowflake
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Templates:** Jinja2
- **Validation:** Pydantic
- **Fingerprinting:** SimHash

---

## 📁 Project Structure

```text
Kaavach/
├── app/          # Backend / application logic
├── config/       # Configuration
├── docs/         # Architecture, threat model, Snowflake docs
├── fixtures/     # Sample / test data
├── skills/       # Scam-triage resources
├── sql/          # Snowflake / database SQL
├── web/          # Frontend
├── benchmarks.py
├── seed_snow.py
├── test_dna.py
├── test_extract.py
├── test_gemma.py
├── test_health.py
├── test_rules.py
├── .env.example
├── requirements.txt
└── submission.md
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/karanray06/Kaavach.git
cd Kaavach
```

### 2. Create a virtual environment

**Windows**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials.

Required configuration includes:

```env
GEMINI_API_KEY=
GEMINI_MODEL_ID=

SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
SNOWFLAKE_ROLE=

KAVACH_HMAC_KEY=
```

> **Never commit `.env` or any secrets to Git.**

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

For local API documentation:

```text
http://127.0.0.1:8000/docs
```

For Snowflake setup, see [`docs/SNOWFLAKE.md`](docs/SNOWFLAKE.md).

For the security model, see [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

---

## 🔐 Privacy & Security

- Images and text are processed in memory rather than stored as raw content.
- Sensitive indicators such as phone numbers and UPI IDs are HMAC-hashed before Snowflake storage.
- Submitted messages are sent to Google's Gemini API for analysis.
- Kaavach is an advisory security tool and does not guarantee that content is safe.

---

## 🗺️ Roadmap

- WhatsApp and Telegram integrations
- Improved Scam DNA / campaign clustering
- Embedding-based similarity
- Better multilingual scam detection
- Expanded threat-intelligence integrations
- Automated reporting workflows

---

## 🤝 Contributing

Contributions are welcome!

1. Create a feature branch:
   ```bash
   git switch -c feat/your-feature
   ```
2. Make focused changes.
3. Test your changes.
4. Review with:
   ```bash
   git status
   git diff
   ```
5. Commit and push your branch:
   ```bash
   git add .
   git commit -m "feat: describe your change"
   git push -u origin feat/your-feature
   ```
6. Open a Pull Request.

Please avoid unrelated changes, never commit secrets, and add/update tests when changing backend behavior.

---

## 📄 License

Kaavach is released under the **MIT License**.

See [`LICENSE`](LICENSE) for details.

---

## 🛡️ Vision

> **Don't just detect a scam — connect it to the campaign behind it.**

Kaavach aims to turn individual scam reports into shared intelligence that can help communities recognize emerging threats earlier.