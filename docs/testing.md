# SpectrumSentry AI - Testing Guide

## Running Tests
Tests are executed using `pytest` inside the virtual environment:

```bash
./backend/.venv/bin/pytest backend/tests
```

## Test Suites
- `test_generator.py`: Verifies synthetic I/Q generation for BPSK, QPSK, 16-QAM.
- `test_noise.py`: Verifies AWGN channel modeling and SNR accuracy.
- `test_features.py`: Verifies moment and spectral feature extraction consistency.
- `test_classifier.py`: Verifies model training, inference, and accuracy thresholds.
- `test_monitoring.py`: Verifies packet telemetry, interruption, and recovery state tracking.
- `test_api.py`: Tests HTTP REST API endpoints and WebSocket channels.
