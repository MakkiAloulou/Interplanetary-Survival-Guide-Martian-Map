"""python -m server: run the copilot server with the settings from the environment."""

import uvicorn

from server.config import Settings

if __name__ == "__main__":
    s = Settings.from_env()
    uvicorn.run("server.app:app", host=s.host, port=s.port, log_level="info")
