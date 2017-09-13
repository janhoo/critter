# coding=utf-8
import psycopg2, re
from helper.printtools import SmartPrint
from collections import OrderedDict

"""
-----------------------------------------------------------------------
DB-Tools
-----------------------------------------------------------------------
"""

# Bildschirmausgabe
class DbTools:

    # Konstruktor
    def __init__(self, model):

        # Instanzvariablen
        self.__model = model
        self.__prnt = SmartPrint(model=model)
        # DB-Login
        self.sDbHost = ""
        self.sDbPort = ""
        self.sDbName = ""
        self.__sDbSchema = ""  # TODO: Achtung SQL-Injektion. Das DB-Schema sollte fix sein. Es darf dauerhaft nicht per "+Konkatenation" in SQL-Statements gebaut werden
        self.sDbUser = ""
        self.sDbPw = ""

    # Check SQL-Strings (Benutzung für Tabellen/Attributnamen, Werte werden durch Framework getestet)
    def isSqlUnsafe(self, eingabe):
        # Nur ein Element uebergeben -> Liste
        if not isinstance(eingabe, (list,tuple)):
            lstText = [eingabe]
        else:
            lstText = eingabe
        # Jedes Listenelement pruefen (erlaube nur nicht leere alphanumerische Strings)
        for sText in lstText:
            if not (re.match(r'^[A-Za-z0-9_-]+$', sText)):
                self.__prnt.normal("Achtung: SQL-Teilstring besitzt nicht erlaubte Zeichen: \""+str(sText)+"\"")
                return True
        return False

    # Getter/Setter: Db-Schema (Check auf Alphanumerik)
        # Get
    def getDbSchema(self):
        if self.__sDbSchema != "" and self.isSqlUnsafe(self.__sDbSchema):
            self.__prnt.normal("DB-Schema ("+self.__sDbSchema+") wird nicht von Model geliefert.")
            return ""
        else:
            return self.__sDbSchema
        # Set
    def setDbSchema(self, schema):
        if self.isSqlUnsafe(schema):
            self.__prnt.normal("DB-Schema (" + schema + ") wird nicht in Model gespeichert.")
            return False
        else:
            self.__sDbSchema = schema
            return True

    # Hole DB Connection-String
    def getConnStr(self):
        return "dbname='" + self.sDbName + "' user='" + self.sDbUser + "' password='" + self.sDbPw + "' host='" + self.sDbHost + "' port='" + self.sDbPort + "'"  # Verbindungs-String

    # Hole Obligatinfo
    def getObligat(self, cursor, sTab, sCol):
        if self.isSqlUnsafe([sCol, sTab]):
            return False
        cursor.execute("SELECT is_nullable FROM information_schema.columns where table_name = '" + sTab + "' and table_schema = '" + self.getDbSchema() + "' and column_name = '" + sCol + "'")
        sNullable = str(cursor.fetchone()[0])
        bObligat = False
        if sNullable.lower() == "no":
            return True
        return False

    # Hole Comment
    def getComment(self, cursor, sTab, sCol):
        if self.isSqlUnsafe([sCol, sTab]):
            return ""
        cursor.execute("SELECT oid FROM pg_catalog.pg_namespace WHERE nspname = '" + self.getDbSchema() + "'")
        sRelnamespace = str(cursor.fetchone()[0])
        cursor.execute("SELECT oid FROM pg_class WHERE relname = '" + sTab + "' and relnamespace='" + sRelnamespace + "';")
        sObjoid = str(cursor.fetchone()[0])
        cursor.execute("SELECT ordinal_position FROM information_schema.columns WHERE table_schema = '" + self.getDbSchema() + "' AND table_name = '" + sTab + "' and column_name = '" + sCol + "'")
        sObjsubid = str(cursor.fetchone()[0])
        cursor.execute("SELECT description FROM pg_catalog.pg_description WHERE objsubid ='" + sObjsubid + "' AND objoid ='" + sObjoid + "'")
        try:
            sCommentColumn = str(cursor.fetchone()[0])
        except:
            sCommentColumn = ""
        return sCommentColumn

    # Hole alle Attribute zu einer Tabelle
    def getAttributnamen(self, cursor, sTab):
        if self.isSqlUnsafe(sTab):
            return None
        cursor.execute("SELECT column_name FROM information_schema.columns where table_schema='" + self.getDbSchema() + "' AND table_name = '" + sTab + "';")
        lstSqlRet = cursor.fetchall()
        if lstSqlRet == list():
            return None
        lstRet = list()
        for i in lstSqlRet:
            lstRet.append(i[0])
        return lstRet

    # Hole Anzahl aller Tabelleneintraege
    def getCountEntries(self, cursor, sTab):
        if self.isSqlUnsafe(sTab) :
            return None
        sSqlCmd = "SELECT count(*) from " + self.getDbSchema() + "."+sTab+";"
        cursor.execute(sSqlCmd)
        iCount = cursor.fetchone()[0]  # Antwort
        return iCount

    # Hole alle Tabelleneintraege
    def getWholeTable(self, cursor, sTab):
        if self.isSqlUnsafe(sTab) :
            return None
        sSqlCmd = "SELECT * from " + self.getDbSchema() + "."+sTab+";"
        cursor.execute(sSqlCmd)
        lstHeader = [head[0] for head in cursor.description]
        lstContent = cursor.fetchall()
        return (lstHeader, lstContent)

    # Check Datenbankverbindung
    def checkConnection(self):
        pn = self.__prnt.normal
        try:
            conn = psycopg2.connect("dbname='" + self.sDbName + "' user='" + self.sDbUser + "' password='" + self.sDbPw + "' host='" + self.sDbHost + "' port='" + self.sDbPort + "'")
            cursor = conn.cursor()
            cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = '"+self.getDbSchema()+"'")
            if cursor.fetchone() == None:
                raise NameError("Das Schema \""+self.getDbSchema()+"\" exisitert nicht.")
        except Exception as e:
            pn("Fehler (Test DB-Verbindung): " + str(e))
            return False
        return True

    # Hole einen Eintrag einer Tabelle
    def getTableEntry(self, cursor, sTab, sIdName, iId):
        if self.isSqlUnsafe([sTab,sIdName]) :
            return None
        sSqlCmd = "SELECT * from " + self.getDbSchema() + "."+sTab+" where "+sIdName+" = %s;"
        cursor.execute(sSqlCmd,[str(iId)])
        lstHeader = [head[0] for head in cursor.description]
        lstContent = cursor.fetchone()
        return (lstHeader, lstContent)

    # Lösche einen Eintrag in einer Tabelle
    def delTableEntry(self, cursor, sTab, iId):
        if self.isSqlUnsafe(sTab):
            return False
        sSqlCmd = "delete from " + self.__model.db.getDbSchema() + "."+sTab+" where id=%s;"
        cursor.execute(sSqlCmd, [str(iId)])
        return True

    # Eintrag in eine Tabelle vornehmen
    def insertIntoTable(self, cursor, sTab, dicIn):
        if self.isSqlUnsafe(sTab):
            return False
        sSqlCmdTeil1 = ""
        sSqlCmdTeil2 = ""
        sSqlVal = []
        # Durchlaufe alle Attribute und Werte
        for sAttribut, sWert in dicIn.items():
            if self.isSqlUnsafe(sAttribut):
                return False
            if sWert != "" and sWert is not None:
                sSqlCmdTeil1 += sAttribut + ","
                sSqlCmdTeil2 += "%s,"
                sSqlVal.append(sWert)
        # Sql-Cmd zusammenbauen
        sSqlCmd = "INSERT INTO " + self.__model.db.getDbSchema() + "." + sTab + \
                  "(" + sSqlCmdTeil1[:-1] + ") VALUES (" + sSqlCmdTeil2[:-1] + ") returning id;"
        # Führe Sql-Cmd aus
        cursor.execute(sSqlCmd, sSqlVal)
        return True

    # Verändere einen Eintrag in einer Tabelle
    def editTableEntry(self, cursor, sTab, sIdName, iId, dicEdit):
        if self.isSqlUnsafe([sTab, sIdName]):
            return False
        if sIdName in dicEdit: # Id-Attribut darf nicht mit verändert werden können
            self.__prnt.normal("Achtung: Id-Attribut darf nicht verändert werden: \"" + str(sIdName) + "\"")
            return False
        sSqlCmdTeil = ""
        sSqlVal = []
        # Durchlaufe alle Attribute und Werte
        for sAttribut, sWert in dicEdit.items():
            if self.isSqlUnsafe(sAttribut):
                return False
            if sWert != "" and sWert is not None:
                sSqlCmdTeil += sAttribut + "=%s,"
                sSqlVal.append(sWert)
        # Sql-Cmd
        sSqlCmd = "update " + self.__model.db.getDbSchema() + "." + sTab + " set " + sSqlCmdTeil[:-1] + " where " + sIdName + " = "+str(iId)+";"
        cursor.execute(sSqlCmd, sSqlVal)
        return True