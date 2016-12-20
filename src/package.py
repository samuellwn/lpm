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

import db

class Environment:
    class Variable:
        def __init__(self, values=[], mode="append", sep=None):
            self.mode = mode

            if mode == "append" or mode == "prepend":
                self.values = values
                if sep is None:
                    self.separator = ":"
                else:
                    self.separator = sep
            elif mode == "overwrite":
                self.value = value
            else:
                # blow up

        def addValue(self, value):
            if self.mode == "append":
                self.values.append(value)
            elif self.mode == "prepend":
                self.values.insert(0, value)
            elif self.mode == "overwrite":
                self.value = value

        def setValue(self, value):
            if self.mode == "overwrite":
                self.addValue(value):
            else:
                # blow up

        def get(self):
            if self.mode == "overwrite":
                return self.value
            else:
                result = ""
                for value in self.values:
                    result += value + self.sep
                return result[:-1] # strip the trailing separator

        def removeValue(self, value):
            self.values.remove(value)
            

    def __init__(self, getter, setter, remover):
        self.variables = {}
        self.getter = getter
        self.setter = setter
        self.remover = remover

    def _cache(self, name):
        if name not in self.variables:
            var = self.getter(name)
            if var is not None:
                self.variables[name] 

    def get(self, name):
        self._cache(name):
        return self.variables[name].get()

    def asDict(self):
        result = {}

        for name in self.variables:
            result[name] = self.variables[name].get()

        return result

    def addValue(self, name, value):
        self._cache(name)
        self.setter(name, value, self.variable[name].mode,
                    self.variable[name].separator)
        self.variable[name].addValue(value)

    def removeValue(self, name, value):
        self._cache(name)
        self.remover(name, value)
        self.variable[name].remove(value)

    def addVariable(self, name, values=[], mode="append", sep=None):
        self.setter(name, values, mode, sep)
        self.variable[name] = Variable(values, mode, sep)

    def removeVariable(self, name):
        for value in self.variables[name].values:
            self.remover(name, value)

        del self.variables[name]

class Package:
    def __init__(self, conf, packageDb, name, vers):
        self.db = packageDb
        self.name = name
        self.version = vers
        self.config = conf

        self.buildEnv = Environment()
        self.runEnv = Environment()
        self.depCache = []
        self.bindirCache = []
        self.libdirCache = []
        self.binaryCache = []

    def _buildEnvSetter(self, varName, varValue, varMode, varSep):
        self.db.addPackageEnv(self.name, self.version, varName,
                              varValue, varMode, varSep, build=True)

    def 

    def initialize(self):
        packageDir = Path(self.config.locations.packageDir)
        instDir = packageDir / self.name / self.version.safeStr()

        packageDir.mkdir(mode=self.config.install.permissions,
                         parents=True)
        instDir.mkdir(parents=True)

        self.db.setPackageStatus(self.name, self.version, 'installing')

    def addDep(self, dep):
        self.db.addPackageDep(self.name, self.version,
                              dep.name, dep.version)

    def removeDep(self, dep):
        self.db.removePackageDep(self.name, self.version,
                                 dep.name, dep.version)

    def addLibdir(self, dir):
        self.db.addPackageLibdir(self.name, self.version, dir)
        self.libdirCache.append(dir)

    def removeLibdir(self, dir):
        self.db.removePackageLibdir(self.name, self.version, dir)
        self.libdirCache.remove(dir)

    def addBindir(self, dir):
        self.db.addPackageBindir(self.name, self.version, dir)
        self.bindirCache.append(dir)

    def removeBindir(self, dir):
        self.db.removePackageBindir(self.name, self.version, dir)
        self.bindirCache.remove(dir)

    def addBinary(self, binary):
        self.db.addPackageBinary(self.name, self.version, binary)
        self.binaryCache.append(binary)

    def removeBinary(self, binary):
        self.db.removePackageBinary(self.name, self.version, binary)
        self.binaryCache.remove(binary)

    def getRunEnv(self):
        
