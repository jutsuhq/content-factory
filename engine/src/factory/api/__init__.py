"""`factory serve`: the local HTTP API behind the desktop app, bound to 127.0.0.1 only.

app.py builds the FastAPI app (CORS, write guard, static files) and mounts one router per area from routes/;
handlers.py holds what queued jobs do. Add an endpoint to the router of its area; add a job kind to
handlers.HANDLERS."""

from factory.api.app import app, run

__all__ = ["app", "run"]
