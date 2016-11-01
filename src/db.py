# The MIT License (MIT)
# Copyright (c) 2016 Samuel Loewen <samuellwn@samuellwn.org>

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from pathlib import Path
import logging

import package
import version

log = logger.getLogger(__name__)

# Use this for a list of dependancies so that sqlite3 knows how to
# automatically convert it to/from text for database storage.
# Format is the string representation of each dependancy separated by
# tabs.
class Deps(list):
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            depStrings = []
            for dep in self:
                depStrings.append(
                    dep.__conform__(sqlite3.PrepareProtocol))
            return '\t'.join(depStrings)

# Simple class used to represent a package. For internal use ONLY!! Do
# not confuse with package.Package, which is intended to manipulate
# packages. Sqlite3 string format is like so:
#     <self.name>;<str(version)>
class SPackage:
    def __init__(self, name, vers):
        self.name = name
        self.version = vers

    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return "%s;%s" % (self.name, str(self.version))

# Pass the configuration root in. The result will be a database object
# if the database configuration is sane. Will raise an exception
# otherwise.
def getDb(conf):
    if conf.packageDb.type == "sqlite3":
        sqlite3Setup()

        dbFile = Path(conf.packageDb.dbFile)

        if dbFile.exists():
            if dbFile.is_file():
                # TODO: handle empty files
                return openSqlite3Db(conf.packageDb.dbFile)
            else:
                log.critical("Sqlite3 DB (%s) is not a file",
                             conf.packageDb.dbfile);
        else:
            return createSqlite3Db(conf.packageDb.dbFile)

def sqlite3ConvertDeps(s):
    depStrings =  s.split('\t')

    deps = Deps()
    for dep in depStrings:
         deps.append(sqlite3ConvertPackage(dep))

    return deps

def sqlite3ConvertPackage(s):
    name, vers = s.decode().split(';')
    return SPackage(name, version.Version(vers))

def sqlite3ConvertPath(s):
    return Path(s.decode())

def sqlite3AdaptPath(path):
    path.resolve()
    return str(path)

def sqlite3Setup():
    import sqlite3

    # sqlite3.register_converter("deps", sqlite3ConvertDeps)
    sqlite3.register_converter("package", sqlite3ConvertPackage)

    sqlite3.register_adapter(Path, sqlite3AdaptPath)
    sqlite3.register_converter("path", sqlite3ConvertPath)

def sqlite3Connect(dbFile):
    return sqlite3.connect(dbFile, detect_types=sqlite3.PARSE_DECLTYPES)

def openSqlite3Db(conf):
    conn = sqlite3Connect(conf.packageDb.dbFile)
    cursor = conn.cursor()

    cursor.execute('select version from format_version;')
    formatVersion = cursor.fetchone()[0]

    if formatVersion <= 1:
        return Sqlite3V1(conn, cursor)
    else:
        log.critical("Sqlite3 DB (%s) format is not supported", dbFile)

def createSqlite3Db(conf):
    conn = sqlite3Connect(conf.packageDb.dbFile)
    cursor = conn.cursor()

    tableFile = open(conf.locations.dataDir + '/sql/sqlite3V1TablesCreate')
    tableScript = tableFile.read()
    tableFile.close()

    cursor.executescript(tableScript)

    cursor.commit()

    return Sqlite3V1(conn, cursor)

class Sqlite3V1:
    def __init__(self, conn, cursor):
        self.conn = conn
        self.cursor = cursor

    def createPackage(self, name, vers):
        self.cursor.execute('insert into packages values (%s, %s);',
                            SPackage(name, vers), 'unitialized')

        self.cursor.commit()

    def deletePackage(self, name, vers):
        tableName = name + vers.safeStr()

        # sqlite3 will automatically clean the environment and path
        # tables for us.
        self.cursor.execute('delete from packages where package = %s;',
                            SPackage(name, vers))

        self.cursor.commit()

    # status is the packages current install status. One of
    # 'uninitialized', 'installing', or 'installed'.
    def setPackageStatus(self, name, vers, status):
        pack = SPackage(name, vers)

        self.cursor.execute('update table packages set status = %s;',
                            status)

    def packageExists(self, name, vers):
        # Let's make sure we have record of the package
        pack = SPackage(name, vers)
        self.cursor.execute('select from packages where package = %s;',
                            pack)

        if self.cursor.fetchone() is None:
            return False
        else:
            return True

    def addPackageEnv(self, pName, pVersion, varName, varValue,
                      varMode, varSep, build):
        if build:
            table = 'build_env'
        else:
            table = 'run_env'

        pack = SPackage(pName, pVersion)

        self.cursor.execute('''
            insert into %s (package, variable, value, mode, sep)
            values (%s, %s, %s, %s, %s);''', table, pack, varName,
                            varValue, varMode, varSep)

        self.cursor.commit()

    def removePackageEnv(self, pName, pVersion, varName, varValue,
                         build):
        if build:
            table =  'build_env'
        else:
            table = 'run_env'

        pack = SPackage(pName, pVersion)

        self.cursor.execute('''
            delete from %s where
            package = %s and variable = %s and value = %s;''',
                            table, varName, varValue)

        self.cursor.commit()

    def addPackageDep(self, pName, pVersion, depName, depVersion):
        pack = SPackage(pName, pVersion)
        dep = SPackage(depName, depVersion)

        self.cursor.execute('''
            insert into dependancies (package, dependancy)
            values (%s, %s);''', pack, dep)

        self.cursor.commit()

    def removePackageDep(self, pName, pVersion, depName, depVersion):
        pack = SPackage(pName, pVersion)
        dep = SPackage(depName, depVersion)

        self.cursor.execute('''
            delete from dependancies where
            package = %s and dependancy = %s;''', pack, dep)

        self.cursor.commit()

    def addPackageBindir(self, name, vers, dir):
        pack = SPackage(name, vers)

        self.cursor.execute('''
            insert into bindirs (package, dir)
            values (%s, %s);''', pack, dir)

        self.cursor.execute()

    def removePackageBindir(self, name, vers, dir):
        pack = SPackage(name, vers)

        self.cursor.execute('''
            delete from bindirs where
            package = %s and dir = %s;''', pack, dir)

        self.cursor.commit()

    def addPackageLibdir(self, name, vers, dir):
        pack = SPackage(name, vers)

        self.cursor.execute('''
            insert into libdirs (package, dir)
            values (%s, %s);''', pack, dir)

        self.cursor.execute()

    def removePackageLibdir(self, name, vers, dir):
        pack = SPackage(name, vers)

        self.cursor.execute('''
            delete from libdirs where
            package = %s and dir = %s;''', pack, dir)

        self.cursor.commit()

    def addPackageBinary(self, name, vers, binary):
        pack = SPackage(name, vers)

        self.cursor.execute('''
            insert into binaries (package binary)
            values (%s, %s);''', pack, binary)

        self.cursor.commit()

    def removePackageBinary(self, name, vers, binary):
        pack = SPackage(name, vers)

        self.cursor.execute('''
            delete from binaries where
            package = %s and binary = %s;''', pack, binary)

        self.cursor.commit()
