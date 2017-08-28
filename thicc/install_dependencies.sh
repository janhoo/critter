#!/bin/bash
echo "*** Installation der Abhaengigkeiten fuer Ingest"
echo "* Installiere Paketmanager Hombrew"
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
echo "* Installiere Python3 (via Hombrew)"
brew install python3
echo "* Installiere Python-Pakete (via pip3)"
pip3 install pyqt5 xlsxwriter psycopg2 folium
echo "Fertig..."
