# Analytics Agent - Complete Setup & Operation Guide

A complete enterprise analytics workspace: **CSV / Excel File Upload → Deduplication & Data Profiling → Summary Preview → Multi-Stack Code Synthesis (Excel, PowerBI, MySQL, Python, All) → High-Resolution Dashboard Visual → Executive PDF Report**.

---

## Architecture Overview

```
                        ┌─────────────────────────────────────────┐
                        │       Android Client (Mobile App)       │
                        │  Jetpack Compose + Material 3 + Coil   │
                        └───────────────────┬─────────────────────┘
                                            │ REST / Multipart
                                            ▼
                        ┌─────────────────────────────────────────┐
                        │       FastAPI Analytics Backend         │
                        │  Uvicorn + Pandas + ReportLab + LLM     │
                        └───────────────────┬─────────────────────┘
                                            │
       ┌──────────────────┬─────────────────┼─────────────────┬──────────────────┐
       ▼                  ▼                 ▼                 ▼                  ▼
┌──────────────┐   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
│ 1. Excel     │   │ 2. PowerBI   │  │ 3. MySQL     │  │ 4. Python    │   │ 5. Multi PDF │
│ Dynamic LET  │   │ DAX Measures │  │ DDL Schemas  │  │ Pandas Clean │   │ Exec Report  │
│ XLOOKUP, M   │   │ Star Schema  │  │ Window/CTEs  │  │ Plots/KPIs   │   │ + Dashboard  │
└──────────────┘   └──────────────┘  └──────────────┘  └──────────────┘   └──────────────┘
```

---

## 1. Prerequisites

Make sure the following tools are installed on your machine:
- **Python**: `3.10` or higher (`3.11` recommended)
- **Java**: JDK `17` (required for Android build)
- **Android SDK**: API level `34` or `35` (or Android Studio Ladybug/Koala)
- **Git**: Installed and configured

---

## 2. Backend Setup (FastAPI Engine)

The backend performs deterministic calculations, deduplication, DAX/Excel/MySQL/Python synthesis, and PDF compilation.

### Step 2.1: Open Terminal in Backend Directory
```bash
cd "d:\Download\claude desktop\analytics-agent\backend"
```

### Step 2.2: Create & Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

**On Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### Step 2.3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
*(Includes `fastapi`, `uvicorn`, `pandas`, `numpy`, `reportlab`, `matplotlib`, `openpyxl`, `xlrd`)*

### Step 2.4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings in `.env`:
```ini
PORT=8000
HOST=0.0.0.0

# Optional: Set to true if using OpenAI/Gemini for narrative prose
LLM_ENABLED=false
OPENAI_API_KEY=your_openai_api_key_here

# Max Upload Size (MB)
MAX_UPLOAD_MB=100
```

### Step 2.5: Start Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will start at:
- **API Docs (Swagger UI)**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

---

## 3. Android App Setup (Jetpack Compose Client)

### Step 3.1: Open Terminal in Android Directory
```bash
cd "d:\Download\claude desktop\analytics-agent\android"
```

### Step 3.2: Configure Gradle Properties
Open or create `android/gradle.properties` (or `local.properties`) and specify your backend URL:

```properties
# If running on Android Emulator:
ANALYTICS_AGENT_API_URL=http://10.0.2.2:8000

# If running on Physical Phone (Use your PC's Local Wi-Fi IP address):
# ANALYTICS_AGENT_API_URL=http://192.168.1.XX:8000

# Optional Supabase config (if using multi-user project storage):
ANALYTICS_AGENT_SUPABASE_URL=https://your-project.supabase.co
ANALYTICS_AGENT_SUPABASE_KEY=your_publishable_anon_key
```

### Step 3.3: Build Debug APK
```bash
# Windows
.\gradlew.bat :app:assembleDebug

# Linux / Mac
./gradlew :app:assembleDebug
```
Generated APK will be located at:
`android/app/build/outputs/apk/debug/app-debug.apk`

### Step 3.4: Run on Connected Phone or Emulator
```bash
# Direct install to connected device via ADB:
adb install -r app/build/outputs/apk/debug/app-debug.apk
```
Or simply open the `android/` folder in **Android Studio** and click **Run (Shift + F10)**.

---

## 4. End-to-End Workflow & Modes

### 5 Selectable Delivery Modes:
1. **1. Excel Sirf**:
   - Generates dynamic array formulas: `LET`, `LAMBDA`, `XLOOKUP`.
   - Power Query (M-Code) ETL scripts.
   - Pivot table automation macro code.
2. **2. PowerBI**:
   - Star Schema data modeling (Fact tables, Dimension tables, 1:N cardinality).
   - Time-intelligence DAX measures (YoY, YTD, running totals, Pareto 80/20, KPI measures).
3. **3. MySQL**:
   - Production MySQL 8.0+ DDL schemas with `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`.
   - B-Tree index strategies.
   - Common Table Expressions (CTEs) & Window functions (`LAG`, `LEAD`, `DENSE_RANK`).
4. **4. Python**:
   - Pandas data cleaning & deduplication script (identifying duplicates vs unique records).
   - NumPy financial & KPI aggregations.
   - Matplotlib/Seaborn dark-theme plotting scripts matching the executive dashboard visual.
5. **5. All (Sabko)**:
   - Concurrently generates **all 4 stacks** (Excel + PowerBI + MySQL + Python)!

---

## 5. Live App Screens & Features

1. **Enterprise Prompt Library Screen**:
   - Pre-built corporate templates for **Executive C-Suite**, **Retail & E-Commerce**, **Finance & P&L**, **Supply Chain & Operations**, **HR & Workforce**, and **Marketing & Sales Funnel**.
   - 1-tap **"Use This Corporate Prompt"** button.

2. **Summary Preview Screen**:
   - Ingests file and shows **Total Records**, **Unique Records**, **Duplicate Rows (count & %)**, and **Quality Score (%)** before running full generation.

3. **Animated Execution Timeline**:
   - Live glowing multi-step pipeline with real-time descriptions:
     1. 📂 *Reading Dataset*
     2. 🔍 *Profiling Duplicates & Uniques*
     3. 🧹 *Data Cleaning & Star Schema Modeling*
     4. 🧠 *Deterministic Calculations*
     5. ⚡ *DAX & Formula Synthesis*
     6. 📊 *Rendering Suggested Dashboard Visual*
     7. 📑 *Compiling Executive PDF Report*
     8. ✅ *Validation & Complete*

4. **App Deliverables Hub**:
   - **DAX Tab**: Formatted measures with 1-click **Copy Measure**.
   - **Excel Tab**: Dynamic formulas with 1-click **Copy Formula**.
   - **MySQL Tab**: DDL & queries with 1-click **Copy SQL**.
   - **Python Tab**: Pandas/Matplotlib scripts with 1-click **Copy Script**.
   - **Data Model Tab**: Fact/Dimension tables and cardinality.
   - **Dashboard Tab**: High-resolution chart visual.
   - **PDF Report Action**: 1-tap **Download / Share Executive PDF Report**.

---

## 6. Testing via cURL / Postman (Direct API)

### A. Summary Preview (Fast Health Check):
```bash
curl -X POST "http://localhost:8000/api/v1/analyze/direct" \
  -F "file=@sample_sales.csv" \
  -F "prompt=Executive revenue and profitability analysis" \
  -F "mode=all" \
  -F "action=preview"
```

### B. Full Analysis with Multi-Stack Code & PDF:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze/direct" \
  -F "file=@sample_sales.csv" \
  -F "prompt=Executive revenue and profitability analysis" \
  -F "mode=all" \
  -F "action=full"
```

### C. Direct PDF Download:
```bash
curl -O -J "http://localhost:8000/api/v1/analyze/pdf/<RUN_ID>"
```

---

## 7. Troubleshooting & FAQ

- **Q: ReportLab import error on backend?**
  Run `pip install reportlab>=4.2` inside your active virtual environment.
- **Q: Android app cannot connect to backend?**
  If using Android emulator, use `http://10.0.2.2:8000`. If using a physical phone, ensure phone and PC are on the same Wi-Fi network and use your PC's IP address (e.g. `http://192.168.1.45:8000`), with Windows Firewall permitting incoming traffic on port 8000.
- **Q: How to run offline tests?**
  Run `pytest` in `backend/`:
  ```bash
  cd backend && pytest
  ```
