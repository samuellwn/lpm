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

import os
import logging
import ply.lex as lex
import ply.yacc as yacc

# A special form of dictionary which allows using the form
# <dict>.<key> to access its values.
class Dict:
    def __init__(self, d={}):
        for key in d:
            self.set(key, d[key])

    def __iter__(self):
        return self.__dict__.iter()

    # Set a key to a specific value. If the key currently has
    # a Dict for its value, and the new value is a dict or Dict,
    # then the old and new values are merged, with the new value's
    # contents having precedence.
    def set(self, key, value):
        if key in self.__dict__ and type(self.__dict__[key]) == Dict and \
           (type(key) == dict or type(key) == Dict):
            self.__dict__[key].setFromDict(value)
        elif type(key) == dict:
            # if the key type is dict and we got here than the current value for
            # the key (if any) is not a Dict
            self.__dict__[key] = Dict(value)
        else:
            self.__dict__[key] = value

    # Merge the contents of d with the contents of self. The contents of d
    # have priority. d can be of type supporting dictionary-like access to
    # to its contents and iteration over its keys with its default iterator.
    def setFromDict(self, d):
        for key in d:
            self.set(key, d[key])

    def __setattr__(self, key, value):
        return self.set(key, value)

    def get(self, key):
        return self.__dict__[key]

_home = os.getenv("HOME")

defaultConfig = Dict()
defaultConfig.locations = Dict()
defaultConfig.locations.confDir = os.getenv("XDG_CONFIG_HOME", _home + "/.config") + "/lpm"
defaultConfig.locations.dataDir = os.getenv("XDG_DATA_HOME", _home + "/.local/share") + "/lpm"

defaultConfig.install = Dict()
defaultConfig.install.permissions = 0o755
defaultConfig.install.dir = defaultConfig.locations.dataDir + "/packages"

defaultConfig.packageDb = Dict()
defaultConfig.packageDb.type = 'sqlite3'
defaultConfig.packageDb.dbFile = defaultConfig.locations.dataDir + '/packages.db'

class ParseException(Exception):
    pass

# Config file parser. A config file is in the form of a series of variable
# assignments separated by semicolons or newlines. There are three forms of
# assignments:
#   <name> = <value>
#   <name> : <value>
#   <name> <value>
# A value is a string surrounded by double quotes, an integer, a list, or a
# dict. A list is of the form [<elem 1>, <elem 2>, ... ,<elem n>]. A dict is
# a series of variable assignments surrounded by braces '{}'. The variable
# assignments are of the same forms as their top level counterparts.
class ConfigFileParser:
    tokens = (
        'COMMENT',
        'ID',
        'LBRACE',
        'RBRACE',
        'LBRACKET',
        'RBRACKET',
        'STRING',
        'INT',
        'COMMA',
        'EQUALS',
        'COLON',
        'SEMICOLON',
    )

    t_ignore = ' \t'
    t_ignore_COMMENT = r'\#.*'
    t_ID = r'[A-Za-z_][0-9A-Za-z_]*'
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_COMMA = r','
    t_EQUALS = r'='
    t_COLON = r':'
    t_SEMICOLON = r';'

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_STRING(self, t):
        r'"(?:[^"]|\\")*"'
        t.value = t.value[1:-1]
        t.value = t.value.replace(r'\"', '"').replace(r'\\', '\\')
        return t

    def t_INT(self, t):
        r'(?:[1-9][0-9]*)|0|(?:0[oO][0-7]+)|(?:0[xX][0-9a-fA-F]+)|(?:0[bB][01]+)'
        t.value = int(t.value)
        return t

    def p_directives_collect(self, p):
        'directives : directive optsemi directives'
        p[0] = p[3]
        p[0][p[1]['id']] = p[1]['value']

    def p_directives_term(self, p):
        'directives : directive'
        p[0] = dict()
        p[0][p[1]['id']] = p[1]['value']

    def p_directive_delimited(self, p):
        """directive : name EQUALS value
                     | name COLON value"""
        p[0] = dict(id=p[1], value=p[3])

    def p_directive(self, p):
        'directive : name value'
        p[0] = dict(id=p[1], value=p[2])

    def p_name(self, p):
        '''name : ID
                | STRING'''
        p[0] = p[1]

    def p_value(self, p):
        """value : dict
                 | list
                 | STRING
                 | INT"""
        p[0] = p[1]

    def p_dict(self, p):
        'dict : LBRACE directives RBRACE'
        p[0] = p[2]

    def p_list(self, p):
        'list : LBRACKET elems RBRACKET'
        p[0] = p[2]

    def p_elems_collect(self, p):
        'elems : elems COMMA elem'
        p[0] = p[1]
        p[0].append(p[3])

    def p_elems_term(self, p):
        'elems : elem'
        p[0] = [p[1]]
        
    def p_elem(self, p):
        'elem : value'
        p[0] = p[1]

    def p_optsemi(self, p):
        '''optsemi : SEMICOLON
                   | empty'''
        pass

    def p_empty(self, p):
        'empty :'
        pass

    def p_error(self, t):
        #TODO: handle better
        raise ParseException("Config file parse error in line " + str(t.lineno) +  \
                             " with token '" + t.type + "' (" + str(t.value) + ")")

    def __init__(self):
        lexErrLog = logging.getLogger(__name__ + ".lexer")
        lexDebugLog = logging.getLogger(__name__ + ".lexer.debug")
        parseErrLog = logging.getLogger(__name__ + ".lexer")
        parseDebugLog = logging.getLogger(__name__ + ".lexer.debug")
        
        self.lexer = lex.lex(module=self, errorlog=lexErrLog, debug=lexDebugLog)
        self.parser = yacc.yacc(module=self, errorlog=parseErrLog, debug=parseDebugLog)

    def parseFile(self, f):
        file = open(f)
        try:
            return self.parser.parse(file.read(), lexer=self.lexer)
        finally:
            file.close()
        
    

