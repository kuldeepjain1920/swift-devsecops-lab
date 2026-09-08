import logging
from dotenv import load_dotenv

# Load .env BEFORE anything else imports os.environ values.
# This has to run first because routes.py reads SIGNING_KEY_PATH and
# AES_KEY the moment it's imported (not later, when a request comes in) —
# so if load_dotenv() ran after that import, those lookups would fail.
load_dotenv()

# Basic logging setup — timestamp + logger name + message. This is what
# makes the "routing:" and "audit:" prefixes show up cleanly in output,
# on top of the JSON lines audit.py already produces.
logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(name)s: %(message)s",
)

from fastapi import FastAPI
from src.api.routes import router

# This is the actual web application object — the thing uvicorn serves.
# FastAPI itself only defines app logic; it doesn't listen on a port —
# that's uvicorn's job (see the run command below).
app = FastAPI(title="SWIFT-Style Messaging API — Phase 1")

# Attaches the /messages POST and GET endpoints (defined in routes.py)
# to this app. Without this line, the app would run but have no routes.
app.include_router(router)


@app.get("/health")
def health():
    # Simple liveness check, separate from the payment message logic.
    # Useful once this is deployed to the GCP VM to confirm the
    # container is up before running the real smoke test (§16).
    return {"status": "ok"}


##After this run below command
# uvicorn        -> the actual web server program; FastAPI only defines
#                   app logic, uvicorn is what listens on a port and
#                   passes incoming HTTP requests to that app
# src.main:app   -> where to find the app object: inside src/main.py,
#                   use the variable named `app`
# --reload       -> auto-restarts the server on file changes; LOCAL DEV
#                   ONLY, this flag won't be used in the GCP VM deploy (§15)
#### uvicorn src.main:app --reload
