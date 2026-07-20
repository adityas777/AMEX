# Amex Card Benefit Activation Engine

An automated claims processing platform that parses transaction feeds and trigger logs, applies smart rule configurations, predicts benefit categories using a local NLP Machine Learning classifier, and automatically drafts claims. It also features a real-time Gmail Ingestion pipeline allowing users to sync claims directly from unread purchase alerts and flight delay emails.

**Live Frontend Application URL:** [https://amex-frontend-service.onrender.com/](https://amex-frontend-service.onrender.com/)

**Video Explaination:** [https://www.youtube.com/watch?v=iusS8zFyRfg](https://www.youtube.com/watch?v=iusS8zFyRfg)

---

## 🌟 Key Features

### 1. Multi-Benefit Detection
* **Purchase Protection**: Automatically identifies cardholder purchases (like electronics or cameras) that are stolen or accidentally damaged within 90 days.
* **Return Protection**: Detects instances where a store refuses to accept a return within 90 days, enabling cardholders to claw back the purchase cost.
* **Travel Delay Insurance**: Scans for flight ticket purchases and linked delay events (exceeding 6 hours for Platinum, 12 hours for Gold) to automatically reimburse essential meal and lodging expenses.

### 2. Live Gmail Ingestion Path
* Integrates securely with the **Google Gmail API** using OAuth 2.0.
* Scans the authenticated inbox for purchase alerts and flight delay notifications.
* **Robust Parser**: Uses regex with line-break normalization and semantic heuristic fallbacks to parse amounts, merchants, dates, and flight details out of unstructured email bodies.
* **Self-Healing Sandbox Fallback**: If no credentials are provided or auth fails, it automatically enters a mock sandbox mode to ensure the demo is always fully functional.
* **Intelligent Deduplication**: Uses database-stored email message IDs to prevent duplicate ingestions.

### 3. Machine Learning (NLP) Underwriting Layer
* Utilizes a local **scikit-learn** model (TF-IDF Vectorization + Logistic Regression with `lbfgs` multiclass solver).
* Classifies purchase items and descriptions into target benefit categories (`purchase_protection`, `travel_delay`, `return_protection`, or `none`) with confidence scores.
* Acts as an underwriting safety net: if a transaction matches the hardcoded rules but the ML layer flags it as unrelated (low confidence), it is flagged for manual audit.

### 4. Interactive Dashboards
* **Cardholder Console**: A luxury-themed dark dashboard displaying card limits, progress rings for utilized benefits, stepper claims trackers, and upload slots for police reports or invoices. Exposes transparent "Why am I seeing this?" rule matching traces.
* **Admin Operations Portal**: Allows claims adjusters to inspect automated rules, view ML prediction scores, change claim states (Review, Approve, Pay, Deny), and process transactions.

---

## 📐 Architecture Overview

```
┌──────────────────┐      ┌─────────────────────────┐      ┌───────────────────────────┐
│  Test Gmail      │      │  Gmail Ingestion Poller │      │  Rules Engine + ML Layer  │
│  Inbox (Unread)  │ ───▶ │  (gmail_poller.py)      │ ───▶ │  - evaluate_rules()       │
└──────────────────┘      │  - Parse fields (regex) │      │  - Predict item class     │
                          │  - Deduplicate email ID │      └─────────────┬─────────────┘
                          └─────────────────────────┘                    │
                                                                         ▼
┌──────────────────┐      ┌─────────────────────────┐      ┌───────────────────────────┐
│  Vite React UI   │ ◀─── │  FastAPI Web Endpoints  │ ◀─── │  SQLite Database          │
│  (Vercel/Render) │      │  (main.py on port 8000) │      │  (amex_benefits.db)       │
└──────────────────┘      └─────────────────────────┘      └───────────────────────────┘
```

---

## 🚀 Setup & Local Execution

### Prerequisites
* Python 3.10+ (tested successfully on Python 3.14.0)
* Node.js 18+

### Quick Start with Docker Compose
To build and run the entire ecosystem (both frontend and backend) inside container networks:
```bash
docker-compose up --build
```
* **Frontend Dashboard**: `http://localhost:5173`
* **FastAPI Backend Swagger**: `http://localhost:8000/docs`

---

### Manual Installation (Local Development)

#### 1. Setup Backend
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI reload server:
   ```bash
   $env:PYTHONPATH="."
   python -m uvicorn backend.main:app --reload --port 8000
   ```

#### 2. Setup Frontend
1. Navigate to the `frontend` folder:
   ```bash
   cd ../frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```

---

## ⚙️ Testing the Gmail Feature

1. Open the dashboard at `http://localhost:5173`.
2. Click **Sync Alerts from Gmail** in the right sidebar.
3. **No Setup (Sandbox)**: If `backend/credentials.json` is missing, the app ingests mock unread alerts (an Apple Store purchase and a Lufthansa flight delay) to demonstrate claim auto-detection instantly.
4. **Real Inbox Setup**: 
   * Enable the Gmail API on Google Cloud Console.
   * Download the Desktop Client secrets, rename it to `credentials.json`, and place it in the `backend/` folder.
   * Send unread test emails to your inbox containing subjects like `"Amex Transaction Alert"` (with text like `made at Apple Store for $1199`) and `"Lufthansa Flight Status Update"` (with text like `Lufthansa Flight LH424 delayed by 8 hours`).
   * Click **Sync Alerts from Gmail** in the UI, complete the browser login consent screen, and watch your actual emails parse dynamically!

---

## 🧪 Running Automated Tests
The repository features comprehensive unit tests for evaluating policy limit caps, MCC constraints, travel delay hour limits, ML predictions, and email parsing regexes:
```bash
$env:PYTHONPATH="."
python -m pytest backend/test_engine.py
```
