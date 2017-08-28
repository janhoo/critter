#!/bin/bash
IFS=$' '

# Variablen

DATA=$PWD/.. # $PWD = aktuelles Arbeitsverzeichnis (Tweak /..)
DBUSER=critter-adm
DBUSERRO=critter-user
DBSCHEMA=""
DBSCHEMATEMPL=edna
TABELLEN="gear status ship lifestage positioningsystem person sieve ingest scope taxon crs dataset cruise station sample population autopsy sediment sieveanalysis" # Reihenfolge beachten 
DBNAME=critter
DBHOST=postgres4.awi.de
DBPORT=5432

DO_INGEST=false # Aktion Ingest

# --- Funktionen

# Synopsis
synopsis(){
	echo "SYNOPSIS: buildcritter [OPTIONEN] SCHEMA"
	echo "Argumente:"
	echo "   SCHEMA      Name es zu erzeugenden Schemas in der Datenbank (obligat)"
	echo "Optionen:"
	echo "   -i          Zusaetzliches Ingest von Csv-Daten in Schema"
	exit 1
}

# Argumente auswerten
check_args(){

	# Hole optionale Argumente
	while getopts "i" opt; do
	  	case $opt in
		i)
			DO_INGEST=true
			;;
	   \?)
	   	echo "Invalid option: -$OPTARG" >&2
		   synopsis
		   exit 1
		   ;;
		:)
	      echo "Option -$OPTARG requires an argument." >&2
	      synopsis
	      exit 1
	      ;;
		*)
			synopsis
			exit 1
			;;
	  	esac
	done

	# Hole positionale Argumente
	DBSCHEMA=${@:$OPTIND:1} # Positional Argument 1

	# Tests
	if test -z $DBSCHEMA; then synopsis; fi # kein Schema

}

# DB-Passwort holen
get_pw(){
	echo "* Hole Passwort fuer weitere DB-Aktionen"
	# Hier wird das PG-Passwort in der Umgebungsvariablen gespeichert und an Subshells exportiert
	# Es ist also keine .pgpasswd noetig
	read -s -p "Password fuer Postgres-User \"$DBUSER\": " PGPASSWORD; export PGPASSWORD
	DBLOGIN="-d $DBNAME -U "$DBUSER" -h $DBHOST -p $DBPORT " # Loginstring
	echo
}

# Sicherheitsabfrage
really(){
	echo
	echo '      /\'
	echo '     ( /   @ @    ()'
	echo '      \\ __| |__  /'
	echo '       \/   "   \/'
	echo '      /-|       |-\'
	echo '     / /-\     /-\ \'
	echo '      / /-`---'-\ \'
	echo '       /         \      critterdb'
	echo
	echo "* Critter Build-Skript"
	echo
	echo "Folgendes Schema mit Tabellen wird erzeugt."
	if $DO_INGEST; then echo "Es wird ein zusaetzliches Ingest in Tabellen durchgefuehrt."; fi
	echo
	echo "DB-Name:         $DBNAME "
	echo "DB-Schema-Tmpl:  $DBSCHEMATEMPL"
	echo "DB-Schema:       $DBSCHEMA"
	echo "Host:            $DBHOST"
	echo "Port:            $DBPORT"
	echo "User:            $DBUSER"
	echo "User(RO):        $DBUSERRO"
	if $DO_INGEST;
		then
			echo -ne "Ingest-Tabellen: "
			for T in ${TABELLEN[@]}; do echo -ne "$T\n                 "; done
	fi
	echo
	echo "Achtung: Vorhandene Daten werden ohne Rueckfragen geloescht!"
	echo
	read -p "Wirklich Fortfahren[jN]? " ANTWORT
	case $ANTWORT in
		[jJyY]) REALLY="YES";;
		*) echo "Abbruch..."; exit;;
	esac
}

# Loesche alte Schemata
del_old_schemata(){
	echo "* Loesche alte Schemata (mit Tabellen) aus DB"
	echo "- Loesche Schema: $DBSCHEMATEMPL"
	psql $DBLOGIN -qc "DROP SCHEMA IF EXISTS $DBSCHEMATEMPL CASCADE;"
	echo "- Loesche Schema: $DBSCHEMA"
	psql $DBLOGIN -qc "DROP SCHEMA IF EXISTS $DBSCHEMA CASCADE;"
}

# Erzeuge Schema (Vorlage)
create_schema_templ(){
	echo "* Erzeuge Schema-Vorlage"
	echo "Schema: $DBSCHEMATEMPL"
	echo "- Durchlaufe Praeambel-Datei"
	echo "Datei: $DATA/scripte/preamble.sql"
	cat $DATA/scripte/preamble.sql | psql $DBLOGIN -q
	echo "- Durchlaufe Schema-Datei"
	echo "Datei: $DATA/scripte/db.ddl.sql"
	cat $DATA/scripte/db.ddl.sql | psql $DBLOGIN -q
}

# Rename Schema
rename_schema(){
	echo "* Benenne Schema um"
	echo "Schemaname (Vorlage): $DBSCHEMATEMPL"
	echo "Schemaname neu:       $DBSCHEMA"
	psql $DBLOGIN -qc "ALTER SCHEMA $DBSCHEMATEMPL RENAME TO $DBSCHEMA;"
	}

# Fuelle alle Tabellen mit Automapping der Spaltennamen
ingest_csv(){
	echo "* Fuelle Tabellen mit Daten der csv-Dateien"
	echo "Pfad: $DATA/csv"
	for TABELLE in ${TABELLEN[@]}; do
		echo -ne "$DBSCHEMA.$TABELLE ($TABELLE.csv): "
		COL_CSV=$(head -1 $DATA/csv/$TABELLE.csv | tr -d \" | tr -s " " | sed 's/^ *//g' | sed 's/ *$//g') # Ueberschriften der aktuellen csv-Datei -> String (Automapping: DB weiss somit welche Spalte wie heisst und ordnet sie dem entprechenden Tabellen-Attribut)
		cat $DATA/csv//$TABELLE.csv | psql $DBLOGIN -c "COPY $DBSCHEMA.$TABELLE($COL_CSV) FROM STDIN CSV HEADER;" # Muss per cat funktionieren, damit der Benutzer nicht Superuser sein muss
	done
}

# Stelle alle Autoinkrementzeiger korrekt ein
set_all_autoinc_pointers(){
	echo "* Stelle alle Autoinkrementzeiger korrekt ein"
		for TABELLE in ${TABELLEN[@]}; do
			set_autoinc_pointer $TABELLE id
		done
}

# Setze Autoinkrementzeiger auf Maximum (Parameter: Tabellenname, Spaltenname Integer Autoinkrement)
set_autoinc_pointer(){
	echo -en "$DBSCHEMA.$1.$2: "
	psql $DBLOGIN -Atc "SELECT setval('$DBSCHEMA.$1_$2_SEQ',(select max($2) from $DBSCHEMA.$1));"
}

# Setze Rechte
set_readonly_rights_to_normaluser(){
	echo "* Gib Standarduser Leserechte"
	echo "- Standarduser: $DBUSERRO"
	echo "- Nutzungesrechte fuer Schema: $DBSCHEMA"
	psql $DBLOGIN -Atc "GRANT USAGE ON SCHEMA $DBSCHEMA to \"$DBUSERRO\"";
	echo "- Leserechte fuer alle Tabellen in Schema: $DBSCHEMA"
	psql $DBLOGIN -Atc "GRANT SELECT ON ALL TABLES IN SCHEMA $DBSCHEMA to \"$DBUSERRO\"";
}

# --- Hauptprogramm (hier startet das Programm)

check_args "$@"
really
get_pw

del_old_schemata
create_schema_templ
rename_schema

if $DO_INGEST; then
	ingest_csv
	set_all_autoinc_pointers
fi

set_readonly_rights_to_normaluser

echo "Fertig."
