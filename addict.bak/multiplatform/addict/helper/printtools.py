# coding=utf-8
import time, datetime

"""
-----------------------------------------------------------------------
Hilfsklassen und Methoden
-----------------------------------------------------------------------
"""

# Bildschirmausgabe
class SmartPrint:

    # Konstruktor
    def __init__(self, **kwargs):
        # Instanzvariablen
            # Default
        self.__bVerbose = False
        self.__bDebug = False
        self.__model = None
            # Werte aus Konstruktorparameterliste verteilen
        for arg in kwargs:
            if "verbose" in kwargs:
                self.__bVerbose = kwargs['verbose']
            if "debug" in kwargs:
                self.__bDebug = kwargs['debug']
            if "model" in kwargs:
                self.__model = kwargs['model']

    # Geschwaetzigkeit einstellen
    def setVerbosity(self, verbose, debug):
        self.__bVerbose = verbose
        self.__bDebug = debug

    # Getter
    def getVerbose(self):
        return True if self.__bVerbose or self.__model != None and self.__model.bVerbose else False
    def getDebug(self):
        return True if self.__bDebug or self.__model != None and self.__model.bDebug else False

    # *** Ausdrucken

    # Ausdrucken im Normalmodus
    def normal(self, text="", appendix="\n"):
        if (self.__model != None and self.__model.observer != None):
            self.__printGui(text, appendix)  # GUI
        else:
            self.__printConsole(text, appendix)  # CLI

    # Ausdruck im Verbosemodus (inkl. Debugmodus)
    def verbose(self, text="", appendix="\n"):
        if (self.__model != None and self.__model.observer != None) and (self.__model.bVerbose == True or self.__model.bDebug == True):
            self.__printGui(text, appendix)  # GUI
        elif self.__model != None and (self.__model.bVerbose == True or self.__model.bDebug == True):
            self.__printConsole(text, appendix)  # CLI
        elif self.__bVerbose == True or self.__bDebug == True:
            self.__printConsole(text, appendix)  # CLI

    # Ausdruck im Debugmodus
    def debug(self, text="", appendix="\n"):
        if (self.__model != None and self.__model.observer != None) and self.__model.bDebug == True:
            self.__printGui(text, appendix)  # GUI
        elif self.__model != None and self.__model.bDebug == True:
            self.__printConsole(text, appendix)  # CLI
        elif self.__bDebug == True:
            self.__printConsole(text, appendix)  # CLI

    # Ausdruck auf Konsole (nicht threadsafe, shared ressource: Konosle)
    def __printConsole(self, text="", appendix="\n"):
        print(text, end=appendix)# Ausdruck in GUI-Konsole
        self.__logToFile(text, True)

    # Ausdruck auf Gui (nicht threadsafe, shared ressource: Text-Widget)
    def __printGui(self, text="", appendix="\n"):
        if self.__model is not None and self.__model.observer is not None:
            self.__model.observer.printGui(text)
            #self.__model.observer.giveQtTimeToUpdate() # Gib QT Zeit
            self.__logToFile(text, True)

    # Logging in Datei (nicht threadsafe, shared ressource: Logdatei)
    def __logToFile(self, text, stamp=False):
        if self.__model != None and self.__model.bLogging:
            sTimestamp =""
            if stamp:
                sTimestamp= datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H:%M:%S')+":"
            try:
                with open(self.__model.sDateiLogging, 'a') as log:
                    log.write(sTimestamp+text+"\n")
            except:
                sError = "Logging in funktioniert nicht: "+self.__model.sDateiLogging
                if self.__model.observer:
                    self.__model.observer.printGui(sError)
                else:
                    print(sError)

    # *** Zusatzfunktionen

    # Zeige Fortschritt (im Normalmodus)
    def progress(self, iWertAktuell, iWertMax, iSchritte, **kwargs):

        sText = "" # Infotext
        bAbs = True # Absoluten Schritt anzeigen
        bCli = True # Progress auch in CLI ausgeben

        for arg in kwargs:
            if "guiText" in kwargs:
                sText = kwargs['guiText']
            if "abs" in kwargs:
                bAbs = kwargs['abs']
            if "cli" in kwargs:
                bCli = kwargs['cli']

        sProgress = self.__getProgress(iWertAktuell, iWertMax, iSchritte)
        if sProgress != None:
            if self.__model is not None and self.__model.observer is not None:
                # Gui
                sFortschrittsText = sText
                if bAbs:
                    sFortschrittsText += " " + str(iWertAktuell) + "/" + str(iWertMax)
                self.__model.observer.setProgressbarProzAnzeigen(True) # Prozentwert anzeigen
                self.__model.observer.setProgressbarMinMax(1,iWertMax) # Range
                self.__model.observer.setProgressbarWert(iWertAktuell) # Aktueller Wert
                self.__model.observer.setProgressbarText(sFortschrittsText) # Text
            else:
                if bCli:
                    sFortschrittsText = str(sProgress) + "%"
                    if bAbs:
                        sFortschrittsText += " (" + str(iWertAktuell) + "/" + str(iWertMax) + ")"
                    self.normal(sFortschrittsText)

        # Gui? -> QT immer etwas Zeit geben
        if self.__model is not None and self.__model.observer is not None:
            self.__model.observer.giveQtTimeToUpdate()

    # Ermittle Fortschritt in Prozent (Schrittweise)
    def __getProgress(self, iWertAktuell, iWertMax, iSchritte):
        # Info: iSchritte teilt Gesamtfortschritt in Einzelteile auf (1 ~ einem 100%-Schritt, 100 ~ 100 1%-Schritten)
        if iSchritte > 100:
            # Mehr als 100 Teile gibt es nicht (1%-Schritte)
            iSchritte = 100
        fStepsZeilen = iWertMax / iSchritte
        if iWertAktuell % fStepsZeilen < 1:
            # Nächster Schritt erreicht -> String zurückgeben
            iProzent = int(iWertAktuell / fStepsZeilen / iSchritte * 100)
            return iProzent
        # Nächster Schritt noch nicht erreicht
        return None