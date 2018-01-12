try:
    import time
    from gui.view import View
    from gui.model import Model
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren.")
    quit()

"""
-----------------------------------------------------------------------
Observer (Push-Observer der View fuer das Model)
-----------------------------------------------------------------------
"""

class Observer():

    # Konstruktor
    def __init__(self, view):
        # Instanzvariablen
        self.view = view # View

    # Ausdruck in GUI-Konsole
    def printGui(self, text):
        self.view.textBox.append(text)

    # Progress-Dialog: anzeigen
    def showProgress(self, bReset = True):
        if bReset:
            self.setProgressbarWert(0)
        self.view.centerWidget(self.view.widgetProgress) # Zentrieren zu View
        self.view.widgetProgress.show()

    # Progress-Dialog: verbergen
    def hideProgress(self):
        self.view.widgetProgress.hide()

    # Progressbar-Dialog: Progressbar Grenzen
    def setProgressbarMinMax(self,min=0,max=0):
        self.view.widgetProgress.setMinMax(min,max)

    # Progressbar-Dialog: Progressbar Wert
    def setProgressbarWert(self, wert):
        self.view.widgetProgress.bar.setValue(wert)

    # Progressbar-Prozentwert anzeigen
    def setProgressbarProzAnzeigen(self, bProzAnzeige):
        self.view.widgetProgress.bar.setTextVisible(bProzAnzeige)

    # Progressbar-Dialog: Text
    def setProgressbarText(self, text):
        self.view.widgetProgress.setText(text)

    # Gib QT-Loop Zeit zum Widget-Update
    def giveQtTimeToUpdate(self):
        self.view.giveQtTimeToUpdate()


