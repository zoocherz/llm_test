"""One backend-local env file, independent of the launch directory."""
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / '.env'
