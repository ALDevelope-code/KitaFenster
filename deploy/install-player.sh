#!/bin/bash
# Für ein dediziertes Gerät mit Raspberry Pi OS Lite (32-bit), Debian 13/Trixie.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "Bitte mit sudo bash deploy/install-player.sh ausführen."
  exit 1
fi
source /etc/os-release
if [[ ${VERSION_ID:-0} -lt 12 ]]; then
  echo "Raspberry Pi OS auf Basis von Debian 12 oder neuer erforderlich. Empfohlen: Trixie Lite 32-bit."
  exit 1
fi
task_source=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_target=/opt/kita-frame
for task_required in player/__main__.py shared/schedule.py deploy/kita-player-kms.service LICENSE NOTICE; do
  if [[ ! -f "$task_source/$task_required" ]]; then
    echo "Unvollständiger Projektordner: $task_required fehlt. Bitte das Release-ZIP vollständig entpacken."
    exit 1
  fi
done
export DEBIAN_FRONTEND=noninteractive
apt-get update
# KMSDRM loads EGL/GLES at runtime; pygame alone does not pull these in on Lite.
apt-get install -y --no-install-recommends python3 python3-pygame python3-gpiozero python3-lgpio \
  libdrm2 libgbm1 libegl1 libegl-mesa0 libgles2 libgl1-mesa-dri kbd fontconfig fonts-dejavu-core tzdata
if ! id frame >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash frame
fi
if ! getent group gpio >/dev/null; then
  groupadd --system gpio
fi
usermod -a -G video,render,audio,input,gpio frame
# Stop an existing player before replacing its program files.
if systemctl cat kita-player-kms.service >/dev/null 2>&1; then
  systemctl stop kita-player-kms.service
fi
# On affected 32-bit Pis, starting X11 can leave HDMI black until the next boot.
# Mask LightDM even on upgrades; merely stopping its session is insufficient.
if systemctl cat lightdm.service >/dev/null 2>&1; then
  systemctl stop lightdm.service
  systemctl disable lightdm.service
fi
systemctl mask lightdm.service
# Reserve VT1 for the player; login prompts remain available on the other VTs.
systemctl mask getty@tty1.service
install -d -m 755 "$task_target"
if [[ "$task_source" != "$task_target" ]]; then
  cp -a "$task_source/player" "$task_source/shared" "$task_source/deploy" "$task_target/"
  cp -a "$task_source/LICENSE" "$task_source/NOTICE" "$task_target/"
fi
# Remove only the obsolete start files belonging to this application.
rm -f -- "$task_target/deploy/kita-session.sh" "$task_target/deploy/kita-player.service" \
  "$task_target/deploy/kita-frame.desktop" /etc/systemd/user/kita-player.service \
  /usr/share/xsessions/kita-frame.desktop /etc/lightdm/lightdm.conf.d/50-kita-frame.conf
chown -R root:root "$task_target/player" "$task_target/shared" "$task_target/deploy"
# Samba uploads use private directory modes; frame must be able to read the installed code.
chmod -R a+rX "$task_target/player" "$task_target/shared" "$task_target/deploy"
install -d -o frame -g frame -m 700 /home/frame/.config/kita-frame
install -d -m 755 /etc/systemd/system
install -m 644 "$task_target/deploy/kita-player-kms.service" /etc/systemd/system/kita-player-kms.service
timedatectl set-timezone Europe/Berlin
timedatectl set-ntp true
systemctl daemon-reload
systemctl enable kita-player-kms.service
systemctl set-default multi-user.target
echo
echo "Installation abgeschlossen. Bei der ersten Einrichtung jetzt als frame koppeln:"
echo "sudo -u frame -H bash -c 'cd /opt/kita-frame && python3 -m player --pair http://NAS-IP:8088'"
echo "Eine vorhandene Kopplung und der Bildercache bleiben erhalten."
echo "Danach unbedingt: sudo reboot (der KMS/DRM-Player startet ohne LightDM)."
echo "Protokoll: sudo journalctl -b -u kita-player-kms.service --no-pager"
