#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
/usr/bin/python3 -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk' 2>/dev/null || {
  echo 'Instale Python 3, python3-gi e gir1.2-gtk-3.0 pelo gerenciador de pacotes.'
  exit 1
}
/usr/bin/python3 - "$ROOT" <<'PY'
import os,shutil,sys
from pathlib import Path
source=Path(sys.argv[1]);destination=Path.home()/'.local/share/clanm-control'
destination.mkdir(parents=True,exist_ok=True)
for name in ['app.py','iniciar.sh','permissoes.sh','clanm','vendor','udev','docs','README.md','LICENSE','THIRD_PARTY.md','icon.svg']:
 p=source/name
 if not p.exists():continue
 target=destination/name
 if p.resolve()==target.resolve():continue
 if p.is_dir():shutil.copytree(p,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 else:shutil.copy2(p,target)
applications=Path.home()/'.local/share/applications';applications.mkdir(parents=True,exist_ok=True)
def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')+'"'
(applications/'clanm-control.desktop').write_text('[Desktop Entry]\nType=Application\nName=Clanm Control\nComment=Controle do teclado e mouse Clanm no Linux\nExec='+quote(destination/'iniciar.sh')+'\nIcon='+str(destination/'icon.svg')+'\nTerminal=false\nCategories=Settings;HardwareSettings;\nStartupNotify=true\n')
print('Instalado. Procure Clanm Control no menu de aplicativos.')
print('No primeiro uso, clique em Liberar acesso USB se os dispositivos pedirem permissão.')
PY
if command -v update-desktop-database >/dev/null; then update-desktop-database "$HOME/.local/share/applications"; fi
