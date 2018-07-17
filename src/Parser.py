# -*- coding: utf-8 -*-
'''
    Copyright (c) 2016-2018 The Cats Project

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
'''

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


class Tokenizer:
    def __init__(self):
        self.space = re.compile('[ \t\r\n]+')
        self.commentBegin = re.compile('/\*')
        self.commentEnd = re.compile('\*/')
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
    def tokenizeError(self, info):
        raise RuntimeError(info)
    def tokenize(self, data):
        tokens = []
        pos = 0
        while pos < len(data):
            m = self.space.match(data, pos)
            if m:
                pos = m.end()
                continue
            m = self.commentBegin.match(data, pos)
            if m:
                pos = m.end()
                m = self.commentEnd.search(data, pos)
                if not m:
                    self.tokenizeError('Unterminated comment')
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
                self.tokenizeError('Unknown token at ' + str(pos) + ': ' + data[pos])
        tokens.append(Token('End', '<End>'))
        return tokens


class Type:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

class TemplateType:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments
    def __str__(self):
        s = self.name + '('
        first = True
        for argument in self.arguments:
            if not first:
                s += ', '
            else:
                first = False
            s += str(argument)
        s += ')'
        return s

class FunctionType:
    def __init__(self, arguments, ret):
        self.arguments = arguments
        self.ret = ret
    def __str__(self):
        s = '('
        first = True
        for argument in self.arguments:
            if not first:
                s += ', '
            else:
                first = False
            s += argument[0] + ': ' + str(argument[1])
        s += ')'
        if self.ret is not None:
            s += ' -> ' + str(self.ret)
        return s

class EnumType:
    def __init__(self, name, type, enumerators):
        self.name = name
        self.type = type
        self.enumerators = enumerators
    def __str__(self):
        s = 'enum ' + self.name + ' : ' + str(self.type) + ' {\n'
        for enumerator in self.enumerators:
            s += '    ' + enumerator + ',\n'
        s += '}'
        return s

class StructType:
    def __init__(self, name, parent, members):
        self.name = name
        self.parent = parent
        self.members = members
    def __str__(self):
        s = 'struct ' + self.name
        if self.parent is not None:
            s += ' : ' + str(self.parent)
        s += ' {\n'
        for member in self.members:
            s += '    ' + member[0] + ': ' + str(member[1]) + '\n'
        s += '}'
        return s

class InterfaceType:
    def __init__(self, name, parent, members):
        self.name = name
        self.parent = parent
        self.members = members
    def __str__(self):
        s = 'interface ' + self.name
        if self.parent is not None:
            s += ' : ' + str(self.parent)
        s += ' {\n'
        for member in self.members:
            s += '    ' + member[0] + ': ' + str(member[1]) + '\n'
        s += '}'
        return s


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
                arguments = []
                first = True
                while self.token.type != ')':
                    if not first:
                        self.expectToken(',')
                        self.nextToken()
                    else:
                        first = False
                    arguments.append(self.parseType())
                self.nextToken()
                return TemplateType(name, arguments)
            else:
                return Type(name)
        elif self.token.type == '(':
            self.nextToken()
            arguments = []
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
                arguments.append((name, arg))
            self.nextToken()
            ret = None
            if self.token.type == '->':
                self.nextToken()
                ret = self.parseType()
            return FunctionType(arguments, ret)
        else:
            self.parseError()
    def parseStruct(self):
        type = self.token.data
        self.nextToken()
        self.expectToken('Identifier')
        name = self.token.data
        self.nextToken()
        parent = None
        if self.token.type == ':':
            self.nextToken()
            parent = self.parseType()
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
            return StructType(name, parent, members)
        else:
            return InterfaceType(name, parent, members)
    def parseEnum(self):
        self.nextToken()
        self.expectToken('Identifier')
        name = self.token.data
        self.nextToken()
        self.expectToken(':')
        self.nextToken()
        self.expectToken('Identifier')
        type = Type(self.token.data)
        self.nextToken()
        self.expectToken('{')
        self.nextToken()
        enumerators = []
        while self.token.type != '}':
            self.expectToken('Identifier')
            enumerators.append(self.token.data)
            self.nextToken()
            if self.token.type == '}':
                break
            elif self.token.type == ',':
                self.nextToken()
            else:
                self.parseError()
        self.nextToken()
        return EnumType(name, type, enumerators)
    def parse(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.token = self.tokens[0]
        while self.token.type != 'End':
            if self.token.type == 'Identifier':
                if self.token.data == 'enum':
                    print(self.parseEnum())
                    continue
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
