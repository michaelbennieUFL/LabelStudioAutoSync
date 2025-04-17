# ---------- base image --------------------------------------------------------
FROM python:3.11-slim

# ---------- OS packages -------------------------------------------------------
#  - cron   : the daemon we schedule into
#  - tzdata : so cron knows local time (set TZ=UTC, or inject your own)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        cron tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- python dependencies ----------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8 \
    TERM=xterm-256color       # blessed wants color terminfo

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- project code ------------------------------------------------------
COPY . .

# ---------- non‑root user (optional but recommended) --------------------------
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# ---------- entrypoint --------------------------------------------------------
# 1. start cron in the background
# 2. exec the command given by `docker run … <cmd>`
ENTRYPOINT ["/bin/sh", "-c", "crond && exec \"$@\""]
CMD ["python", "sync.py"]
