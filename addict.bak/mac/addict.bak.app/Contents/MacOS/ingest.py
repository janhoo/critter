#!/usr/local/bin/python3
# coding=utf-8

'''
TODOS

*** WF-Tweak für Nordseedaten

* Veränderungen an Datenmodell
- sediment
  - not nullable: description (obligates Triggerfeld, damit kein Datensatz verlorengeht)
- population
  - neu: org_name_opt
- autopsy
  - neu, not nullable: org_population_name_opt (obligates Triggerfeld, damit kein Datensatz verlorengeht)
  - neu: not nullabel: sample_id (fk sample.id)

* Veränderung an Nordseedaten, um eine stattgefundene Ingestierung abzubilden
  - in sediment:
    wo description und remark == null -> update "Keine Beschreibung"
  - in autopsy:
    wo autopsys.population_id == population.id -> setzte autopsy.org_population_name_opt = autopsy.population_id
    wo autopsys.population_id == population.id -> setze autopsy.sample_id = entsprechendes population.sample_id
  - in population:
    wenn irgendwo in autopsy autopsys.population_id == population.id -> setze entprechend population.org_name_opt = population.id

* Verändereungen am R-Skript zum Erzeugen der CSV-Nordseedaten
- ingest.csv: workflow und log (via R-Skript) hinzufuegen
  - So soll das CSV nachher aussehen:
    "id","name","created_on","description","workflow","log"
    1,"anonymous","2017-08-25 14:32:40","prime dataset","n","---"

'''

try:
    import argparse, sys, os, textwrap, getpass, configparser
    from PyQt5.QtWidgets import *
    from logik.workflow import Workflow
    from gui.controller import Controller
    from gui.model import Model
    from helper.printtools import SmartPrint
    from helper.dbtools import DbTools
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren")
    quit()

# Main
if __name__ == "__main__":

    # Model erzeugen
    m = Model()

    # CLI-Parser
        # Kurzinfo zum Programm
    sInfo = m.sInfoPrgName + " " + m.sInfoPrgVersion + " ("+m.sInfoDbSchemaVersion+")\n" \
            + m.sInfoKommentar.replace("<br>","\n").replace("<i>","").replace("</i>","") + "\n" \
            "Kontakt: " + m.sInfoWeb + "\n" + \
            m.sInfoDatum
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(sInfo),
        add_help=False)
    gruppeWF = parser.add_argument_group("Workflows fuer die Ingestion")
    gruppeWF.add_argument("-nds", metavar="<datei.csv>", help="Nordseedaten in DB einpflegen", type=str, nargs=1)
    gruppeWF.add_argument("-ark", metavar="<datei.csv>", help="Arktisdaten in DB einpflegen", type=str, nargs=1)

    gruppeTempl = parser.add_argument_group("Excel-Templates fuer die Ingestion")
    gruppeTempl.add_argument("-tnds", metavar="<datei.xlsx>", help="Template fuer Nordseedaten erzeugen", type=str, nargs='?', const="template_nordsee.xlsx")
    gruppeTempl.add_argument("-tark", metavar="<datei.xlsx>", help="Template fuer Arktisdaten erzeugen", type=str, nargs='?', const="template_arktis.xlsx")

    gruppeDB = parser.add_argument_group("Datenbank")
    gruppeDB.add_argument("-db", help="Datenbankverbindung anzeigen/konfigurieren", action="store_true")

    gruppeEtc = parser.add_argument_group("Sonstiges")
    gruppeEtc.add_argument("-gui", metavar="Stil", help="Start im GUI-Modus, alle anderen Parameter werden ignoriert. (Stilarten: "+",".join(QStyleFactory.keys())+")", type=str, nargs='?', const="_system_")
    gruppeEtc.add_argument("-i", help="zeigt genauere Informationen zum Programm",action="store_true")
    gruppeEtc.add_argument("-dry", help="schreibende DB Aktionen werden nur simuliert", action="store_true")
    gruppeEtc.add_argument("-log", metavar="<datei.log>", help="Logdatei angeben", type=str, nargs=1)

    gruppeEtc.add_argument("-v", help="geschwaetzigere Ausgabe", action="store_true")
    gruppeEtc.add_argument("-d", help="debuggingartige Ausgabe", action="store_true")
    gruppeEtc.add_argument("-vs", "--version", help="Version", action="store_true")
    gruppeEtc.add_argument("-h", "--help", help="zeigt diese Hilfe an", action="store_true")

    gruppeTesting = parser.add_argument_group("Testing")
    gruppeTesting.add_argument("--test", help="Test", action="store_true")

    # Parse CLI-Argumente
    try:
        args = parser.parse_args()
    except:
        print("Fehler bei der Parameteruebergabe... Abbruch")
        quit()

    # Werte CLI-Parameter aus (ohne Serververbindung)
    if len(sys.argv) <= 1:
        # Nichts übergeben -> GUI starten
        del m  # Sauberkeit: loesche das Model, welches hier im CLI-Modus benutzt wird
        Controller()
        quit()
    elif args.gui:
        # GUI
        del m # Sauberkeit: loesche das Model, welches hier im CLI-Modus benutzt wird
        sGuiStyle = args.gui
        if args.gui == "_system_":
            sGuiStyle = None
        Controller(sGuiStyle)
        quit()
    elif args.help:
        # Hilfe
        parser.print_help()
        quit()
    elif args.version:
        # Version
        print(m.sInfoPrgVersion+" ("+m.sInfoDbSchemaVersion+")")
        quit()

    # Veraenderungen (zur eingelesenen Konfigurationsdatei) am Model vornehmen (CLI-Parameter)
        # Geschwaetzigkeit
    m.setVerbosity(args.v, args.d)
        # Dry Run
    m.bDry = args.dry
        # Logging
    m.setLogging(False, "") # Std: Logging ausschalten
    if args.log is not None and args.log != "":
        if os.path.isfile(args.log[0]):
            print("Logdatei '" + args.log[0]+ "' existiert bereits.")
            ein = input("Soll wirklich in die Datei geschrieben werden [jN]? ")
            if ein != "" and ein.lower()[0] in ('y', 'j'):
                m.setLogging(True, args.log[0]) # Datei existiert bereits -> reinloggen
        else:
            m.setLogging(True, args.log[0]) # Datei neu erzeugen und reinlogen

    # Server-Config veraendern
    if args.db:
        print("* Einstellung der DB-Verbindung")
        print("Konfigurationsdatei: " + m.sConfigFilename)
        if m.db.sDbPw != "":
            print("Test der Serververbindung: ", end="")
            bOk = m.db.checkConnection()
            print("ok" if bOk == True else "")
        print("---")
        print("Host:   " + m.db.sDbHost)
        print("Port:   " + m.db.sDbPort)
        print("Name:   " + m.db.sDbName)
        print("Schema: " + m.db.getDbSchema())
        print("User:   " + m.db.sDbUser)
        if m.db.sDbPw == "":
            print("Pw:     <nicht gespeichert>")
        else:
            print("Pw:     <gespeichert>")
        print("---")
        ein = input("Sollen die Daten veraendert werden [jN]? ")
        if ein == "" or ein.lower()[0] not in ('y', 'j'):
            quit()
        print("* Veraenderung der DB-Verbindung")
        ein = input("Server (" + m.db.sDbHost + "): ")
        if ein != "": m.db.sDbHost = ein
        ein = input("Port (" + m.db.sDbPort + "): ")
        if ein != "": m.db.sDbPort = ein
        ein = input("DB-Name (" + m.db.sDbName + "): ")
        if ein != "": m.db.sDbName = ein
        ein = input("DB-Schema (" + m.db.getDbSchema() + "): ")
        if ein != "": # Check auf Alphanumerik
            if m.db.setDbSchema(ein) == False:
                quit()
        ein = input("User(" + m.db.sDbUser + "): ")
        if ein != "": m.db.sDbUser = ein
        if m.db.sDbPw == "":
            sPrompt = "Passwort (<nicht gespeichert>): "
        else:
            sPrompt = "Passwort (<gespeichert>): "
        m.db.sDbPw = getpass.getpass(prompt=sPrompt)
        m.cfgSave()
        quit()

    # Initialisiere Workflows (Serververbindung und Passwort)
    if m.db.sDbPw == "":
        m.db.sDbPw = getpass.getpass(prompt="Passwort: ") # Pw holen
    bOK = m.workflow.initialisierung()
    if bOK == False:
        quit()

    # Programmkonfiguration zeigen
    if args.i:
        print("* Informationen")
        m.info()
        m.workflow.info()

    # Werte CLI-Parameter aus (Serververbindung noetig)
    elif args.tnds != None:
        # Template Nordseedaten
        if os.path.isfile(args.tnds):
            print("Datei '" + args.tnds + "' existiert bereits.")
            ein = input("Soll die Datei ueberschrieben werden [jN]? ")
            if ein == "" or ein.lower()[0] not in ('y','j'):
                print("Abbruch...")
                quit()
        m.workflow.exportTemplate(args.tnds, "n")
    elif args.tark != None:
        # Template Arktisdaten
        if os.path.isfile(args.tark):
            print("Datei '" + args.tark + "' existiert bereits.")
            ein = input("Soll die Datei ueberschrieben werden [jN]? ")
            if ein == "" or ein.lower()[0] not in ('y','j'):
                print("Abbruch...")
                quit()
        m.workflow.exportTemplate(args.tark,"a")
    elif args.nds != None:
        # Workflow Nordsee
        if not os.path.isfile(args.nds[0]):
            print("Eingabedatei '"+args.nds[0]+"' existiert nicht... Abbruch")
            quit()
        m.workflow.ingestData(args.nds[0],"n")
    elif args.ark != None:
        # Workflow Arktis
        if not os.path.isfile(args.ark[0]):
            print("Eingabedatei '"+args.ark[0]+"' existiert nicht... Abbruch")
            quit()
        m.workflow.ingestData(args.ark[0],"a")
    elif args.test:
        m.workflow.test()
    else:
        # Nichts ausgewaehlt
        print("Nichts zu tun...")

