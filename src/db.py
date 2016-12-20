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

import package as p
import version as v

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
    def __init__(self, name, version):
        self.name = name
        self.version = version

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
    return SPackage(name, v.Version(vers))

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
    conn.row_factory = sqlite3.Row
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

    def createPackage(self, package):
        self.cursor.execute('insert into packages values (%s, %s);',
                            package, 'unitialized')

        self.cursor.commit()

    def deletePackage(self, package):
        # sqlite3 will automatically clean the environment and path
        # tables for us.
        self.cursor.execute('delete from packages where package = %s;',
                            package)

        self.cursor.commit()

    # status is the packages current install status. One of
    # 'uninitialized', 'installing', or 'installed'.
    def setPackageStatus(self, package, status):
        self.cursor.execute('''
            update table packages set status = %s
            where package = %s;''', status, package)

    def packageExists(self, package):
        # Let's make sure we have record of the package
        self.cursor.execute('select * from packages where package = %s;',
                            package)

        if self.cursor.fetchone() is None:
            return False
        else:
            return True

    def addPackageEnv(self, package, varName, varValue,
                      varMode, varSep, build):
        if build:
            table = 'build_env'
        else:
            table = 'run_env'

        self.cursor.execute('''
            insert into %s (package, variable, value, mode, sep)
            values (%s, %s, %s, %s, %s);''', table, package, varName,
                            varValue, varMode, varSep)

        self.cursor.commit()

    def removePackageEnv(self, package, varName, varValue,
                         build):
        if build:
            table =  'build_env'
        else:
            table = 'run_env'

        self.cursor.execute('''
            delete from %s where
            package = %s and variable = %s and value = %s;''',
                            table, package, varName, varValue)

        self.cursor.commit()

    def getPackageEnv(self, package, varName=None, build=False):
        if build:
            table = 'build_env'
        else:
            table = 'run_env'

        if varName is None:
            self.cursor.execute('''
                select (variable, value, mode, sep) from %s
                where package = %s;''', table, package)

        else:
            self.cursor.execute('''
                select (package, variable, value, mode sep) from %s
                where package = %s and variable = %s''',
                                table, package, varName)

        return self.cursor.fetchall()
            

    def addPackageDep(self, package, dep):

        self.cursor.execute('''
            insert into dependancies (package, dependancy)
            values (%s, %s);''', package, dep)

        self.cursor.commit()

    def removePackageDep(self, package, dep):
        self.cursor.execute('''
            delete from dependancies where
            package = %s and dependancy = %s;''', package, dep)

        self.cursor.commit()

    def getPackageDeps(self, package):
        self.cursor.execute('''
            select (dependancy) from dependancies
            where package = %s;''', package)

        return self.cursor.fetchall()

    def addPackageBindir(self, package, dir):
        self.cursor.execute('''
            insert into bindirs (package, dir)
            values (%s, %s);''', package, dir)

        self.cursor.execute()

    def removePackageBindir(self, package, dir):
        self.cursor.execute('''
            delete from bindirs where
            package = %s and dir = %s;''', package, dir)

        self.cursor.commit()

    def getPackageBindirs(self, package):
        self.cursor.execute('''
            select (dir) from bindirs
            where package = %s;''', package)

        return self.cursor.fetchall()

    def addPackageLibdir(self, package, dir):
        self.cursor.execute('''
            insert into libdirs (package, dir)
            values (%s, %s);''', package, dir)

        self.cursor.execute()

    def removePackageLibdir(self, package, dir):
        self.cursor.execute('''
            delete from libdirs where
            package = %s and dir = %s;''', package, dir)

        self.cursor.commit()

    def getPackageLibdirs(self, package):
        self.cursor.execute('''
            select (dir) from libdirs
            where package = %s;''', package)

        return self.cursor.fetchall()

    def addPackageBinary(self, package, binary):
        self.cursor.execute('''
            insert into binaries (package binary)
            values (%s, %s);''', package, binary)

        self.cursor.commit()

    def removePackageBinary(self, package, binary):
        self.cursor.execute('''
            delete from binaries where
            package = %s and binary = %s;''', package, binary)

        self.cursor.commit()

    def getPackageBinaries(self, package):
        self.cursor.execute('''
            select (binary) from binaries
            where package = %s;''', package)

        return self.cursor.fetchall()
