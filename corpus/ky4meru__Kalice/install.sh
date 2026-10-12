#!/bin/sh

set -eu

DEBIAN_FRONTEND=noninteractive
REPO_URL="${KALICE_REPO:-https://github.com/ky4meru/Kalice.git}"
REPO_DIR="${KALICE_DIR:-${HOME}/.kalice}"

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

if [ "$(id -u)" -eq 0 ]; then
    die "Do not run as root. Use another sudoer."
fi

command -v apt-get >/dev/null 2>&1 || die "Command apt-get not found. Kalice targets Kali Linux only."

sudo apt-get update -y
sudo apt-get install -y ansible git

if [ -d "${REPO_DIR}/.git" ]; then
    git -C "${REPO_DIR}" pull --ff-only \
        || die "Cannot fast-forward ${REPO_DIR}. Resolve its state or remove it."
else
    git clone "${REPO_URL}" "${REPO_DIR}"
fi

cd "${REPO_DIR}"
ansible-galaxy collection install -r requirements.yml
ANSIBLE_CONFIG="${REPO_DIR}/ansible.cfg" ansible-playbook main.yml --ask-become-pass

if [ -r /dev/tty ]; then
    printf '[*] Reboot now? [y/N] '
    read -r reply < /dev/tty || reply=""
    case "${reply}" in
        [yY] | [yY][eE][sS])
            sudo reboot
            ;;
        *)
            ;;
    esac
fi
