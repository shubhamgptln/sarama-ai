"""
main.py

Entry point for the Python LlamaIndex chunker service.
Runs FastAPI server on port 8001 (separate from Go server on 8080).
"""

import uvicorn
import logging
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
import sys
sys.path.insert(0, str(project_root))

from chunker.adapter.api import app
from chunker.logging import set_log_level, get_logger

logger = get_logger(__name__)


def main():
    """Start the chunker service"""
    # Configuration
    host = os.getenv("CHUNKER_HOST", "0.0.0.0")
    port = int(os.getenv("CHUNKER_PORT", "8001"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").upper()

    # Set log level
    if log_level == "DEBUG":
        set_log_level(logging.DEBUG)
    else:
        set_log_level(logging.INFO)

    logger.info(
        "chunker_service_starting",
        host=host,
        port=port,
        debug=debug,
        log_level=log_level,
    )

    # Run FastAPI server
    uvicorn.run(
        "adapter.api:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level.lower(),
    )


if __name__ == "__main__":
    main()
