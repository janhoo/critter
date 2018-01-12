#!/bin/bash

# Standardkodierung definieren (wichtig für das Lesen von Dateien)
export LANG=de_DE.UTF-8

# Definitionen
PY_MODULE="folium xlsxwriter psycopg2 PyQt5"

# Aufbereitungen
PY_MODULE_CSV=$(echo $PY_MODULE | tr " " ",")
INFO_INST_MANUELL="Installieren Sie zuerst Python3.x:\n· https://www.python.org/downloads\n\nInstallieren Sie dann in der Konsole folgendermaßen die benötigten Python-Module:\n· pip3 install $PY_MODULE"

# Teste Rueckgabewert
function check_prg(){
    eval "$*"
    if test $? -ne 0; then RETURN=false; else RETURN=true; fi
}

# Pfade holen, damit Python3 gefunden wird
source /etc/profile
source ~/.bash_profile

# Wechsle in Verzeichnis indem dieses Programm liegt
DIR="$(dirname "$0")"
cd $DIR

# Teste Abhaengigkeiten
check_prg 'python3 -c "import '$PY_MODULE_CSV'"'
if $RETURN; then
    # Ok: Starte Programm
    python3 ingest.py
    exit 0
fi

# Es fehlen Abhängigkeiten
RET=$(osascript -e 'display alert "Es fehlen einige Dinge" message "Wollen Sie die fehlenden Abhängigkeiten manuell installieren oder soll ein Installationsskript gestartet werden?" buttons {"Installationsskript starten","manuelle Installation"} default button 1')
echo $RET

# Manuelle Installation
if test "$RET" = "button returned:manuelle Installation"; then
    osascript -e 'display alert "Manuelle Installation" message "'"$INFO_INST_MANUELL"'"'
    exit
fi

# Installationsskript starten
open -a Terminal "install.sh"
