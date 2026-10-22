# SpectrumSentry AI - Installation & Setup Guide

## Requirements
- Python 3.12
- Node.js (v18+) & npm

## 1. Backend Setup
```bash
# From repository root
/opt/homebrew/bin/python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Frontend Setup
```bash
cd frontend
npm install
```

## 3. Running Development Servers
- Backend:
  ```bash
  source backend/.venv/bin/activate
  uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
  ```
- Frontend:
  ```bash
  cd frontend
  npm run dev
  ```
