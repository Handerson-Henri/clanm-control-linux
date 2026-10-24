#!/bin/sh
set -eu
# Executado como administrador apenas para instalar regras estáticas de acesso.
[ "$(id -u)" -eq 0 ] || { echo 'Execute pelo botão Liberar acesso USB do aplicativo.'; exit 1; }
cat > /etc/udev/rules.d/70-clanm-control.rules <<'EOF'
# Identifica o teclado primeiro; depois seleciona somente a interface RGB.
ACTION!="remove", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="320f", ATTRS{idProduct}=="5078", ENV{CLANM_KEYBOARD}="1"
ACTION!="remove", SUBSYSTEM=="hidraw", ENV{CLANM_KEYBOARD}=="1", ATTRS{bInterfaceNumber}=="01", TAG+="uaccess"
# Mouse: protocolo de configuração na interface USB 2.
ACTION!="remove", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="04d9", ATTR{idProduct}=="a09f", TAG+="uaccess"
EOF
chmod 0644 /etc/udev/rules.d/70-clanm-control.rules
udevadm control --reload-rules
udevadm trigger --action=add --subsystem-match=hidraw
udevadm trigger --action=add --subsystem-match=usb --attr-match=idVendor=04d9 --attr-match=idProduct=a09f
udevadm settle
