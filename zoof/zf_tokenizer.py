"""
Tokenizer for the experimental WIP Zoof lang. Written in a form that is
reproducable with minimal language requirements (e.g. no regexp) so
that it can be self-hosting relatively easy. The tokenizer splits
a code text into tokens (e.g. comments, strings, words, numbers, special
chars, etc.), which are then turned into an AST by the parser.

Policy wrt comments and whitespace: comments are included as tokens. a linestart
token is generated for lines that contain non-comment tokens. If the produced
list of tokens is not empty, the first token will be a linestart token. 
Unknown characters are wrapped in an unknown token. We do define an eof token
but this is mostly for internal use in the parser, the tokenizer will never 
generate it.

"""

import os

keywords = ('import', 'export',
            'type', 'func', 'return',
            'loop', 'while', 'if', 'elseif', 'else', 'with', 'do', 'continue', 'break',
            'try', 'catch', 'finally', 'throw', 'assert',
            'in', 'as',
            'and', 'or', 'not',
            'true', 'false',
            )

maybe_keywords = 'none', 'has', 'const', 'global', 'nonlocal', 'local', 'switch'

#operators = '=+*/^%!&|><'
operators = ('+', '-', '*', '/', '^', '%', '!', '&', '|', '>', '<',
             '==', '>=', '<=', '~',
            )
assignment_operators = '=', '+=', '-=', '*=', '/='
operators += assignment_operators


class TYPES:
    _all = ('comment', 'identifier', 'keyword', 'number', 'string',
            'multilinestring', 'statementsep', 'bracket', 'attr', 'sep',
            'operator', 'assign',
            'linestart', 'instr', 'unknown', 'eof',
            )

for token_name in TYPES._all:
    setattr(TYPES, token_name, token_name)


def tokenize_py(text):
    """Using Pythons tokenizer."""
    lines = text.lstrip().encode().splitlines()
    lines_iter = iter(lines)
    def readline():
        return lines_iter.__next__() or b';'
    import tokenize
    return [t for t in tokenize.tokenize(readline)][1:]


class Token:
    """Representation of a token in the text.
    """
    
    __slots__ = ['type', 'text', 'filename', 'linenr', 'column']
    
    def __init__(self, type, text, filename, linenr, column):
        assert type in TYPES._all, str(type) + ' is not a known token'
        self.type = type
        self.text = text
        self.filename = filename
        self.linenr = linenr
        self.column = column
    
    def __repr__(self):
        text = repr(self.text)
        if len(text) > 50:
            text = 'too long'
        return '<Token %s %i:%i %s>' % (self.type, self.linenr, self.column, text)
    
    def get_location_info(self):
        # todo: cache files
        if self.filename and os.path.isfile(self.filename):
            lines = open(self.filename, 'rb').read().decode().splitlines()
            if self.linenr > 0 and self.linenr <= len(lines):
                extra = '\n    ' + lines[self.linenr - 1] + '\n   ' + ' ' * self.column + '^'
                if self.linenr > 1:
                    extra = '\n    ' + lines[self.linenr - 2] + extra
                return extra
        return ''
    
    def show(self):
        print('%r%s' % (self, self.get_location_info()))

def find_rest_of_indent(text, i):
    i += 1
    while i < len(text):
        c = text[i]
        if c in ('\n', '#'):  # empty lines or commented lines do not count
            return i, False
        elif c not in ' \t':
            return i, True
        i += 1
    return i, False  # eof


def find_rest_of_comment(text, i):
    i += 1
    while i < len(text):
        c = text[i]
        if c == '\n':
            break
        i += 1
    return i


def find_rest_of_identifier(text, i):
    i += 1
    while i < len(text):
        c = text[i]
        if not (c.isalnum() or c == '_'):
            break
        i += 1
    return i


def find_rest_of_number(text, i):
    i += 1
    can_have_dot = True
    while i < len(text):
        c = text[i]
        if c.isdigit():
            pass
        elif c == '.' and can_have_dot:
            can_have_dot = False
        elif c in 'Ee':
            can_have_dot = False
            if i + 1 < len(text) and text[i + 1].isdigit():
                i += 1
            elif i + 2 < len(text) and text[i + 1] in '-+' and text[i + 2].isdigit():
                i += 2
            else:
                break
        else:
            break
        i += 1
    return i


def find_rest_of_string(text, i):
    # Returns (end-index, lines-skipped)
    escape = False
    lines_skipped = 0
    i += 1
    while i < len(text):
        c = text[i]
        i += 1
        if c == '\n':
            lines_skipped += 1
            j = i
            while j < len(text):
                c = text[j]
                j += 1
                if c in ' \t':
                    continue
                elif c == '"':
                    i = j + 1  # string continues on next line
                    break
                else:
                    return i, lines_skipped  # string runs to end of line
        elif escape:
            pass
        elif c == '"':
            break
        elif c == '\\':
            escape = True
    return i, lines_skipped


def find_rest_of_meta_or_compiler_instruction(text, i):
    
    if len(text) < i + 3:
        return 'unknown', i + 1
    
    if text[i+1] != '@':
        return 'unknown', i + 1
    
    i += 2
    while i < len(text):
        c = text[i]
        if not (c.isalnum() or c in '_.'):
            break
        i += 1
    return 'instr', i
    
# def find_rest_of_multiline_string(text, i):
#     escape = False
#     count = 0
#     i += 2
#     while i < len(text):
#         i += 1
#         c = text[i]
#         if escape:
#             continue
#         elif c == '"':
#             count += 1
#             if count == 3:
#                 break
#         elif c == '\\':
#             escape = True
#             count = 0
#         else:
#             count = 0
#     return i + 1


def tokenize(text, filename='', linenr_offset=1):
    """ Find tokens in the given text. This function never raises an exception
    (unless it contains a bug), e.g. it can process invalid characters.
    """
    
    i = 0
    linenr = linenr_offset
    linestart = 0
    text_len = len(text)
    tokens = []
    token = None
    loc = filename, linenr, 1
    
    # Process initial indent
    i, indent = find_rest_of_indent(text, -1)
    if indent:
        tokens.append(Token('linestart', text[:i], *loc))
    
    while i < text_len:
        loc = filename, linenr, i - linestart
        c = text[i]
        
        if c in ' \t':
            i += 1  # Note that \r will end up as an unknown character
        elif c == '\n':
            linenr += 1
            linestart = i  # count from 1 
            i2, indent = find_rest_of_indent(text, i)
            if indent:
                loc = filename, linenr, 1
                tokens.append(Token('linestart', text[linestart+1:i2], *loc))
            i = i2
        
        elif c == '#':
            i2 = find_rest_of_comment(text, i)
            token = Token('comment', text[i:i2], *loc)
            tokens.append(token)
            i = i2
        
        elif c.isalpha() or c == '_':
            i2 = find_rest_of_identifier(text, i)
            name = text[i:i2]
            if name in keywords:
                token = Token('keyword', name, *loc)
            else:
                token = Token('identifier', name, *loc)
            tokens.append(token)
            i = i2
        
        elif c.isdigit():
            i2 = find_rest_of_number(text, i)
            token = Token('number', text[i:i2], *loc)
            tokens.append(token)
            i = i2
        
        elif c == '"':
            i2, lines_skipped = find_rest_of_string(text, i)
            token = Token('string', text[i:i2], *loc)
            tokens.append(token)
            if lines_skipped > 0:
                linenr += lines_skipped
                linestart = i - len(token.text.rsplit('\n', 1)[-1])
            i = i2
        
        elif c in '([{}])':
            token = Token('bracket', c, *loc)
            tokens.append(token)
            i += 1
        
        elif c in '.':
            token = Token('attr', c, *loc)
            tokens.append(token)
            i += 1
        
        elif c in ',':
            token = Token('sep', c, *loc)
            tokens.append(token)
            i += 1
        
        elif c in operators:
            if i + 1 < text_len and text[i:i+2] in operators:
                c = text[i:i+2]
            name = 'assign' if c in assignment_operators else 'operator'
            tokens.append(Token(name, c, *loc))
            i += len(c)
        
        elif c == '@':
            kind, i2 = find_rest_of_meta_or_compiler_instruction(text, i)
            token = Token(kind, text[i:i2], *loc)
            tokens.append(token)
            i = i2
        
        else:
            token = Token('unknown', text[i], *loc)
            tokens.append(token)
            i += 1
    
    # tokens.append(Token('eof', '', *loc)
    return tokens

      
if __name__ == '__main__':
    
    EXAMPLE1 = '''
    func add(a, b) {
        @@wasm.f32.add(a, b)
    }
    '''
    
    EXAMPLE2 = '''
    a.b
    a ; b
    # this is a comment
    for i in range(10):
    meeh = 3 + 4;
    done ? @  `
    print("asdasd")
    
    "normal string"
    "multiline-single
    
    "multiline
    "multi
    
    " Func x does stuff
    " to x
    func xx()
    foo()
    end
    
    a += 3 >= 4
    
    loop i in 1:10
        foo()
    
    
    '''
    
    '''
    "a
    "b'''
    
    EXAMPLE = EXAMPLE1
    
    print('py')
    for token in tokenize_py(EXAMPLE):
        print(repr(token))
    
    print('zoof')
    for token in tokenize(EXAMPLE, __file__, 286):
        print(token)
