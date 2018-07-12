import enum
import os
import re
import sys


class Token:
    def __init__(self, type, data):
        self.type = type
        self.data = data
    def __str__(self):
        return '({}, {})'.format(self.type, self.data)

class Type:
    class Type(enum.Enum):
        TYPE = 'type'
        TEMPLATE = 'template'
        FUNCTION = 'function'
        STRUCT = 'struct'
        INTERFACE = 'interface'
    def __init__(self, type, name, args = None, ret = None):
        self.type = type
        self.name = name
        self.args = args
        self.ret = ret
    def __str__(self):
        if self.type == Type.Type.TYPE:
            s = self.name
        elif self.type == Type.Type.TEMPLATE:
            s = self.name + '('
            first = True
            for arg in self.args:
                if not first:
                    s += ', '
                else:
                    first = False
                s += str(arg)
            s += ')'
        elif self.type == Type.Type.FUNCTION:
            s = '('
            first = True
            for arg in self.args:
                if not first:
                    s += ', '
                else:
                    first = False
                s += arg[0] + ': ' + str(arg[1])
            s += ')'
            if self.ret is not None:
                s += ' -> ' + str(self.ret)
        elif self.type == Type.Type.STRUCT or self.type == Type.Type.INTERFACE:
            if self.type == Type.Type.STRUCT:
                s = 'struct '
            else:
                s = 'interface '
            s += self.name + ' {\n'
            for arg in self.args:
                s += '    ' + arg[0] + ': ' + str(arg[1]) + '\n'
            s += '}'
        else:
            s = '<Unknown>'
        return s

class Tokenizer:
    def __init__(self):
        self.space = re.compile('[ \t\r\n]+')
        self.tokenTypes = [
            ('Identifier', '[A-Z_a-z][0-9A-Z_a-z]*'),
            ('(', '\('),
            (')', '\)'),
            (',', ','),
            (':', ':'),
            (';', ';'),
            ('{', '{'),
            ('}', '}'),
            ('->', '->'),
        ]
        self.regexs = []
        for tokenType in self.tokenTypes:
            self.regexs.append(re.compile(tokenType[1]))
    def tokenize(self, data):
        tokens = []
        pos = 0
        while pos < len(data):
            m = self.space.match(data, pos)
            if m:
                pos = m.end()
                continue
            match = False
            for i in range(0, len(self.regexs)):
                regex = self.regexs[i]
                result = regex.match(data, pos)
                if result:
                    tokens.append(Token(self.tokenTypes[i][0], data[pos : result.end()]))
                    pos = result.end()
                    match = True
                    break
            if not match:
                raise RuntimeError('Unknown token at ' + str(pos) + ': ' + data[pos])
        tokens.append(Token('End', '<End>'))
        return tokens

class Parser:
    def nextToken(self):
        self.pos += 1
        self.token = self.tokens[self.pos]
    def parseError(self):
        raise RuntimeError('Unexpected token ' + str(self.token.data))
    def expectToken(self, type):
        if self.token.type != type: self.parseError()
    def parseType(self):
        if self.token.type == 'Identifier':
            name = self.token.data
            self.nextToken()
            if self.token.type == '(':
                self.nextToken()
                args = []
                first = True
                while self.token.type != ')':
                    if not first:
                        self.expectToken(',')
                        self.nextToken()
                    else:
                        first = False
                    args.append(self.parseType())
                self.nextToken()
                return Type(Type.Type.TEMPLATE, name, args)
            else:
                return Type(Type.Type.TYPE, name)
        elif self.token.type == '(':
            self.nextToken()
            args = []
            first = True
            while self.token.type != ')':
                if not first:
                    self.expectToken(',')
                    self.nextToken()
                else:
                    first = False
                self.expectToken('Identifier')
                name = self.token.data
                self.nextToken()
                self.expectToken(':')
                self.nextToken()
                arg = self.parseType()
                args.append((name, arg))
            self.nextToken()
            ret = None
            if self.token.type == '->':
                self.nextToken()
                ret = self.parseType()
            return Type(Type.Type.FUNCTION, None, args, ret)
        else:
            self.parseError()
    def parseStruct(self):
        type = self.token.data
        self.nextToken()
        self.expectToken('Identifier')
        name = self.token.data
        self.nextToken()
        self.expectToken('{')
        self.nextToken()
        members = []
        while self.token.type != '}':
            self.expectToken('Identifier')
            memberName = self.token.data
            self.nextToken()
            self.expectToken(':')
            self.nextToken()
            memberType = self.parseType()
            self.expectToken(';')
            self.nextToken()
            members.append((memberName, memberType))
        self.nextToken()
        if type == 'struct':
            return Type(Type.Type.STRUCT, name, members)
        else:
            return Type(Type.Type.INTERFACE, name, members)
    def parse(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.token = self.tokens[0]
        while self.token.type != 'End':
            if self.token.type == 'Identifier':
                if self.token.data == 'struct' or self.token.data == 'interface':
                    print(self.parseStruct())
                    continue
            self.parseError()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage:')
        print('    Parser <file>')
        exit(1)
    with open(sys.argv[1], 'r') as file:
        data = file.read()
    
    tokenizer = Tokenizer()
    tokens = tokenizer.tokenize(data)
    parser = Parser()
    parser.parse(tokens)