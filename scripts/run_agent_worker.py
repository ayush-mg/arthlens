"""
Durable Agent Worker Daemon.

Authoritative Specification: ArthLens Build Handbook Part 8.2-8.5, 9.1.
Runs independently of FastAPI BackgroundTasks, claiming pending agent runs with
PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED, executing them deterministically,
and recovering any stale or crashed runs across worker restarts.
"""

import argparse
import logging
import signal
import sys
import threading
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.arthlens.agent.worker import run_worker_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent_worker")


def main() -> int:
    parser = argparse.ArgumentParser(description="ArthLens Durable Agent Worker")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Poll interval in seconds when idle (default: 1.0)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one batch of pending runs and exit",
    )
    args = parser.parse_args()

    stop_event = threading.Event()

    def sig_handler(sig, frame):
        logger.info("Shutdown signal (%s) received, gracefully stopping worker...", sig)
        stop_event.set()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    logger.info("Starting ArthLens Durable Agent Worker (poll_interval=%.2fs)...", args.poll_interval)
    max_iter = 1 if args.once else None

    try:
        processed = run_worker_loop(
            poll_interval=args.poll_interval,
            stop_event=stop_event,
            max_iterations=max_iter,
        )
        logger.info("Worker stopped. Total runs processed in session: %d", processed)
        return 0
    except Exception as exc:
        logger.exception("Worker encountered a fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

