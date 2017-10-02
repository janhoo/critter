#!/bin/bash

# Definitionen
PY_MODULE="folium xlsxwriter psycopg2 PyQt5"

# Aufbereitungen
PY_MODULE_CSV=$(echo $PY_MODULE | tr " " ",")

# Info
function info(){
clear
echo '      /\'
echo '     ( /   @ @    ()'
echo '      \\ __| |__  /'
echo '       \/   "   \/'
echo '      /-|       |-\'
echo '     / /-\     /-\ \'
echo '      / /-`---'-\ \'
echo '       /         \      critterdb'
echo '-----------------------------------'
echo 'Installationsskript'
echo '-----------------------------------'
}

# Dialog
function dialog_info() {
    osascript -e 'display alert "'"$1"'" message "'"$2"'"'
}

# Fehler
function fehler(){
    dialog_info "Automatische Installation fehlgeschlagen" "Bitte installieren Sie die nötigen Abhängigkeiten manuell."
    clear
    exit
}

# Teste Rueckgabewert
function check_prg(){
    eval "$*" 2> /dev/null 1> /dev/null
    if test $? -ne 0; then RETURN=false; else RETURN=true; fi
}

# Pfade holen, damit Python3 gefunden wird
source /etc/profile 2> /dev/null
source ~/.bash_profile2 2> /dev/null

# Wechsle in Verzeichnis indem dieses Programm liegt
DIR="$(dirname "$0")"
cd $DIR

# Teste Python
info
echo "* Teste Python3"
check_prg 'which python3'
if ! $RETURN; then
    echo "Python3 ist nicht installiert"
    RET=$(osascript -e 'display alert "Python3 ist nicht installiert" message "Es wird nun mit dem Paketmanager Brew installiert." buttons {"OK","Abbrechen"} default button 1')
    if test "$RET" = "button returned:Abbrechen"; then exit; fi
    # Teste Brew
    info
    echo "* Teste Brew"
    check_prg 'which brew'
    if ! $RETURN; then
        echo "Brew ist nicht installiert"
        RET=$(osascript -e 'display alert "Brew ist nicht installiert" message "Es wird nun der Paketmanager Brew installiert." buttons {"OK","Abbrechen"} default button 1')
        if test "$RET" = "button returned:Abbrechen"; then exit; fi
        # Installiere Brew
        info
        echo "* Installiere Brew"
        /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
        echo "* Test Brew"
        check_prg 'which brew'
        if ! $RETURN; then echo "Brew ist nicht installiert"; fehler; else echo "Brew ist installiert"; fi
        RET=$(osascript -e 'display alert "Paketmanager Brew ist installiert" message "Es wird nun Python3 und Pip3 mittels Brew installiert." buttons {"OK","Abbrechen"} default button 1')
        if test "$RET" = "button returned:Abbrechen"; then exit; fi
    fi
    # Installiere Python3 und Pip3
    info
    echo "* Installiere Python3 und Pip3 mit Brew"
    brew install python3
    # Teste ob Python3 installiert ist
    echo "* Teste Python3"
    check_prg 'which python3'
    if ! $RETURN; then echo "Python3 ist nicht installiert"; fehler; else echo "Python3 ist installiert"; fi
else
    echo "Python3 ist installiert"
fi

# Teste ob Pip3 installiert ist
echo "* Teste Pip3"
check_prg 'which pip3'
if ! $RETURN; then echo "Pip3 ist nicht installiert"; fehler; else echo "Pip3 ist installiert"; fi
RET=$(osascript -e 'display alert "Python3 und Pip3 sind installiert" message "Es werden nun die fehlenden Python-Module ermittelt und installiert." buttons {"OK","Abbrechen"} default button 1')
if test "$RET" = "button returned:Abbrechen"; then exit; fi

# Teste und installiere fehlende Python-Module
info
echo "* Installation der fehlenden Python-Module"
for PM in ${PY_MODULE[@]}
    do
        echo "- Test $PM"
        check_prg 'python3 -c "import '$PM'"'
        if ! $RETURN; then echo "$PM fehlt"; echo "Starte Installation ..."; pip3 install $PM; else echo "$PM ist installiert"; fi
    done
RET=$(osascript -e 'display alert "Alle Python3-Module sind installiert" message "Es werden nochmals alle Abhängigkeiten getestet." buttons {"OK","Abbrechen"} default button 1')
if test "$RET" = "button returned:Abbrechen"; then exit; fi

# Abschlusstest
info
echo "* Teste Abhaengigkeiten nochmals"
check_prg 'python3 -c "import '$PY_MODULE_CSV'"'
if $RETURN;
    then
        # Ok: Starte Programm
        echo "Alle Abhängigkeiten sind erfuellt"
	    dialog_info "Alles ist in Ordnung" "Alle Abhängigkeiten sind erfüllt. Das Hauptprogramm kann nun gestartet werden."
        clear
        exit
    else
        # Immer noch ein Problem -> Manuelle Installation
        echo "Es sind immer noch nicht alle Abhaengigkeiten erfuellt"
        fehler
        clear
        exit
fi

