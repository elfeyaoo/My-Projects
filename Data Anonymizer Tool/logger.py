
# logger.py
import logging
from logging.handlers import RotatingFileHandler
import os

AUDIT_LOG = "audit.log"

def setup_logging():
    os.makedirs(os.path.dirname(AUDIT_LOG) or ".", exist_ok=True)
    handler = RotatingFileHandler(AUDIT_LOG, maxBytes=5*1024*1024, backupCount=2)
    fmt = "%(asctime)s - %(user)s - %(action)s - %(filename)s - %(extra)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger = logging.getLogger("audit")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

logger = setup_logging()

def log_action(user, action, filename, extra=""):
    """
    Log a user action to the audit log.
    Extra can include info like mode, percentage, and DP usage.
    """
    # ✅ Enrich message if DP info is included
    if "dp=True" in str(extra):
        extra = f"{extra} | Differential Privacy Applied"
    logger.info("", extra={"user": user, "action": action, "filename": filename, "extra": extra})


