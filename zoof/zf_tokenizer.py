"""
Tokenizer for the experimental WIP Zoof lang. Written in a form that is
reproducable with minimal language requirements (e.g. no regexp) so
that it can be self-hosting relatively easy. The tokenizer splits
a code text into tokens (e.g. comments, strings, words, numbers, special
chars, etc.), which are then turned into an AST by the parser.
"""

keywords = ('import', 'export',
            'type', 'func', 'return', 'end',
            'for', 'while', 'if', 'elseif', 'else', 'with', 'do', 'done', 'continue', 'break',
            'try', 'catch', 'finally', 'throw', 'assert',
            'in', 'as',
            'and', 'or', 'not',
            'true', 'false',
            )

maybe_keywords = 'none', 'has', 'const', 'global', 'nonlocal', 'local', 'switch'

#operators = '=+*/^%!&|><'
operators = ('+', '-', '*', '/', '^', '%', '!', '&', '|', '>', '<',
             '==', '>=', '<=',
            )
assignment_operators = '=', '+=', '-=', '*=', '/='
operators += assignment_operators


class TYPES:
    _all = ('comment', 'identifier', 'keyword', 'number', 'string',
            'multilinestring', 'endofstatement', 'bracket', 'attr', 'sep',
            'operator', 'assign',
            'unterminated_string', 'unterminated_multilinestring', 'unknown'
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
    
    __slots__ = ['type', 'linenr', 'column', 'text']
    
    def __init__(self, type, linenr, column, text):
        assert type in TYPES._all, str(type) + ' is not a known token'
        self.type = type
        self.linenr = linenr
        self.column = column
        self.text = text
    
    def __repr__(self):
        text = repr(self.text)
        if len(text) > 50:
            text = 'too long'
        return '<Token %s %i:%i %s>' % (self.type, self.linenr, self.column, text)


def find_rest_of_comment(text, i):
    i_lim = len(text) - 1
    while i < i_lim:
        i += 1
        c = text[i]
        if c == '\n':
            break
    return i


def find_rest_of_identifier(text, i):
    i_lim = len(text) - 1
    while i < i_lim:
        i += 1
        c = text[i]
        if c.isalnum() or c == '_':
            continue
        break
    return i


def find_rest_of_number(text, i):
    i_lim = len(text) - 1
    can_have_dot = True
    while i < i_lim:
        i += 1
        c = text[i]
        if c.isdigit():
            continue
        elif c == '.' and can_have_dot:
            can_have_dot = False
            continue
        elif c in 'Ee':
            can_have_dot = False
            if i+1 <= i_lim and text[i+1].isdigit():
                i += 1
                continue
            if i+2 <= i_lim and text[i+1] in '-+' and text[i+2].isdigit():
                i += 2
                continue
            break
        break
    return i


def find_rest_of_string(text, i):
    escape = False
    i_lim = len(text) - 1
    while i < i_lim:
        i += 1
        c = text[i]
        if c == '\n':
            return i
        elif escape:
            continue
        elif c == '"':
            break
        elif c == '\\':
            escape = True
    return i + 1


def find_rest_of_multiline_string(text, i):
    escape = False
    count = 0
    i += 2
    i_lim = len(text) - 1
    while i < i_lim:
        i += 1
        c = text[i]
        if escape:
            continue
        elif c == '"':
            count += 1
            if count == 3:
                break
        elif c == '\\':
            escape = True
            count = 0
        else:
            count = 0
    return i + 1


def tokenize(text):
    """ Find tokens in the given text. This function never raises an exception
    (unless it contains a bug), e.g. it can process unterminated strings and
    invalid characters.
    """
    
    i = 0
    linenr = 1
    linestart = 0
    text_len = len(text)
    tokens = []
    token = None
    
    while i < text_len:
        
        c = text[i]
        
        if c in ' \t\r':
            i += 1 # todo: better deal with \r
        
        elif c == '\n':
            if tokens and tokens[-1].type != 'endofstatement':
                tokens.append(Token('endofstatement', linenr, i - linestart, '\n'))
            linenr += 1
            linestart = i  # count from 1 
            i += 1
        
        elif c == ';':
            if tokens and tokens[-1].type != 'endofstatement':
                tokens.append(Token('endofstatement', linenr, i - linestart, ';'))
            i += 1
        
        elif c == '#':
            i2 = find_rest_of_comment(text, i)
            token = Token('comment', linenr, i - linestart, text[i:i2])
            tokens.append(token)
            i = i2
        
        elif c.isalpha() or c == '_':
            i2 = find_rest_of_identifier(text, i)
            name = text[i:i2]
            if name in keywords:
                token = Token('keyword', linenr, i - linestart, name)
            else:
                token = Token('identifier', linenr, i - linestart, name)
            tokens.append(token)
            i = i2
        
        elif c.isdigit():
            i2 = find_rest_of_number(text, i)
            token = Token('number', linenr, i - linestart, text[i:i2])
            tokens.append(token)
            i = i2
        
        elif c == '"':
            if i + 2 < text_len and text[i:i+3] == '"""':
                i2 = find_rest_of_multiline_string(text, i)
                token = Token('multilinestring', linenr, i - linestart, text[i:i2])
                if token.text[:3] != token.text[-3:]:
                    token.type = 'unterminated_' + token.type
            else:
                i2 = find_rest_of_string(text, i)
                token = Token('string', linenr, i - linestart, text[i:i2])
                if token.text[0] != token.text[-1]:
                    token.type = 'unterminated_' + token.type
            tokens.append(token)
            if '\n' in token.text:
                linenr += token.text.count('\n')
                linestart = i - len(token.text.rsplit('\n', 1)[0])
            i = i2
        
        elif c in '([{}])':
            token = Token('bracket', linenr, i - linestart, c)
            tokens.append(token)
            i += 1
        
        elif c in '.':
            token = Token('attr', linenr, i - linestart, c)
            tokens.append(token)
            i += 1
        
        elif c in ',':
            token = Token('sep', linenr, i - linestart, c)
            tokens.append(token)
            i += 1
        
        elif c in operators:
            if i + 1 < text_len and text[i:i+2] in operators:
                c = text[i:i+2]
            name = 'assign' if c in assignment_operators else 'operator'
            tokens.append(Token(name, linenr, i - linestart, c))
            i += len(c)
        
        else:
            token = Token('unknown', linenr, i - linestart, text[i])
            tokens.append(token)
            i += 1
    
    return tokens


if __name__ == '__main__':
    
    EXAMPLE = '''
    a.b
    a ; b
    # this is a comment
    for i in range(10):
    meeh = 3 + 4;
    done ? @  `
    print("asdasd")
    
    """
    Func x does stuff
    """
    func xx()
    foo()
    end
    
    a += 3 >= 4
    
    '''
    
    '''
    "a
    "b'''
    
    print('py')
    for token in tokenize_py(EXAMPLE):
        print(repr(token))
    
    print('zoof')
    for token in tokenize(EXAMPLE):
        print(token)
