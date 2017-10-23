# coding=utf-8

try:
    import os, sys, csv, psycopg2, xlsxwriter, getpass, platform, datetime, time
    from difflib import SequenceMatcher
    from collections import Counter, OrderedDict
    from helper.printtools import SmartPrint
    from helper.dbtools import DbTools
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren")
    
"""
-----------------------------------------------------------------------
Workflows (Zugriff RW auf Model)
-----------------------------------------------------------------------

*** Info zu Workflow

ALGORITHMUS

- Lookup/Ingest-Daten
  - Lookup-Tabellen sind 1-n Beziehungen bei denen Datensatz beim Ingest bereits existiert
  - Ingest-Tabellen sind 1-n Beziehungen bei denen der entsprechende Datensatz beim Ingest erzeugt wird
- Workflow ist CSV-Zentriert
- Eine CSV-Zeile wird von links nach rechts durchlaufgen
- Es gibt drei Zeilenarten
  - Die originale/externe CSV-Zeile
  - die interne CSV-Zeile, die aus der originalen zusammengebaut wird
  - die interne alte CSV-Zeile
- ReUse
  - wenn deaktiviert, wird ab dem entspechendem Index der Inhalt der internen CSV-Spalte durch den Inhalt der externen ersetzt
  - wenn aktiviert werden alle Inhalte der Internen Zeile weiterbenutzt
  - Im Blattbereich ist ReUse immer deaktiviert
- Ein Trigger ist ein CSV-Header welcher den Beginn eines neuen Datensatzes definiert
- Ein Trigger repräsentiert einen Datensatz 
  - In bezug auf Einmaligkeit (Uniq)
  - In Bezug auf Veränderung zu Vorzeile (ReUse)
- Zwischen zwei Triggern befinden sich die Daten für einen Datensatz (Eintrag in eine Tabelle)
- Ist Trigger gedrückt wird ein neuer Eintrag erzeugt (Rueckgabewert = Id)
- Rueckgabewerte
  - Rueckgabewerte können in folgenden Datensätzen erzeugt werden
  - Sie werden erst beim Erzeugen eines neuen Datensatzes erneuert
- Ist Trigger gedrückt wird ReUse für die restliche Zeile deaktiviert
- Ein Trigger gilt als gedrückt wenn ...
  - Triggerfeldinhalt der ext. CSV leer ist
  - Triggerfeldinhalt der ext. CSV dem Inhalt der alten int. CSV gleicht
    (Grund: Zeilen dürfen doppelt in der ext CSV stehen, es wird aber kein neuer Datensatz erzeugt sondern ReUse benutzt)
  - Evtl. Problem: Dinge nach gleichem Trigger werden nicht beachtet (ist aber auch nicht sehr sinnvoll -> nur Warnung auf evtl Tippfehler)
- Ist ein Trigger gedrückt 
  - ist ein ReUse danach für alle Datensätze daktiviert
  - wird der Sichbarkeitsbereich aller Trigger rechts davon zurückgesetzt
- Sichtbarkeitesbereich und Einmaligkeit
  - Die Triggerfeldinhalte sind bezüglich ihres Sichtbarkeitsbereiches (links hat Priorität vor rechts) einmalig
  - Im Blattbereich liegen alle Triggerwerte im Sichtbarkeitsbereich des letzten Triggers im Astbereich
- Kardinalitäten
  - Es können nur 1-n Beziehungen automtisiert abgebildet werden
- Baumstruktur
  - Ast
    - (Ingest)Datensatz auf den andere (Ingest)Datensätze zeigen
    - links
    - Datensätze: Cruise,Station,Sample
    - Betrachtet als Gruppe: Beinhalten eher Metadaten
  - Blatt
    - (Ingest)Datensatz auf den keine weiteren (Ingest)Datensätze mehr zeigen
    - rechts
    - Datensätze: Population,Sieveanalysis,Sediment
    - Alle Haben alle eine Gemeinsamkeit: sie Zeigen alle auf Sample 
    - Betrachtet als Gruppe: Beinhalten die eigentlichen Messdaten
  - Baum ist ausgeglichen 
    - von Wurzel zu jedem Blatt sind die Entfernungen immer gleich
- Tag-Link System
  - Das Tag-Link System wird zum benutzt um Blatt-Datensätze untereinander in einem Sample zu verknüpfe
  - Es spiegelt die Verbindung von Blatt-Datensätze in der CSV-Welt wider
  - Tag
    - Der Inhalt eines Tag-Feldes wird normal in einer Tabelle/Attribut gespeichert
    - Weiterhin werden Rückgabewerte von Triggern anhand des Zell-Inhaltes dieses Tag-Feldes gemerkt
    - Der Sichbarkeitsbereich verhält sich analog den Uniq-Feldern
  - Link
    - Der Inhalt eines Link-Feldes wird normal in einer Tabelle/Attribut gespeichert
    - Weiterhin wird der Inhalt des Feldes benutzt um die ID eines Rückgabewertes eines durch Tag gekennzeichneten Triggers ermittelt
    - Diese ID wird dann in einer angegeben Tabelle/Attribut gespeichert 
    - Der Sichbarkeitsbereich verhält sich analog den Uniq-Feldern
- Untermengen des Workflows
  - Durch das Workflowfeld werden einzelne Felder unterschiedlichen Workflows zugeordnet werden
  - Somit können eingeschränkte Sichten auf das gesamte Workflowmodell begildet werden

WORKFLOW-DEFINITIONSDATEI

- Spaltenbreiche: 
  Header(1): Csv-Name (1) 
  Ziel(2): Eintrag von (1) in Zieltabelle/Attribut eintragen
  Lookup(3): Vor Eintrag von (1) den Wert auflösen via Lookup-Tabelle
  Tag(1): In diesem Header-Feld steht der Bezeichner für den sich der Rückgabewert des aktuellen Triggers gemerkt wird
  Link(3): Der Inhalt dieses Headerfeldes wird benutzt um den Rückgabewert von Link.TriggerHead zu bestimmen, dieser wird dann in Tabelle Link.Tab,Link.Attrib eingetragen
  Trigger(1): ja/nein
  Workflow(1): In diesem Feld wird das Workflowkuerzel angegeben
- Csv-Typen: 
  Name (normal)
  --Name (nicht einlesen, sondern vorherigen Wert neu benutzen)
  __Name (nicht einlesen, sondern letzten Rückgabewert eines Triggers benutzen)

"""

class Workflow:

    # Konstruktor
    def __init__(self, model):

        # Instanzvariablen
            # Model
        self.__model = model
            # SpartPrint
        self.__smartprint = SmartPrint(model = model)
            # Ist Workflowmodel funktionsfaehig
        self.__bReady = None
            # Liste Csv Header
        self.__dic_lstCsvHeader = None
            # Wf/Csv-Header -> Tabelle/Attribut
        self.__dic_dicCsv2Table = None
            # Wf/Csv-Header-> LookUpTable (Name -> Id)
        self.__dicCsv2Lookup = None
            # Csv-Header-> LookUpTable Reverse (~Original) (Id -> Name)
        self.__dicCsv2LookupReverse = None
            # Csv-Header -> Pop-Up-Help
        self.__dicCsv2Popup = None
            # Csv-Header -> Obligat
        self.__dicCsv2Obligat = None
            # Wf/Csv-Header -> Trigger
        self.__dic_dicCsv2Trigger = None
            # Trigger -> Trigger-Daten
        self.__dic_odicTrig2Dat = None
            # Csv-Header -> Tag
        self.__dicCsv2Tag = None
            # Csv-Header -> Link-Informationen
        self.__dicCsv2Link = None
            # Name des Blatt-Trigger
        self.__sTriggerLetzterAst = None
            # Workflow kuerzel
        self.__odicWfNamen = {"a":"Arktis","n":"Nordsee"}
            # Workflowmodell
        self.bOkWorkflowModell = False # Ist das Model Ok
        self.__lstWorkflowModell = self.createWorkflowModell("gesamt_abgespeckt.wf") # Erzeugen
            # Erzeuge Liste aller Lookup-Tabellen aus Workflowmodell
        self.__lstLookupTables = self.__buildListOfLookupTables() # Erzeugen

        # --------------------------------------------------------------------
        # Spezialisierung
        self.__dicSpezialTaxonAid2Name = None # Taxon: Aid -> Taxon
        self.__dicSpezialGearName2Area = None # Gear: Name -> Area
        # --------------------------------------------------------------------

    # Erzeuge Workflowmodell
    def createWorkflowModell(self, sDatei):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        sDateiWf = os.path.dirname(os.path.realpath(__file__))+"/"+sDatei

        pd("* Erzeuge Workflowmodel")
        pd("Datei: "+sDateiWf)
        lstWfm = list() # Aufbau: In(Csv,Return), DB-Eintrag(Tabelle,Attr), LookUp(Tabelle,Attr-Name,Attr-Id), Tag, Link(TriggerHead,Tab,Attrib), Trigger, LetzterAstTrigger, Workflow(Liste)

        try:
            # Einlesen der CSV-Datei
            with open(sDateiWf, newline='') as csvfile:
                csvReader = csv.reader(csvfile, delimiter=',', quotechar='"')
                # Zeilen
                for lstZeile in csvReader:
                    # Nicht leer und kein Kommentar
                    if len(lstZeile) != 0 and not lstZeile[0].startswith("#"):
                        # Check: SQL-Sicherheit
                        for spalte in lstZeile:
                            if spalte != "" and self.__model.db.isSqlUnsafe(spalte):
                                raise NameError("Unsicherer Eintrag in WF-Model: "+str(spalte))
                        # Hole Strings
                        sCsvName = lstZeile[0]
                        sDbTab = lstZeile[1]
                        sDbAttr = lstZeile[2]
                        sLookUpTab = lstZeile[3]
                        sLookUpAttr = lstZeile[4]
                        sLookUpId = lstZeile[5]
                        sTag = lstZeile[6]
                        sLinkTrigg = lstZeile[7]
                        sLinkTab = lstZeile[8]
                        sLinkAttr = lstZeile[9]
                        sTrigger = lstZeile[10]
                        sLetzterAstTrigger = lstZeile[11]
                        sWf = lstZeile[12]

                        # Bilde Einheiten
                            # Zieleintrag in DB
                        lstDbEintrag = (sDbTab,sDbAttr)
                            # Lookup
                        lstLookUp = None
                        if sLookUpTab != "" and sLookUpAttr != "" and sLookUpId != "":
                            lstLookUp = (sLookUpTab,sLookUpAttr,sLookUpId)
                            # Link
                        lstLink = None
                        if sLinkTrigg != "" and sLinkTab != "" and sLinkAttr != "":
                            lstLink = (sLinkTrigg, sLinkTab, sLinkAttr)
                            # Trigger
                        if sTrigger.lower() in ("true", "ja", "yes", "j", "y"):
                            bTrigger = True
                        else:
                            bTrigger = False
                            # Letzer Ast
                        if sLetzterAstTrigger.lower() in ("true", "ja", "yes", "j", "y"):
                            bAst = True
                        else:
                            bAst = False
                            # Tag
                        if sTag.lower() in ("true", "ja", "yes", "j", "y"):
                            bTag = True
                        else:
                            bTag = False
                            # Wf-Kuerzel
                        lstWf = []
                        for bs in sWf:
                            if bs not in self.__odicWfNamen:
                                raise NameError("Unbekanntes Workflowkuerzel in WF-Model: " + str(spalte))
                            lstWf.append(bs)
                        lstWfm.append((sCsvName,lstDbEintrag,lstLookUp,bTrigger,bTag,lstLink,bAst,lstWf))

        except Exception as ex:
            pn("Fehler beim Aufbau des Workflowmodells: "+str(ex))
            self.bOkWorkflowModell = False
            return None

        pd("ok")
        self.bOkWorkflowModell = True
        return lstWfm

    # Initialisiere Workflow
    def initialisierung(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        pv("* Initialisiere Workflow")
        sInfo = "Verbinde mit Server...\n"
        iMax = 13
        pnProgress(1, iMax, iMax, guiText=sInfo + "überprüfe Verbindung", abs=False, cli=False)
        bOkConnection = self.__model.db.checkConnection()
        pnProgress(2, iMax, iMax, guiText=sInfo + "überprüfe Header", abs=False, cli=False)
        bOkCsv = self.__buildCsvHeader()
        pnProgress(3, iMax, iMax, guiText=sInfo + "hole Tabellen", abs=False, cli=False)
        bOkTable = self.__buildCsv2Table()
        pnProgress(4, iMax, iMax, text=sInfo + "erzeuge Lookup-Tabellen", abs=False, cli=False)
        bOkLookup = self.__buildCsv2Lookup()
        pnProgress(5, iMax, iMax, guiText=sInfo + "hole Popuphilfen", abs=False, cli=False)
        bOkPopup = self.__buildCsv2Popup()
        pnProgress(6, iMax, iMax, guiText=sInfo + "lade Obligatinfos", abs=False, cli=False)
        bOkObligate = self.__buildCvs2Obligat()
        pnProgress(7, iMax, iMax, guiText=sInfo + "bestimme Trigger", abs=False, cli=False)
        bOkTrigger = self.__buildCvs2Trigger()
        pnProgress(8, iMax, iMax, guiText=sInfo + "bestimme Letzten Ast", abs=False, cli=False)
        bOkAst = self.__buildLetzerAst()
        pnProgress(9, iMax, iMax, guiText=sInfo + "erzeuge Triggerinformationen", abs=False, cli=False)
        bOkTrigDat = self.__buildTrig2Dat()
        pnProgress(10, iMax, iMax, text=sInfo + "bestimme Tags", abs=False, cli=False)
        bOkTag = self.__buildCsv2Tag()
        pnProgress(11, iMax, iMax, text=sInfo + "bestimme Links", abs=False, cli=False)
        bOkLink = self.__buildCsv2Link()
        pnProgress(12, iMax, iMax, guiText=sInfo + "erzeuge Wörterbuch: Taxon-Aid/Name", abs=False, cli=False)
        bOkSpecialTaxonAid2Name = self.__buildSpecialTaxonAid2Name()
        pnProgress(13, iMax, iMax, guiText=sInfo + "erzeuge Wörterbuch: Gear-Name/Area", abs=False, cli=False)
        bOkSpecialGearName2Area = self.__buildSpecialGearName2Aread()

        # Gab es Fehler?
        self.__bReady = self.bOkWorkflowModell and bOkConnection and bOkPopup and bOkObligate and bOkCsv and bOkTable and bOkTrigger and bOkTrigDat and bOkLookup and bOkSpecialTaxonAid2Name and bOkSpecialGearName2Area and bOkTag and bOkLink and bOkAst

        # Info
        pv("- WF-Modell:       " + ("ok" if self.bOkWorkflowModell == True else "Fehler"))
        pv("- DB-Verbindung:   " + ("ok" if bOkConnection == True else "Fehler"))
        pv("- CSV-Header:      " + ("ok" if bOkCsv == True else "Fehler"))
        pv("- Tab/Attr:        " + ("ok" if bOkTable == True else "Fehler"))
        pv("- Lookup:          " + ("ok" if bOkLookup == True else "Fehler"))
        pv("- Trigger:         " + ("ok" if bOkTrigger == True else "Fehler"))
        pv("- Trigger2Daten:   " + ("ok" if bOkTrigDat == True else "Fehler"))
        pv("- Letzter Ast:     " + ("ok" if bOkAst == True else "Fehler"))
        pv("- Tag:             " + ("ok" if bOkTag == True else "Fehler"))
        pv("- Link:            " + ("ok" if bOkLink == True else "Fehler"))
        pv("- Hilfetexte:      " + ("ok" if bOkPopup == True else "Fehler"))
        pv("- Obligat:         " + ("ok" if bOkObligate == True else "Fehler"))
        pv("- Taxon-Aid/Name:  " + ("ok" if bOkSpecialTaxonAid2Name == True else "Fehler"))
        pv("- Gear-Name/Area:  " + ("ok" if bOkSpecialGearName2Area == True else "Fehler"))

        if self.__bReady == False:
            pn("Fehler: Workflows sind nicht funktionsfaehig ")
        return self.__bReady

    # Informationen
    def info(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Workflows

        lstAlleWf = self.getWfListeAlleKuerzel()
        lstAlleWf.append("*")
        pn("Workflows:  " + str(len(lstAlleWf)))
        for wf in lstAlleWf:
            wfName = self.getWfNameZuKuerzel(wf)
            pv("\t" + wfName + " ("+wf+")")

        # Header
        lstAlleWf = self.getWfListeAlleKuerzel()
        lstAlleWf.append("*")
        pn("Csv-Header: " + str(len(self.__dic_lstCsvHeader["*"])) +" (voll)")
        for wf in lstAlleWf:
            wfName = self.getWfNameZuKuerzel(wf)
            pv("\t"+wfName+" ("+str(len(self.__dic_lstCsvHeader[wf]))+")")
            for data in self.__dic_lstCsvHeader[wf]:
                pd("\t\t"+data)

        # Tabelle/Attribut
        lstAlleWf = self.getWfListeAlleKuerzel()
        lstAlleWf.append("*")
        pn("In-Tbl/Atr: " + str(len(self.__dic_dicCsv2Table["*"]))+" (voll)")
        for wf in lstAlleWf:
            wfName = self.getWfNameZuKuerzel(wf)
            pv("\t" + wfName + " (" + str(len(self.__dic_dicCsv2Table[wf])) + ")")
            for k,v in self.__dic_dicCsv2Table[wf].items():
                pd("\t\t"+str(k)+":"+str(v[0])+"/"+str(v[1]))

        # CsV-Header zu Lookup-Table
        pn("Csv-Lookup: " + str(len(self.__dicCsv2Lookup))+" (voll)")
        for lookup in self.__dicCsv2Lookup.items():
            pv("\t"+lookup[0]+"("+str(len(lookup[1]))+")")
            for k,v in lookup[1].items():
                pd("\t\t"+str(k)+":"+str(v))

        # Liste aller Lookup-Tables
        pn("Lup-Tabs:   " + str(len(self.__lstLookupTables))+" (voll)")
        for lookup in self.__lstLookupTables:
            pv("\t" + lookup)

        # Trigger
        lstAlleWf = self.getWfListeAlleKuerzel()
        lstAlleWf.append("*")
        pn("Csv-Trigg:  " + str(Counter(self.__dic_dicCsv2Trigger["*"].values())[True])+" (voll)")
        for wf in lstAlleWf:
            wfName = self.getWfNameZuKuerzel(wf)
            pv("\t" + wfName + " (" + str(Counter(self.__dic_dicCsv2Trigger[wf].values())[True]) + ")")
            for k, v in self.__dic_dicCsv2Trigger[wf].items():
                if v == True:
                    pd("\t\t" + str(k))

        # Trigger-Daten
        lstAlleWf = self.getWfListeAlleKuerzel()
        lstAlleWf.append("*")
        pn("Trig-Data:  " + str(len(self.__dic_odicTrig2Dat["*"])) + " (voll)")
        for wf in lstAlleWf:
            wfName = self.getWfNameZuKuerzel(wf)
            pv("\t" + wfName + " (" + str(len(self.__dic_odicTrig2Dat[wf])) + ")")
            for k, v in self.__dic_odicTrig2Dat[wf].items():
                pv("\t\t"+k+" ("+str(len(v))+")")
                for it in v:
                    pd("\t\t\t" + str(it))

        # Obligat
        pn("Csv-Oblig:  " + str(Counter(self.__dicCsv2Obligat.values())[True])+" (voll)")
        for k, v in self.__dicCsv2Obligat.items():
            if v == True:
                pv("\t" + str(k))

        # Popups
        pn("Csv-Popup:  " + str(len(self.__dicCsv2Popup))+" (voll)")
        for k, v in self.__dicCsv2Popup.items():
            #pv("\t"+str(k)+":\""+(' '.join(v.split()))[0:30]+"...\"")
            pd("\t"+str(k)+":\""+(' '.join(v.split()))+"\"")

        # Spezial: Taxon-Aid-Name
        pn("TaxAidName: " + str(len(self.__dicSpezialTaxonAid2Name)))
        for k, v in self.__dicSpezialTaxonAid2Name.items():
            pd("\t" + str(k) + ":" + str(v))

        # Spezial: Gear-Name-Area
        pn("Grab2Area:  " + str(len(self.__dicSpezialGearName2Area)))
        for k, v in self.__dicSpezialGearName2Area.items():
            pd("\t" + str(k) + ":" + str(v))

        # Tags
        pn("Csv-Tag  :  " + str(Counter(self.__dicCsv2Tag.values())[True]))
        for k, v in self.__dicCsv2Tag.items():
            if v == True:
                pv("\t" + str(k))

        # Links
        pn("Csv-Link :  " + str(len(self.__dicCsv2Link)))
        for k, v in self.__dicCsv2Link.items():
            pv("\t" + str(k) + " : " + v[0] + ","+v[1] + ","+v[2])

        # Letzter Ast
        pn("LastAst  :  " + self.__sTriggerLetzterAst)

        # Fingerprint
        pn("Fingerpint: " + self.getUserFingerprint())

    # Ist das Workflows-Objekt einsatzfaehig?
    def isReady(self):
        return self.__bReady

    # Ermittle einige Daten ueber den aktuellen Benutzer
    def getUserFingerprint(self):
        return "User:"+ str(getpass.getuser()) +", OS:" + str(platform.system()) + " " + str(platform.release())+ ", Host:" + str(platform.node())
    def getOsUserLoginName(self):
        return str(getpass.getuser())
    def getOsInfos(self):
        return "OS:" + str(platform.system()) + " " + str(platform.release()) + ", Host:" + str(platform.node())

    # Hole Kopie einer Lookup-Table
    def getLookupTableCopy(self, name):
        if name in self.__dicCsv2Lookup:
            return self.__dicCsv2Lookup[name].copy()
        return None

    # Hole Liste aller Tabellen Dictionary
    def getAllUsedTableNames(self):
        lst = list()
        # Extrahiere alle Tabellennamen aus Workflowmodel
        # Lookup
        for zeile in self.__lstWorkflowModell:
            try:
                lookup = zeile[2]
                if lookup is not None:
                    sTab = zeile[2][0]
                    if sTab not in lst:
                        lst.append(sTab)
            except:
                pass
        # Ingest
        for zeile in self.__lstWorkflowModell:
            try:
                sTab = zeile[1][0]
                if sTab not in lst:
                    lst.append(sTab)
            except:
                pass
        return lst

    # Ist Tabelle ein Lookup-Table
    def isTabLookup(self, sTab):
        if sTab in self.__lstLookupTables:
            return True
        else:
            return False

    # Hole Kopie CSV-Header
    def getCsvHeaderCopy(self, sWfKuerzel):
        return self.__dic_lstCsvHeader[sWfKuerzel].copy()

    # Hole Kopie Workflow Namen
    def getWfNamenDictCopy(self):
        return self.__odicWfNamen.copy()

    # Hole Workflow-Namen zu Workflow-Kuerzel
    def getWfNameZuKuerzel(self, sWfKuerzel):
        if sWfKuerzel not in self.__odicWfNamen:
            return "voll"
        else:
            return self.__odicWfNamen[sWfKuerzel]

    # Hole Liste aller Workflow-Kuerzel
    def getWfListeAlleKuerzel(self):
        return list(self.__odicWfNamen)

    # DB Connection-String bauen
    def __getDbConnStr(self):
        return "dbname='" + self.__model.sDbName + "' user='" + self.__model.sDbUser + "' password='" + self.__model.sDbPw + "' host='" + self.__model.sDbHost + "' port='" + self.__model.sDbPort + "'"  # Verbindungs-String

    # Tabellendaten für Ausgabe bearbeiten/verändern
    def tweakTableDataForHumanOutput(self, sTab, lstHeader, lstContent):
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        pd("* Tweak DB-Ergebnis: " + sTab)

        # Fortschritt an
        self.__model.observer.showProgress()

        # Vorbereitungen
            # Dictionary Person:ID->Name
        dicId2PErson = dict((v, k) for k, v in self.__dicCsv2Lookup["cruise_leader"].items())

        # Zeilenergebnisse der DB von RO-Tuple in RW-Liste umwandeln
        lstContent = [list(row) for row in lstContent]

        # Zeilen
        for iRow, row in enumerate(lstContent):

            # Fortschritt
            pnProgress(iRow, len(lstContent), 50, guiText="Verbessere Leserlichkeit\nBearbeite Zeile ", abs=True, cli=False)  # Fortschritt

            # Spalten
            for iCol, col in enumerate(row):

                # -----------------------------------------------------------------
                # Veränderungen vornehmen
                # -----------------------------------------------------------------

                # dataset
                    # person id -> person name
                if sTab == "dataset" and lstHeader[iCol] == "contact_person_id":
                    if str(col) in dicId2PErson:
                        lstContent[iRow][iCol] = dicId2PErson[str(col)]
                # ingest
                    # description kürzen
                if sTab == "ingest" and lstHeader[iCol] == "log":
                    sDescription = col[:25]+" ..."
                    sDescription = sDescription.replace("\n",", ")
                    lstContent[iRow][iCol] = sDescription

                # -----------------------------------------------------------------

        # Fortschritt aus
        self.__model.observer.hideProgress()

        return (lstHeader, lstContent)

    # Ingest-Tabellendaten für leserliche Ausgabe verändern
    def tweakIngestDataForHumanOutput(self, lstHeader, lstContent):
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        # Nichts angekommen?
        if lstContent is None or lstHeader is None:
            return (lstHeader, lstContent)

        # Fortschritt an
        self.__model.observer.showProgress()

        pd("* Tweak Ingest-Table-Data")

        # Zeilenergebnisse der DB von RO-Tuple in RW-Liste umwandeln
        lstContent = [list(row) for row in lstContent]

        # Zeilen
        for iRow, row in enumerate(lstContent):

            # Fortschritt
            pnProgress(iRow, len(lstContent), 50, guiText="Verbessere Leserlichkeit\nBearbeite Zeile ", abs=True, cli=False)

            # Spalten
            for iCol, col in enumerate(row):

                # -----------------------------------------------------------------
                # Veränderungen vornehmen
                # -----------------------------------------------------------------

                sHeader = lstHeader[iCol]
                if sHeader in self.__dicCsv2LookupReverse:
                    if col in self.__dicCsv2LookupReverse[sHeader]:
                        lstContent[iRow][iCol] = self.__dicCsv2LookupReverse[sHeader][col]

                # -----------------------------------------------------------------

        # Fortschritt aus
        self.__model.observer.hideProgress()

        return (lstHeader, lstContent)

    # -----------------------

    # Erstelle Liste aller Lookuptables
    def __buildListOfLookupTables(self):
        if not self.bOkWorkflowModell:
            return None
        lstLookup = list()
        for zeile in self.__lstWorkflowModell:
            try:
                if zeile[2] is not None:
                    sTabLookUp = zeile[2][0]
                    lstLookup.append(sTabLookUp)
            except:
                pass
        return lstLookup

    # Erstelle Liste: Csv-Header
    def __buildCsvHeader(self):
        pd = self.__smartprint.debug
        sModulname = "Bestimme die Namen der CSV-Header fuer jeden Workflow"
        pd("* " + sModulname)
        self.__dic_lstCsvHeader = dict()
        # Durchlaufe alle WfKuerzel
        lstAlleWfKuerzel = self.getWfListeAlleKuerzel()
        lstAlleWfKuerzel.append("*") # Alle
        for sWfKuerzel in lstAlleWfKuerzel:
            sWfName = self.getWfNameZuKuerzel(sWfKuerzel)
            lstCsvHeader = []
            # Durchlaufe das WF-Modell
            for data in self.__lstWorkflowModell:
                # Gehört die Zeile zu Workflow?
                if sWfKuerzel in data[7] or sWfKuerzel == "*":
                    if data[0][0:2] != "__" and data[0][0:2] != "--":  # Trigger-Return-/Zweitbenutzungswerte rausfiltern "__Name,--Name"
                        try:
                            lstCsvHeader.append(data[0])
                        except:
                            return False
            self.__dic_lstCsvHeader[sWfKuerzel] = lstCsvHeader
        return True

    # Erstelle Liste: Trigger-Eintraege
    def __buildTrig2Dat(self):
        pd = self.__smartprint.debug
        sModulname = "Aufbau Trigger-Daten"
        pd("* " + sModulname)
        self.__dic_odicTrig2Dat = dict()

        # Durchlaufe alle WfKuerzel
        lstAlleWfKuerzel = self.getWfListeAlleKuerzel()
        lstAlleWfKuerzel.append("*")  # Alle

        # Durchlaufe alle Workflows
        for sWfKuerzel in lstAlleWfKuerzel:
            trig = None
            odicTrig2Dat = OrderedDict()
            for data in self.__lstWorkflowModell:
                if sWfKuerzel in data[7] or sWfKuerzel == "*":
                    head = data[0]
                    if head in self.__dic_dicCsv2Trigger[sWfKuerzel] and self.__dic_dicCsv2Trigger[sWfKuerzel][head]:
                        trig = head
                        odicTrig2Dat[trig]=[]
                    if trig != None:
                        odicTrig2Dat[trig].append(head)
            self.__dic_odicTrig2Dat[sWfKuerzel] = odicTrig2Dat
        return True

    # Erstelle Dictionary: Eingang(Csv-Header, Rückgabewerte) -> (DB-Tabelle, Attribut)
    def __buildCsv2Table(self):
        pd = self.__smartprint.debug
        sModulname = "Hole Zieltabellen und Attribute"
        pd("* " + sModulname)
        self.__dic_dicCsv2Table = dict()
        # Durchlaufe alle WfKuerzel
        lstAlleWfKuerzel = self.getWfListeAlleKuerzel()
        lstAlleWfKuerzel.append("*")  # Alle
        for sWfKuerzel in lstAlleWfKuerzel:
            dicCsv2Table = dict()
            for data in self.__lstWorkflowModell:
                try:
                    # Gehört die Zeile zu Workflow?
                    if sWfKuerzel in data[7] or sWfKuerzel == "*":
                        dicCsv2Table[data[0]]=(data[1][0], data[1][1])
                except:
                    return False
            self.__dic_dicCsv2Table[sWfKuerzel] = dicCsv2Table
        return True

    # Erstelle Dictionary: Csv-Header -> LookUp-Table(Name -> Id)
    def __buildCsv2Lookup(self):
        pn = self.__smartprint.normal
        pd = self.__smartprint.debug

        sModulname = "Aufbau Lookup-Tables"
        pd("* "+sModulname)

        # Extrahiere aus reduziertem Datenmodell eine Liste mit Daten der Lookup-Tables (Kandidaten)
        lstLookup = []
        for data in self.__lstWorkflowModell:
            if data[0][0:2] != "__" and data[0][0:2] != "--":  # Trigger-Returnwert/Zweitbenutzungswert rausfiltern "__Name,--Name"
                sCsvHead = data[0]
                lookup = data[2]
                if lookup is not None:
                    sLookupTable = lookup[0]
                    sLookupName = lookup[1]
                    sLookupId = lookup[2]
                    lstLookup.append((sCsvHead, sLookupTable, sLookupName, sLookupId))

        # Erstelle die Lookup-Tables
        self.__dicCsv2Lookup = dict()
        self.__dicCsv2LookupReverse = dict()

        try:
            # DB-Connection
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()

            # Durchlaufe alle Lookup-Table-Kandidaten
            for it in lstLookup:
                sCsvHead = it[0]
                sTable = it[1]
                sName = it[2]
                sId = it[3]
                # INFO: SQL-String wird hier sicher zusammengebaut, weil alle Variableninhalt direkt aus Programmcode kommen
                sSqlCmd = "SELECT "+sName+","+sId+" from " + self.__model.db.getDbSchema() + "."+sTable+";"
                cursor.execute(sSqlCmd)
                lstAntwort = cursor.fetchall()

                self.__dicCsv2LookupReverse[sCsvHead] = dict((str(id), str(name).lower()) for name, id in lstAntwort)
                self.__dicCsv2Lookup[sCsvHead] = dict((str(name).lower(), str(id)) for name, id in lstAntwort)

        except Exception as e:
            pn("Fehler (" + sModulname + " : " +sCsvHead+"): Zugriff auf Datenbank: " + str(e))
            return False

        cursor.close()
        conn.close()
        return True

    # Erstelle Dictionary: Csv-Header -> Popup-Hilfen
    def __buildCsv2Popup(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        sModulname = "Hole Popups"
        pd("* " + sModulname)
        self.__dicCsv2Popup = dict()
        sTab = sCol = ""
        try:
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()
            # Durchlaufe alle CSV-Header (Wf=*)
            for head in self.__dic_lstCsvHeader["*"]:
                sTab = self.__dic_dicCsv2Table["*"][head][0]
                sCol = self.__dic_dicCsv2Table["*"][head][1]
                sCommentColumn = self.__model.db.getComment(cursor,sTab,sCol)
                self.__dicCsv2Popup[head] = sCommentColumn
        except Exception as e:
            pn("Fehler (" + sModulname + "): Zugriff auf Datenbank (Tabelle="+sTab+", Attribut="+sCol+"): " + str(e))
            return False
        cursor.close()
        conn.close()
        return True

    # Erstelle Dictionary: Csv-Header -> "Ist ein Eintrag für den CSV-Header obligat"
    def __buildCvs2Obligat(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        sModulname = "Hole Obligatinfo"

        pd("* " + sModulname)
        self.__dicCsv2Obligat = dict()
        try:
            head=sTab=sCol=None
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()
            # Durchlaufe alle Header (Wf=*)
            for head in self.__dic_lstCsvHeader["*"]:
                sTab = self.__dic_dicCsv2Table["*"][head][0]
                sCol = self.__dic_dicCsv2Table["*"][head][1]
                bObligat = self.__model.db.getObligat(cursor,sTab,sCol)
                self.__dicCsv2Obligat[head] = bObligat
        except Exception as e:
            pn("Fehler (" + sModulname + "): Zugriff auf Datenbank ("+str(head)+","+str(sTab)+","+str(sCol)+") : " + str(e))
            return False
        cursor.close()
        conn.close()
        return True

    # Erstelle Dictionary: Csv-Header -> Trigger
    def __buildCvs2Trigger(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        sModulname = "Hole Zieltabellen und Attribute"
        pd("* " + sModulname)
        self.__dic_dicCsv2Trigger = dict()
        # Durchlaufe alle WfKuerzel
        lstAlleWfKuerzel = self.getWfListeAlleKuerzel()
        lstAlleWfKuerzel.append("*")  # Alle
        for sWfKuerzel in lstAlleWfKuerzel:
            dicCsv2Trigger= dict()
            try:
                for data in self.__lstWorkflowModell:
                    # Gehört die Zeile zu Workflow?
                    if sWfKuerzel in data[7] or sWfKuerzel == "*":
                        dicCsv2Trigger[data[0]] = data[3]
            except:
                return False
            self.__dic_dicCsv2Trigger[sWfKuerzel] = dicCsv2Trigger
        return True

    # Bestimme letzten Ast
    def __buildLetzerAst(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        sModulname = "Ermittle letztes Blatt"
        pd("* " + sModulname)
        sAstFund = ""
        iAstFunde = 0
        try:
            for data in self.__lstWorkflowModell:
                sAstCsvName = data[0]
                bAst = data[6]
                if bAst:
                    sAstFund = sAstCsvName
                    iAstFunde += 1
        except:
            return False
        if iAstFunde == 1:
            self.__sTriggerLetzterAst = sAstFund
            return True
        else:
            pn("Fehler (" + sModulname + "): Fehler beim Bestimmen des letzten Astes (Funde!=1): Funde="+str(iAstFunde))
            return False

    # Erstelle Dictionary: Csv-Header -> Tag
    def __buildCsv2Tag(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        sModulname = "Bestimme Tag-Position"
        pd("* " + sModulname)
        self.__dicCsv2Tag = dict()
        try:
            for data in self.__lstWorkflowModell:
                self.__dicCsv2Tag[data[0]] = data[4]
        except:
            return False
        return True

    # Erstelle Dictionary: Csv-Header -> Link-Infos
    def __buildCsv2Link(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        sModulname = "Bestimme Link-Informationen"

        pd("* " + sModulname)
        self.__dicCsv2Link = dict()
        try:
            for data in self.__lstWorkflowModell:
                if data[5] is not None:
                    self.__dicCsv2Link[data[0]] = (data[5][0],data[5][1],data[5][2])
                    pd(data[0] + " : " + data[5][0]+","+data[5][1]+","+data[5][2])
        except Exception as ex:
            print(ex)
            return False
        return True

    # Spezial: Erstelle Dictionary: Gear: Name -> Area
    def __buildSpecialGearName2Aread(self):
        pn = self.__smartprint.normal
        pd = self.__smartprint.debug

        sModulname = "Spezial: Aufbau Dictionary: Gear: Name -> Area"
        pd("* " + sModulname)

        try:
            # DB-Connection
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()
            sSqlCmd = "SELECT name, area from " + self.__model.db.getDbSchema() + ".gear where category='grab' and area is not Null;"
            cursor.execute(sSqlCmd)
            lstAntwort = cursor.fetchall()
            self.__dicSpezialGearName2Area = dict((str(name).lower(), area) for name, area in lstAntwort)
        except Exception as e:
            pn("Fehler (" + sModulname +"): Zugriff auf Datenbank: " + str(e))
            return False

        cursor.close()
        conn.close()
        return True


    # Spezial: Erstelle Dictionary: Taxon: Aid -> Name
    def __buildSpecialTaxonAid2Name(self):
        pn = self.__smartprint.normal
        pd = self.__smartprint.debug

        sModulname = "Spezial: Aufbau Dictionary: Taxon: Aid -> Name"
        pd("* " + sModulname)

        try:
            # DB-Connection
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()
            # TODO: Hier muss später der valid_name rein
            sSqlCmd = "SELECT aid, scientificname from " + self.__model.db.getDbSchema() + ".taxon;"
            cursor.execute(sSqlCmd)
            lstAntwort = cursor.fetchall()
            self.__dicSpezialTaxonAid2Name = dict((str(name).lower(), id) for name, id in lstAntwort)
        except Exception as e:
            pn("Fehler (" + sModulname +"): Zugriff auf Datenbank: " + str(e))
            return False

        cursor.close()
        conn.close()
        return True

    # Checke Header und baue Dictionary: Headername -> Headerpos
    def __buildCsv2Pos(self, file, sWfKuerzel):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        try:
            # Oeffne CSV-Datei
            with open(file, newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                header = next(reader)
        except Exception as ex:
            pn("Fehler in CSV Datei: "+str(ex))
            return None

        # Check CSV-Datei auf Konsistenz
        if not self.__checkCsvHeaderKonsistenz(header, self.__dic_lstCsvHeader[sWfKuerzel]):
            return None

        # Erzeuge Dict Headernamen:Headerposition
        return self.__buildDicCsvHeaderIndices(header)

    # Teste CSV-Header auf Konsistenz
    def __checkCsvHeaderKonsistenz(self, lstHeader, lstNeededHeader):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        pv("* Check CSV-Datei")

        # Check: Header gefunden
        pv("- Headerzeile vorhanden:\t\t", "")
        if all(x == "" for x in lstHeader):
            pv("")
            pn("Fehler in CSV-Datei: Header ist leer")
            return False
        pv("ok")

        # Check: Korrekte Spaltenanzahl
        pv("- korrekte Spaltenanzahl:\t\t", "")
        if len(lstHeader) != len(lstNeededHeader):
            pv("")
            pn("Fehler in CSV-Datei: Unterschiedliche Spalteneintraege: " + "CSV=" + str(
                len(lstHeader)) + "," + "DB=" + str(len(lstNeededHeader)))
            pn("  benoetigte Header: " + " ".join(lstNeededHeader))
            pn("  gefundene Header:  " + " ".join(lstHeader))
            return False
        pv("ok")

        # Check: Doppelte Eintraege
        pv("- keine doppelten Header gefunden:\t", "")
        c = Counter(lstHeader)
        if c.most_common(1)[0][1] > 1:
            pv("")
            pn("Fehler: Mehrfacher Eintrag in CSV-Datei von Header: \"" + str(c.most_common(1)[0][0])+"\"")
            return False
        pv("ok")

        # Check_ Alle noetigen Eintraege vorhanden
        pv("- alle benoetigen Header gefunden:\t", "")
        for h in lstNeededHeader:
            if h not in lstHeader:
                pv("")
                pn("Fehler: Header fehlt in CSV-Datei: " + h)
                pn("  benoetigte Header: "+" ".join(lstNeededHeader))
                pn("  gefundene Header:  "+" ".join(lstHeader))
                return False
        pv("ok")
        return True

    # Ermittle Indizes der benoetigten Header in CSV-Datei
    def __buildDicCsvHeaderIndices(self, lstHeader):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        pd("* Ermittle Headerpositionen in CSV")

        dicCvsHeaderName2Pos = dict()
        try:
            for i, h in enumerate(lstHeader):
                dicCvsHeaderName2Pos[h] = i
                pd(h + " : " + str(i))
        except:
            pn("Fehler: Erzeugung Mapping Headernamen zu Position")
            return None

        return dicCvsHeaderName2Pos

    # Ermittle Trigger des ersten Blattes
    def __getTriggerFirstLeaf(self, sWfKuerzel):
        sTriggerBlatt = None
        try:
            lstTrig = list(self.__dic_odicTrig2Dat[sWfKuerzel])
            sTriggerBlatt = lstTrig[lstTrig.index(self.__sTriggerLetzterAst) + 1]
        except Exception as ex:
            print(ex)
            pass
        return sTriggerBlatt

    # ---------------------------

    # Ingest Lookup
    def ingestLookup(self, cursor, sTabelle, sCsvFilename):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        sModulname = "Ingest Lookup ("+sTabelle+")"
        sFehler = "" # Fehlerstring
        pn("* "+sModulname)
        pn("DB-Tabelle: "+sTabelle)
        pn("CSV-Datei:  "+sCsvFilename)

        # DB: Hole Attribute
        try:
            lstTmp = self.__model.db.getAttributnamen(cursor, sTabelle)
        except Exception as ex:
            sFehler += "Fehler (" + sModulname + "): Zugriff auf die Datenbank (Hole Attribute, ...): " + str(ex)
            pn(sFehler)
            return (False, 0, sFehler)

        # Entferne nicht gewuenschte Attribute
        lstAttributAusschluss = ["id"]

        # ---------------------------------------------------------------
        # TWEAK/SPEZIALISIERUNG: Attribute entfernen
        # ---------------------------------------------------------------
        if sTabelle == "taxon":
            # Taxon
                # Accepted_Id entfernen
            lstAttributAusschluss.append("accepted_id")
        # ----------------------------------------------------------------

        lstAttr = [x for x in lstTmp if (x not in lstAttributAusschluss)]

        # CSV-Datei: Teste auf Konsistenz und hole die Indizes der benötigten Header
        try:
            # Hole Header aus CSV
            with open(sCsvFilename, newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                lstHeader = next(reader)
        except Exception as ex:
            sFehler += "Fehler in CSV Datei: "+str(ex)
            pn(sFehler)
            return (False, 0, sFehler)
            # Check Header auf Konsistenz
        if not self.__checkCsvHeaderKonsistenz(lstHeader, lstAttr):
            return (False, 0, "Fehler bei Konsistenzcheck der Header")
            # Erzeuge Dict Headernamen:Headerposition
        dicHeaderPos = self.__buildDicCsvHeaderIndices(lstHeader)
        if dicHeaderPos == None:
            return (False, 0, "Fehler beim Auswerten der Header")

        # Hole Gesamtanzahl aller Zeilen in CSV-Datei
        iZeilenGesamt = sum(1 for line in open(sCsvFilename))

        # GUI: Progressbar an
        if self.__model is not None and self.__model.observer is not None:
            self.__model.observer.showProgress()

        # Lies CSV zeilenweise und Trage in DB ein
        bFehler = False
        iAnzahlErzeugterDatensaetze = 0
        try:
            # Einlesen der CSV-Datei
            with open(sCsvFilename, newline='') as csvfile:
                csvReader = csv.reader(csvfile, delimiter=',', quotechar='"')
                csvReader.__next__() # Header entfernen
                for lstZeile in csvReader:
                    # Aktuelle Zeile
                    iZeile = csvReader.line_num

                    # Erzeuge aus aktueller Zeile Dictionary mit Attributnamen und Wert
                    dicVal = {}
                    bDicValEmpty = True
                    for sAttr in lstAttr:
                        sWert = lstZeile[dicHeaderPos[sAttr]]

                        # ---------------------------------------------------------------
                        # TWEAK/SPEZIALISIERUNG
                        # ---------------------------------------------------------------

                        # Dataset
                            # Name -Auflösen via Lookup-Table-> contact_person_id
                        if sTabelle == "dataset" and sAttr == "contact_person_id":
                            sWert = self.__dicCsv2Lookup["cruise_leader"][sWert.lower()]

                        # ----------------------------------------------------------------

                        if sWert != "":
                            bDicValEmpty = False
                        dicVal[sAttr] = sWert

                    # Leerzeile ueberspringen
                    if bDicValEmpty:
                        pv(str(iZeile) + " leer")
                    else:
                        # Trage in DB ein
                        self.__model.db.insertIntoTable(cursor, sTabelle, dicVal)
                        iAnzahlErzeugterDatensaetze += 1
                        sSqlQuery = cursor.query.decode("utf-8")
                        iId = cursor.fetchone()[0]
                        # Fortschritt
                        pnProgress(iZeile, iZeilenGesamt, 20, guiText="Bearbeite Zeile ", abs=True, cli=True)
                        # Info
                        pd("SQL: " + sSqlQuery + " -> " + str(iId))
                        pv(str(iZeile) +" +"+ sTabelle+"(" +str(iId)+")")

        except Exception as ex:
            bFehler = True
            sFehler += "Fehler in Zeile #"+str(iZeile) + "\n" + str("|".join(lstZeile))+"\n"+str(ex)
            pn(sFehler)

        # Progressbar aus
        if self.__model is not None and self.__model.observer is not None:
            self.__model.observer.hideProgress()

        return (not bFehler, iAnzahlErzeugterDatensaetze, sFehler)

    # ---------------------------

    # Ingest Daten
    def ingestData(self, file, sWfKuerzel):

        sWfName = self.getWfNameZuKuerzel(sWfKuerzel) # Hole Namen zu Wf-Kuerzel

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        pn("* Starte Workflow")
        pn("Daten: " + sWfName)
        pn("CSV-Datei: "+str(file))

        # Check CSV und erzeuge Dictionary Headername 2 Position
        dicCvs2Pos = self.__buildCsv2Pos(file,sWfKuerzel)
        if dicCvs2Pos == None:
            return (False, 0, None, None, "Fehler beim Checken der Konsistenz der CSV-Datei.")

        # DB-Connection
        try:
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()
        except Exception as e:
            pn("Fehler: Beim Zugriff auf die Datenbank: "+str(e))
            return (False, 0, None, None, str(e))

        # Hole Gesamtanzahl aller Zeilen in CSV-Datei
        iZeilenGesamt = sum(1 for line in open(file))

        # GUI: Progressbar an
        if self.__model is not None and self.__model.observer is not None:
            self.__model.observer.showProgress()

        # Wichtige Daten/Variablen
            # Aktuelle vollstaendige Zeile
        dicAktZeile = dict()
        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
            dicAktZeile[sHeadName] = None
        # Aktuelle vollstaendige Zeile (nach Lookup-Aufloesung)
        dicAktZeileNachLookup = dict()
        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
            dicAktZeileNachLookup[sHeadName] = None
            # Letzte vollstaendige Zeile
        dicLetzteZeile = dict()
        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
            dicLetzteZeile[sHeadName] = None
            # Trigger
        odicTrig = OrderedDict()
        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
            if self.__dic_dicCsv2Trigger[sWfKuerzel][sHeadName]:
                odicTrig[sHeadName] = False
            # Trigger Rueckgabewerte
        dicTrigRet = dict()
        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
            dicTrigRet[sHeadName] = None
            # Triggerfeld ist einmalig im Sichtbarkeitsbereich des Papa
        odicTriqUniq = OrderedDict()
        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
             if self.__dic_dicCsv2Trigger[sWfKuerzel][sHeadName]:
                odicTriqUniq[sHeadName] = []
            # Dictionary für Tags (Tag->ID) für jeden Trigger
        dicTrigTags = dict()
        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
            if self.__dic_dicCsv2Trigger[sWfKuerzel][sHeadName]:
                dicTrigTags[sHeadName] = dict()
            # Zähler für Erzeugte Datensaetze (~Trigger)
        odicTrigCounter = OrderedDict()
        for k in odicTrig:
            odicTrigCounter[k] = 0
            # Fehler
        bFehler = False
        sFehler = ""
            # Warnungen
        lstWarn = []
            # Zaehler DB-Aktionen
        iCountDbAktionen = 0
            # Zeitmessung (Startzeit)
        iZeitStart = time.time()
            # Ertser Trigger im Blattbereich
        sTriggerBlatt = None
            # Flag: Blattbereich erreicht
        bBlatt = False
            # Flag: ReUse
        bReUse = False
            # Flag: Wurden in Zeile bereits einmal alle UniqFelder resettet (Hat _nur_ die Aufbage nicht unnötig häufig zu Resetten in einer Zeile -> Laufzeit wird besser)
        bUniqReset = False
            # Sonderfall: Eingegebene Aphia-ID (vor Lookup-Auflösung, wichtig für Uniq- und Taxonnamen/Aid-Test)
        sTmpPraeLookupTaxonAid = None
            # Info-Strings
        sInfoCsvDebug = None
        sInfoDebugLastZeile = None
        sInfoSqlVerbose = None
        sInfoSqlDebug = None
        sInfoTriqUniqResetDebug = None
        sInfoTagResetDebug = None
            # Debug
        iZeileCode = -1 # Zeile in dem ein Fehler aufgetreten ist
            # Automatisch zusammengestelltes SQL-Kommando
        sSqlCmdTeil1 = None
        sSqlCmdTeil2 = None
        sSqlCmdLinkTeil1 = None
        sSqlCmdLinkTeil2 = None

        # Ermittle ersten Trigger im Blattbereich
        sTriggerBlatt = self.__getTriggerFirstLeaf(sWfKuerzel)
        if sTriggerBlatt is None:
            sFehler = "Fehler (Hole Ingest): Beim Ermitteln des Blattberiches im Workflow"
            bFehler = True

        # Eintrag in Ingestion-Tabelle
        pd("* Erzeuge Eintrag in Ingestionstabelle")
        try:
            sSqlCmd = "INSERT INTO " + self.__model.db.getDbSchema() + ".ingest (name, created_on, workflow, description, log) VALUES (%s,%s,%s,%s,%s) returning id;"
            sName = self.getOsUserLoginName()
            sDatum = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sDatenTyp = str(sWfKuerzel)
            cursor.execute(sSqlCmd, (sName,sDatum,sDatenTyp, "---", "---"))
            iIngestId = cursor.fetchone()[0]  # Antwort
            sSqlQuery = cursor.query.decode("utf-8")
        except Exception as ex:
            sFehler = "Fehler beim Eintragen in die Ingestion-Tabelle: "+str(ex)
            pn(sFehler)
            # Progressbar aus
            if self.__model is not None and self.__model.observer is not None:
                self.__model.observer.hideProgress()
            return (False, 0, None, None, sFehler)

        pd("SQL: "+sSqlQuery+" -> "+str(iIngestId))

        try:
            # Einlesen der CSV-Datei
            with open(file, newline='') as csvfile:
                csvReader = csv.reader(csvfile, delimiter=',', quotechar='"')
                csvReader.__next__() # Entferne Zeile 1 (Header)

                # -----------------------------------------------------------------
                # Durchlaufe alle CSV-Zeilen (ab Zeile 2)
                # -----------------------------------------------------------------

                pv("* Durchlaufe CSV-Datei")

                # Durchlaufe alle CSV-Zeilen
                for lstZeile in csvReader:
                    iZeile = csvReader.line_num  # Aktuelle Zeilennummer

                    # Teste auf eine komplett leere Zeile
                    if all(x == "" for x in lstZeile):
                        # Leere Zeile
                        pd(str(iZeile) + "<leer>")
                    else:
                        # Alle Trigger resetten
                        for it in odicTrig:
                           odicTrig[it]=False

                        # -----------------------------------------------------------------
                        # datenreduzierte CSV-Zeile -> vollstaendige interne Zeile
                        # -----------------------------------------------------------------

                        bBlatt = False
                        sTmpPraeLookupTaxonAid = ""
                        bReUse = True
                        bUniqReset = False
                        sInfoCsvDebug = ""
                        sInfoTriqUniqResetDebug = ""
                        sInfoTagResetDebug = ""
                        sTrigName = None # Workaround: Muss für Fehlerbehandlung hier schon definiert werden

                        # Durchlaufe Header-Namen in korrekter Reihenfolge
                        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:

                            # Csv-Head-Inhalt
                            sHeadInhalt = lstZeile[dicCvs2Pos[sHeadName]] # aktuell
                            sHeadInhaltVorLookup = sHeadInhalt # aktuell vor Lookupaufloesung
                            sHeadInhaltLast = dicLetzteZeile[sHeadName]  # letzter

                            # --------------------------------
                            # SONDERFALL
                            # Merke Taxon-Aid -> für späteren Taxon-Namen-Check
                            if sHeadName == "taxon_aid":
                                sTmpPraeLookupTaxonAid = sHeadInhalt
                            # --------------------------------

                            # ***************************************************
                            # Ist der Blattbereich erreicht -> ReUse deaktivieren
                            # ***************************************************
                            if sHeadName == sTriggerBlatt:
                                bBlatt = True
                                bReUse = False

                            # ***************************************************
                            # Test: Muss ein Trigger gedrueckt werden?
                            # ***************************************************

                            # Ist Header ein Trigger-Feld
                            # a) Ast: Hat sich Inhalt zur vorherigen Zeile veraendert und ist nicht leer -> Trigger drücken
                            # b) Blatt: Inhalt nicht leer -> Trigger drücken
                            if sHeadName in odicTrig and (
                                    (sHeadInhaltLast != sHeadInhalt and sHeadInhalt != "") or
                                    (sHeadInhalt != "" and bBlatt)
                            ):

                                # ***************************************************
                                # ReUse deaktivieren
                                # ***************************************************
                                bReUse = False
                                odicTrig[sHeadName] = True # Trigger explizit druecken

                                # ***************************************************
                                # Trigger auf Einmaligkeit in Sichbarkeitsbereich checken
                                # ***************************************************
                                if sHeadInhalt in odicTriqUniq[sHeadName]:

                                    # ---------------------------------------------------------
                                    # SONDERFAELLE
                                    # ---------------------------------------------------------
                                    # Taxon -> Einmaligkeit ergibt nur eine Warnung
                                    if sHeadName == "taxon_aid":
                                        # Ist das Taxon ein Artefakt -> Bitte keine Warnung
                                        if sTmpPraeLookupTaxonAid != "-1":
                                            sInfoCruise = dicAktZeile["cruise_name"]
                                            sInfoStation = dicAktZeile["station_name"]
                                            sInfoSample = dicAktZeile["sample_name"]
                                            sWarn = "Zeile "+str(iZeile)+": Taxon-AphiaID nicht einmalig: Aid=\'"+str(sTmpPraeLookupTaxonAid)+ "\' in Cruise=\'"+sInfoCruise+"\' Station=\'"+sInfoStation+"\' Sample=\'"+sInfoSample+"\'"
                                            lstWarn.append(sWarn)
                                    # Sieveanalyis, Sediment, Autopsy -> Einmaligkeit ist aufgehoben
                                    elif sHeadName == "sieveanalysis_residue" or \
                                        sHeadName == "sediment_weight" or \
                                        sHeadName == "autopsy_population_name":
                                        pass

                                    # ---------------------------------------------------------

                                    else:
                                        raise NameError("Verstoss gegen Einmaligkeit in Sichtbarkeitsbereich: Attribut=\'"+sHeadName+ "\', Wert=\'"+sHeadInhalt+"\'\n")
                                else:
                                    odicTriqUniq[sHeadName].append(sHeadInhalt) # *) Trigger-UniqListe erweitern

                                # ***************************************************
                                # Lösche alle folgenden Trigger Uniq Felder, wenn
                                # ich noch im Astbereich bin
                                # Im Blattbereich werden Trigger Uniq Felder nie mehr resettet
                                # ***************************************************
                                if not bBlatt:
                                    if sHeadName in odicTriqUniq and not bUniqReset:
                                        bUniqReset = True
                                        sInfoTriqUniqResetDebug += "  rstU: trigger=" + sHeadName + " -> reset trig_uniq="
                                        sInfoTagResetDebug += "  rstT: trigger=" + sHeadName + " -> reset tag_(uniq)="
                                        # Setze Trigger-Uniq-Felder zurück ab diesem Trigger
                                        lstTU = list(odicTriqUniq)
                                        iIdx = lstTU.index(sHeadName)
                                        for sTmpHead in lstTU[iIdx+1:]:
                                            sInfoTriqUniqResetDebug += sTmpHead+" "
                                            odicTriqUniq[sTmpHead] = []
                                        # Setze Tag-(Uniq)-Felder zurück ab diesem Trigger
                                        lstTag = list(dicTrigTags)
                                        iIdx = lstTag.index(sHeadName)
                                        for sTmpHead in lstTag[iIdx + 1:]:
                                            sInfoTagResetDebug += sTmpHead + " "
                                            dicTrigTags[sTmpHead] = dict()

                            # ***************************************************
                            # Wurde ReUse in diesem oder im vorherigen Durchlauf deaktiviert?
                            # ***************************************************
                            if not bReUse:

                                # ***************************************************
                                # Setze (alle folgenden) Triggerfeld(er)
                                # ***************************************************
                                if sHeadName in odicTrig:
                                    # Noch nicht im Blattbereich -> Setze jeden weiteren Trigger
                                    if not bBlatt:
                                        odicTrig[sHeadName] = True

                                # ***************************************************
                                # Alle (folgenden) CSV-Felder neu einlesen
                                # ***************************************************
                                dicAktZeile[sHeadName] = sHeadInhalt
                            else:
                                # Warnung: Strict-Mode
                                if sHeadInhalt != "" and sHeadInhalt != sHeadInhaltLast:
                                    sWarn = "Zeile " + str(
                                        iZeile) + ": Zellinhalt anders als erwartet: Header=\'" + sHeadName + "\' Inhalt=\'" + str(sHeadInhalt) + "\' Vorgabe=\'" + str(sHeadInhaltLast)+"\'"
                                    lstWarn.append(sWarn)

                            # Debug-Info
                            sInfoCsvDebug += sHeadName+"("+ ("T" if self.__dic_dicCsv2Trigger[sWfKuerzel][sHeadName] else "") + ("L" if sHeadName in self.__dicCsv2Lookup else "") + ("R" if bReUse else "") + ")=" + (("\"" + sHeadInhaltVorLookup + "\"") if sHeadInhalt != "" else "-") + " "

                        # -----------------------------------------------------------------
                        # Ab hier ist die aktuelle Arbeitszeile intern vollständig aufgebaut
                        # und die entsprechenden Trigger sind gedrueckt ...
                        # -----------------------------------------------------------------

                        # Kopiere aktuelle Zeile in alte Zeile
                        for sHead,sInhalt in dicAktZeile.items():
                            dicLetzteZeile[sHead] = sInhalt

                        # Erzeuge Kopie der akt Zeile mit aufgeloesten Lookup-Feldern
                        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
                            sHeadInhalt = dicAktZeile[sHeadName]
                            if sHeadInhalt != "" and sHeadName in self.__dicCsv2Lookup:
                                # Lookup aufloesen
                                try:
                                    sHeadInhalt = str(self.__dicCsv2Lookup[sHeadName][sHeadInhalt.lower()])
                                except Exception as ex:
                                    raise NameError(
                                        "Eintrag nicht in Lookup-Table gefunden: Attribut=\"" + sHeadName + "\", Wert=\"" + sHeadInhalt + "\"\n")
                            dicAktZeileNachLookup[sHeadName] = sHeadInhalt

                        # DebugInfo: Jetzt die Info ueber letzte Zeile sichern
                        sInfoDebugLastZeile = ""
                        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
                            sInfoDebugLastZeile += sHeadName + "=\"" + str(dicLetzteZeile[sHeadName]) + "\" "

                        # -----------------------------------------------------------------
                        # Erzeuge die Eintraege in DB
                        # -----------------------------------------------------------------

                        sInfoSqlVerbose = ""
                        sInfoSqlDebug = ""
                        # Alle Trigger durchlaufen
                        for sTrigName, bTrig in odicTrig.items():
                            # Ist Trigger aktiviert?
                            if bTrig:
                                odicTrigCounter[sTrigName] += 1 # Counter: Gedrückte Trigger -> ~ Einträge in DB

                                # -----------------------------------------------------------------
                                # SONDERFAELLE
                                # Abfangen -> evtl. SQL-Befehle manuell erzeugen
                                # -----------------------------------------------------------------

                                # Dataset
                                if sTrigName == "dataset":
                                    iIdDataset = dicAktZeileNachLookup["dataset"]
                                    sInfoSqlVerbose += "dataset(" + str(iIdDataset)+ ") "
                                    dicTrigRet[sTrigName] = iIdDataset

                                # -----------------------------------------------------------------

                                else:

                                    # ------------------------------
                                    # SONDERFALL
                                    # Check Taxon-Aid vs Taxon-Name
                                    # ------------------------------
                                    try:
                                        if sTrigName == "taxon_aid":
                                            sTestTaxonAid = None
                                            sTestTaxonNameEingabe = None
                                            sTestTaxonNameAusTaxonliste = None
                                            # Hole Aid aus Eingabe
                                            sTestTaxonAid = str(dicAktZeile["taxon_aid"])
                                            # Ist Aid nicht -1 für Artefakt?
                                            if sTestTaxonAid != "-1":
                                                sTestTaxonNameEingabe = str(dicAktZeileNachLookup["taxon_name"]).lower()
                                                sTestTaxonNameAusTaxonliste = str(self.__dicSpezialTaxonAid2Name[sTestTaxonAid]).lower()
                                                # Eingabename stimmt zu <80% mit Namen aus Taxonliste überein
                                                if SequenceMatcher(None,sTestTaxonNameEingabe,sTestTaxonNameAusTaxonliste).ratio() < 0.8:
                                                    sWarn = "Zeile " + str(iZeile) + ": Taxon-Name stimmt nicht mit Namen aus Taxon-Liste überein: Aid=" + sTestTaxonAid + " Name=\'"+ sTestTaxonNameEingabe + "\' Taxonliste=\'"+ sTestTaxonNameAusTaxonliste+"\'"
                                                    lstWarn.append(sWarn)
                                    except Exception as ex:
                                        # ... falls aber doch, dann ist das einen Glückwusch wert!
                                        pn("Glückwunsch! "+
                                           "Es wurde beim Taxon-Aid/Namen-Test ein äußerst seltenes, quasie unmögliches technisches Problemchen endeckt: "+
                                           "Zeile: "+str(iZeile)+
                                           " AID: "+ str(sTestTaxonAid) +
                                           " Name: \'" + str(sTestTaxonNameEingabe) + "\'"+
                                           " Taxonliste: \'" + str(sTestTaxonNameAusTaxonliste) + "\'"+
                                           " Fehler: "+str(ex))
                                    # ------------------------------

                                    # ------------------------------
                                    # SONDERFALL
                                    # Check: Gear Area differiert von Wert in Gear-Tabelle
                                    # ------------------------------
                                    try:
                                        if sTrigName == "sample_gear":
                                            sGearName = dicAktZeile["sample_gear"]
                                            sGearArea = dicAktZeile["sample_area"]
                                            if sGearName in self.__dicSpezialGearName2Area:
                                                iGearAreaInGearTab = self.__dicSpezialGearName2Area[sGearName.lower()]
                                                if str(iGearAreaInGearTab) != sGearArea:
                                                    sWarn = "Zeile " + str(
                                                        iZeile) + ": angegebene Gear-Area stimmt nicht mit Vorgabe aus Gear-Tabelle überein: Gear=\'" + sGearName + "\' Area=" + sGearArea + " Area-Gear-Tabelle=" + str(iGearAreaInGearTab)
                                                    lstWarn.append(sWarn)
                                    except Exception as ex:
                                        # ... falls aber doch, dann ist das einen Glückwusch wert!
                                        pn("Glückwunsch! " +
                                           "Es wurde beim Sample-Gear-Area-Test ein äußerst seltenes, quasie unmögliches technisches Problemchen endeckt: " +
                                           "Zeile: " + str(iZeile) +
                                           " Name: \'" + sGearArea+ "\'" +
                                           " Area: " + sGearArea+
                                           " Area-Gear-Tabelle: " + str(iGearAreaInGearTab) +
                                           " Fehler: " + str(ex))
                                        # ------------------------------

                                    # -------------------------------------------------------------
                                    # Automatisierter Bau: Sql-Commando
                                    # Benutze nur Attribute, die auch einen Wert in der Excel-Tabelle haben
                                    # -------------------------------------------------------------

                                    sSqlCmdTeil1 = ""
                                    sSqlCmdTeil2 = ""
                                    sSqlCmdLinkTeil1 = ""
                                    sSqlCmdLinkTeil2 = ""
                                    sSqlVal = []
                                    bTagGefunden = False
                                    sTagHeader = ""
                                    # Durchlaufe Header des aktuellen Triggers
                                    for sHead in self.__dic_odicTrig2Dat[sWfKuerzel][sTrigName]:

                                        # Teste ob Header ein Tag ist -> Feld merken
                                        if self.__dicCsv2Tag[sHead] == True and dicAktZeileNachLookup[sHead] != "":
                                            bTagGefunden = True
                                            sTagHeader = sHead

                                        # ------------------------------
                                        # SONDERFALL
                                        # Check: Gear Area differiert von Wert in Gear-Tabelle
                                        # ------------------------------
                                        try:
                                            if sHead == "sample_gear":
                                                sGearName = dicAktZeile["sample_gear"]
                                                sGearArea = dicAktZeile["sample_area"]
                                                if sGearName in self.__dicSpezialGearName2Area and sGearArea != "":
                                                    iGearAreaInGearTab = self.__dicSpezialGearName2Area[sGearName.lower()]
                                                    if str(iGearAreaInGearTab) != sGearArea:
                                                        sWarn = "Zeile " + str(
                                                            iZeile) + ": Gear-Area stimmt nicht mit Vorgabe aus Gear-Tabelle überein: Gear=\'" + sGearName + "\' Area=\'" + sGearArea + "\' Area(Gear-Tabelle)=\'" + str(iGearAreaInGearTab)+"\'"
                                                        lstWarn.append(sWarn)
                                        except Exception as ex:
                                            # ... falls aber doch, dann ist das einen Glückwusch wert!
                                            pn("Glückwunsch! " +
                                               "Es wurde beim Sample-Gear-Area-Test ein äußerst seltenes, quasie unmögliches technisches Problemchen endeckt: " +
                                               "Zeile: " + str(iZeile) +
                                               " Name: \'" + sGearArea + "\'" +
                                               " Area: " + sGearArea +
                                               " Area-Gear-Tabelle: " + str(iGearAreaInGearTab) +
                                               " Fehler: " + str(ex))
                                        # ------------------------------

                                        # a) Bau: Variablen-Liste
                                        if sHead[0:2] == "__":
                                            # Rückgabewert von anderem Trigger
                                            sSqlVal.append(dicTrigRet[sHead[2:]])
                                        elif sHead[0:2] == "--":
                                            # Ein bereits eingelesener Wert aus CSV
                                            if dicAktZeileNachLookup[sHead[2:]] != "":
                                                # --------------------------------
                                                # SONDERFALL
                                                # Original Taxon-Aid/Gear-Namen verwenden (vor Lookup-Auflösung)
                                                # --------------------------------
                                                if sHead == "--taxon_aid":
                                                    sSqlVal.append(dicAktZeile["taxon_aid"])
                                                elif sHead == "--sample_gear":
                                                    sSqlVal.append(dicAktZeile["sample_gear"])
                                                # --------------------------------
                                                else:
                                                    sSqlVal.append(dicAktZeileNachLookup[sHead[2:]])
                                        else:
                                            # Wert aus CSV (nur wenn Wert!="")
                                            if dicAktZeileNachLookup[sHead] != "":
                                                sSqlVal.append(dicAktZeileNachLookup[sHead])

                                        # Link (Wenn gefunden... abschliessend noch zusätzlich die Link-Id eintragen)
                                        if  sHead in self.__dicCsv2Link and dicAktZeileNachLookup[sHead] != "":
                                            sTagBezeichner = dicAktZeileNachLookup[sHead]
                                            sTagTrigHeader = self.__dicCsv2Link[sHead][0]
                                            if sTagBezeichner in dicTrigTags[sTagTrigHeader]:

                                                iTagId = dicTrigTags[sTagTrigHeader][sTagBezeichner]
                                            else:
                                                raise NameError("Bezeichner wurde in Geltungsbereich nicht gefunden: Attribut=\"" + sHead + "\", Bezeichner=\"" + sTag + "\"\n")
                                            sSqlVal.append(iTagId)

                                        # b) Bau: Sql-Cmd-Teile (nur wenn Wert==Rückgabewert/Zweitbenutzung oder Wert!=Rückgabewert/Zweitbenutzun und Wert!="")
                                        if sHead[0:2] == "__" or sHead[0:2] == "--" or (sHead[0:2] != "__" and sHead[0:2] != "--" and dicAktZeileNachLookup[sHead] != ""):
                                            sSqlCmdTeil1 += self.__dic_dicCsv2Table[sWfKuerzel][sHead][1] + ","
                                            sSqlCmdTeil2 += "%s,"

                                        # Link (Wenn gefunden... abschliessend noch zusätzlich das Link Attribut eintragen)
                                        if sHead in self.__dicCsv2Link and dicAktZeileNachLookup[sHead] != "":
                                            sTagTrigAttribut = self.__dicCsv2Link[sHead][2]
                                            sSqlCmdTeil1 += sTagTrigAttribut + ","
                                            sSqlCmdTeil2 += "%s,"

                                    sSqlVal.append(str(iIngestId)) # IngestID

                                    # Sql-Cmd zusammenbauen
                                    sSqlCmd = "INSERT INTO " + self.__model.db.getDbSchema() + "." + self.__dic_dicCsv2Table[sWfKuerzel][sTrigName][0] + \
                                              "("+sSqlCmdTeil1+"ingest_id) VALUES ("+sSqlCmdTeil2+"%s) returning id;"

                                    # Führe Sql-Cmd aus
                                    cursor.execute(sSqlCmd, sSqlVal)
                                    sSqlQuery = cursor.query.decode("utf-8")
                                    iId = cursor.fetchone()[0] # Antwort
                                    dicTrigRet[sTrigName]= iId

                                    # Tags: Gab es ein Tag Feld in Datensatz -> Merke die Id zum Tag
                                    if bTagGefunden:
                                        sTag = dicAktZeile[sTagHeader]
                                        if sTag not in dicTrigTags[sTrigName]:
                                            dicTrigTags[sTrigName][sTag] = iId
                                        else:
                                            # Tag wurde bereits benutzt -> Fehler
                                            raise NameError("Bezeichner wurde in Geltungsbereich bereits benutzt: Attribut=\"" + sTagHeader + "\", Bezeichner=\"" + sTag + "\"\n")

                                    sInfoSqlVerbose += "+"+self.__dic_dicCsv2Table[sWfKuerzel][sTrigName][0] + "(" + str(iId) + ") "
                                    sInfoSqlDebug += "  Sql:  "+sSqlQuery+"\n"
                                    iCountDbAktionen += 1
                                    # ---

                        # -----------------------------------------------------------------

                        # Info
                            # Normal
                        pnProgress(iZeile, iZeilenGesamt, 50, guiText="Ingest: " + sWfName + "\nBearbeite Zeile ", abs=True, cli=True)  # Fortschritt
                            # Verbose
                        pv(str(iZeile)+" "+sInfoSqlVerbose)
                            # Debug
                        pd("  csv:  "+sInfoCsvDebug)
                        pd("  last: "+sInfoDebugLastZeile)
                        sInfoDebug = "  akt:  "
                        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
                            sInfoDebug += sHeadName + "=\"" + str(dicAktZeile[sHeadName])+"\" "
                        pd(sInfoDebug)
                        sInfoDebug = "  aktL: "
                        for sHeadName in self.__dic_lstCsvHeader[sWfKuerzel]:
                            sInfoDebug += sHeadName + "=\"" + str(dicAktZeileNachLookup[sHeadName]) + "\" "
                        pd(sInfoDebug)
                        sInfoDebug = "  trig: "
                        for sTrigName, bTrig in odicTrig.items():
                            sInfoDebug += (sTrigName if bTrig else "-")+" "
                        pd(sInfoDebug)
                        if sInfoTriqUniqResetDebug != "":
                            pd(sInfoTriqUniqResetDebug)
                        if sInfoTagResetDebug != "":
                            pd(sInfoTagResetDebug)
                        sInfoDebug = "  tRet: "
                        for sTrigName, bTrig in odicTrig.items():
                            iRet = dicTrigRet[sTrigName]
                            sInfoDebug += sTrigName + "(" + (str(iRet) if iRet is not None else "-") + ") "
                        pd(sInfoDebug)
                        sInfoDebug = "  uniq: "
                        for sTrigUniqName, lstUniqListe in odicTriqUniq.items():
                            sInfoDebug += (sTrigUniqName+"("+str(lstUniqListe)+")" if len(lstUniqListe) > 0 else "-") + " "
                        pd(sInfoDebug)
                        sInfoDebug = "  tags: "
                        for sTrigTagName, lstTags in dicTrigTags.items():
                            sInfoDebug += (sTrigTagName+"("+str(lstTags)+") " if len(lstTags)>0 else "-") + " "
                        pd(sInfoDebug)
                        pd(sInfoSqlDebug)

        except Exception as ex:

            # Debug
            exc_type, exc_obj, exc_tb = sys.exc_info()
            iZeileCode = exc_tb.tb_lineno # Falls ein Fehler entsteht -> Zeile
            sFehler += "Fehler in Zeile #" + str(iZeile) + "\n"
            sFehler += '|'.join(lstZeile)+"\n"
            sFehler += "Trigger = "+ str(sTrigName) + "\n"
            sFehler += str(ex)
            bFehler = True

        # Progressbar aus
        if self.__model is not None and self.__model.observer is not None:
            self.__model.observer.hideProgress()

        # Trigger Counter: CSV-Header in Zieltabellennamen umwandeln


        odicTrigCounterTmp = OrderedDict()
        for k,v in odicTrigCounter.items():
            # ------------------------
            # SONDERFALL
            # Dataset herausnehmen -> das ist kein Datensatz
            # ------------------------
            if k != "dataset":
                odicTrigCounterTmp[self.__dic_dicCsv2Table[sWfKuerzel][k][0]] = v

        odicTrigCounter = odicTrigCounterTmp

        # Description in in Ingestion-Tabelle eintragen
        pv("* Erweitere Eintrag in Ingestiontabelle um Log")
        try:

            # Bezeichnung lang
            sName = self.getOsUserLoginName()
            sDatum = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sDatenTyp = str(sWfKuerzel)
            sSrcFileName = os.path.basename(file)
            sWarnungen = ""
            for sWarn in lstWarn:
                sWarnungen += sWarn+"\n"
            sBezeichnungLang = \
                "Datum: " + sDatum +"\n" + \
                "Benutzer: " + sName + "\n" + \
                "OS: " + str(platform.system()) + " "+str(platform.release()) + "\n" + \
                "Host: " + str(platform.node()) +"\n" + \
                "Datei: " + sSrcFileName + "\n" + \
                "Daten: " + sWfName + "\n" + \
                "Zeilen: " + str(iZeilenGesamt) + "\n" + \
                "Erzeugte Datensätze in DB: "
            for k,v in odicTrigCounter.items():
                if v > 0:
                    sBezeichnungLang += k+"("+str(v)+") "
            sBezeichnungLang = sBezeichnungLang[:-1]
            sBezeichnungLang += "\n"
            sBezeichnungLang += "Warnungen: "+str(len(lstWarn)) + "\n"
            if len(lstWarn) > 0:
                sBezeichnungLang += "Warnmeldungen:\n"+ sWarnungen + "\n"

            # Bezeichnung kurz
            sBezeichnungKurz = \
                "Datei:" + sSrcFileName + "," + \
                "Zeilen:" + str(iZeilenGesamt) + "," + \
                "Warnungen:" + str(len(lstWarn))

            # Komanndo
            sSqlCmd = "UPDATE " + self.__model.db.getDbSchema() + ".ingest set description = %s, log = %s where id = %s;"
            cursor.execute(sSqlCmd, (sBezeichnungKurz, sBezeichnungLang, iIngestId))
            sSqlQuery = cursor.query.decode("utf-8")
            pd("Info: "+sBezeichnungKurz)

        except Exception as ex:
            sFehler += "Fehler beim Eintragen Log in die Ingestion-Tabelle: " + str(ex)
            bFehler = True

        # --- DB-TRANSAKTION
        # Fehler?
        if bFehler:
            # Fehler
            pn("Fehler aufgetreten")
            conn.rollback()
            pn(sFehler)
            pn("DB-Transaktion wird nicht durchgefuehrt")
            pd("Fehler wurde ausgeloest in Programmzeile: " + str(iZeileCode))
        else:
            # Alles OK
            pn("Keine Fehler aufgetreten")
            # Warnungen ausgeben
            if lstWarn != []:
                pn("Warnungen aufgetreten: "+str(len(lstWarn)))
                for sWarn in lstWarn:
                    pn(" "+sWarn)
            # Info
            sCountInfo = ""
            for k, v in odicTrigCounter.items():
                sCountInfo += k + " " + str(v) + "\n"
            sCountInfo = sCountInfo[:-1]
            if not self.__model.bDry:
                conn.commit()
                pn("DB-Transaktion wurde durchgefuehrt")
                pn("Die Ingest-ID lautet: "+str(iIngestId))
                pn("Es wurden folgende Datensaetze erzeugt:")
            else:
                pn("<Dry Run> aktiviert")
                pn("DB-Transaktion wird nicht durchgefuehrt")
                conn.rollback()
                pn("Es waeren folgende Datensaetze erzeugt worden:")
            pn(sCountInfo)

            # Info zur Dauer
            try:
                iSekTotal = time.time() - iZeitStart
                iStd = int(iSekTotal // 3600)
                iMin = int((iSekTotal % 3600) // 60)
                iSek = int(iSekTotal % 60)
                pn("Dauer: " + str(iStd) + " Stunden, " + str(iMin) + " Minuten, " + str(iSek) + " Sekunden")
                pn("Anzahl DB-Zugriffe: "+str(iCountDbAktionen))
                pn("Dauer pro DB-Zugriff: "+ str(round((iSekTotal/iCountDbAktionen*1000),2))+ " Millisekunden")
            except:
                pass

        # DB-Verbindung schliessen
        cursor.close()
        conn.close()

        return (not bFehler, odicTrigCounter, iIngestId, lstWarn, sFehler)

    # Template Arktis
    def exportTemplate(self, file, sWfKuerzel):

        sWfName = self.getWfNameZuKuerzel(sWfKuerzel) # Hole Namen zu Wf-Kuerzel

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pn("* Erzeuge Excel-Template")
        pn("Ausschnitt: " + str(sWfName))
        pn("Datei: " + str(file))

        try:
            # Excel-Workbook
            excelWorkbook = xlsxwriter.Workbook(file)

            # Excel-Sheets
            sSheetKeyName = 'lookup' # Lookup
            sSheetDatenName = sWfName.lower() # Daten
            excelSheetDaten = excelWorkbook.add_worksheet(sSheetDatenName)
            excelSheetKeys = excelWorkbook.add_worksheet(sSheetKeyName)

            # Freezer
            excelSheetDaten.freeze_panes(1, 0)
            #excelSheetKeys.freeze_panes(1, 0)

            # Format: Farben
            lstFarben = ['#FFE5CC','#FFCCCC','#FFFFCC','#CCFFCC','#CCE5FF']

            # Maximal mögliche Zeile (Tweak, da kein Bereiche einer "ganzen Spalte" angegeben werden kann)
            iMaxZeile = 1048575 # Max 1048575

            # Erzeuge Lookup-Sheet
            pv("* Lookup-Sheet")
            pv("Spalte\tUeberschrift (Eintraege)")
            # Durchlaufe alle Header, die auch Lookup-Felder sind
            for iHead, sHeadName in enumerate([x for x in self.__dic_lstCsvHeader[sWfKuerzel] if x in self.__dicCsv2Lookup]):
                # Titel
                excelSheetKeys.write(0, iHead, sHeadName, excelWorkbook.add_format({'bold': True}))
                # Eintraege
                for iEintrag, data in enumerate(sorted(self.__dicCsv2Lookup[sHeadName].items())):
                    excelSheetKeys.write(iEintrag + 1, iHead, data[0])
                # Bereich in Excel definieren
                excelWorkbook.define_name(sHeadName, '=' + \
                    sSheetKeyName + "!" + \
                    xlsxwriter.utility.xl_rowcol_to_cell(1, iHead, True, True) + ":" + \
                    xlsxwriter.utility.xl_rowcol_to_cell(len(self.__dicCsv2Lookup[sHeadName]), iHead, True, True))
                # Info
                pv(str(iHead) + "\t" + sHeadName + " (" + str(len(self.__dicCsv2Lookup[sHeadName])) + ")") # Info

            # Erzeuge Daten-Sheet
            pv("* Daten-Sheet")
            pv("Spalte\tUeberschrift (Attribute)")
            # Durchlaufe alle Header
            iFarbe = 0
            for iHead, sHeadName in enumerate(self.__dic_lstCsvHeader[sWfKuerzel]):
                # Header
                    # Format ...
                    # Spalte ist Trigger -> Neue HG-Farbe
                if self.__dic_dicCsv2Trigger[sWfKuerzel][sHeadName]:
                    iFarbe = (iFarbe + 1) % len(lstFarben)
                fmt = excelWorkbook.add_format()
                fmt.set_bg_color(lstFarben[iFarbe])
                    # Obligat/Nicht-Obligat
                if self.__dicCsv2Obligat[sHeadName]:
                    fmt.set_bold() # fett
                else:
                    fmt.set_italic() # kursiv
                    excelSheetDaten.set_column(iHead, iHead, None, None, {'level': 1, 'collapsed' : True}) # Kollabierer
                    # Spalte ist Trigger -> links Rahmen
                if self.__dic_dicCsv2Trigger[sWfKuerzel][sHeadName]:
                    if sHeadName == self.__getTriggerFirstLeaf(sWfKuerzel):
                        fmt.set_left()  # Header
                        excelSheetDaten.set_column(iHead, iHead, 10,excelWorkbook.add_format({'left': True, 'left_color': "red"}))  # Rest der Spalte
                    else:
                        fmt.set_left() # Header
                        excelSheetDaten.set_column(iHead, iHead, 10, excelWorkbook.add_format({'left': True})) # Rest der Spalte
                    # Header schreiben
                excelSheetDaten.write(0, iHead, sHeadName, fmt)
                # Popup
                excelSheetDaten.write_comment(0, iHead, self.__dicCsv2Popup[sHeadName])
                # Validation
                if sHeadName in self.__dicCsv2Lookup:
                    excelSheetDaten.data_validation(1, iHead, iMaxZeile, iHead, {'validate': 'list', 'source': sHeadName})
                # Info
                pv(str(iHead)+"\t"+sHeadName)

            excelWorkbook.close()  # Datei schreiben

        except Exception as e:
            pn("Fehler:")
            pn(str(e))
            return False
        pn("OK")
        return True

    # Hole ein Ingest (Manuell)
    def getIngestFromDb(self, iIngestId, sWfKuerzel):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Ermittle ersten Trigger im Blattbereich
        sTriggerBlatt = self.__getTriggerFirstLeaf(sWfKuerzel)
        if sTriggerBlatt is None:
            pn("Fehler (Hole Ingest): Beim Ermitteln des Blattberiches im Workflow")
            return (None,None)

        sSqlCmd = ""

        try:
            # DB-Verbindung
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()

            # Schema
            sSchema = self.__model.db.getDbSchema()

            # ------------------------------------------------------------------------------------
            # Baum
            # ------------------------------------------------------------------------------------

            # Baue alle Attribute fuer Baum zusammen
            sAttributeBaum = ""
            for sCsvHead in self.__dic_lstCsvHeader[sWfKuerzel]:
                if sCsvHead == sTriggerBlatt:
                    break
                sDb = self.__dic_dicCsv2Table[sWfKuerzel][sCsvHead][0] + "." + self.__dic_dicCsv2Table[sWfKuerzel][sCsvHead][1]
                sAttributeBaum += sDb + "::text AS " + sCsvHead + ","
            sAttributeBaum += "sample.id as sample_id"

            sAttributeBaumOhneSampleId = ""
            for sCsvHead in self.__dic_lstCsvHeader[sWfKuerzel]:
                if sCsvHead == sTriggerBlatt:
                    break
                sAttributeBaumOhneSampleId += "baum."+sCsvHead + "::text,"

            # Bau Baum-Kommando zusammen
            sSqlCmdBaum = \
                "-- Baum\n" \
                "drop view if exists baum cascade;\n" \
                "create or replace temp view baum as\n" \
                "select\n" \
                "   "+ sAttributeBaum + "\n" \
                "from\n" + \
                "   "+ sSchema + ".cruise\n" \
                "join\n" \
                "   "+ sSchema + ".station\n" \
                "on\n" \
                "   "+ sSchema + ".station.cruise_id = " + sSchema + ".cruise.id\n" \
                "join\n" \
                "   " + sSchema + ".sample\n" \
                "on\n" \
                "   " + sSchema + ".sample.station_id = "+ sSchema + ".station.id\n" \
                "where\n" \
                "   " + sSchema + ".cruise.ingest_id =%s;\n"

            # ------------------------------------------------------------------------------------
            # Blaetter
            # ------------------------------------------------------------------------------------

            # Baue Arbeits-Dictionary mit allen nötigen Daten zu allen Blatt-Triggern auf
            odicTrigDat = OrderedDict()
            bTreffer = False
            for k, v in self.__dic_odicTrig2Dat[sWfKuerzel].items():
                if k == sTriggerBlatt:
                    bTreffer = True
                if bTreffer:
                    lstTrig = list()
                    for it in v:
                        if it[0:2] != "__" and it[0:2] != "--":
                            lstTrig.append((str(it), self.__dic_dicCsv2Table[sWfKuerzel][it][0], self.__dic_dicCsv2Table[sWfKuerzel][it][1]))
                    odicTrigDat[str(k)] = lstTrig

            # Baue alle Blatt-Views auf
            sSqlCmdBlaetter = ""
            iAnzahlTrigBlatt = len(odicTrigDat)
            for k1,v1 in odicTrigDat.items():
                sSqlCmdBlaetter += \
                "-- Blatt: "+k1+"\n" \
                "drop view if exists baum_"+k1+" cascade;\n" \
                "create or replace temp view baum_"+k1+" as\n" \
                "select\n" \
                + sAttributeBaumOhneSampleId +"\n" \
                "   "
                for k2,v2 in odicTrigDat.items():
                    if k1 == k2:
                        for dat in v2:
                            sSqlCmdBlaetter += dat[1]+"."+dat[2]+"::text as " + dat[0] +","
                    else:
                        for dat in v2:
                            sSqlCmdBlaetter += "Null::text as " + dat[0] +","
                sSqlCmdBlaetter = sSqlCmdBlaetter[:-1]+"\n"
                sSqlCmdBlaetter += \
                "from\n" \
                "   baum\n" \
                "join\n" \
                "   "+sSchema+"."+v1[0][1]+"\n" \
                "on\n" \
                "   "+sSchema+"."+v1[0][1]+".sample_id = baum.sample_id;\n"

            # ------------------------------------------------------------------------------------
            # Baue Blaetter mit Union zusammen
            # ------------------------------------------------------------------------------------

            sSqlCmdUnion = "-- Union\n"
            for k,v in odicTrigDat.items():
                sSqlCmdUnion += \
                    "select * from baum_"+k+"\n" \
                    "union all\n"
            sSqlCmdUnion = sSqlCmdUnion[:-10]+"\n"
            sSqlCmdUnion += "order by "
            for k, v in self.__dic_odicTrig2Dat[sWfKuerzel].items():
                sSqlCmdUnion += k+","
            sSqlCmdUnion = sSqlCmdUnion[:-1]+";"
            # ------------------------------------------------------------------------------------
            # Baue gesamtes SQL-Kommando zusammen
            # ------------------------------------------------------------------------------------

            # Baue gesamtes SQL-Kommando zusammen
            sSqlCmd = \
                sSqlCmdBaum + \
                sSqlCmdBlaetter + \
                sSqlCmdUnion

            #pd(sSqlCmd)

            # ------------------------------------------------------------------------------------
            # Starte Kommado
            # ------------------------------------------------------------------------------------

            cursor.execute(sSqlCmd, [str(iIngestId)])
            sSqlQuery = cursor.query.decode("utf-8")
            pd("SQL: "+sSqlQuery)

            # Irgendwas ist schiefgegangen
            if cursor.description is None:
                pn("Info (Hole Ingest): Es gab keinen Fehler und es kam nichts von der DB zurück ...")
                return(None, None)

            # Ergebnis
            lstHeader = [head[0] for head in cursor.description]
            lstContent = cursor.fetchall()

            # DB-Verbindung schliessen
            cursor.close()
            conn.close()
            pd("ok")

            return (lstHeader, lstContent)

        except Exception as ex:
            pn("Fehler (Hole Ingest): Beim Zugriff auf die Datenbank: " + str(ex) +", SQL-Cmd:"+str(sSqlCmd))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            iZeileCode = exc_tb.tb_lineno  # Falls ein Fehler entsteht -> Zeile
            pd("Fehler ist in aufgetreten in Zeile: "+ str(iZeileCode))

        return (None,None)

    # Hole alle Sample-Orte eines Ingest (Manuell)
    def getIngestSampleLocationsFromDb(self, iIngestId):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        try:
            # DB-Verbindung
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()

            # SQL-Command
            # Schema
            sSchema = self.__model.db.getDbSchema()


            # Manuell: Join aller benötigten Datensätze zu einer Tabelle
            sSqlCmd = '''
                SELECT DISTINCT sample.start_lon AS lon,
                sample.start_lat AS lat,
                cruise.name as cruise,
                sample.name as sample,
                station.name as station,
                dataset.name as dataset FROM
                (((((''' \
                      +sSchema+".population " \
                "JOIN "+sSchema+".taxon ON "+sSchema+".population.taxon_id = "+sSchema+".taxon.id) " \
                "JOIN "+sSchema+".sample ON "+sSchema+".population.sample_id = "+sSchema+".sample.id) " \
                "JOIN "+sSchema+".station ON "+sSchema+".sample.station_id = "+sSchema+".station.id) " \
                "JOIN "+sSchema+".cruise ON "+sSchema+".station.cruise_id = "+sSchema+".cruise.id) " \
                "JOIN "+sSchema+".dataset ON "+sSchema+".sample.dataset_id = "+sSchema+".dataset.id) " \
                "WHERE "+sSchema+".population.ingest_id=%s;"

            cursor.execute(sSqlCmd, [str(iIngestId)])
            sSqlQuery = cursor.query.decode("utf-8")
            pd("SQL: " + sSqlQuery)

            # Ergebnis
            lstHeader = [head[0] for head in cursor.description]
            lstContent = cursor.fetchall()

            # DB-Verbindung schliessen
            cursor.close()
            conn.close()
            pd("ok")

            return (lstHeader, lstContent)

        except Exception as ex:
            pn("Fehler (Hole Sample-Orte Ingest Arktis): Beim Zugriff auf die Datenbank: " + str(ex))

        return (None, None)

    # Lösche ein gesamtes Ingest (Manuell)
    def delIngestInDb(self, iIngestId):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        try:
            # DB-Verbindung
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()

            dicErg = OrderedDict()

            # Manuell: Korrekte Reihenfolge der Löschungen
                # Autopsy
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".autopsy auto where auto.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["autopsy"] = cursor.rowcount
                # Sediment
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".sediment sedi where sedi.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["sediment"] = cursor.rowcount
                # Sieveanalysis
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".sieveanalysis sieve where sieve.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["sieveanalysis"] = cursor.rowcount
                # Population
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".population pop where pop.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["population"] = cursor.rowcount
                # Sample
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".sample smp where smp.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["sample"] = cursor.rowcount
                # Station
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".station st where st.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["station"] = cursor.rowcount
                # Cruise
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".cruise cr where cr.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["cruise"] = cursor.rowcount
                # Ingest
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".ingest ing where ing.id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            if cursor.rowcount > 0:
                dicErg["ingest"] = cursor.rowcount

            if not self.__model.bDry:
                conn.commit()
                pn("Loeschung wurde durchgefuehrt")
                pn("Folgende Datensaetze sind geloescht worden")
            else:
                pn("<Dry Run> aktiviert")
                pn("Nichts wurde geloescht")
                pn("Folgende Datensaetze waeren geloescht worden")
                conn.rollback()

            # DB-Verbindung schliessen
            cursor.close()
            conn.close()
            pd("ok")

            return (dicErg, None)

        except Exception as ex:
            pn("Fehler (Loesche Ingest Arktis): Beim Zugriff auf die Datenbank: " + str(ex))
            return (None, str(ex))

        return (None, None)

    # Hole das Workflowkuerzel zu einem Ingest
    def getWfKuerzelZuIngestAusDb(self, iIngestId):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        sWfKuerzel = None

        sSchema = self.__model.db.getDbSchema()

        try:
            # DB-Verbindung
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()

            # Kommando
            sSqlCmd = "select workflow from "+sSchema+".ingest where id = %s"
            cursor.execute(sSqlCmd, [str(iIngestId)])

            # Ergebnis
            lstContent = cursor.fetchall()
            sWfKuerzel = lstContent[0][0]


        except Exception as ex:
            pn("Fehler (Ermittlung Workflow-Kuerzel): Beim Zugriff auf die Datenbank: " + str(ex))

        # DB-Verbindung schliessen
        cursor.close()
        conn.close()
        pd("ok")

        return sWfKuerzel

