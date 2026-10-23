"""Convenience script to start the SpectrumSentry AI FastAPI server."""

import uvicorn

from _bootstrap import force_utf8_stdio
force_utf8_stdio()

from backend.app.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    print(f"Starting {settings.APP_NAME} on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
