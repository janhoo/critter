# coding=utf-8

try:
    import os, csv, psycopg2, xlsxwriter, getpass, platform, datetime
    from collections import Counter, OrderedDict
    from helper.printtools import SmartPrint
    from helper.dbtools import DbTools
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren")
    
"""
-----------------------------------------------------------------------
Workflows (Zugriff RW auf Model)
-----------------------------------------------------------------------

* Info zu Workflow
Algorithmus
- Workflow ist CSV-Zentriert
- Die CSV wird von links nach rechts durchlaufgen
- Ein Trigger definiert den eintrag in eine Tabelle
- Bis zum nächsten Trigger werden die nötigen Werte eingelesen
- CSV-Felder werden nur neu eingelesen, wenn sich der Trigger verändert hat 
- Hat sich ein Triggerfeld verändert müssen alle folgenden Felder neu eingelesen werden 
- Die Triggerfelder sind bezüglich ihres Sichhtbarkeitsbereiches (links hat Priorität vor rechts) einmalig
Definitionsdatei
- Spalten: 1 Csv-Name, Eintrag von 1 in Zieltabelle/Attribut eintragen, Vor Eintrag von 1 den Wert auflösen via Lookup, Trigger(ja/nein)  
- Csv-Typen: Name (normal), --Name (nicht einlesen, sondern vorherigen Wert neu benutzen), __Name (nicht einlesen, sondern letzten Rückgabewert eines Triggers benutzen)
"""

class Workflows:

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
        self.__lstCsvHeader = None
            # Csv -> Tabelle/Attribut
        self.__dicCsv2Table = None
            # Csv-Header-> LookUpTable (Name -> Id)
        self.__dicCsv2Lookup = None
            # Csv-Header-> LookUpTable Reverse (~Original) (Id -> Name)
        self.__dicCsv2LookupReverse = None
            # Csv -> Pop-Up-Help
        self.__dicCsv2Popup = None
            # WF-Nordsee: CSV-Header -> Obligat
        self.__dicCsv2Obligat = None
            # Csv-Header -> Trigger
        self.__dicCsv2Trigger = None
            # Triger -> Trigger-Daten
        self.__dicTrig2Dat = None
            # Workflowmodell
        self.bOkWorkflowModell = False # Ok
        self.__lstWorkflowModell = self.createWorkflowModell("arktis.wf") # Erzeugen

    # Erzeuge Workflowmodell
    def createWorkflowModell(self, sDatei):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        sDateiWf = os.path.dirname(os.path.realpath(__file__))+"/"+sDatei

        pd("* Erzeuge Workflowmodel")
        pd("Datei: "+sDateiWf)
        lstWfm = list() # Aufbau: In(Csv,Return), DB-Eintrag(Tabelle,Attr), LookUp(Tabelle,Attr-Name,Attr-Id), Trigger

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
                        sTrigger = lstZeile[6]
                        # Bilde Einheiten
                            # Zieleintrag in DB
                        dbEintrag = (sDbTab,sDbAttr)
                            # Lookup
                        lookUp = None
                        if sLookUpTab != "" and sLookUpAttr != "" and sLookUpId != "":
                            lookUp = (sLookUpTab,sLookUpAttr,sLookUpId)
                            # Trigger
                        if sTrigger.lower() in ("true", "ja", "yes", "j", "y"):
                            bTrigger = True
                        else:
                            bTrigger = False
                        # Baue WorkflowModell auf
                        lstWfm.append((sCsvName,dbEintrag,lookUp,bTrigger))
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

        pv("* Initialisiere Workflows")
        sInfo = "Verbinde mit Server...\n"
        iMax = 9
        pnProgress(1, iMax, iMax, guiText=sInfo + " überprüfe Verbindung", abs=False, cli=False)
        bOkConnection = self.__model.db.checkConnection()
        pnProgress(2, iMax, iMax, guiText=sInfo + "überprüfe Header", abs=False, cli=False)
        bOkCsv = self.__buildCsvHeader()
        pnProgress(3, iMax, iMax, guiText=sInfo + "hole Tabellen", abs=False, cli=False)
        bOkTable = self.__buildIn2Table()
        pnProgress(4, iMax, iMax, text=sInfo + "erzeuge Lookup-Tabellen", abs=False, cli=False)
        bOkLookup = self.__buildCsv2Lookup()
        pnProgress(5, iMax, iMax, guiText=sInfo + "hole Popuphilfen", abs=False, cli=False)
        bOkPopup = self.__buildCsv2Popup()
        pnProgress(6, iMax, iMax, guiText=sInfo + "lade Obligatinfos", abs=False, cli=False)
        bOkObligate = self.__buildCvs2Obligat()
        pnProgress(7, iMax, iMax, guiText=sInfo + "lade Trigger", abs=False, cli=False)
        bOkTrigger = self.__buildCvs2Trigger()
        pnProgress(8, iMax, iMax, guiText=sInfo + "erzeuge Triggerinformationen", abs=False, cli=False)
        bOkTrigDat = self.__buildTrig2Dat()

        # Gab es Fehler?
        self.__bReady = self.bOkWorkflowModell and bOkConnection and bOkPopup and bOkObligate and bOkCsv and bOkTable and bOkTrigger and bOkTrigDat and bOkLookup

        # Info
        pv("- WF-Modell:       " + ("ok" if self.bOkWorkflowModell == True else "Fehler"))
        pv("- DB-Verbindung:   " + ("ok" if bOkConnection == True else "Fehler"))
        pv("- CSV-Header:      " + ("ok" if bOkCsv == True else "Fehler"))
        pv("- Tab/Attr:        " + ("ok" if bOkTable == True else "Fehler"))
        pv("- Lookup:          " + ("ok" if bOkLookup == True else "Fehler"))
        pv("- Trigger:         " + ("ok" if bOkTrigger == True else "Fehler"))
        pv("- Trigger2Daten:   " + ("ok" if bOkTrigDat == True else "Fehler"))
        pv("- Hilfetexte:      " + ("ok" if bOkPopup == True else "Fehler"))
        pv("- Obligat:         " + ("ok" if bOkObligate == True else "Fehler"))
        if self.__bReady == False:
            pn("Fehler: Workflows sind nicht funktionsfaehig ")
        return self.__bReady

    # Informationen
    def info(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Header
        pn("Csv-Header: "+str(len(self.__lstCsvHeader)))
        for data in self.__lstCsvHeader:
            pv("\t"+data)

        # Tabelle/Attribut
        pn("In-Tbl/Atr: " + str(len(self.__dicCsv2Table)))
        for k,v in self.__dicCsv2Table.items():
            pv("\t"+str(k)+":"+str(v[0])+"/"+str(v[1]))

        # Lookup-Tables
        pn("Csv-Lookup: " + str(len(self.__dicCsv2Lookup)))
        for lookup in self.__dicCsv2Lookup.items():
            pv("\t"+lookup[0]+"("+str(len(lookup[1]))+")")
            for k,v in lookup[1].items():
                pd("\t\t"+str(k)+":"+str(v))

        # Trigger
        pn("Csv-Trigg:  " + str(Counter(self.__dicCsv2Trigger.values())[True]))
        for k, v in self.__dicCsv2Trigger.items():
            if v == True:
                pv("\t" + str(k))

        # Trigger-Daten
        pn("Trig-Data:  " + str(len(self.__dicTrig2Dat)))
        for k, v in self.__dicTrig2Dat.items():
            pv("\t"+k+" ("+str(len(v))+")")
            for it in v:
                pv("\t\t" + str(it))

        # Obligat
        pn("Csv-Oblig:  " + str(Counter(self.__dicCsv2Obligat.values())[True]))
        for k, v in self.__dicCsv2Obligat.items():
            if v == True:
                pv("\t" + str(k))

        # Popups
        pn("Csv-Popup:  " + str(len(self.__dicCsv2Popup)))
        for k, v in self.__dicCsv2Popup.items():
            pv("\t"+str(k)+":\""+(' '.join(v.split()))[0:30]+"...\"")
            #pd("\t"+str(k)+":\""+(' '.join(v.split()))+"\"")

        # Fingerprint
        pv("Fingerpint:\n\t[" + self.getUserFingerprint() + "]")

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
        for zeile in self.__lstWorkflowModell:
            # CSV-Table
            try:
                sTab = zeile[1][0]
                if sTab not in lst:
                    lst.append(sTab)
            except:
                pass
            # Lookup
            try:
                lookup = zeile[2]
                if lookup is not None:
                    sTab = zeile[2][0]
                    if sTab not in lst:
                        lst.append(sTab)
            except:
                pass
        return lst

    # Hole Kopie CSV-Header
    def getCsvHeaderCopy(self):
        return self.__lstCsvHeader.copy()

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
                    if col in dicId2PErson:
                        lstContent[iRow][iCol] = dicId2PErson[col]

                # -----------------------------------------------------------------

        # Fortschritt aus
        self.__model.observer.hideProgress()

        return (lstHeader, lstContent)

    # Ingest-Tabellendaten für leserliche Ausgabe verändern
    def tweakIngestDataForHumanOutput(self, lstHeader, lstContent):
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

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

    # Erstelle Liste: Csv-Header
    def __buildCsvHeader(self):
        pd = self.__smartprint.debug
        sModulname = "Hole Namen der CSV-Header"
        pd("* " + sModulname)
        self.__lstCsvHeader = []
        for data in self.__lstWorkflowModell:
            if data[0][0:2] != "__" and data[0][0:2] != "--":  # Trigger-Return-/Zweitbenutzungswerte rausfiltern "__Name,--Name"
                pd(data[0])
                try:
                    self.__lstCsvHeader.append(data[0])
                except:
                    return False
        return True

    # Erstelle Liste: Trigger-Eintraege
    def __buildTrig2Dat(self):
        pd = self.__smartprint.debug
        sModulname = "Aufbau Trigger-Daten"
        pd("* " + sModulname)
        self.__dicTrig2Dat = {}
        trig = None
        for data in self.__lstWorkflowModell:
            head = data[0]
            if head in self.__dicCsv2Trigger and self.__dicCsv2Trigger[head]:
                trig = head
                self.__dicTrig2Dat[trig]=[]
            if trig != None:
                self.__dicTrig2Dat[trig].append(head)
        return True

    # Erstelle Dictionary: Eingang(Csv-Header, Rückgabewerte) -> (DB-Tabelle, Attribut)
    def __buildIn2Table(self):
        pd = self.__smartprint.debug
        sModulname = "Hole Zieltabellen und Attribute"
        pd("* " + sModulname)
        self.__dicCsv2Table = dict()
        for data in self.__lstWorkflowModell:
            pd(data[0]+" -> "+data[1][0]+"."+data[1][1])
            try:
                self.__dicCsv2Table[data[0]]=(data[1][0], data[1][1])
            except:
                return False
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

                self.__dicCsv2LookupReverse[sCsvHead] = dict((id, str(name).lower()) for name, id in lstAntwort)
                self.__dicCsv2Lookup[sCsvHead] = dict((str(name).lower(), id) for name, id in lstAntwort)

                pd(sCsvHead)
                pd(" sql:               " + sSqlCmd)
                pd(" sql-len:           " + str(len(lstAntwort)))
                pd(" lookup_tb-len:     " + str(len(self.__dicCsv2Lookup[sCsvHead])))
                pd(" lookup_tb_rev-len: " + str(len(self.__dicCsv2LookupReverse[sCsvHead])))

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

            for head in self.__lstCsvHeader:
                sTab = self.__dicCsv2Table[head][0]
                sCol = self.__dicCsv2Table[head][1]
                sCommentColumn = self.__model.db.getComment(cursor,sTab,sCol)
                pd(head)
                pd(" sql:     " + cursor.query.decode("utf-8"))
                pd(" comment: " + (' '.join(sCommentColumn.split())))
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
            for head in self.__lstCsvHeader:
                sTab = self.__dicCsv2Table[head][0]
                sCol = self.__dicCsv2Table[head][1]
                bObligat = self.__model.db.getObligat(cursor,sTab,sCol)
                pd(head)
                pd(" sql:     " + cursor.query.decode("utf-8"))
                pd(" obligat: " + str(bObligat))
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
        sModulname = "Hole Triggerinfo"

        pd("* " + sModulname)
        self.__dicCsv2Trigger= dict()
        try:
            for data in self.__lstWorkflowModell:
                self.__dicCsv2Trigger[data[0]] = data[3]
                pd(data[0]+" : "+ str(data[3]))
        except:
            return False
        return True

    # Checke Header und baue Dictionary: Headername -> Headerpos
    def __buildCsv2Pos(self, file):
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
        if not self.__checkCsvHeaderKonsistenz(header, self.__lstCsvHeader):
            return None

        # Erzeuge Dict Headernamen:Headerposition
        return self.__buildDicCsvHeaderIndices(header)

    # Teste CSV-Header auf Konsistenz
    def __checkCsvHeaderKonsistenz(self, lstHeader, lstNeededHeader):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        pv("* Check CSV-Datei")

        pv(str(len(lstHeader)))
        pv(str(len(lstNeededHeader)))

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

    # Ingest Arktis
    def ingestArktis(self, file):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        pn("* Starte Workflow: Arktisdaten")
        pn("CSV-Datei: "+str(file))

        # Check CSV und erzeuge Dictionary Headername 2 Position
        dicCvs2Pos = self.__buildCsv2Pos(file)
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
        for sHeadName in self.__lstCsvHeader:
            dicAktZeile[sHeadName] = None
            # Letzte vollstaendige Zeile
        dicLetzteZeile = dict()
        for sHeadName in self.__lstCsvHeader:
            dicLetzteZeile[sHeadName] = None
            # Trigger
        odicTrig = OrderedDict()
        for sHeadName in self.__lstCsvHeader:
            if self.__dicCsv2Trigger[sHeadName]:
                odicTrig[sHeadName] = False
            # Trigger Rueckgabewerte
        dicTrigRet = dict()
        for sHeadName in self.__lstCsvHeader:
            dicTrigRet[sHeadName] = None
            # Triggerfeld ist einmalig im Sichtbarkeitsbereich des Papa
        odicTriqUniq = OrderedDict()
        for sHeadName in self.__lstCsvHeader:
             if self.__dicCsv2Trigger[sHeadName]:
                odicTriqUniq[sHeadName] = []
            # Zähler für Erzeugte Datensaetze (~Trigger)
        odicTrigCounter = OrderedDict()
        for k in odicTrig:
            odicTrigCounter[k] = 0
            # Fehler
        bFehler = False
        sFehler = ""
            # Warnungen
        lstWarn = []

        # Eintrag in Ingestion-Tabelle
        try:
            sSqlCmd = "INSERT INTO " + self.__model.db.getDbSchema() + ".ingest (name, created_on, description) VALUES (%s,%s,%s) returning id;"
            sName = self.getOsUserLoginName()
            sDatum = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sBezeichnung = "Zeilen:"+str(iZeilenGesamt)+", Datei:"+os.path.basename(file)+", "+self.getOsInfos()
            cursor.execute(sSqlCmd, (sName,sDatum,sBezeichnung))
            iIngestId = cursor.fetchone()[0]  # Antwort
            sSqlQuery = cursor.query.decode("utf-8")
        except Exception as ex:
            sFehler = "Fehler beim Eintragen in die Ingestion-Tabelle: "+str(ex)
            pn(sFehler)
            # Progressbar aus
            if self.__model is not None and self.__model.observer is not None:
                self.__model.observer.hideProgress()
            return (False, 0, None, None, sFehler)

        pv("* Ingest Fingerprint\n"+self.getUserFingerprint())
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
                for lstZeile in csvReader:
                    iZeile = csvReader.line_num  # Aktuelle Zeile

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

                        bRefresh = False
                        sInfoCsvDebug = ""
                        sTrigName = None # Workaround: Muss für Fehlerbehandlung hier schon definiert werden
                        # Durchlaufe Header-Namen in korrekter Reihenfolge
                        for sHeadName in self.__lstCsvHeader:

                            # A) Refresh im vorherigen Durchlauf eingetreten?
                            if bRefresh == True:
                                # *) Loesche (alle folgenden) TriggerUniq-Feld(er)
                                if sHeadName in odicTriqUniq:
                                    odicTriqUniq[sHeadName] = []
                            # Csv-Head-Inhalt
                            sHeadInhalt = lstZeile[dicCvs2Pos[sHeadName]] # aktuell
                            sHeadInhaltLast = dicLetzteZeile[sHeadName] # letzter

                            # B) Ist Header ein Trigger-Feld und hat sich Inhalt zur vorherigen Zeile veraendert?
                            if sHeadName in odicTrig and (sHeadInhaltLast is None or (sHeadInhaltLast != sHeadInhalt and sHeadInhalt != "")):
                                # *) Nachtest: Ist Header ein Lookup -> dann Löse den Inhalt auf und teste nochmal ob sich was verändert hat
                                # ---------------------------------------------------------
                                # Sonderfall: Taxon ist Trigger und Lookup und muss sich verändern
                                # ---------------------------------------------------------
                                if sHeadName in self.__dicCsv2Lookup and \
                                    sHeadInhalt.lower() in self.__dicCsv2Lookup[sHeadName] and \
                                    self.__dicCsv2Lookup[sHeadName][sHeadInhalt.lower()] == sHeadInhaltLast and \
                                        sHeadName != "taxon_aid":
                                    pass # Lookupauflösung hat doch keine Veraenderung ergeben
                                # ---------------------------------------------------------
                                else:
                                    # *) Refresh setzen
                                    bRefresh = True
                                    # *) Trigger auf Einmaligkeit in Sichbarkeitsbereich checken
                                    if sHeadInhalt in odicTriqUniq[sHeadName]:
                                        # ---------------------------------------------------------
                                        # Sonderfall: Taxon -> Einmaligkeit ergibt nur eine Warnung
                                        # ---------------------------------------------------------
                                        if sHeadName == "taxon_aid":
                                            sWarn = "Zeile "+str(iZeile)+": Taxon-AphiaID nicht einmalig in Sample: "+sHeadInhalt
                                            lstWarn.append(sWarn)
                                        # ---------------------------------------------------------
                                        else:
                                            raise NameError("Verstoss gegen Einmaligkeit in Sichtbarkeitsbereich: Attribut=\""+sHeadName+ "\", Wert=\""+sHeadInhalt+"\"\n")
                                    else:
                                        odicTriqUniq[sHeadName].append(sHeadInhalt) # *) Trigger-UniqListe erweitern

                            # C) Refresh in diesem oder im vorherigen Durchlauf eingetreten?
                            if bRefresh:
                                # *) setze (alle folgenden) Triggerfeld(er)
                                if sHeadName in odicTrig:
                                    odicTrig[sHeadName] = True
                                # *) alle (folgenden) CSV-Felder neu einlesen
                                # Lookup
                                if sHeadInhalt != "" and sHeadName in self.__dicCsv2Lookup:
                                    try:
                                        dicAktZeile[sHeadName] = self.__dicCsv2Lookup[sHeadName][sHeadInhalt.lower()]
                                    except Exception as ex:
                                        raise NameError("Eintrag nicht in Lookup-Table gefunden: Attribut=\"" + sHeadName + "\", Wert=\"" + sHeadInhalt + "\"\n")
                                else:
                                    dicAktZeile[sHeadName] = sHeadInhalt # direkt
                            # Debug-Info
                            sInfoCsvDebug += sHeadName+"("+ ("T" if self.__dicCsv2Trigger[sHeadName] else "") + ("L" if sHeadName in self.__dicCsv2Lookup else "") +("R" if bRefresh else "")+")="+(("\"" + sHeadInhalt + "\"") if sHeadInhalt !="" else "-")+" "

                        # -----------------------------------------------------------------

                        # Kopiere aktuelle Zeile in alte Zeile
                        for sHead,sInhalt in dicAktZeile.items():
                            dicLetzteZeile[sHead] = sInhalt

                        # DB-Eintraege
                        sInfoSqlVerbose = ""
                        sInfoSqlDebug = ""
                        for sTrigName, bTrig in odicTrig.items(): # Alle Trigger durchlaufen
                            if bTrig: # Ist Trigger aktiviert?

                                odicTrigCounter[sTrigName] += 1 # Counter: Gedrückte Trigger -> ~ Einträge in DB

                                # -----------------------------------------------------------------
                                # Sonderfälle abfangen (evtl. SQL-Befehle manuell erzeugen)
                                # -----------------------------------------------------------------

                                # Dataset
                                if sTrigName == "dataset":
                                    iIdDataset = dicAktZeile["dataset"]
                                    sInfoSqlVerbose += "dataset(" + str(iIdDataset)+ ") "
                                    dicTrigRet[sTrigName] = iIdDataset

                                # ---

                                else:

                                    # -------------------------------------------------------------
                                    # Automatisierter Bau: Sql-Commando
                                    # Benutze nur Attribute, die auch einen Wert in der Excel-Tabelle haben
                                    # -------------------------------------------------------------

                                    sSqlCmdTeil1 = ""
                                    sSqlCmdTeil2 = ""
                                    sSqlVal = []
                                    # Durchlaufe Header des aktuellen Triggers
                                    for sHead in sorted(self.__dicTrig2Dat[sTrigName]):
                                        # a) Bau: Variablen-Liste
                                        if sHead[0:2] == "__":
                                            # Rückgabewert von anderem Trigger
                                            sSqlVal.append(dicTrigRet[sHead[2:]])
                                        elif sHead[0:2] == "--":
                                            # Ein bereits eingelesener Wert aus CSV
                                            if dicAktZeile[sHead[2:]] != "":
                                                sSqlVal.append(dicAktZeile[sHead[2:]])
                                        else:
                                            # Wert aus CSV (nur wenn Wert!="")
                                            if dicAktZeile[sHead] != "":
                                                sSqlVal.append(dicAktZeile[sHead])
                                        # b) Bau: Sql-Cmd-Teile (nur wenn Wert==Rückgabewert/Zweitbenutzung oder Wert!=Rückgabewert/Zweitbenutzun und Wert!="")
                                        if sHead[0:2] == "__" or sHead[0:2] == "--" or (sHead[0:2] != "__" and sHead[0:2] != "--" and dicAktZeile[sHead] != ""):
                                            sSqlCmdTeil1 += self.__dicCsv2Table[sHead][1] + ","
                                            sSqlCmdTeil2 += "%s,"
                                    sSqlVal.append(str(iIngestId)) # IngestID
                                    # Sql-Cmd zusammenbauen
                                    sSqlCmd = "INSERT INTO " + self.__model.db.getDbSchema() + "." + self.__dicCsv2Table[sTrigName][0] + \
                                              "("+sSqlCmdTeil1+"ingest_id) VALUES ("+sSqlCmdTeil2+"%s) returning id;"
                                    # Führe Sql-Cmd aus
                                    cursor.execute(sSqlCmd, sSqlVal)
                                    sSqlQuery = cursor.query.decode("utf-8")
                                    iId = cursor.fetchone()[0] # Antwort
                                    dicTrigRet[sTrigName]= iId
                                    sInfoSqlVerbose += "+"+self.__dicCsv2Table[sTrigName][0]+"("+str(iId)+") "
                                    sInfoSqlDebug += "\tSql:   "+sSqlQuery+"\n"

                                    # ---

                        # -----------------------------------------------------------------

                        # Info
                            # Normal
                        pnProgress(iZeile, iZeilenGesamt, 50, guiText="Bearbeite Zeile ", abs=True, cli=True)  # Fortschritt
                            # Verbose
                        pv(str(iZeile)+" "+sInfoSqlVerbose)
                            # Debug
                        pd("\tcsv:   "+sInfoCsvDebug)
                        sInfoDebug = "\tlast:  "
                        for sHeadName in self.__lstCsvHeader:
                            sInfoDebug += sHeadName+"=\""+str(dicLetzteZeile[sHeadName])+"\" "
                        pd(sInfoDebug)
                        sInfoDebug = "\takt:   "
                        for sHeadName in self.__lstCsvHeader:
                            sInfoDebug += sHeadName + "=\"" + str(dicAktZeile[sHeadName])+"\" "
                        pd(sInfoDebug)
                        sInfoDebug = "\ttrig:  "
                        for sTrigName, bTrig in odicTrig.items():
                            sInfoDebug += (sTrigName if bTrig else "-")+" "
                        pd(sInfoDebug)
                        sInfoDebug = "\tuniq:  "
                        for sTrigUniqName, lstUniqListe in odicTriqUniq.items():
                            sInfoDebug += (sTrigUniqName+"("+str(lstUniqListe)+")" if len(lstUniqListe) > 0 else "-") + " "
                        pd(sInfoDebug)
                        pd(sInfoSqlDebug)

        except Exception as ex:
            sFehler += "Fehler in Zeile #" + str(iZeile) + "\n"
            sFehler += '|'.join(lstZeile)+"\n"
            sFehler += "Trigger = "+ str(sTrigName) + "\n"
            sFehler += str(ex)
            bFehler = True

        # Progressbar aus
        if self.__model is not None and self.__model.observer is not None:
            self.__model.observer.hideProgress()

        # --- DB-TRANSAKTION
        # Fehler?
        if bFehler:
            # Fehler
            pn("Fehler aufgetreten")
            conn.rollback()
            pn(sFehler)
            pn("DB-Transaktion wird nicht durchgefuehrt")
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

        # DB-Verbindung schliessen
        cursor.close()
        conn.close()

        return (not bFehler, odicTrigCounter, iIngestId, lstWarn, sFehler)

    # Template Arktis
    def templateArktis(self, file):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pn("* Erzeuge Excel-Template: Arktisdaten")
        pn("Datei: " + str(file))

        try:
            # Excel-Workbook
            excelWorkbook = xlsxwriter.Workbook(file)

            # Excel-Sheets
            sSheetKeyName = 'lookup' # Lookup
            sSheetDatenName = 'arktis' # Daten
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
            for iHead, sHeadName in enumerate([x for x in self.__lstCsvHeader if x in self.__dicCsv2Lookup]):
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
            for iHead, sHeadName in enumerate(self.__lstCsvHeader):
                # Header
                    # Format ...
                    # Spalte ist Trigger -> Neue HG-Farbe
                if self.__dicCsv2Trigger[sHeadName]:
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
                if self.__dicCsv2Trigger[sHeadName]:
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
    def getIngestArktis(self, iIngestId):

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

                # Automatisch: Attributauswahl und -namen für die Rückgabe
            sAttributAuswahl = ""
            for sCsvHead in self.__lstCsvHeader:
                sDb = self.__dicCsv2Table[sCsvHead][0] + "." + self.__dicCsv2Table[sCsvHead][1]
                sAttributAuswahl += sDb + " AS " + sCsvHead + ","
            sAttributAuswahl = sAttributAuswahl[:-1]

                # Manuell: Join aller benötigten Datensätze zu einer Tabelle
            sSqlCmd = \
                "SELECT " + sAttributAuswahl + " FROM " \
                "(((((" \
                ""+sSchema+".population " \
                "JOIN "+sSchema+".taxon ON "+sSchema+".population.taxon_id = "+sSchema+".taxon.id) " \
                "JOIN "+sSchema+".sample ON "+sSchema+".population.sample_id = "+sSchema+".sample.id) " \
                "JOIN "+sSchema+".station ON "+sSchema+".sample.station_id = "+sSchema+".station.id) " \
                "JOIN "+sSchema+".cruise ON "+sSchema+".station.cruise_id = "+sSchema+".cruise.id) " \
                "JOIN "+sSchema+".dataset ON "+sSchema+".sample.dataset_id = "+sSchema+".dataset.id) " \
                "WHERE "+sSchema+".population.ingest_id=%s " \
                "ORDER BY dataset.name, cruise.name, station.name, sample.name, taxon.aid;"

            cursor.execute(sSqlCmd, [str(iIngestId)])
            sSqlQuery = cursor.query.decode("utf-8")
            pd("SQL: "+sSqlQuery)

            # Ergebnis
            lstHeader = [head[0] for head in cursor.description]
            lstContent = cursor.fetchall()

            # DB-Verbindung schliessen
            cursor.close()
            conn.close()
            pd("ok")

            return (lstHeader, lstContent)

        except Exception as ex:
            pn("Fehler (Hole Ingest Arktis): Beim Zugriff auf die Datenbank: " + str(ex))

        return (None,None)

    # Hole alle Sample-Orte eines Ingest (Manuell)
    def getIngestArktisSampleLocations(self, iIngestId):

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
            sSqlCmd = \
                "SELECT DISTINCT sample.start_lon AS lon, sample.start_lat AS lat, cruise.name as cruise, sample.name as sample, station.name as station, dataset.name as dataset FROM"  \
                "(((((" \
                ""+sSchema+".population " \
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
    def delIngestArktis(self, iIngestId):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        try:
            # DB-Verbindung
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()

            dicErg = OrderedDict()

            # Manuell: Korrekte Reihenfolge der Löschungen
                # Population
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".population pop where pop.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            dicErg["population"] = cursor.rowcount
                # Sample
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".sample smp where smp.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            dicErg["sample"] = cursor.rowcount
                # Station
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".station st where st.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            dicErg["station"] = cursor.rowcount
                # Cruise
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".cruise cr where cr.ingest_id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
            dicErg["cruise"] = cursor.rowcount
                # Ingest
            sSqlCmd = "delete from " + self.__model.db.getDbSchema() + ".ingest ing where ing.id=%s;"
            cursor.execute(sSqlCmd, [str(iIngestId)])
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

    # ---------------------------

    # Ingest Antarktis
    def ingestAntarktis(self, file):
        pn = self.__smartprint.normal
        pn("* Starte Workflow: Antarktisdaten")
        pn("Csv-Datei: " + str(file))
        pn("...")

    # Template Antarktis
    def templateAntarktis(self, file):
        pn = self.__smartprint.normal
        pn("* Erzeuge Excel-Template: Antarktisdaten")
        pn("Datei: " + str(file))
        pn("...")

    # ---------------------------

    # Ingest Nordsee
    def ingestNordsee(self, file):
        pn = self.__smartprint.normal
        pn("* Starte Workflow: Nordseedaten")
        pn("Csv-Datei: " + str(file))
        pn("...")

    # Template Nordsee
    def templateNordsee(self, file):
        pn = self.__smartprint.normal
        pn("* Erzeuge Excel-Template: Nordsee")
        pn("Datei: " + str(file))
        pn("...")

    # ---------------------------

    # Test
    def test(self):
        pn = self.__smartprint.normal
        pn("* Testing area")
