import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CERTIFICATES_DIR
from app.database import Base, engine
from app.routers.certificates import router as jobs_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
)

# create tables on first run (idempotent)
Base.metadata.create_all(bind=engine)

# make sure the output folder exists
CERTIFICATES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Bulk Certificate Generator",
    description=(
        "Submit a list of recipients and generate PDF certificates "
        "in the background.  Track progress and download results."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/", tags=["Health"])
def health_check():
    """Quick liveness probe."""
    return {"status": "healthy", "service": "Bulk Certificate Generator"}
