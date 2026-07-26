from __future__ import annotations

import logging
import sys


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s", "%H:%M:%S"))

    root = logging.getLogger("WAGE")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.propagate = False


logger = logging.getLogger("WAGE")
