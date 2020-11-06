"""
The MIT License (MIT)
Copyright © 2018 Jean-Christophe Bos & HC² (www.hc2.fr)
"""

import re

class MustachTemplate :
    TOKEN_OPEN                = '{{'
    TOKEN_CLOSE                = '}}'
    TOKEN_OPEN_LEN            = len(TOKEN_OPEN)
    TOKEN_CLOSE_LEN            = len(TOKEN_CLOSE)
    
    def __init__(self, code) :
        self._code           = code
        self._pos            = 0
        self._endPos         = len(code)-1
        self._line           = 1
        self._pyGlobalVars    = { }
        self._pyLocalVars    = { }
        self._rendered        = ''

    def Validate(self, pyGlobalVars=None, pyLocalVars=None) :
        try :
            self._parseCode(pyGlobalVars, pyLocalVars, execute=False)
            return None
        except Exception as ex :
            return str(ex)

    def execute(self, pyGlobalVars=None, pyLocalVars=None) :
        try :
            self._parseCode(pyGlobalVars, pyLocalVars, execute=True)
            return self._rendered
        except Exception as ex :
            raise Exception(str(ex))

    def _parseCode(self, pyGlobalVars, pyLocalVars, execute) :
        if pyGlobalVars:
            self._pyGlobalVars.update(pyGlobalVars) 
        if pyLocalVars:
            self._pyLocalVars.update(pyLocalVars)
        self._rendered       = ''
        newTokenToProcess  = self._parseBloc(execute)
        if newTokenToProcess is not None :
            raise Exception( '"%s" instruction is not valid here (line %s)'
                             % (newTokenToProcess, self._line) )

    def _parseBloc(self, execute) :
        while self._pos <= self._endPos :
            c = self._code[self._pos]
            if c == MustachTemplate.TOKEN_OPEN[0] and \
                self._code[ self._pos : self._pos + MustachTemplate.TOKEN_OPEN_LEN ] == MustachTemplate.TOKEN_OPEN :
                self._pos    += MustachTemplate.TOKEN_OPEN_LEN
                tokenContent  = ''
                x               = self._pos
                while True :
                    if x > self._endPos :
                        raise Exception("%s is missing (line %s)" % (MustachTemplate.TOKEN_CLOSE, self._line))
                    c = self._code[x]
                    if c == MustachTemplate.TOKEN_CLOSE[0] and \
                       self._code[ x : x + MustachTemplate.TOKEN_CLOSE_LEN ] == MustachTemplate.TOKEN_CLOSE :
                       self._pos = x + MustachTemplate.TOKEN_CLOSE_LEN
                       break
                    elif c == '\n' :
                         self._line += 1
                    tokenContent += c
                    x              += 1
                self._processToken(tokenContent, execute)
                continue
            elif c == '\n' :
                self._line += 1
            if execute :
                self._rendered += c
            self._pos += 1
        return None

    def _processToken(self, tokenContent, execute) :
        tokenContent = tokenContent.strip()
        if execute :
            try :
                s = str( eval( tokenContent,
                               self._pyGlobalVars,
                               self._pyLocalVars ) )
                self._rendered += s
            except Exception as ex :
                raise Exception('%s (line %s)' % (str(ex), self._line))
