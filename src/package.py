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

class Package:
    def __init__(self, conf, packageDb, name, vers):
        self.db = packageDb
        self.name = name
        self.version = vers
        self.config = conf

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

    def envAddAppend(self, variable, value, sep, build):
        self.envAdd(variable, value, 'append', sep, build)

    def envAddPrepend(self, variable, value, sep, build):
        self.envAdd(variable, value, 'prepend', sep, build)

    def envAddSet(self, variable, value, build):
        self.envAdd(variable, value, 'overwrite', None, build)

    def envAdd(self, variable, value, mode, sep, build):
        self.db.addPackageEnv(self.name, self.version, variable, value,
                              mode, sep, build)
        
    def envRemove(self, variable, value, build):
        self.db.removePackageEnv(self.name, self.version, variable,
                                 value, build)
