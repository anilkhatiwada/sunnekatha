"""Role-aware container health check.

Web processes exercise Django liveness. Other process roles are healthy while
their PID 1 command is running; the container runtime detects its exit directly.
"""

import sys
from pathlib import Path
from urllib.request import urlopen

role_file = Path("/tmp/sunnekatha-process-role")
role = role_file.read_text().strip() if role_file.exists() else "web"

if role != "web":
    raise SystemExit(0)

try:
    with urlopen("http://127.0.0.1:8000/api/v1/health/", timeout=3) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected health status: {response.status}")
except Exception as exc:
    print(f"Web health check failed: {exc}", file=sys.stderr)
    raise SystemExit(1) from None
