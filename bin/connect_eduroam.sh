#!/usr/bin/env bash
# connect_eduroam.sh — connect the Jetson to eduroam (WPA2-Enterprise / 802.1X).
#
# Run this ON THE JETSON:
#     bash ~/golf-cart-code/bin/connect_eduroam.sh
#
# It prompts for your eduroam identity + password. The password is read hidden
# (not echoed, not stored in shell history) and handed straight to
# NetworkManager, which stores it in the connection profile (root-readable, as
# usual for saved Wi-Fi). It does NOT print or upload your password.
#
# Defaults are FAU's usual eduroam settings (PEAP / MSCHAPv2). Override via env:
#     IFACE=wlP1p1s0  SSID=eduroam  EAP=peap  PHASE2=mschapv2  bash connect_eduroam.sh
#
# This only touches the Wi-Fi interface — your USB link to the workstation
# (192.168.55.1, used for SSH) is unaffected, so you can't lock yourself out.
set -euo pipefail

IFACE="${IFACE:-wlP1p1s0}"
SSID="${SSID:-eduroam}"
EAP="${EAP:-peap}"
PHASE2="${PHASE2:-mschapv2}"
CON="eduroam"

if ! command -v nmcli >/dev/null 2>&1; then
    echo "nmcli (NetworkManager) not found — cannot configure Wi-Fi this way." >&2
    exit 1
fi

echo "Interface: $IFACE   SSID: $SSID   EAP: $EAP/$PHASE2"
read -rp "eduroam identity (e.g. you@fau.edu): " IDENTITY
if [ -z "${IDENTITY}" ]; then echo "No identity given — aborting." >&2; exit 1; fi
read -rsp "eduroam password: " PASSWORD; echo
if [ -z "${PASSWORD}" ]; then echo "No password given — aborting." >&2; exit 1; fi

# Outer/anonymous identity for privacy (same realm as your identity).
REALM="${IDENTITY#*@}"
ANON="anonymous@${REALM:-fau.edu}"

echo "Configuring '$CON' ..."
sudo nmcli connection delete "$CON" >/dev/null 2>&1 || true
sudo nmcli connection add type wifi ifname "$IFACE" con-name "$CON" ssid "$SSID" >/dev/null

sudo nmcli connection modify "$CON" \
    wifi-sec.key-mgmt wpa-eap \
    802-1x.eap "$EAP" \
    802-1x.phase2-auth "$PHASE2" \
    802-1x.identity "$IDENTITY" \
    802-1x.anonymous-identity "$ANON" \
    802-1x.password "$PASSWORD" \
    connection.autoconnect yes \
    connection.autoconnect-priority 20

# No CA cert pinned -> connects without validating the RADIUS server cert. This
# "just works" on most campuses but is less secure (can't detect a spoofed AP).
# To pin FAU's CA later:  sudo nmcli connection modify eduroam 802-1x.ca-cert /path/to/fau-ca.pem
sudo nmcli connection modify "$CON" 802-1x.system-ca-certs no >/dev/null 2>&1 || true

unset PASSWORD   # drop it from this shell; NetworkManager now holds it

echo "Bringing up '$CON' (this may take ~10 s to authenticate) ..."
if ! sudo nmcli connection up "$CON"; then
    echo "⚠ Failed to associate/authenticate. Common fixes:"
    echo "   - wrong username/password, or identity should/shouldn't include @fau.edu"
    echo "   - FAU may use a different EAP: retry with  EAP=ttls PHASE2=pap  bash $0"
    exit 1
fi

echo "Testing real internet (captive-portal-proof) ..."
CODE=$(curl -sS -m 12 -o /dev/null -w "%{http_code}" \
       http://connectivitycheck.gstatic.com/generate_204 2>/dev/null || echo 000)
if [ "$CODE" = "204" ]; then
    echo "✅ eduroam connected — real internet works (generate_204 = 204)."
    echo "   IP: $(ip -4 -br addr show "$IFACE" | awk '{print $3}')"
else
    echo "⚠ Associated to eduroam, but internet check returned '$CODE'."
    echo "   Give it a few seconds and re-test:  curl -I http://connectivitycheck.gstatic.com/generate_204"
    echo "   If it stays non-204, credentials or EAP settings may be off."
fi
