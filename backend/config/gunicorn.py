"""Environment-driven Gunicorn configuration for production web containers."""

import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
worker_class = "sync"
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT_SECONDS", "60"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT_SECONDS", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE_SECONDS", "5"))
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "127.0.0.1")

accesslog = "-"
errorlog = "-"
capture_output = True
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '{"time":"%(t)s","remote":"%(h)s","method":"%(m)s","path":"%(U)s",'
    '"status":%(s)s,"bytes":%(b)s,"duration_us":%(D)s,'
    '"user_agent":"%(a)s"}'
)
