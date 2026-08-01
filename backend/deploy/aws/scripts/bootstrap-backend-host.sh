#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install --yes --no-install-recommends \
  build-essential \
  ca-certificates \
  curl \
  ffmpeg \
  git \
  libpq-dev \
  nginx \
  postgresql \
  postgresql-contrib \
  python3-dev \
  python3-venv \
  redis-server \
  rsync \
  unattended-upgrades

if ! id sunnekatha >/dev/null 2>&1; then
  useradd \
    --system \
    --create-home \
    --home-dir /srv/sunnekatha \
    --shell /bin/bash \
    sunnekatha
fi

install -d -m 0750 -o sunnekatha -g sunnekatha /srv/sunnekatha/app
install -d -m 0750 -o sunnekatha -g sunnekatha /var/log/sunnekatha
install -d -m 0750 -o root -g sunnekatha /etc/sunnekatha
install -d -m 0755 -o sunnekatha -g sunnekatha /var/www/sunnekatha/static

if ! swapon --show=NAME --noheadings | grep -qx "/swapfile"; then
  if [ ! -f /swapfile ]; then
    fallocate -l 1G /swapfile
    chmod 0600 /swapfile
    mkswap /swapfile
  fi
  install -m 0644 /tmp/swapfile.swap /etc/systemd/system/swapfile.swap
  systemctl daemon-reload
  systemctl enable --now swapfile.swap
fi

systemctl enable --now postgresql redis-server nginx unattended-upgrades

redis-cli ping
pg_isready
nginx -t
