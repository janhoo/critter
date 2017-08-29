try:
    from gui.view import View
    from gui.model import Model
    from gui.observer import Observer
    from PyQt5 import QtCore, QtGui, QtGui, uic
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import *
    import sys
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren.")
    quit()

"""
-----------------------------------------------------------------------
Controller (dumm, besitzt keine Logik)
-----------------------------------------------------------------------
"""

class Controller():

    # Konstruktor
    def __init__(self, sGuiStyle=None):

        # QT starten
        app = QApplication(sys.argv)
        #app.setAttribute(QtCore.Qt.AA_DontShowIconsInMenus, True)
        if sGuiStyle is not None:
            app.setStyle(QStyleFactory.create(sGuiStyle))

        # Instanzvariablen
        self.model = Model() # Model
        self.view = View(self.model) # View
        observer = Observer(self.view) # Observer der View
        self.model.addObserver(observer) # Observer bei Model anmelden
        # QT
        self.view.show() # Hauptfenster
        # Info
        sys.exit(app.exec_()) # Eventloop starten

