import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'certificates.db'}",
)

CERTIFICATES_DIR = BASE_DIR / "generated_certificates"

# how many threads the background worker uses for parallel PDF generation
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

# upper limit on recipients in a single request – avoids accidental mega-payloads
MAX_RECIPIENTS_PER_JOB = int(os.getenv("MAX_RECIPIENTS_PER_JOB", "500"))
