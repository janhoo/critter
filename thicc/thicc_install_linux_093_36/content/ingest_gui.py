#!/usr/local/bin/python3
# coding=utf-8

try:
    from gui.controller import Controller
except ImportError as ex:
    print("Folgendes Modul fehlt: " + ex.name + "\nBitte installieren")
    quit()

# Main
if __name__ == "__main__":
    Controller(None)
