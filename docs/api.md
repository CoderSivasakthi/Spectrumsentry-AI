# SpectrumSentry AI - API Reference

## Base URL
- Local: `http://127.0.0.1:8000`
- Interactive Swagger Docs: `http://127.0.0.1:8000/docs`
- Redoc: `http://127.0.0.1:8000/redoc`

## Phase 1 Endpoints
- `GET /`: Returns application name and status.
- `GET /health`: Returns service health status.

## Future Phase Endpoints
- Signal Generation & DSP (`/api/signals/*`)
- AI Classification & Novelty Detection (`/api/ai/*`)
- Communication Monitoring (`/api/monitoring/*`)
- Experiment History & Export (`/api/experiments/*`)
- Real-time Telemetry (`/ws/*`)
