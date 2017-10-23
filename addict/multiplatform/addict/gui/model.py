try:
    import os, getpass, psycopg2, configparser, hashlib, base64
    from os.path import expanduser
    from helper.printtools import SmartPrint
    from helper.dbtools import DbTools
    from logik.workflow import Workflow
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren.")
    quit()

"""
-----------------------------------------------------------------------
Model (besitzt Geschaeftslogik und -Daten)
-----------------------------------------------------------------------
"""

class Model:

    # Konstruktor
    def __init__(self):

        # Instanzvariablen
            # Observer der View
        self.observer = None
            # Geschwaetzigkeit
        self.bVerbose = False
        self.bDebug = False
            # Dry Run
        self.bDry = False
            # Logging
        self.bLogging = False
        self.sDateiLogging = os.path.expanduser("~") + "/addict.log"
            # Sicht auf die Daten
        self.bDataViewInHuman = False # Eingabe
        self.bDataViewOutHuman = False # Ausgabe
        # Intelligentes Print
        self.prnt = SmartPrint(model = self)
            # Infos zum Programm
        self.sInfoPrgName = "addict"
        self.sInfoPrgVersion = "v.3.0.2~"
        self.sInfoDbSchemaVersion = "fiona"
        self.sInfoDatum = u"Copyright \N{COPYRIGHT SIGN} 2017"
        self.sInfoKommentar = "<i>Another Diversity Data Ingest and Curation Tool</i><br><br>" \
                              "Dieses Programm hilft bei der massenweisen Ingestion von Excel-Dateien in eine Datenbank. Es bietet weiterhin Funktionen zum Qualitätsmanagement und zur Verwaltung der Daten in der Datenbank."
        self.sInfoWeb = "http://www.awi.de/en/science/biosciences/functional-ecology/main-research-focus/ecosystem-functions.html"
        # Hole Programmversion aus Datei "version.txt" (im Besten Falle durch Git erzeugt)
        try:
            sVersionDatei = os.path.dirname(os.path.realpath(__file__)) + "/../version.txt"
            with open(sVersionDatei, 'r') as f:
                self.sInfoPrgVersion = "v." + f.read().strip()
        except:
            pass
            # Datenbank
        self.db = DbTools(self)
            # Hole die Konfiguration
        self.sConfigFilename = os.path.expanduser("~") + "/addict.conf"
        self.cfgRead()
            # Workflows
        self.workflow = Workflow(self)
        if not self.workflow.bOkWorkflowModell:
            quit()

    # -----------------------

    # Workflow neu erstellen
    def newWorkflow(self):
        self.workflow = Workflow(self)

    # Observer der View anmelden
    def addObserver(self, observer):
        self.observer = observer

    # Konfiguration einlesen
    def cfgRead(self):
        try:
            cfg = configparser.ConfigParser()
            cfg.read(self.sConfigFilename)
                # DB
            if cfg.has_option("DB", "db_host"): self.db.sDbHost = str(cfg["DB"]["db_host"])
            if cfg.has_option("DB", "db_port"): self.db.sDbPort = str(cfg["DB"]["db_port"])
            if cfg.has_option("DB", "db_name"): self.db.sDbName = str(cfg["DB"]["db_name"])
            if cfg.has_option("DB", "db_schema"): self.db.setDbSchema(str(cfg["DB"]["db_schema"]))
            if cfg.has_option("DB", "db_user"): self.db.sDbUser = str(cfg["DB"]["db_user"])
            if cfg.has_option("DB", "db_pw"): self.db.sDbPw = self.decrypt(str(cfg["DB"]["db_pw"]))
                # Etc
            if cfg.has_option("ETC", "verbose"): self.bVerbose = (True if str(cfg["ETC"]["verbose"]) == "True" else False)
            if cfg.has_option("ETC", "debug"): self.bDebug = (True if str(cfg["ETC"]["debug"]) == "True" else False)
            if cfg.has_option("ETC", "dry"): self.bDry = (True if str(cfg["ETC"]["dry"]) == "True" else False)
            if cfg.has_option("ETC", "data_view_input_human"): self.bDataViewInHuman = (True if str(cfg["ETC"]["data_view_input_human"]) == "True" else False)
            if cfg.has_option("ETC", "data_view_output_human"): self.bDataViewOutHuman = (True if str(cfg["ETC"]["data_view_output_human"]) == "True" else False)
            if cfg.has_option("ETC", "logging"): self.bLogging = (True if str(cfg["ETC"]["logging"]) == "True" else False)
            if cfg.has_option("ETC", "logging_datei"): self.sDateiLogging = str(cfg["ETC"]["logging_datei"])
        except (configparser.Error, ValueError) as ex:
            self.prnt.normal("Fehler beim Einlesen der Konfigurationsdatei (" + self.sConfigFilename, "): " + str(ex))
            return False
        return True
    
    # Konfiguration speichern
    def cfgSave(self, **kwargs):
        bSavePw = True # Passwort speichern
        # Hole Argumente
        for arg in kwargs:
            if "savePw" in kwargs:
                bSavePw =  kwargs['savePw']
        try:
            cfg = configparser.ConfigParser()
            cfg.read(self.sConfigFilename)
                # DB
            cfg["DB"] = {}
            cfg["DB"]["db_host"] = self.db.sDbHost
            cfg["DB"]["db_port"] = self.db.sDbPort
            cfg["DB"]["db_name"] = self.db.sDbName
            cfg["DB"]["db_schema"] = self.db.getDbSchema()
            cfg["DB"]["db_user"] = self.db.sDbUser
            if bSavePw == True:
                cfg["DB"]["db_pw"] = self.encrypt(self.db.sDbPw)
            else:
                cfg["DB"]["db_pw"] = ""
                # Etc
            cfg["ETC"] = {}
            cfg["ETC"]["verbose"] = "True" if self.bVerbose else "False"
            cfg["ETC"]["debug"] = "True" if self.bDebug else "False"
            cfg["ETC"]["logging"] = "True" if self.bLogging else "False"
            cfg["ETC"]["dry"] = "True" if self.bDry else "False"
            cfg["ETC"]["data_view_input_human"] = "True" if self.bDataViewInHuman else "False"
            cfg["ETC"]["data_view_output_human"] = "True" if self.bDataViewOutHuman else "False"
            cfg["ETC"]["logging_datei"] = self.sDateiLogging
            with open(self.sConfigFilename, 'w') as cfgdat:
                cfg.write(cfgdat)
            self.prnt.normal("Konfiguration wurde gespeichert in Datei: " + self.sConfigFilename)
        except (configparser.Error, ValueError) as ex:
            self.prnt.normal("Fehler beim Speichern der Konfigurationsdatei (" + self.sConfigFilename, "): " + str(ex))
            return False
        return True

    # String mit Konfiguration liefern
    def info(self):
        pn = self.prnt.normal
        sInfo = "Konf-Datei: "+self.sConfigFilename + " " + ("<existiert>" if os.path.isfile(self.sConfigFilename) else "<existiert nicht>") +"\n"
        sInfo += "DB-Host:    " + self.db.sDbHost +"\n"
        sInfo += "DB-Port:    " + self.db.sDbPort + "\n"
        sInfo += "DB-Name:    " + self.db.sDbName + "\n"
        sInfo += "DB-Schema:  " + self.db.getDbSchema()+ "\n"
        sInfo += "User:       " + self.db.sDbUser + "\n"
        sInfo += "Passwort:   " + ("<gespeichert>" if self.db.sDbPw != "" else "<nicht gespeichert>")+ "\n"
        if self.db.sDbPw != "":
            sInfo += "Verbindung: "+("ok" if self.db.checkConnection() == True else "")+"\n"
        sInfo += "Logging:    " + ("an" if self.bLogging == True else "aus") + "\n"
        sInfo += "Log-Datei:  " + (self.sDateiLogging+" " if self.sDateiLogging != "" else "") + ("<existiert>" if os.path.isfile(self.sDateiLogging) else "<existiert nicht>") +"\n"
        sInfo += "Verbose:    " + ("an" if self.bVerbose == True else "aus") + "\n"
        sInfo += "Debug:      " + ("an" if self.bDebug == True else "aus") + "\n"
        sInfo += "Human-In:   " + ("an" if self.bDataViewInHuman == True else "aus") +"\n"
        sInfo += "Human-Out:  " + ("an" if self.bDataViewOutHuman == True else "aus") +"\n"
        sInfo += "Dry:        " + ("an" if self.bDry == True else "aus")
        pn(sInfo)

    # Getter
        # Observer
    def getObserver(self):
        return self.observer

    # Setter
        # Geschwaetzigkeit
    def setVerbosity(self, verbose, debug):
        self.bVerbose = verbose
        self.bDebug = debug

    # Encrypt
    def encrypt(self, txt, mode="base64"):
        if mode == "base64":
            return base64.encodebytes(txt.encode()).decode()
        return None

    # Decrypt
    def decrypt(self, txt, mode="base64"):
        if mode == "base64":
            return base64.decodebytes(txt.encode()).decode()
        return None

    # Logging
    def setLogging(self, logging, dateiLogging):
        self.bLogging = logging
        self.sDateiLogging = dateiLogging


