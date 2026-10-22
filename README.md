# SpectrumSentry AI

> AI-Based Wireless Communication Monitoring, Signal Analysis, Modulation Classification, Experiment History, and Anomaly Detection Platform.

---

## Overview

SpectrumSentry AI combines Digital Signal Processing (DSP), synthetic I/Q complex signal generation, Machine Learning modulation classification, and communication metrics tracking into a completely local, portable, offline-first application.

### Key Highlights
- **100% Offline / Local Operation**: Uses SQLite and local file storage without external database server dependencies.
- **Synthetically Modeled I/Q Baseband**: Mathematically generated complex signals (BPSK, QPSK, 16-QAM) with AWGN channels—no SDR hardware required for v1, while architecturally ready for future SDR inputs.
- **AI-Powered Modulation Classification**: Scikit-Learn MLPClassifier trained on high-order moments and spectral features.
- **Defensive & Observational**: Rigorously designed for legitimate communication quality monitoring, anomaly observation, and research.

---

## Main Architecture

```
                    SpectrumSentry AI
                           |
                    React Dashboard
                           |
                      FastAPI API
                           |
       +-------------------+-------------------+
       |                   |                   |
Communication         Signal Processing      AI/ML
Monitor Engine            Engine             Engine
       |                   |                   |
       +-------------------+-------------------+
                           |
                     Decision Engine
                           |
                 +---------+---------+
                 |                   |
              SQLite             File Storage
                 |                   |
          Metadata/Results      I/Q / datasets
                 |                   |
                 +---------+---------+
                           |
                    Experiment History
```

---

## Technology Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy, aiosqlite, NumPy, SciPy, scikit-learn, joblib, WebSockets, HTTPX
- **Database**: SQLite (`storage/spectrumsentry.db`)
- **Signal Storage**: NumPy `.npy` files under `storage/experiments/`
- **Frontend**: React 18/19, TypeScript, Vite, Tailwind CSS, Axios, Plotly.js, react-plotly.js

---

## Quickstart (Development)

### 1. Backend Setup
```bash
# Set up Python 3.12 virtual environment
/opt/homebrew/bin/python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run FastAPI backend
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Verification
- Backend API: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/health`
- Frontend Dashboard: `http://localhost:5173`
