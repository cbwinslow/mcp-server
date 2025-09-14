#!/usr/bin/env bash
# Dry-run cleanup script for desktops and old kernels.
# Run with --apply to actually remove packages. Default is --dry-run.

set -euo pipefail

DRY_RUN=1
if [[ ${1:-} == "--apply" ]]; then
  DRY_RUN=0
fi

echo "Dry-run: ${DRY_RUN}" >&2

# Candidate desktop packages to remove
DESKTOPS=(openbox i3 budgie-desktop plasma-desktop kde-plasma-desktop xfce4)

echo "Checking installed desktop packages..."
for d in "${DESKTOPS[@]}"; do
  if dpkg -l | grep -qi "$d"; then
    echo "Found installed desktop package: $d"
    if [[ $DRY_RUN -eq 0 ]]; then
      sudo apt-get remove --purge -y "$d" || true
    fi
  fi
done

# Clean old kernels (keep 3 most recent)
echo "Listing kernels..."
KERNELS=$(dpkg -l 'linux-image-*' | awk '/^ii/ { print $2 }' | sort -V)
KEEP=3
TO_REMOVE=$(echo "$KERNELS" | tail -n +$((KEEP+1)))
if [[ -n "$TO_REMOVE" ]]; then
  echo "Kernels to remove:"
  echo "$TO_REMOVE"
  if [[ $DRY_RUN -eq 0 ]]; then
    sudo apt-get remove --purge -y $TO_REMOVE || true
    sudo update-grub || true
  fi
else
  echo "No old kernels found to remove."
fi

echo "Autoremove unused packages (dry-run)"
if [[ $DRY_RUN -eq 0 ]]; then
  sudo apt-get autoremove --purge -y
else
  apt-get -s autoremove
fi

echo "Cleanup script finished. Run with --apply to actually remove packages."
