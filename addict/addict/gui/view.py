try:
    import sys, os, time, psycopg2, csv, re, folium, webbrowser
    from functools import partial
    from PyQt5 import uic
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from helper.printtools import SmartPrint
    from logik.workflows import Workflows
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren.")
    quit()

# UI-Definitionen
fileHauptfenster = os.path.dirname(os.path.realpath(__file__)) + "/ressource/mainwindow.ui"
fileOptionen = os.path.dirname(os.path.realpath(__file__)) + "/ressource/options.ui"
fileProgress = os.path.dirname(os.path.realpath(__file__)) + "/ressource/progress.ui"
fileWaiting = os.path.dirname(os.path.realpath(__file__)) + "/ressource/waiting.ui"

"""
-----------------------------------------------------------------------
View (intelligent, besitzt Verwaltungslogik)
-----------------------------------------------------------------------
"""

# Hauptfenster (View)

class View(QMainWindow, uic.loadUiType(fileHauptfenster)[0]):

    # Konstruktor
    def __init__(self, model):

        # Super
        QMainWindow.__init__(self)

        # Instanzvariablen
        self.__model = model
        self.__smartprint = SmartPrint(model = model)

        # Initialisierung
        self.setupUi(self)
            # Window Icon
        self.setWindowIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/crabby.png"))
        self.guiRefeshWindowTitelDryRun()
            # Actions
        self.actionArktis.triggered.connect(self.actionArktisClicked)
        self.actionTemplateArktis.triggered.connect(self.actionTemplateArktisClicked)
        self.actionOptionen.triggered.connect(self.actionOptionenClicked)
        self.actionInfo.triggered.connect(self.actionInfoClicked)
        self.actionBeenden.triggered.connect(self.actionBeendenClicked)
            # ToolBar-Buttons
        buttonSize = QSize(48,48)
                # Ingest
        toolButtonIngest = QToolButton()
        toolButtonIngest.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/icon_input.png"))
        toolButtonIngest.setIconSize(buttonSize)
        toolButtonIngest.setToolTip("Ingest CSV-Dateien")
        toolButtonIngestMenu = QMenu()
        toolButtonIngestMenu.addAction(self.actionArktis) # Arktis
        toolButtonIngestMenu.addAction(self.actionAntarktis)  # Antarktis
        toolButtonIngestMenu.addAction(self.actionNordsee) # Nordsee
        toolButtonIngest.setMenu(toolButtonIngestMenu)
        toolButtonIngest.setPopupMode(QToolButton.InstantPopup)
        self.toolBar.addWidget(toolButtonIngest)
                # Template
        toolButtonTempl = QToolButton()
        toolButtonTempl.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/icon_excel.png"))
        toolButtonTempl.setIconSize(buttonSize)
        toolButtonTempl.setToolTip("Excel-Template exportieren")
        toolButtonTemplMenu = QMenu()
        toolButtonTemplMenu.addAction(self.actionTemplateArktis) # Arktis
        toolButtonTemplMenu.addAction(self.actionTemplateAntarktis)  # Antarktis
        toolButtonTemplMenu.addAction(self.actionTemplateNordsee)  # Nordsee
        toolButtonTempl.setMenu(toolButtonTemplMenu)
        toolButtonTempl.setPopupMode(QToolButton.InstantPopup)
        self.toolBar.addWidget(toolButtonTempl)
                # Optionen
        toolButtonOpt = QToolButton()
        toolButtonOpt.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/icon_settings.png"))
        toolButtonOpt.setIconSize(buttonSize)
        toolButtonOpt.setToolTip("Einstellungen")
        toolButtonOpt.clicked.connect(self.actionOptionenClicked)
        self.toolBar.addWidget(toolButtonOpt)
                # Beenden
        toolButtonExit = QToolButton()
        toolButtonExit.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/icon_exit.png"))
        toolButtonExit.setIconSize(buttonSize)
        toolButtonExit.setToolTip("Programm beenden")
        toolButtonExit.clicked.connect(self.actionBeendenClicked)
        self.toolBar.addWidget(toolButtonExit)

        # Andere Buttons
        self.buttonConsoleClear.clicked.connect(self.guiConsoleClear)
        self.buttonConnectionToggle.clicked.connect(self.actionVerbindungToggleClicked)
        self.buttonSqlCmd.clicked.connect(self.actionButtonSqlCmd)
        # Andere Widgets
            # Optionen
        self.diaOptionen = DialogOptionen(model)
            # Progress
        self.widgetProgress = WidgetProgress()
        self.widgetProgress.setFixedHeight(1)
            # Waiting
        self.widgetWaiting = WidgetWaiting()

        # Baue DB-Tabellenstatus-Box
            # Zusatztabellen
        self.__lstTableStatusZusatz = ["ingest"]
            # Zu entfernende Tabellen
        self.__lstTableStatusBlacklist = []
            # Zeiger auf DB-Status-Box-Elemente
        self.__dicDbTableStatusBoxWidgets = {}
            # Aufbauen
        self.buildGuiDbTableStatusBox()

        # Erzeuge Menueintraege: Neuer Datensatz
            # Zusatz Tabellen
        self.__lstMenuNeuDatensatzZusatz = []
            # Zu entfernende Tabellen
        self.__lstMenuNeuDatensatzBlacklist = ["station","population","cruise","sample"]

        # Aufbauen
        self.buildGuiMenuNeuDatensatz()

        # Groesse auf Minimum
        self.resize(self.minimumSizeHint().width(), self.sizeHint().height())

        # Etc
            # Refresh View-Widget
        self.guiRefreshAll()

    # --- Allgemein ---

    # Verbinde mit Server
    def serverConnect(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pv("* Verbindung mit Server wird hergestellt")
        if self.__model.db.sDbHost == "" or \
                        self.__model.db.sDbPort == "" or \
                        self.__model.db.sDbUser == "" or \
                        self.__model.db.sDbName == "" or \
                        self.__model.db.setDbSchema == "":
            self.popupFehler("Probleme bei Verbindung zur Datenbank", "Daten zur Verbindung mit Datenbankserver sind unvollständig.")
            return False
        if self.__model.db.sDbPw == "":
            pv("DB-Passwort fehlt -> Hole Passwort manuell")
            self.getPassword()  # Passwort manuell holen
        self.widgetProgress.setMinMax()
        self.widgetProgress.setText("Verbinde mit Server ...")
        self.centerWidget(self.widgetProgress)
        self.widgetProgress.show()
        bOk = False
        try:
            bOk = self.__model.workflows.initialisierung()
        except:
            pass
        self.widgetProgress.hide()
        if bOk:
            pn("Serververbindung steht")
        self.guiRefreshAll()
        return bOk

    # Trenne mit Server
    def serverDisconnect(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pv("* Trenne Verbindung mit Server")
        self.__model.newWorkflow()
        pn("Serververbindung getrennt")
        self.guiRefreshAll()

    # Popup: Info
    def popupInfo(self, sTitel, sText, sDetail=None):
        self.__popupGeneric(titel=" ", text=sTitel, textExtra=sText, textDetail=sDetail)

    # Popup: Fehler
    def popupFehler(self, sTitel, sText, sDetail=None):
        self.__popupGeneric(titel=" ", text=sTitel, textExtra=sText, textDetail=sDetail, icon="error")

    # Popup Generic
    def __popupGeneric(self, **kwargs):

        # Kwargs
        sTitel = None
        sText = None
        sTextInformativ = None
        sTextDetail = None
        sIcon = None
        for arg in kwargs:
            if "titel" in kwargs:
                sTitel = kwargs['titel']
            if "text" in kwargs:
                sText = kwargs['text']
            if "textExtra" in kwargs:
                sTextInformativ = kwargs['textExtra']
            if "textDetail" in kwargs:
                sTextDetail = kwargs['textDetail']
            if "icon" in kwargs:
                sIcon = kwargs['icon']

        # Icon bestimmen
        if sIcon == "info":
            icon = QMessageBox.Information
        elif sIcon == "warn":
            icon = QMessageBox.Warning
        elif sIcon == "error":
            icon = QMessageBox.Critical
        else:
            icon = QMessageBox.Information

        # Dialog zusammenbauen
        msg = QMessageBox()
        msg.setIcon(icon)
        if sTitel is not None and sTitel != "":
            msg.setWindowTitle(sTitel)
        if sText is not None and sText != "":
            msg.setText("<h3>"+sText+"</h3>")
        if sTextInformativ is not None and sTextInformativ != "":
            msg.setInformativeText(sTextInformativ)
        if sTextDetail is not None and sTextDetail != "":
            msg.setDetailedText(sTextDetail)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Popup: Info
    def popupInfoBackup(self, sTitel, sText):
        dia = QDialog()
        dia.setWindowTitle(sTitel)
        dia.setWindowModality(Qt.ApplicationModal)
        vbox = QVBoxLayout(dia)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok, Qt.Horizontal, dia)
        buttonBox.accepted.connect(dia.accept)
        #vbox.addWidget(tabelle)
        vbox.addWidget(buttonBox)
        #dia.setFixedSize(dia.sizeHint())
        dia.exec()

    # Zentriere Kindfenster zu View (oder anderem Fenster)
    def centerWidget(self, childWidget, parentWidget = None):
        if childWidget is None:
            return
        if parentWidget is None:
            parentWidget = self
        childWidget.move(parentWidget.frameGeometry().center().x() - int(childWidget.frameGeometry().width() / 2),
                 parentWidget.frameGeometry().center().y() - int(childWidget.frameGeometry().height() / 2))

    # Generisches Warte-Widget anschalten
    def popupWaitingOn(self, txt):
        self.widgetWaiting.setText(txt)
        self.centerWidget(self.widgetWaiting)
        self.widgetWaiting.show()
        self.giveQtTimeToUpdate(1000)

    # Generisches Warte-Widget ausschalten
    def popupWaitingOff(self):
        self.widgetWaiting.hide()

    # Mach dich bereit (Workflows sollen laufen)
    def readyUp(self):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose

        pv("* Teste Verbindung zum Server")
        bOk = self.__model.workflows.isReady()
        if bOk is None:
            # Serververbindung ist noch nie hergestellt worden
            bOk = self.serverConnect()
        if not bOk:
            # Serververbindung ist gestört
            pn("Serververbindung fehlgeschlagen")
            self.popupFehler("Verbindung zum Datenbankserver fehlgeschlagen", "Näheres siehe Konsolenausgabe ...")
        return bOk

    # Hole DB-Passwort manuell
    def getPassword(self):
        pw, ok = QInputDialog.getText(self, 'Serververbindung', 'Passwort:', QLineEdit.Password)
        if ok:
            self.__model.db.sDbPw = pw

    # --- GUI-Aktionen ---

    # Ingest Arktis
    def actionArktisClicked(self):
        if not self.__model.workflows.isReady():
            #self.popupInfo("Noche keine Serververbindung","Bitte erst mit dem Datenbankserver verbinden.")
            return
        csvFile = QFileDialog.getOpenFileName(self, "CSV-Datei", filter="*.csv;; *.*")[0]  # Hole CSV-Datei
        if csvFile != "":
            bOk, odicCounter, iIngestId, lstWarn, sFehler = self.__model.workflows.ingestArktis(csvFile)  # Starte Workflow
            if bOk == False:
                # Fehler
                self.popupFehler("Ingestion wurde abgebrochen", "Näheres siehe Konsolenausgabe ...", sFehler)
            else:
                # OK
                sInfo = "<b>Erzeugte Datensätze in Datenbank</b>"
                sInfo += "<ul>"
                for k, v in odicCounter.items():
                    sInfo += "<li><i>"+ k + "</i> (" + str(v) + "x)</li>"
                sInfo += "</ul>"
                if lstWarn != []:
                    sInfo += "<b>Es sind Warnungen aufgetreten</b>"
                    sInfo += "<ul><li>" + str(len(lstWarn)) + "x (siehe Konsole)</li></ul>"
                sInfo += "<b>Ingest-Identifikationsnummer</b>"
                sInfo += "<ul><li>"+str(iIngestId)+"</li></ul>"
                sWarn = ""
                for zeile in lstWarn:
                    sWarn += zeile +"\n"
                self.guiRefreshStatusTabellen()
                self.guiRefeshIngestionTabelle()
                self.popupInfo("Ingestion ist abgeschlossen", sInfo, sWarn)

    # Template Arktis
    def actionTemplateArktisClicked(self):
        if not self.__model.workflows.isReady():
            return
        excelFile = QFileDialog.getSaveFileName(self, "Speichere Excel-Datei", "template_arktis.xlsx")[0]
        if excelFile != "":
            bOk = self.__model.workflows.templateArktis(excelFile)
            if bOk == False:
                self.popupFehler("Fehler", "Es gab Probleme beim Erzeugen des Templates.\nNäheres siehe Konsolenausgabe ...")

    # Optionen
    def actionOptionenClicked(self):
        pn = self.__smartprint.normal

        # Hole Daten aus Model
            # DB
        self.diaOptionen.db_user.setText(self.__model.db.sDbUser)
        self.diaOptionen.db_pw.setText(self.__model.db.sDbPw)
        self.diaOptionen.db_host.setText(self.__model.db.sDbHost)
        self.diaOptionen.db_port.setText(self.__model.db.sDbPort)
        self.diaOptionen.db_name.setText(self.__model.db.sDbName)
        self.diaOptionen.db_schema.setText(self.__model.db.getDbSchema())
            # Geschwaetzigkeit
        self.diaOptionen.combo_verbosity.setCurrentIndex(0)
        if self.__model.bVerbose == True:
            self.diaOptionen.combo_verbosity.setCurrentIndex(1)
        if self.__model.bDebug == True:
            self.diaOptionen.combo_verbosity.setCurrentIndex(2)
            # Datensicht
        self.diaOptionen.combo_dataview_in.setCurrentIndex(0)
        if self.__model.bDataViewInHuman == True:
            self.diaOptionen.combo_dataview_in.setCurrentIndex(1)
        self.diaOptionen.combo_dataview_out.setCurrentIndex(0)
        if self.__model.bDataViewOutHuman == True:
            self.diaOptionen.combo_dataview_out.setCurrentIndex(1)
            # Logging
        self.diaOptionen.text_logging.setText(self.__model.sDateiLogging)
        self.diaOptionen.check_logging.setCheckState(2 if self.__model.bLogging == True else 0)
        self.diaOptionen.text_logging.setEnabled(self.__model.bLogging)  # Logging deaktviert -> Felder ausgrauen
        self.diaOptionen.button_loggingDatei.setEnabled(self.__model.bLogging)
            # Dry Run
        self.diaOptionen.check_dry.setCheckState(2 if self.__model.bDry == True else 0)

        # Starte Dialog
        self.centerWidget(self.diaOptionen)
        ant = self.diaOptionen.exec_()
        bPwSpeichern = self.diaOptionen.check_pwSpeichern.isChecked()

        # Aenderungen anwenden
        if ant == 1 or ant == 2:
            pn("* Wende Einstellungen an")

            # Teste, ob Workflows neu initialisiert werden muessen
            bWfRestart = False
            if self.__model.db.sDbUser != self.diaOptionen.db_user.text() or \
                            self.__model.db.sDbHost != self.diaOptionen.db_host.text() or \
                            self.__model.db.sDbPw != self.diaOptionen.db_pw.text() or \
                            self.__model.db.sDbPort != self.diaOptionen.db_port.text() or \
                            self.__model.db.sDbName != self.diaOptionen.db_name.text() or \
                            self.__model.db.getDbSchema() != self.diaOptionen.db_schema.text():
                bWfRestart = True

            # Speichere Daten in Model
                # DB
            self.__model.db.sDbUser = self.diaOptionen.db_user.text()
            self.__model.db.sDbPw = self.diaOptionen.db_pw.text()
            self.__model.db.sDbHost = self.diaOptionen.db_host.text()
            self.__model.db.sDbPort = self.diaOptionen.db_port.text()
            self.__model.db.sDbName = self.diaOptionen.db_name.text()
            self.__model.db.setDbSchema(self.diaOptionen.db_schema.text())
                # Geschwaetzigkeit
            self.__model.bVerbose = False
            self.__model.bDebug = False
            if self.diaOptionen.combo_verbosity.currentIndex() == 1:
                self.__model.bVerbose = True
            elif self.diaOptionen.combo_verbosity.currentIndex() == 2:
                self.__model.bDebug = True
                # Datensicht
            self.__model.bDataViewInHuman = False
            if self.diaOptionen.combo_dataview_in.currentIndex() == 1:
                self.__model.bDataViewInHuman = True
            self.__model.bDataViewOutHuman = False
            if self.diaOptionen.combo_dataview_out.currentIndex() == 1:
                self.__model.bDataViewOutHuman = True
                    # Logging
            self.__model.bLogging = self.diaOptionen.check_logging.isChecked()
            self.__model.sDateiLogging = self.diaOptionen.text_logging.text()
            if self.diaOptionen.text_logging.text() == "": # Keine Datei -> Logging aus
                self.__model.bLogging = False
                self.diaOptionen.text_logging.setEnabled(False)  # Felder ausgrauen
                self.diaOptionen.button_loggingDatei.setEnabled(False)
                # Dry
            self.__model.bDry = self.diaOptionen.check_dry.isChecked()

            # Speichere in Konfigurationsdatei
            if ant == 2:
                pn("* Speichere Einstellungen")
                if bPwSpeichern  == True:
                    self.__model.cfgSave()
                else:
                    pn("Passwort wird nicht mitgespeichert")
                    self.__model.cfgSave(savePw=False)

            # Dry-Run im Titel einstellen (stumpf immer)
            self.guiRefeshWindowTitelDryRun()

            # Workflows neu starten
            if bWfRestart == True:
                pn("* Workflows muessen neu initialisiert werden... ")
                self.serverDisconnect()
                bOk = self.serverConnect()
                if bOk == False:
                    self.popupFehler("Verbindungsfehler zum Datenbankserver","Einstellungen haben einen Fehler bei Verbindung mit Server bewirkt.<br>Näheres siehe Konsolenausgabe ...")

    # Info
    def actionInfoClicked(self):
        info = "<h3>"+self.__model.sInfoPrgName + " " + self.__model.sInfoPrgVersion+ " ("+ self.__model.sInfoDbSchemaVersion+ ")</h3>"
        info += self.__model.sInfoKommentar
        info += "<p align=\"right\"> Kontakt: <a href=\""+self.__model.sInfoWeb+"\">AWI|Functional Ecology|Ecosystem Functions</a><br>"
        info += self.__model.sInfoDatum + "</p>"
        QMessageBox.about(self,"Über dieses Programm", info)

    # Neuen Datensatz erzeugen
    def actionNeuerDatensatz(self, sTab):
        if self.__model.workflows.isReady():
            self.inputGeneric("Neuer Datensatz in Tabelle: " + sTab.replace("_", " ").title(), sTab)

    # Verbindung zum Server herstellen/unterbrechen
    def actionVerbindungToggleClicked(self):
        if self.__model.workflows.isReady() is not None:
            self.serverDisconnect()
        else:
            self.serverConnect()

    # SQL-Kommando abschicken
    def actionButtonSqlCmd(self):
        pn = self.__smartprint.normal

        if self.__model.workflows.isReady():
            sSqlCmd = str(self.lineSqlCmd.currentText())

            # Whitespace entfernen
            sSqlCmd = sSqlCmd.strip()

            # Nichts
            if sSqlCmd == "":
                return

            # Sicherheit
            lstBadSql = ["insert","delete","update","drop","create","grand","execute","trigger"]
            for sBad in lstBadSql:
                if sBad in sSqlCmd.lower():
                    self.popupFehler("SQL-Sicheheitsüberprüfung", "Das SQL-Kommando wurde nicht ausgeführt, da es folgenden nicht erlaubten Wortanteil enthält:<ul><li>"+sBad+"</li></ul>")
                    return

            try:
                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()

                # Popup Warten an
                self.popupWaitingOn("Hole Antwort aus Datenbank ...")

                # SQL
                cursor.execute(sSqlCmd)
                lstHeader = [head[0] for head in cursor.description]
                lstContent = cursor.fetchall()
                pn("* Fuehre SQL-Kommando aus (read only)\n"+sSqlCmd)

                # Popup Warten aus
                self.popupWaitingOff()

                # Befehl merken
                self.lineSqlCmd.clearEditText()
                if sSqlCmd != "" and self.lineSqlCmd.findText(sSqlCmd) == -1:
                    self.lineSqlCmd.addItem(sSqlCmd)

                # Ergenis anzeigen
                self.__showGenericTable(sSqlCmd, lstHeader, lstContent, save = True)

                # Rollback
                conn.rollback()

                # DB-Verbindung schliessen
                cursor.close()
                conn.close()
                return True

            except Exception as ex:

                # Popup Warten aus
                self.popupWaitingOff()
                # Popup Fehler
                sFehler = "Fehler (SQL-Kommando ausfuehren): " + str(ex)
                pn(sFehler)
                self.popupFehler("SQL-Fehlermeldung","Das SQL-Kommando hat eine Fehlermeldung beim Datenbankserver erzeugt.", str(ex))
                return False
        return True

    # Ende
    def actionBeendenClicked(self):
        self.close()
        # mb = QMessageBox.warning(
        #     self,"Programm Beenden?",
        #     "Programm wirklich beenden?",
        #     QMessageBox.Yes | QMessageBox.No)
        # if mb == QMessageBox.Yes:
        #     self.close()

    # --- GUI ---

    # Gib QT-Loop Zeit zum Widget-Update
    def giveQtTimeToUpdate(self, max=1):
        # Tweak: Häufig reicht ein Aufruf nicht zum GUI-Refresh, sondern erst 10000 ...
        for i in range(max):
            QApplication.processEvents()

    # Baue Menueeintraege: Neue Datensaetze erzeugen
    def buildGuiMenuNeuDatensatz(self):

        lstTables = self.__model.workflows.getAllUsedTableNames()

        # Zusaetzliche Tabellen hinzufuegen
        for sTab in self.__lstMenuNeuDatensatzZusatz:
            if sTab not in lstTables:
                lstTables.append(sTab)

        # Auf Blacklist befindliche Tabellen entfernen
        for sTab in self.__lstMenuNeuDatensatzBlacklist:
            if sTab in lstTables:
                lstTables.remove(sTab)

        # Erzeuge alle Menu-Einträge
        for sTabName in lstTables:
            action = QAction(sTabName.replace("_", " ").title(), self)
            #self.connect(action, SIGNAL('triggered()'), partial(self.actionNeuerDatensatz, sTabName))
            action.triggered.connect(partial(self.actionNeuerDatensatz, sTabName))
            self.menuNeuerDatensatz.addAction(action)

    # Baue DB-Status-Box auf
    def buildGuiDbTableStatusBox(self):
        grid = QGridLayout()
        grid.setSpacing(2)
        grid.setContentsMargins(0,0,0,0)
        iColMax = 4  # Anzahl der 4-Tuple-Widgets in einer Zeile
        iCol = iRow = 1

        lstTables = self.__model.workflows.getAllUsedTableNames()

        # Zusaetzliche Tabellen hinzufuegen
        for sTab in self.__lstTableStatusZusatz:
            if sTab not in lstTables:
                lstTables.append(sTab)

        # Auf Blacklist befindliche Tabellen entfernen
        for sTab in self.__lstTableStatusBlacklist:
            if sTab in lstTables:
                lstTables.remove(sTab)

        for sTabName in lstTables:
            # Label
            label = QLabel(sTabName.replace("_", " ").title())
            font = label.font()
            font.setPointSize(7)
            label.setFont(font)
            # Button
            btnOpen = QToolButton()
            btnOpen.setText("tab")
            font = btnOpen.font()
            font.setPointSize(7)
            btnOpen.setFont(font)
            btnOpen.setToolTip("Tabelle anzeigen")
            btnOpen.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btnOpen.setFixedWidth(btnOpen.minimumSizeHint().width())
            btnOpen.setFixedHeight(btnOpen.minimumSizeHint().height())
            # Button
            btnCsv = QToolButton()
            btnCsv.setText("csv")
            font = btnCsv.font()
            font.setPointSize(7)
            btnCsv.setFont(font)
            btnCsv.setToolTip("Tabelle als csv-Datei speichern")
            btnCsv.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btnCsv.setFixedWidth(btnCsv.minimumSizeHint().width())
            btnCsv.setFixedHeight(btnCsv.minimumSizeHint().height())
            # Connect
            btnOpen.clicked.connect(partial(self.tableShow, sTabName))
            btnCsv.clicked.connect(partial(self.tableSave, sTabName))
            # Ausgabefeld
            ausgabeFeld = QLineEdit()
            ausgabeFeld.setEnabled(False)
            font = ausgabeFeld.font()
            font.setPointSize(9)
            ausgabeFeld.setFont(font)
            #ausgabeFeld.setFrame(False)
            ausgabeFeld.setReadOnly(True)
            self.__dicDbTableStatusBoxWidgets[sTabName] = ausgabeFeld  # Widgets in Dictionary merken
            # Zusammenbauen
            grid.addWidget(label, iRow, iCol)
            grid.addWidget(btnOpen, iRow, iCol + 1)
            grid.addWidget(btnCsv, iRow, iCol + 2)
            grid.addWidget(ausgabeFeld, iRow, iCol + 3)
            iCol = iCol + 4
            if iCol >= (iColMax * 4):
                iRow += 1
                iCol = 1
        self.groupboxDBStatus.setLayout(grid)

    # Generische Eingabe (wird abhängig von Tabellennamen spezialisiert -> weniger Code)
    def inputGeneric(self, sTitel, sTabelle, lstAttributAusschluss = ["id"]):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        bFehler = False # Gab es dabei Fehler
        sFehler = "" # Fehlerstring
        iCounter = 0 # Anzahl erzeugter Einträge

        pd("* Eingabe: " + sTitel)

        # DB: Hole Attribute, Kommentare, Obligatinfo
        try:
            conn = psycopg2.connect(self.__model.db.getConnStr())
            cursor = conn.cursor()
            lstAttr, dicAttrObligat, dicAttrComments = self.__inputGenericGetAttr(cursor,sTabelle,lstAttributAusschluss)
        except Exception as e:
            bFehler = True
            pn("Fehler (" + sTitel + "): Beim Zugriff auf die Datenbank (Hole Attribute, ...): " + str(e))
            return False

        # Dialog erzeugen
        dia, dicWidgets = self.__inputGenericCreateDialog(sTitel, lstAttr, sTabelle, dicAttrObligat, dicAttrComments, showCsv=True)

        # Zentrieren zum Hauptfenster
        self.centerWidget(dia)

        # Dialog anzeigen
        iAntwort = dia.exec()

        # DB: Dialog auswerten
        if iAntwort == 1:

            # ---------------------------------------------------------------
            # Einzeleintrag in DB
            # ---------------------------------------------------------------

            # Hole Daten aus Dialog
            dicVal = self.__inputGenericEvalDialog(dicWidgets, sTabelle)
                # Trage in DB ein
            if not all(v == "" for k,v in dicVal.items()): # Nur wenn Daten eingetragen wurden
                try:
                    self.__model.db.insertIntoTable(cursor, sTabelle, dicVal)
                    iCounter += 1
                    sSqlQuery = cursor.query.decode("utf-8")
                    iId = cursor.fetchone()[0]
                    pv("+" + sTabelle + "(" + str(iId) + ")")
                    pd("SQL: "+sSqlQuery+" -> "+str(iId))

                    # ---------------------------------------------------------------
                    # TWEAK/SPEZIALISIERUNG (Zusaetzliche DB-Aktion)
                    # ---------------------------------------------------------------

                    # if sTabelle == "taxon":
                    #     # Taxon
                    #         # AcceptedId auf TaxonID setzen
                    #     sSqlCmd = "UPDATE " + self.__model.db.getDbSchema() + ".taxon SET accepted_id = %s WHERE id = %s;"
                    #     cursor.execute(sSqlCmd, (str(iId), str(iId)))
                    #     sSqlQuery = cursor.query.decode("utf-8")
                    #     pd(sSqlQuery)
                    # ----------------------------------------------------------------

                except Exception as ex:
                    bFehler = True
                    sFehler += "Fehler (" + sTitel + "): Beim Zugriff auf die Datenbank (Erzeuge Eintrag): " + str(ex)
                    pn(sFehler)

        elif iAntwort == 2:

            # ---------------------------------------------------------------
            # CSV-Eintrag in DB
            # ---------------------------------------------------------------
            sCsvFilename = QFileDialog.getOpenFileName(self, "CSV-Datei", filter="*.csv;; *.*")[0]
            if sCsvFilename != "":
                bOk, iCounter, sErr = self.__model.workflows.ingestLookup(cursor, sTabelle, sCsvFilename)
                bFehler |= not bOk
                sFehler += sErr

        # Fehler?
        if bFehler:
            # Fehler
            conn.rollback()
            self.popupFehler("Fehler beim Erzeugen eines Datenzsatzes","Näheres siehe Konsolenausgabe ...", sFehler)
        else:
            # Ok
            if iCounter == 0:
                pv("Keine Datensaetze zu erzeugen")
            else:
                pn("Keine Fehler aufgetreten")
                if not self.__model.bDry:
                    conn.commit()
                    pn("DB-Aktion wird durchgefuehrt")
                    pn("Erzeugte Datensaetze:")
                    pn(sTabelle+" : "+str(iCounter))
                    self.serverDisconnect()
                    self.serverConnect()
                else:
                    pn("<Dry Run> aktiviert")
                    pn("DB-Aktion wird nicht durchgefuehrt")
                    pn("Es waeren folgende Datensaetze erzeugt worden:")
                    pn(sTabelle+" "+str(iCounter))
                    conn.rollback()
                self.popupInfo("Es wurden neue Datensätze erzeugt","<b>Tabelle (Anzahl)</b><ul><li><i>" + sTabelle + "</i> (" + str(iCounter)+ "x)</li></ul>")

        # DB-Verbindung schliessen
        cursor.close()
        conn.close()  # Ging alles gut?

    # Generische Eingabe: Hole Attribute, Obligatinfo, Kommentare
    def __inputGenericGetAttr(self, cursor, sTabelle, lstAttributAusschluss):

        # Entferne nicht gewuenscht Attribute
        lstTmp = self.__model.db.getAttributnamen(cursor, sTabelle)
        lstAttr = [x for x in lstTmp if (x not in lstAttributAusschluss)]

        # Hole Kommentare der Attribute
        dicAttrComments = dict()
        for sAttr in lstAttr:
            dicAttrComments[sAttr] = self.__model.db.getComment(cursor, sTabelle, sAttr)

        # Hole Obligatinfos der Attribute
        dicAttrObligat = dict()
        for sAttr in lstAttr:
            dicAttrObligat[sAttr] = self.__model.db.getObligat(cursor, sTabelle, sAttr)

        return (lstAttr, dicAttrObligat, dicAttrComments)

    # Generische Eingabe: Dialog auswerten
    def __inputGenericEvalDialog(self, dicWidgets, sTabelle = None):

        # Durchlaufe alle Eingabe-Widgets
        dicVal = dict()
        for sName, feld in dicWidgets.items():

            # Combobox
            if isinstance(feld,QComboBox):

                # ---------------------------------------------------------------
                # TWEAK/SPEZIALISIERUNG
                # ---------------------------------------------------------------

                # Humane Sicht auf die Daten
                if self.__model.bDataViewInHuman:
                    # Dataset
                        # Name -Auflösen via Lookup-Table-> contact_person_id
                    if sTabelle == "dataset" and sName == "contact_person_id":
                        dicPerson = self.__model.workflows.getLookupTableCopy("cruise_leader")
                        person = feld.currentText()
                        if person in dicPerson:
                            dicVal[sName] = dicPerson[person]
                    else:
                        dicVal[sName] = feld.currentText()

                # ---------------------------------------------------------------

                else:
                    dicVal[sName] = feld.currentText()

            # Textfeld
            elif feld.text() != "":
                dicVal[sName] = feld.text()

        return dicVal

    # Generische Eingabe: Erzeuge Dialog
    def __inputGenericCreateDialog(self, sTitel, lstAttr, sTabelle=None, dicAttrObligat={}, dicAttrComments={}, **kwargs):

        # Kwargs
        dicDefaultData = None
        bShowCsv = False
        for arg in kwargs:
            if "defaultData" in kwargs:  # Default-Werte
                dicDefaultData = kwargs['defaultData']
            if "showCsv" in kwargs:  # Zeige CSV-Import-Funktion
                bShowCsv= kwargs['showCsv']

        # Dialog erzeugen
        dia = QDialog()
        dia.setWindowTitle(sTitel)
        dia.setWindowModality(Qt.ApplicationModal)
        vbox = QVBoxLayout(dia)

        # Tabelle
        tabelle = QWidget()
        grid = QGridLayout(tabelle)
        iNummer = 1  # Aktuelle Attributnummer
        iRow = 1  # dazugehörige Zeile in Tabelle
        iCol = 1  # dazugehörige Spalte in Tabelle
        iAttrPerCol = 10  # Attribute pro Spalte
        dicWidgets = dict()

        # Durchlaufe alle Attribute
        for sName in lstAttr:
            # Label
            label = QLabel(sName.replace("_", " ").title())
            if sName in dicAttrObligat and dicAttrObligat[sName]:  # Obligat
                font = QFont()
                font.setBold(True)
                label.setFont(font)
            else:
                font = QFont()
                font.setItalic(True)
                label.setFont(font)
            grid.addWidget(label, iRow, iCol)

            # Eingabe-Widget
            eingabeFeld = QLineEdit()
                # Defaultwert
            if dicDefaultData is not None and sName in dicDefaultData and dicDefaultData[sName] is not None:
                eingabeFeld.setText(str(dicDefaultData[sName]))
                eingabeFeld.setCursorPosition(0)
            # ---------------------------------------------------------------
            # Tweak/Spezialisierung
            # ---------------------------------------------------------------

            # Humane Sicht auf die Daten
            if self.__model.bDataViewInHuman:
                # Gear
                    # category -> Combobox
                if sTabelle == "gear" and sName == "category":
                    combo = QComboBox()
                    combo.addItems(["grab","trawl"])
                        # Defaultwert
                    if dicDefaultData != None and sName in dicDefaultData:
                        sWert = str(dicDefaultData[sName]).lower()
                        if sWert == "grab":
                            combo.setCurrentIndex(0)
                        elif sWert == "trawl":
                            combo.setCurrentIndex(1)
                    eingabeFeld = combo

                # Dataset
                    # Free-Access -> Combobox
                if sTabelle == "dataset" and sName == "free_access":
                    combo = QComboBox()
                    combo.addItems(["true", "false"])
                        # Defaultwert
                    if dicDefaultData != None and sName in dicDefaultData:
                        sWert = str(dicDefaultData[sName]).lower()
                        if sWert == "true":
                            combo.setCurrentIndex(0)
                        elif sWert == "false":
                            combo.setCurrentIndex(1)
                    eingabeFeld = combo
                    # Person -> Lookuptable -> Combobox
                if sTabelle == "dataset" and sName == "contact_person_id":
                    combo = QComboBox()
                    dicPerson2id = self.__model.workflows.getLookupTableCopy("cruise_leader")
                    lstPerson = list(dicPerson2id)
                    combo.addItems(lstPerson)
                        # Defaultwert
                    if dicDefaultData != None and sName in dicDefaultData:
                        dicId2person = dict((v, k) for k, v in dicPerson2id.items())
                        iId = dicDefaultData[sName]
                        sPerson = dicId2person[iId]
                        combo.setCurrentIndex(combo.findData(sPerson, Qt.DisplayRole))
                    eingabeFeld = combo

            # ---------------------------------------------------------------

            # Kommentar dranhaengen
            if sName in dicAttrComments:
                eingabeFeld.setToolTip(dicAttrComments[sName])

            # Widgets in Dictionary merken
            dicWidgets[sName] = eingabeFeld

            # Widget in Layout einfuegen
            grid.addWidget(eingabeFeld, iRow, iCol + 1)
            iRow += 1
            if (iNummer % iAttrPerCol) == 0:
                iCol += 2
                iRow = 1
            iNummer += 1

        # Buttonbox
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dia)
        buttonBox.accepted.connect(dia.accept)
        buttonBox.rejected.connect(dia.reject)
        if bShowCsv:
            buttonCsv= buttonBox.addButton("CSV", QDialogButtonBox.NoRole)
            buttonCsv.clicked.connect(lambda: QDialog.done(dia, 2))

        # Dialog zusammenbauen
        vbox.addWidget(tabelle)
        vbox.addWidget(buttonBox)
        dia.setFixedSize(dia.sizeHint())  # Groeße fixieren

        return (dia, dicWidgets)

    # Konsole löschen
    def guiConsoleClear(self):
        self.textBox.clear()

    # Refresh Status
    def guiRefreshAll(self):
        self.guiRefreshStatusConnection()
        self.guiRefreshStatusTabellen()
        self.guiRefeshWindowTitelDryRun()
        self.guiRefeshIngestionTabelle()

    # Refresh Status (Connection)
    def guiRefreshStatusConnection(self):
        # Textfelder
        self.infoTextDbConnect.setPalette(QPalette()) # Standardfarbe Text (deaktiviert)
        if self.__model.workflows.isReady() is None:
            self.infoTextDbConnect.setText("nicht verbunden")
        elif self.__model.workflows.isReady() == True:
            self.infoTextDbConnect.setText("verbunden")
        else:
            palette = QPalette()
            palette.setColor(QPalette.Text, Qt.red)
            self.infoTextDbConnect.setPalette(palette)
            self.infoTextDbConnect.setText("Verbindungsfehler!")
        self.infoTextDbNameSchema.setText(self.__model.db.sDbName + "." + self.__model.db.getDbSchema())
        self.infoTextDbHost.setText(self.__model.db.sDbHost + ":" + self.__model.db.sDbPort)
        self.infoTextDbUser.setText(self.__model.db.sDbUser)
        # Icon Verbindung
        if self.__model.workflows.isReady() is None:
            # Offline
            #self.buttonConnectionToggle.setIcon(self.style().standardIcon(getattr(QStyle, "SP_DialogNoButton")))
            self.buttonConnectionToggle.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/icon_offline.png"))
        elif self.__model.workflows.isReady() == True:
            # Online
            #self.buttonConnectionToggle.setIcon(self.style().standardIcon(getattr(QStyle, "SP_DialogYesButton")))
            self.buttonConnectionToggle.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/icon_online.png"))
        else:
            # Error
            #self.buttonConnectionToggle.setIcon(self.style().standardIcon(getattr(QStyle, "SP_BrowserStop")))
            self.buttonConnectionToggle.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/ressource/icon_error.png"))
    # Refresh Tabellen-Inhalte
    def guiRefreshStatusTabellen(self):
        pd = self.__smartprint.debug
        pn = self.__smartprint.normal
        if self.__model.workflows.isReady() is not None:
            try:
                sModulname = "View: Refresh DB-Tabellen-Status"
                pd("* "+sModulname)
                pd("Hole Counter fuer Tabellen aus DB")
                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()
                # Alle DB-Status-Widgets durchlaufen
                for sTableName, sWidget in self.__dicDbTableStatusBoxWidgets.items():
                    iCount = self.__model.db.getCountEntries(cursor,sTableName)
                    if sTableName in self.__dicDbTableStatusBoxWidgets:
                        sWidget.setText(str(iCount) if iCount != False else "-")
                # DB-Verbindung schliessen
                cursor.close()
                conn.close()
                pd("ok")
            except Exception as ex:
                self.guiClearStatusTabellen() # Felder loeschen
                pn("Fehler ("+sModulname+"): Beim Zugriff auf die Datenbank: " + str(ex))
        else:
            self.guiClearStatusTabellen()  # Felder loeschen

    # Loesche die Status-Tabellen
    def guiClearStatusTabellen(self):
        for sTabName, widget in self.__dicDbTableStatusBoxWidgets.items():
            widget.setText("-")

    # Dry-Run-Modus im Titel angeben
    def guiRefeshWindowTitelDryRun(self):
        if self.__model.bDry:
            self.setWindowTitle(self.__model.sInfoPrgName+" "+self.__model.sInfoPrgVersion+" ("+self.__model.sInfoDbSchemaVersion+") <Dry Run>")
        else:
            self.setWindowTitle(self.__model.sInfoPrgName+" "+self.__model.sInfoPrgVersion+" ("+self.__model.sInfoDbSchemaVersion+")")

    # Ingestions anzeigen
    def guiRefeshIngestionTabelle(self, lstIngest=[]):
        pd = self.__smartprint.debug
        pn = self.__smartprint.normal

        # Verbunden mit Server?
        if self.__model.workflows.isReady() is not None:

            # Ja -> Ingestion-Tabelle aufbauen
            try:
                sModulname = "View: Refresh Ingesttabelle"
                pd("* " + sModulname)
                pd("Hole Daten fuer Ingesttabellen aus DB")
                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()
                # Ingests holen
                sSqlCmd = "SELECT * from " + self.__model.db.getDbSchema() + ".ingest;"
                cursor.execute(sSqlCmd)
                lstIngest = cursor.fetchall()
                # DB-Verbindung schliessen
                cursor.close()
                conn.close()
                pd("ok")
            except Exception as ex:
                self.guiClearStatusTabellen()  # Felder loeschen
                pn("Fehler (" + sModulname + "): Beim Zugriff auf die Datenbank: " + str(ex))

            # Table clear
            self.tableIngest.clearContents()
            self.tableIngest.setRowCount(0)

            # Zeilen (alle Ingestions)
            for row in lstIngest:
                rowPosition = self.tableIngest.rowCount()
                self.tableIngest.insertRow(rowPosition)

                # Spalten (eine Ingestion)
                iIngestId = None
                for i, col in enumerate(row):
                    if i == 0:
                        iIngestId = col
                    if i == 3:
                        # Description-Feld um Buttons erweitern
                        btnWidget = QWidget()
                        hbox = QHBoxLayout()
                        hbox.setContentsMargins(0, 0, 0, 0)
                        hbox.setSpacing(1)
                        # Save
                        btnSave = QToolButton()
                        btnSave.setText("csv")
                        font = btnSave.font()
                        font.setPointSize(7)
                        btnSave.setFont(font)
                        btnSave.setToolTip("Ingest als csv-Datei abspeichern")
                        btnSave.setToolButtonStyle(Qt.ToolButtonTextOnly)
                        # Show
                        btnShow = QToolButton()
                        btnShow.setText("tab")
                        font = btnShow.font()
                        font.setPointSize(7)
                        btnShow.setFont(font)
                        btnShow.setToolTip("Ingest in Tabellenform anzeigen")
                        btnShow.setToolButtonStyle(Qt.ToolButtonTextOnly)
                        # Plot
                        btnPlot = QToolButton()
                        btnPlot.setText("map")
                        font = btnPlot.font()
                        font.setPointSize(7)
                        btnPlot.setFont(font)
                        btnPlot.setToolTip("Sample-Koordinaten des Ingest auf Karte anzeigen")
                        btnPlot.setToolButtonStyle(Qt.ToolButtonTextOnly)
                        # Del
                        btnDel = QToolButton()
                        btnDel.setText("del")
                        font = btnDel.font()
                        font.setPointSize(7)
                        btnDel.setFont(font)
                        btnDel.setToolTip("Ingest in DB löschen")
                        btnDel.setToolButtonStyle(Qt.ToolButtonTextOnly)
                        # Connect
                        btnSave.clicked.connect(partial(self.ingestSave, iIngestId))
                        btnShow.clicked.connect(partial(self.ingestShow, iIngestId))
                        btnPlot.clicked.connect(partial(self.ingestPlot, iIngestId))
                        btnDel.clicked.connect(partial(self.ingestDel, iIngestId))
                        # Zusammenbauen
                        label = QLabel(str(col))
                        font = label.font()
                        font.setPointSize(9)
                        label.setFont(font)
                        hbox.addWidget(label)  # Text Letztes Feld
                        hbox.addWidget(btnShow)
                        hbox.addWidget(btnPlot)
                        hbox.addWidget(btnSave)
                        hbox.addWidget(btnDel)
                        btnWidget.setLayout(hbox)
                        self.tableIngest.setCellWidget(rowPosition, i, btnWidget)
                    else:
                        # Normale Felder
                        item = QTableWidgetItem(str(col))
                        item.setFlags(Qt.ItemIsEnabled)
                        self.tableIngest.setItem(rowPosition, i, item)
        else:
            # Nicht verbunden mit Server -> Ingestion-Tabelle löschen
            self.tableIngest.clearContents()
            self.tableIngest.setRowCount(0)

    # Zeige den Inhalt einer Tabelle
    def __showGenericTable(self, sWindowTitle, lstHeader, lstContentFull, **kwargs):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        # Kwargs
        bSave = False
        bEdit = False
        sEditId = "id"
        sEditTab = None
        iRange = 500
        iRangeIdx = 0
        for arg in kwargs:
            if "edit" in kwargs:  # Edit-Modus
                bEdit = kwargs['edit']
            if "save" in kwargs:  # Tabelle kann als csv-Datei gespeichert werden
                bSave = kwargs['save']
            if "editTab" in kwargs:  # Tabelle für Edit-Modus
                sEditTab = kwargs['editTab']
            if "editId" in kwargs:  # Id-Feldname für Edit-Modus
                sEditId = kwargs['editId']
            if "range" in kwargs:  # Anzeigefenster (Zeilen pro Tabelle)
                iRange = kwargs['range']
            if "rangeIdx" in kwargs:  # Index des anzuzeigenden Fensters
                iRangeIdx = kwargs['rangeIdx']

        # Bestimme den Tabellen-Index der Id für den Editierungsmodus
        iIdxEditId = None
        if sEditId in lstHeader:
            iIdxEditId = lstHeader.index(sEditId)
        else:
            bEdit = False

        # Fenster Index überprüfen
        if iRangeIdx < 0:
            iRangeIdx = 0
        if (iRangeIdx * iRange) > len(lstContentFull):
            iRangeIdx = int(len(lstContentFull) / iRange)

        # Elemente in Inhaltsfenster auswählen
        iRangeElementStartIdx = iRangeIdx * iRange
        iRangeElementEndIdx = ((iRangeIdx + 1) * iRange) - 1
        lstContent = lstContentFull[
                     iRangeElementStartIdx:iRangeElementEndIdx + 1]  # Achtung das letzte Element wird von Python nie genommen, also +1
        iRangeIdxMax = int(len(lstContentFull) / iRange)

        pd("* Zeige Inhalt einer Tabelle")
        pd("Tabelle: " + str(sEditTab))
        pd("Editierbar: " + str(bEdit))
        pd("Als csv-Datei abspeicherbar: " + str(bSave))
        pd("Tabellen Edit-ID: " + sEditId)
        pd("Fensterbreite: " + str(iRange))
        pd("Fenster Idx: " + str(iRangeIdx))
        pd("Fenster Idx max: " + str(iRangeIdxMax))
        pd("Elemente Idx:" + str(iRangeElementStartIdx) + "-" + str(iRangeElementEndIdx))

        # Zeilen/Spalten
        iRows = len(lstContent)
        iCols = len(lstHeader)

        # Dialog erzeugen
        dia = QDialog()
        dia.setWindowTitle(sWindowTitle)
        dia.setWindowModality(Qt.ApplicationModal)
        vbox = QVBoxLayout(dia)

        # Tabelle
        tableWidget = QTableWidget(0, iCols)

        # Header
        tableWidget.setHorizontalHeaderLabels(lstHeader)
        tableWidget.horizontalHeader().setStretchLastSection(True)

        # Fonts
        # Tabelle
        font = tableWidget.font()
        font.setPointSize(9)
        tableWidget.setFont(font)
        # Header
        font = tableWidget.horizontalHeader().font()
        font.setBold(True)
        tableWidget.horizontalHeader().setFont(font)

        # Warteanzeige
        self.widgetProgress.show()
        self.centerWidget(self.widgetProgress)

        # Zeilen
        for iZeilennummer, row in enumerate(lstContent):
            rowPosition = tableWidget.rowCount()
            tableWidget.insertRow(rowPosition)
            pnProgress(iZeilennummer, iRows, 100, guiText="Tabelle wird aufgebaut\nBearbeite Zeile", abs=True,
                       cli=False)  # Fortschritt
            # Spalten (eine Ingestion)
            for iSpaltennummer, col in enumerate(row):
                if bEdit and iSpaltennummer == len(row) - 1:
                    # Edit-Modus: Letztes Feld + Buttons
                    # Widget
                    btnWidget = QWidget()
                    hbox = QHBoxLayout()
                    hbox.setContentsMargins(0, 0, 0, 0)
                    hbox.setSpacing(1)
                    # Button Edit
                    btnEdit = QToolButton()
                    btnEdit.setText("edt")
                    font = btnEdit.font()
                    font.setPointSize(7)
                    btnEdit.setFont(font)
                    btnEdit.setToolTip("Eintrag verändern")
                    btnEdit.setToolButtonStyle(Qt.ToolButtonTextOnly)
                    # Button Del
                    btnDel = QToolButton()
                    btnDel.setText("del")
                    font = btnDel.font()
                    font.setPointSize(7)
                    btnDel.setFont(font)
                    btnDel.setToolTip("Eintrag löschen")
                    btnDel.setToolButtonStyle(Qt.ToolButtonTextOnly)
                    # Connect
                    btnEdit.clicked.connect(
                        partial(self.tableEntryEdit, sEditTab, row[iIdxEditId], closeWin=dia))
                    btnDel.clicked.connect(partial(self.tableEntryDel, sEditTab, row[iIdxEditId], closeWin=dia))
                    # Zusammenbauen
                    label = QLabel(str(col))
                    font = label.font()
                    font.setPointSize(9)
                    label.setFont(font)
                    hbox.addWidget(label)  # Text Letztes Feld
                    hbox.addWidget(btnEdit)
                    hbox.addWidget(btnDel)
                    btnWidget.setLayout(hbox)
                    tableWidget.setCellWidget(rowPosition, iSpaltennummer, btnWidget)
                else:
                    # Normale Felder
                    item = QTableWidgetItem(str(col))
                    item.setFlags(Qt.ItemIsEnabled)
                    tableWidget.setItem(rowPosition, iSpaltennummer, item)

        # Zeilen Nummerieren
        lst = list(str(x) for x in range(iRangeElementStartIdx + 1, iRangeElementEndIdx + 2))
        tableWidget.setVerticalHeaderLabels(lst)

        # Zeilen und Spaltenbreite an Textinhalt/-größe anpassen
        tableWidget.resizeColumnsToContents()
        tableWidget.resizeRowsToContents()

        # Auswahl Range
        # Widget
        rangeWidget = QWidget()
        hbox = QHBoxLayout()
        hbox.setSizeConstraint(QLayout.SetFixedSize)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(1)
        # Button Zurueck
        btnZurueck = QToolButton()
        btnZurueck.setText("<")
        font = btnZurueck.font()
        font.setPointSize(7)
        btnZurueck.setFont(font)
        btnZurueck.setToolTip("Bereich zurück")
        btnZurueck.setToolButtonStyle(Qt.ToolButtonTextOnly)
        # Button Anfang
        btnAnfang = QToolButton()
        btnAnfang.setText("|<")
        font = btnAnfang.font()
        font.setPointSize(7)
        btnAnfang.setFont(font)
        btnAnfang.setToolTip("Springe zu erstem Bereich")
        btnAnfang.setToolButtonStyle(Qt.ToolButtonTextOnly)
        # Button Vor
        btnVor = QToolButton()
        btnVor.setText(">")
        font = btnVor.font()
        font.setPointSize(7)
        btnVor.setFont(font)
        btnVor.setToolTip("Bereich vor")
        btnVor.setToolButtonStyle(Qt.ToolButtonTextOnly)
        # Button Ende
        btnEnde = QToolButton()
        btnEnde.setText(">|")
        font = btnEnde.font()
        font.setPointSize(7)
        btnEnde.setFont(font)
        btnEnde.setToolTip("Springe zu letztem Bereich")
        btnEnde.setToolButtonStyle(Qt.ToolButtonTextOnly)
        # Button Go
        btnGo = QToolButton()
        btnGo.setText("go")
        font = btnGo.font()
        font.setPointSize(7)
        btnGo.setFont(font)
        btnGo.setToolTip("Springe zu Bereich")
        btnGo.setToolButtonStyle(Qt.ToolButtonTextOnly)
        # Range
        iBreiteS = 50
        iBreiteM = 100
        # Fenster Idx
        ausgabeFeldRangeFensterIdx = QLineEdit(str(iRangeIdx + 1))
        ausgabeFeldRangeFensterIdx.setAlignment(Qt.AlignRight)
        ausgabeFeldRangeFensterIdx.setFixedWidth(iBreiteS)
        # Fenster Idx Max
        ausgabeFeldRangeFensterIdxMax = QLineEdit(str(iRangeIdxMax + 1))
        ausgabeFeldRangeFensterIdxMax.setAlignment(Qt.AlignRight)
        ausgabeFeldRangeFensterIdxMax.setFixedWidth(iBreiteS)
        ausgabeFeldRangeFensterIdxMax.setEnabled(False)
        #ausgabeFeldRangeFensterIdxMax.setFrame(False)
        # Start
        ausgabeFeldRangeElementStart = QLineEdit(str(iRangeElementStartIdx + 1))
        ausgabeFeldRangeElementStart.setAlignment(Qt.AlignRight)
        ausgabeFeldRangeElementStart.setFixedWidth(iBreiteM)
        ausgabeFeldRangeElementStart.setEnabled(False)
        #ausgabeFeldRangeElementStart.setFrame(False)
        # Ende
        iLetztesElement = iRangeElementEndIdx + 1 if iRangeElementEndIdx + 1 <= len(lstContentFull) else len(
            lstContentFull)
        ausgabeFeldRangeElementEnde = QLineEdit(str(iLetztesElement))
        ausgabeFeldRangeElementEnde.setAlignment(Qt.AlignRight)
        ausgabeFeldRangeElementEnde.setFixedWidth(iBreiteM)
        ausgabeFeldRangeElementEnde.setEnabled(False)
        #ausgabeFeldRangeElementEnde.setFrame(False)
        # Gesamt
        ausgabeFeldRangeElementGesamt = QLineEdit(str(len(lstContentFull)))
        ausgabeFeldRangeElementGesamt.setAlignment(Qt.AlignRight)
        ausgabeFeldRangeElementGesamt.setFixedWidth(iBreiteM)
        ausgabeFeldRangeElementGesamt.setEnabled(False)
        #ausgabeFeldRangeElementGesamt.setFrame(False)

        # Zusammenbauen
        hbox.addWidget(btnAnfang)
        hbox.addWidget(btnZurueck)
        hbox.addWidget(ausgabeFeldRangeFensterIdx)
        hbox.addWidget(QLabel("|"))
        hbox.addWidget(ausgabeFeldRangeFensterIdxMax)
        hbox.addWidget(btnGo)
        hbox.addWidget(btnVor)
        hbox.addWidget(btnEnde)
        rangeWidget.setLayout(hbox)

        # Datensaetze
        # Widget
        datensaetzeWidget = QWidget()
        hbox = QHBoxLayout()
        hbox.setSizeConstraint(QLayout.SetFixedSize)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(1)
        # Zusammenbauen
        hbox.addWidget(QLabel("Datensätze:"))
        hbox.addWidget(ausgabeFeldRangeElementStart)
        hbox.addWidget(QLabel("-"))
        hbox.addWidget(ausgabeFeldRangeElementEnde)
        hbox.addWidget(QLabel("/"))
        hbox.addWidget(ausgabeFeldRangeElementGesamt)
        datensaetzeWidget.setLayout(hbox)

        # Dialog Buttonbox
        buttonBox = QDialogButtonBox(Qt.Horizontal, dia)
            # Save (CSV)
        if bSave:
            btnSave = QPushButton()
            btnSave.setText("CSV")
            btnSave.setToolTip("Speichere Tabelle als csv")
            #QObject.connect(btnSave, SIGNAL("clicked()"), lambda: QDialog.done(dia, 7))
            btnSave.clicked.connect(lambda: QDialog.done(dia, 7))
            buttonBox.addButton(btnSave, QDialogButtonBox.NoRole)
            # Ok
        btnOk = QPushButton()
        btnOk.setText("OK")
        btnOk.clicked.connect(lambda: QDialog.done(dia, 1))
        buttonBox.addButton(btnOk, QDialogButtonBox.NoRole)

        # Button Verbinden
        btnVor.clicked.connect(lambda: QDialog.done(dia, 2))
        btnEnde.clicked.connect(lambda: QDialog.done(dia, 3))
        btnZurueck.clicked.connect(lambda: QDialog.done(dia, 4))
        btnAnfang.clicked.connect(lambda: QDialog.done(dia, 5))
        btnGo.clicked.connect(lambda: QDialog.done(dia, 6))

        # Dialog zusammenbauen
        vbox.addWidget(datensaetzeWidget)
        vbox.addWidget(tableWidget)
        vbox.addWidget(rangeWidget)
        vbox.addWidget(buttonBox)
        vbox.setAlignment(rangeWidget, Qt.AlignHCenter)
        vbox.setAlignment(datensaetzeWidget, Qt.AlignHCenter)
        dia.resize(800, 600)

        # Warteanzeige aus
        self.widgetProgress.hide()

        # Zentrieren zum Hauptfenster
        self.centerWidget(dia)

        # Dialog anzeigen
        iRet = dia.exec()

        # Antwort auswerten
        if iRet == 1:
            # Ende
            return
        elif iRet == 2:
            # Vor
            kwargs["rangeIdx"] = iRangeIdx + 1
            self.__showGenericTable(sWindowTitle, lstHeader, lstContentFull, **kwargs)
        elif iRet == 3:
            # Ende
            kwargs["rangeIdx"] = iRangeIdxMax
            self.__showGenericTable(sWindowTitle, lstHeader, lstContentFull, **kwargs)
        elif iRet == 4:
            # Zurück
            kwargs["rangeIdx"] = iRangeIdx - 1
            self.__showGenericTable(sWindowTitle, lstHeader, lstContentFull, **kwargs)
        elif iRet == 5:
            # Anfang
            kwargs["rangeIdx"] = 0
            self.__showGenericTable(sWindowTitle, lstHeader, lstContentFull, **kwargs)
        elif iRet == 6:
            # Go
            kwargs["rangeIdx"] = int(ausgabeFeldRangeFensterIdx.text()) - 1
            self.__showGenericTable(sWindowTitle, lstHeader, lstContentFull, **kwargs)
        elif iRet == 7:
            # Csv
            self.__saveDataCsv([lstHeader]+lstContentFull,sWindowTitle)

    # Zeige Inhalt einer Tabelle
    def tableShow(self, sTab):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            # Ja -> Lookup-Tabelle anzeigen
            try:
                sModulname = "Zeige Lookuptable"
                pv("* " + sModulname)
                pv("Tabelle: " + sTab)
                pv("Hole Tabelle aus DB ...")

                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()

                # Popup Warten an
                self.popupWaitingOn("Hole Tabelle aus Datenbank ...")

                # Hole Ergebnis aus DB
                lstHeader, lstContent = self.__model.db.getWholeTable(cursor, sTab)

                # Popup Warten aus
                self.popupWaitingOff()

                # Verändere Ergebnis (Ids -Lookup-> Namen)
                if self.__model.bDataViewOutHuman:
                    lstHeader, lstContent = self.__model.workflows.tweakTableDataForHumanOutput(sTab, lstHeader, lstContent)

                # DB-Verbindung schliessen
                cursor.close()
                conn.close()
                pd("ok")

                # Ergenis anzeigen
                self.__showGenericTable("Tabelle: " + sTab.replace("_", " ").title(), lstHeader, lstContent, edit=True, editTab=sTab, rangeIdx=0)

            except Exception as ex:
                self.guiClearStatusTabellen()  # Felder loeschen
                pn("Fehler (" + sModulname + "): Beim Zugriff auf die Datenbank: " + str(ex))

    # Speichere Tabelle in CSV-Datei
    def tableSave(self, sTab):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            # Ja -> Tabelle speichern aufbauen
            try:
                sModulname = "Speichern einer Lookuptabelle in CSV-Datei"
                pv("* " + sModulname)
                pv("Tabelle: " + sTab)
                pv("Hole Tabelle aus DB ...")

                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()

                # Busy an
                self.popupWaitingOn("Hole Tabelle aus DB ...")

                # Hole Ergebnis aus DB
                lstHeader, lstContent = self.__model.db.getWholeTable(cursor, sTab)

                # Busy aus
                self.popupWaitingOff()

                # Menschliche Sicht
                if self.__model.bDataViewOutHuman:

                    # Verändere Ergebnis (Ids -Lookup-> Namen)
                    lstHeader, lstContent = self.__model.workflows.tweakTableDataForHumanOutput(sTab, lstHeader, lstContent)

                    # Entferne gesamte Spalte "id" (Header und Inhalt)
                        # Inhalt
                    for iRow, row in enumerate(lstContent):
                        for iCol, col in enumerate(row):
                            if lstHeader[iCol] == "id":
                             del lstContent[iRow][iCol]
                        # Header
                    lstHeader.remove("id")

                # DB-Verbindung schliessen
                cursor.close()
                conn.close()
                pd("ok")

            except Exception as ex:
                pn("Fehler (" + sModulname + "): Beim Zugriff auf die Datenbank: " + str(ex))
                self.popupFehler("Fehler","<b>Es gab Fehler beim Speichern in CSV-Datei</b><br>Näheres siehe Konsolenausgabe")
                return False

            # Daten speichern
            bAnt = self.__saveDataCsv([lstHeader]+lstContent, self.__model.db.getDbSchema() + "_" + sTab)
            return bAnt

        return True

    # Speichere Daten in CSV-Datei
    def __saveDataCsv(self, lstData, sFilenameDefault="data"):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        sModulname = "Speichern einer Tabelle in CSV-Datei"

        # Nichts zu speichern
        if lstData is None or lstData == []:
            return True

        # "Säubere" den Dateinamen
        sFilenameDefault = re.sub('[^A-Za-z0-9_,. ]+', '', sFilenameDefault)
        sFilenameDefault = sFilenameDefault.replace(",", " ")
        sFilenameDefault = sFilenameDefault.replace(".", " ")
        sFilenameDefault = " ".join(sFilenameDefault.split())
        sFilenameDefault = sFilenameDefault.replace(" ", "_").lower()+".csv"

        # Hole CSV-Dateinamen
        csvFile = QFileDialog.getSaveFileName(self, "CSV-Datei",sFilenameDefault)[0]
        if csvFile == "" or csvFile == None:
            return

        # Popup Warten an
        self.popupWaitingOn("Speichere Tabelle ...")

        try:
            with open(csvFile, 'w') as csvWriter:
                writer = csv.writer(csvWriter, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
                writer.writerows(lstData)
        except Exception as ex:
            pn("Fehler (" + sModulname + "): Beim Speicher in CSV-Datei: " + str(ex))
            self.popupFehler("Fehler",
                             "<b>Es gab Fehler beim Speichern in CSV-Datei</b><br>Näheres siehe Konsolenausgabe")
            # Popup Warten aus
            self.popupWaitingOff()
            return False

        pn("Tabelle wurde in Datei gespeichert: " + str(csvFile))

        # Popup Warten aus
        self.popupWaitingOff()
        return True

    # Ändere einen Eintrag einer Tabelle
    def tableEntryEdit(self, sTab, iId, **kwargs):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Kwargs
        closeWin = None
        for arg in kwargs:
            if "closeWin" in kwargs:  # Fenster, welches nach Veränderung geschlossen werden soll
                closeWin = kwargs['closeWin']

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            bOk = False

            try:
                sModulname = "Aenderung eines Datensatzes"
                pv("* " + sModulname)
                pv("Tabelle: " + sTab)
                pv("Id: " + str(iId))

                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()

                # Daten
                dicDataNeu = dict()

                # DB: Hole aktuellen Datensatz
                lstHeader, lstContent = self.__model.db.getTableEntry(cursor, sTab, "id", iId)
                dicDataAktuell = dict(zip(lstHeader, lstContent))

                pd("Aktuelle Werte: "+str(dicDataAktuell))

                # DB: Hole Attribute, Kommentare, Obligatinfo
                lstAttr, dicAttrObligat, dicAttrComments = self.__inputGenericGetAttr(cursor, sTab,["id"])

                # Edit-Dialog erzeugen
                dia, dicWidgets = self.__inputGenericCreateDialog("Edit "+sTab+" (ID: "+str(iId)+")", lstAttr, sTab, dicAttrObligat, dicAttrComments, defaultData=dicDataAktuell)

                # Edit-Dialog anzeigen
                iAnt = dia.exec()
                if iAnt == 0:
                    # Soll noch ein Fenster geschlossen werden
                    if closeWin is not None:
                        closeWin.close()
                    return True

                # Dialog auswerten
                dicDataNeu = self.__inputGenericEvalDialog(dicWidgets, sTab)
                pd("Neue Werte: " + str(dicDataNeu))

                bOk |= self.__model.db.editTableEntry(cursor, sTab, "id", iId, dicDataNeu)
                pd("SQL: "+str(cursor.query.decode("utf-8")))
                pd(str(bOk))
                # Commit?/Rollback?
                if bOk:
                    if not self.__model.bDry:
                        conn.commit()
                        pn("Eintrag wurde veraendert")
                        self.serverDisconnect()
                        self.serverConnect()
                    else:
                        pn("<Dry Run> aktiviert")
                        pn("Eintrag waere veraendert worden")
                        conn.rollback()
                else:
                    pn("Veraenderung wurde ohne DB-Fehler durch Programm abgelehnt (SQL-Injection, ID-Probleme,...)")
                    conn.rollback()

                # DB-Verbindung schliessen
                cursor.close()
                conn.close()

            except Exception as ex:
                bOk = False
                pn("Fehler (" + sModulname + "): Beim Zugriff auf die Datenbank: " + str(ex))
                self.popupFehler("Fehler beim Verändern eines Datensatzes", "Näheres siehe Konsolenausgabe ...", str(ex))

            # Soll noch ein Fenster geschlossen werden
            if closeWin is not None:
                closeWin.close()

            # Info
            if bOk:
                # Ok
                sInfo = "<b>Tabelle</b>"
                sInfo += "<ul><li>" + sTab + "</li></ul>"
                sInfo += "<b>Datensatz-ID</b>"
                sInfo += "<ul><li>" + str(iId) + "</li></ul>"
                self.popupInfo("Datensatz wurde verändert", sInfo)

            return bOk

    # Lösche einen Eintrag in der Tabelle
    def tableEntryDel(self, sTab, iId, **kwargs):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Kwargs
        closeWin = None
        for arg in kwargs:
            if "closeWin" in kwargs:  # Fenster welches nach löschen geschlossen werden soll
                closeWin = kwargs['closeWin']

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            bOk = False

            try:
                sModulname = "Loeschung eines Datensatzes"
                pv("* " + sModulname)
                pv("Tabelle: " + sTab)
                pv("Id: " + str(iId))

                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()

                # Loeschen
                bOk |= self.__model.db.delTableEntry(cursor, sTab, iId)

                # Info
                pd("SQL: " + str(cursor.query.decode("utf-8")))

                # Soll noch ein Fenster geschlossen werden
                if closeWin is not None:
                    closeWin.close()

                # Rückfrage
                mb = QMessageBox.warning(self," ","<h3>Datensatz löschen</h3>Soll der Datensatz mit der ID "+str(iId)+" wirklich gelöscht werden?",QMessageBox.Yes | QMessageBox.No)
                if mb == QMessageBox.No:
                    return True

                # Commit?/Rollback?
                if bOk:
                    if not self.__model.bDry:
                        conn.commit()
                        pn("Eintrag wurde geloescht")
                        self.serverDisconnect()
                        self.serverConnect()
                    else:
                        pn("<Dry Run> aktiviert")
                        pn("Eintrag waere geloescht worden")
                        conn.rollback()
                else:
                    conn.rollback()
                    pn("Loeschvorgang wurde ohne DB-Fehler durch Programm abgelehnt (SQL-Injection, ID-Probleme,...)")

                # DB-Verbindung schliessen
                cursor.close()
                conn.close()

            except Exception as ex:
                bOk = False
                pn("Fehler (" + sModulname + "): Beim Zugriff auf die Datenbank: " + str(ex))
                self.popupFehler("Fehler beim Löschen eines Datensatzes", "Näheres siehe Konsolenausgabe", str(ex))

            # Soll noch ein Fenster geschlossen werden
            if closeWin is not None:
                closeWin.close()

            # Info
            if bOk:
                # Ok
                sInfo = "<b>Tabelle</b>"
                sInfo += "<ul><li><i>" + sTab + "</i></li></ul>"
                sInfo += "<b>Datensatz-ID</b>"
                sInfo += "<ul><li>" + str(iId) + "</li></ul>"
                self.popupInfo("Datensatz wurde gelöscht", sInfo)

            return bOk

    # Ingestion speichern
    def ingestSave(self, iIngestId):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            # Ja -> Ingestion-Tabelle aufbauen
            try:
                sModulname = "Speichern Ingest in CSV-Datei"
                pv("* " + sModulname)
                pv("IngestID: " + str(iIngestId))
                pv("Lade Ingestdaten aus DB")

                # DB-Verbindung
                conn = psycopg2.connect(self.__model.db.getConnStr())
                cursor = conn.cursor()

                # Busy an
                self.popupWaitingOn("Lade Ingest aus Datenbank ...")

                # Hole Ergebnis aus DB
                lstHeader, lstContent = self.__model.workflows.getIngestArktis(iIngestId)

                # Tweake die Ergebnis-Tabelle (ID-Lookup-Tables->Namen)
                if self.__model.bDataViewOutHuman:
                    lstHeader, lstContent = self.__model.workflows.tweakIngestDataForHumanOutput(lstHeader, lstContent)

                # Busy aus
                self.popupWaitingOff()

                # DB-Verbindung schliessen
                cursor.close()
                conn.close()
                pd("ok")

            except Exception as ex:
                pn("Fehler (" + sModulname + "): Beim Zugriff auf die Datenbank: " + str(ex))
                self.popupFehler("Fehler","<b>Es gab Fehler beim Speichern in CSV-Datei</b><br>Näheres siehe Konsolenausgabe")
                return False

            # Datei speichern
            bAnt = self.__saveDataCsv([lstHeader]+lstContent,"ingest_"+str(iIngestId))

        return bAnt

    # Ingestion zeigen
    def ingestShow(self, iIngestId):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            sModulname = "Zeige Ingest"
            pv("* " + sModulname)
            pv("IngestID: "+str(iIngestId))
            pv("Hole Daten fuer Ingest aus DB ...")

            # Popup Warten as
            self.popupWaitingOn("Lade Ingest aus Datenbank ...")

            # Hole Ergebnis aus DB
            lstHeader, lstContent = self.__model.workflows.getIngestArktis(iIngestId)

            # Popup Warten aus
            self.popupWaitingOff()

            # Tweake die Ergebnis-Tabelle (ID-Lookup-Tables->Namen)
            if self.__model.bDataViewOutHuman:
                lstHeader, lstContent = self.__model.workflows.tweakIngestDataForHumanOutput(lstHeader, lstContent)

            # Ergebnis anzeigen
            if lstHeader is not None and lstContent is not None:
                self.__showGenericTable("Ingestion (ID:" + str(iIngestId) + ")", lstHeader, lstContent)
            else:
                self.guiClearStatusTabellen()  # Felder loeschen

    # Ingestion in Karte plotten
    def ingestPlot(self, iIngestId):

        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug
        pnProgress = self.__smartprint.progress

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            sMap = os.path.expanduser("~") + "/map_ingest_"+str(iIngestId)+".html"

            sModulname = "Zeige Samplekoordinaten des Ingest auf Karte"
            pv("* " + sModulname)
            pv("IngestID: " + str(iIngestId))
            pv("Map: " + sMap)

            map = folium.Map()

            # Popup Warten as
            self.popupWaitingOn("Lade Samplekoordinaten des Ingest aus Datenbank ...")

            lstHeader, lstContent = self.__model.workflows.getIngestArktisSampleLocations(iIngestId)
            pv("Anzahl Marker: "+str(len(lstContent)))

            # Popup Warten as
            self.popupWaitingOff()

            # Fortschritt an
            self.centerWidget(self.widgetProgress)
            self.widgetProgress.show()

            # Samples
            for iRow, item in enumerate(lstContent):
                fLon = float(item[0])
                fLat = float(item[1])
                sCruise = item[2]
                sSample = item[3]
                sStation = item[4]
                sDataset = item[5]
                sPopup = "<b>Dataset</b>: "+str(sDataset)+"<br><b>Cruise</b>: "+str(sCruise)+"<br><b>Station</b>: "+str(sStation)+"<br><b>Sample</b>: "+str(sSample)+"<br><b>Lat/Long</b>: ("+str(fLat)+"/"+str(fLon)+")"
                htmlPopup = folium.Popup(folium.Html(sPopup,script=True))

                folium.CircleMarker(location=[fLat,fLon], radius=5, popup=htmlPopup, fill_color="red", color="grey").add_to(map);
                # Fortschritt
                pnProgress(iRow, len(lstContent), 50, guiText="Baue Karte auf\nBearbeite Marker ", abs=True,cli=False)  # Fortschritt

            # Fortschritt aus
            self.widgetProgress.hide()

            self.popupWaitingOn("Speichere Karte und öffne Browser ...")
            map.save(sMap)
            webbrowser.open("file://"+sMap, new=1)
            self.popupWaitingOff()


        # Ingestions löschen
    def ingestDel(self, iIngestId):
        pn = self.__smartprint.normal
        pv = self.__smartprint.verbose
        pd = self.__smartprint.debug

        # Verbunden mit Server?
        if self.__model.workflows.isReady():

            # Wirklich?
            mb = QMessageBox.warning(self," ","<h3>Ingestion löschen</h3>Soll die Ingestion mit der ID "+str(iIngestId)+" wirklich gelöscht werden?",QMessageBox.Yes | QMessageBox.No)
            if mb == QMessageBox.No:
                return True

            # Loeschen
            odicErg, sFehler = self.__model.workflows.delIngestArktis(iIngestId)

            # Fehler
            if odicErg is None:
                self.popupFehler("Fehler beim Löschen der Ingestion","Näheres siehe Konsolenausgabe ...", sFehler)
                return

            # Info
            sCountInfo = ""
            for k, v in odicErg.items():
                sCountInfo += k + " " + str(v) + "\n"
            sCountInfo = sCountInfo[:-1]
            pn(sCountInfo)

            # Ergenis anzeigen
            # OK
            sInfo = "<b>Ingest-Identifikationsnummer</b>"
            sInfo += "<ul><li>" + str(iIngestId) + "</li></ul>"
            sInfo += "<b>Gelöschte Datensätze in Datenbank</b>"
            sInfo += "<ul>"
            for k, v in odicErg.items():
                sInfo += "<li><i>" + k + "</i> (" + str(v) + "x)</li>"
            sInfo += "</ul>"
            self.guiRefreshStatusTabellen()
            self.guiRefeshIngestionTabelle()
            self.popupInfo("Ingestion wurde gelöscht", sInfo)


# Optionen
class DialogOptionen(QDialog, uic.loadUiType(fileOptionen)[0]):

    # Konstruktor
    def __init__(self, model):
        # Super
        QDialog.__init__(self)

        # Instanzvariablen
        self.__model = model

        # Initialisierung
        self.setupUi(self)
            # Dialogbuttons
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(lambda: QDialog.done(self,1))
        self.buttonBox.button(QDialogButtonBox.Save).clicked.connect(lambda: QDialog.done(self, 2))
        self.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(lambda: QDialog.done(self, 0))
            # Logging
        self.check_logging.clicked.connect(self.actionLoggingAktivieren)
        self.button_loggingDatei.clicked.connect(self.actionLoggingDatei)

    # Logging Datei auswaehlen
    def actionLoggingDatei(self):
        sDateiLogging = QFileDialog.getSaveFileName(self, "Auswahl der Logging-Datei", self.__model.sDateiLogging)[0]
        if sDateiLogging != "":
            self.__model.sDateiLogging = sDateiLogging # Model
            self.text_logging.setText(sDateiLogging) # Textfeld

    # Logging aktivieren
    def actionLoggingAktivieren(self):
        bLog = self.check_logging.isChecked()
        self.text_logging.setEnabled(bLog)
        self.button_loggingDatei.setEnabled(bLog)

# Progress
class WidgetProgress(QWidget, uic.loadUiType(fileProgress)[0]):

    # Konstruktor
    def __init__(self):
        # Super
        QWidget.__init__(self)

        # Initialisierung
        self.setupUi(self)
        self.setWindowFlags(Qt.Window | Qt.WindowModal | Qt.FramelessWindowHint)
        self.setMinMax()
        self.setText("Bitte warten ...")

    # Set Min/Max
    def setMinMax(self,min=0,max=0):
        self.bar.setMinimum(min)
        self.bar.setMaximum(max)

    # Set Text
    def setText(self,text):
        self.text.setText(text)

# Waiting
class WidgetWaiting(QWidget, uic.loadUiType(fileWaiting)[0]):

    # Konstruktor
    def __init__(self):
        # Super
        QWidget.__init__(self)

        # Initialisierung
        self.setupUi(self)
        self.setWindowFlags(Qt.Window | Qt.WindowModal | Qt.FramelessWindowHint)
        self.setText("Bitte warten ...")

    # Set Text
    def setText(self,text):
        self.text.setText(text)

