"""
logger.py - Centralized logging for ClamApp
Provides consistent logging across all modules with file output.
"""

import logging
import os
from datetime import datetime

# Get user's home directory for log file
HOME_DIR = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME_DIR, ".clamapp")
LOG_FILE = os.path.join(LOG_DIR, "clamapp.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
def setup_logging():
    """Setup centralized logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()  # Also output to console for debugging
        ]
    )

# Create logger for modules
def get_logger(name):
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)

# Initialize logging when module is imported
setup_logging()
