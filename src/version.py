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


import weakref
import re

# A prioritized list. Use insert(priority, item) to add an item at a specific priority.
# Use remove(item) to remove an item. Iterating over the list is according to priority.
# Priority must be a positive integer. Lower numbers mean a higher priority. Multiple
# items with the same priority are allowed. Iteration order is not garanteed between
# two items with the same priority.
class PriorityList(list):
    def insert(self, priority, item):
        if len(self) < priority or not self[priority]:
            self[priority] = [item]
        else:
            self[priority].append(item)

    def remove(self, item):
        # We redefined the iterator, we can't use for i in self here
        for i in range(0, len(self)):
            try:
                self[i].remove(item)
            except ValueError:
                pass
                
    def __iter__(self):
        self.currentIndex = 0
        self.currentSubIndex = 0
        return self

    def __next__(self):
        if self.currentIndex < 0:
            raise StopIteration()
        
        result = self[self.currentIndex][self.currentSubIndex]

        self.currentSubIndex += 1
        
        if self.currentSubIndex >= len(self[self.currentIndex]):
            self.currentSubIndex = 0
            self.currentIndex += 1

            if self.currentIndex >= len(self):
                self.currentIndex = -1

        return result

class VersionParseException(Exception):
    pass

class IncomparableException(Exception):
    pass

class VersionMeta(type):
    def __init__(self, name, bases, namespace, **kwds):
        if name != "Version":
            Version.versionHandlers.insert(kwds["priority"], weakref.ref(namespace))

# Base class for internal version storage. Creating an instance of
# Version will create an instance of the appropriate subclass that
# knows how to handle the version string you passed. Subclasses must
# be orderable. Subclasses must define the function __parse__ in their
# class body. The function will be passed the arguments passed to
# Version constructor. The first argument will be the version string
# to be parsed. This function must return an instance of the subclass
# if it knows how to handle the version string, and None if not.
# Subclasses must also define the special function __str__, and they
# must be able to parse the string it returns. Subclasses must define
# the function safeStr, which will called with no arguments to obtain
# a safe name for use in filenames and similar. This safe name must
# be unique between any type of version, and must consist of upper and
# lower case letters, numbers, and underscores only.
class Version(metaclass=VersionMeta):
    versionHandlers = PriorityList()
    
    def __new__(cls, versionString):
        for handlerRef in Version.versionHandlers:
            handler = handlerRef()
            if not handler:
                continue
            
            instance = handler.__parse__(versionString)
            if instance:
                return instance
            
        raise VersionParseException("Failed to parse version string: {0}".format(versionString))

# somepackage version 12.3.4-r1
class DottedNumberVersion(Version, priority=1):
    def __init__(self, numbers, patch, branch):
        self.numbers = numbers
        self.branch = branch

        if patch:
            match = re.match(r'([A-Za-z]+)([1-9][0-9]*)', patch)
            self.patchDesc = match.group(1)
            self.patchNumber = match.group(2)
        else:
            self.patchDesc = None
            self.patchNumber = None

            
    def __parse__(version):
        number = re.compile(r'([1-9][0-9]*|0)\.?')
        rest = re.compile(r'(?:-([A-Za-z]+[1-9][0-9]*))?\s*(?:\((\W+)\))?\s*$')

        numbers = []
        while True:
            match = number.match(version)
            if match:
                numbers.append(match.group(1))
                version = version[match.end():]
            else:
                return None

        match = rest.match(version)
        if match:
            patch = match.group(1)
            branch = match.group(2)
        else:
            return None

        return DottedNumberVersion(numbers, patch, branch)

    def __str__(self):
        numbers = '.'.join(self.numbers)
        if self.patchDesc is not None:
            patch = '-' + self.patchDesc + self.patchNumber
        else:
            patch = ''

        if len(self.branch) == 0:
            # We have no branch
            branch = ''
        else:
            # leading space intentional on first literal of next line
            branch = ' (' + self.branch + ')'

        return numbers + patch + branch

    def safeStr(self):
        numbers = '_'.join(self.numbers)
        if self.patchDesc is not None:
            patch = self.patchDesc + self.patchNumber
        else:
            patch = ''

        return 'dn_' + numbers + patch + self.branch
