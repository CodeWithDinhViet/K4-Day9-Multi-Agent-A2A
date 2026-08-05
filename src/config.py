"""Project-wide paths and fixed runtime settings."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGGING_DIR = PROJECT_ROOT / "logging"

POLICY_VERSION = "EC_POLICY_V2"
CASE_COUNT = 50

# The final model name must be declared here rather than hidden in .env.
# This deterministic implementation does not call an LLM yet.
MODEL_NAME = "deterministic-python-rules"
MODEL_PARAMETER_SIZE = "not_applicable"

