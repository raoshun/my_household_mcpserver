#!/usr/bin/env bash
set -euo pipefail

# Install Japanese CJK fonts (Noto Sans CJK JP) across common Linux distros
# - Detects package manager (apt, dnf, yum, pacman, zypper, apk)
# - Installs appropriate Noto CJK font package
# - Updates font cache

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[!] Please run as root (use sudo) to install system fonts." >&2
  exit 1
fi

PM=""
if command -v apt-get >/dev/null 2>&1; then
  PM="apt"
elif command -v dnf >/dev/null 2>&1; then
  PM="dnf"
elif command -v yum >/dev/null 2>&1; then
  PM="yum"
elif command -v pacman >/dev/null 2>&1; then
  PM="pacman"
elif command -v zypper >/dev/null 2>&1; then
  PM="zypper"
elif command -v apk >/dev/null 2>&1; then
  PM="apk"
else
  echo "[!] Unsupported distro: couldn't find apt/dnf/yum/pacman/zypper/apk" >&2
  exit 2
fi

case "$PM" in
  apt)
    apt-get update
    apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra fonts-noto
    ;;
  dnf)
    dnf install -y google-noto-sans-cjk-ttc-fonts google-noto-sans-cjk-vf-fonts
    ;;
  yum)
    yum install -y google-noto-sans-cjk-ttc-fonts
    ;;
  pacman)
    pacman -Sy --noconfirm noto-fonts-cjk noto-fonts
    ;;
  zypper)
    zypper --non-interactive install noto-sans-cjk-fonts
    ;;
  apk)
    apk add --no-cache font-noto-cjk
    ;;
  *) ;;

esac

# Refresh font cache
if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f -v || true
fi

echo "[+] CJK fonts installed. If matplotlib still warns about glyphs, restart your app."
