"""
Parser for the experimental WIP Zoof lang. It takes the tokens produced
by the tokenizer and converts them in an abstract syntax tree (AST) in the
form of nested expression objects, which can be compiled to WASM.

Some expressions consist of multiple parts and keywords, e.g. ``if ... else ...``.
We can either handle an if in its own code, or keep parsing tokens and when
encountering an else check whether it makes sense.
"""

# Recursive descent
# http://eli.thegreenplace.net/2012/08/02/parsing-expressions-by-precedence-climbing


import os

from zf_tokenizer import Token, tokenize, TYPES


class ZoofSyntaxError(SyntaxError):
    
    def __init__(self, token, msg):
        at = ' at line %i:%i' % (token.linenr, token.column)
        super().__init__(msg + at)


class Expr:
    """ Class to hold expressions. This system is inspired by that of Julia.
    Each Expression object represents a node in the AST tree. Each Expression
    has a kind, indicating the kind of expression, a list of args, and a type
    that indicates the "return type". The kind of args depends on the kind of
    expression:
    
    * block: expressions
    * assign: target-exp (identifier or tuple), expression
    * if: expr for test, body-block, else-block
    * identifier: the name
    * call: expression (often an identifier), arg1-expr, arg2-expr, ...
    """
    
    KINDS = ['block', 'assign', 'if', 'for', 'do', 'identifier', 'call',
             'literal',  # or a literal for each kind?
             'index', # or subscript?
             'bracethingy',  # group or tuple, not known at creation time
             ]
    
    def __init__(self, kind, *args):
        assert kind in self.KINDS
        self.kind = kind
        self.args = list(args)
    
    def __repr__(self):
        return '<Expr %s with %i args>' % (self.kind, len(self.args))
    
    def show(self, indent=0):
        print('    ' * indent + repr(self))
        for arg in self.args:
            if isinstance(arg, Expr):
                arg.show(indent + 1)
            else:
                e = repr(arg)
                if len(e) > 50:
                    e = e[:50] + '...'
                print('    ' * (indent + 1) + e)


class RecursiveDescentParser:
    """ Base class for recursive descent parsers """
    
    def __init__(self):
        self.token = None  # The current token under cursor
        self.tokens = None  # Iterable of tokens
        self._look_ahead = []

    def init_lexer(self, tokens):
        """ Initialize the parser with the given tokens (an iterator) """
        self.token_index = 0
        self.tokens = tokens
        self.token = self.tokens[self.token_index]
        self._look_ahead = []

    def error(self, msg):
        """ Raise an error at the current location """
        raise ZoofSyntaxError(self.token, msg)

    @property
    def current_location(self):
        return self.token.linenr, self.token.column

    # Lexer helpers:
    def consume(self, typ=None):
        """ Assert that the next token is typ, and if so, return it.

        If typ is a list or tuple, consume one of the given types.
        If typ is not given, consume the next token.
        """
        if typ is None:
            typ = self.peak

        expected_types = typ if isinstance(typ, (list, tuple, set)) else [typ]

        if self.peak in expected_types:
            return self.next_token()
        else:
            expected = ', '.join(expected_types)
            self.error(
                'Expected {0}, got "{1}"'.format(expected, self.peak))

    def has_consumed(self, typ):
        """ Checks if the look-ahead token is of type typ, and if so
            eats the token and returns true """
        if self.peak == typ:
            self.consume()
            return True
        return False

    def next_token(self):
        """ Advance to the next token """
        tok = self.token
        if self._look_ahead:
            self.token = self._look_ahead.pop(0)
        else:
            self.token_index += 1
            if self.token_index >= len(self.tokens):
                self.token = Token('eof', self.token.linenr, self.token.column, '')
            else:
                self.token = self.tokens[self.token_index]
        return tok

    def not_impl(self):  # pragma: no cover
        """ Call this function when parsing reaches unimplemented parts """
        raise CompilerError('Not implemented', loc=self.token.loc)

    @property
    def peak(self):
        """ Look at the next token to parse without popping it """
        if self.token:
            return self.token.type

    @property
    def peak_kw(self):
        """ Look at the next keyword token to parse without popping it """
        if self.token:
            return self.token.text if self.token.type == 'keyword' else ''
    
    def look_ahead(self, amount):
        """ Take a look at x tokens ahead """
        if amount > 0:
            while len(self._look_ahead) < amount:
                next_token = next(self.tokens, None)
                if next_token is None:
                    return
                self._look_ahead.append(next_token)
            return self._look_ahead[amount - 1]
        else:
            return self.token

    @property
    def at_end(self):
        return self.peak is None


class Parser(RecursiveDescentParser):
    """
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.stack = []
        self.one_liner = False
        self.exp = None
        self.pending = []  # todo: check validity each time that we add to it
        self.indent = 0
    
    def push(self, exp):
        """ Push expression on stack.
        """
        assert isinstance(exp, Expr)
        self.exp = exp
        self.pending = []
        self.stack.append((self.exp, self.pending))
        return exp
    
    def pop(self):
        """ Pop expression from stack.
        """
        assert len(self.pending) == 0
        exp = self.exp  # == self.stack[-1][0]
        self.stack.pop()
        if len(self.stack) > 0:
            self.exp, self.pending = self.stack[-1]  # todo: ugly
        else:
            self.exp, self.pending = None, []  # done
        return exp
    
    def finish_pending(self):
        """ Resolve pending expression chain and add to args.
        """
        if self.pending:
            self.exp.args.append(_resolve_expressions(self.pending))
            self.pending.clear()
            # self.exp_count += 1

    def parse(self, tokens):
        """ Parse a series of tokens.
        """
        self.init_lexer(tokens)
        self.reset()
        
        root = self.parse_expressions()
        
        # Wrap up
        if len(self.stack) > 0:
            raise ZoofSyntaxError(token, 'Code is incomplete')
        assert not self.pending
        #assert not root.args
        #self.finish_pending()
        return root
    
    ## The parse functions
    
    def parse_expression(self):
        """ Process tokens untill we have a full expression.
        """
        if self.at_end:
            self.error('Unexpected end of file.')
        
        assert len(self.pending) == 0
        
        while True:
            if self.peak == TYPES.linestart:
                self.error('Was not expecting a new line here')
            
            token_type = self.peak
            if token_type == TYPES.keyword:
                # Keyword - start or shape a construct
                kw = self.peak_kw
                if kw == 'if':
                    self.parse_if()
                elif kw == 'loop':
                    assert False
            elif token_type == TYPES.assign: # todo: maybe = should also be an operator, can take part in precedence climbing
                self.parse_assign()
            elif token_type == TYPES.operator:
                self.parse_operator()
            elif token_type in ('number', 'string'):
                self.parse_literal()
            elif token_type == TYPES.identifier:  # todo: rename identifier to symbol
                self.parse_identifier()
            elif token_type == TYPES.bracket:
                self.parse_bracket()
            elif token_type == TYPES.attr:
                # Attribute access. We don't call it an operator
                raise NotImplementedError()
            elif token_type == TYPES.sep:
                # Separator for tuples and function arguments
                raise NotImplementedError()
            elif token_type == TYPES.comment:
                pass  # no action needed
            elif token_type == TYPES.unknown:
                raise ZoofSyntaxError(self.token, 'Unknown token')
            elif token_type == 'eof':
                break
            else:
                raise ZoofSyntaxError(self.token, 'Unexpected %s token' % token_type)
            
            # We must have encountered an expression now
            if len(self.pending) == 0:
                if self.peak == TYPES.keyword:
                    self.error('Expected an expression, not a keyword')
                else:
                    self.error('Expected an expression, not %s' % self.peak)
            
            # Can we finish the exression?
            if self.peak in (TYPES.linestart, TYPES.eof, TYPES.keyword):
                self.finish_pending()
                break
    
    def parse_expression_and_wrap(self):
        """ Pasre expression and wrap it in a block expression.
        """
        stacksize = len(self.stack)
        self.push(Expr('block'))
        self.parse_expression()
        exp = self.pop()
        assert len(self.stack) == stacksize
        return exp
    
    def parse_expressions(self):
        """ Parse a series of expressions, which are each on a line.
        Does not consume the final (dedented) newline token.
        """
        assert self.peak == TYPES.linestart
        prev_indent = self.indent
        self.indent = indent = len(self.token.text)
        
        stacksize = len(self.stack)
        self.push(Expr('block'))
        # assert self.exp.kind == 'block'
        
        while True:
            self.consume(TYPES.linestart)
            if self.peak == TYPES.comment:
                self.consume(TYPES.comment)
            elif self.peak == TYPES.eof:
                break
            else:
                self.parse_expression()
            # todo: lines with comments
            if self.peak == TYPES.linestart:
                token = self.token  #self.consume(TYPES.linestart)  # todo: is consumed at start end end of a block!
                self.one_liner = False
                ind = len(token.text) - self.indent
                if ind > 0:
                    self.error('Unexpected indent.')
                elif ind < 0:
                    if len(token.text) != prev_indent:
                        self.error('Unexpected dedent.')
                    else:
                        break
            elif self.peak == 'eof':
                break
            else:
                self.error('huh')
        
        assert indent == self.indent
        self.indent = prev_indent
        exp = self.pop()
        assert len(self.stack) == stacksize
        return exp
    
    def parse_body(self, context, need_nl_or_do=True):
        """ Parse the body of a construct, which can be a do with one
        expression, or a newline followed by multiple expressions.
        """
        if self.peak == TYPES.linestart:
            self.parse_expressions()
        elif self.peak_kw == 'do':
            self.one_liner = True
            self.consume(TYPES.keyword)
            self.parse_expression_and_wrap()
        elif not need_nl_or_do:
            self.one_liner = True
            self.parse_expression_and_wrap()
        else:
            self.error('Expecting newline or do-keyword before body in %s expression.' % context)
    
    def consume_if_kw_skip_newline(self, kw):
        i = self.token_index
        if self.peak == TYPES.linestart:
            i += 1
        if i < len(self.tokens):
            if self.tokens[i].type == TYPES.keyword and self.tokens[i].text == kw:
                self.token_index = i + 1
                self.token = tokens[self.token_index]
                return True
        return False
    
    def parse_if(self):
        self.push(Expr('if'))
        assert self.consume(TYPES.keyword).text == 'if'
        # Get test-expression and corresponding body
        self.parse_expression()
        self.parse_body('if')
        # Get any elseif clauses
        while self.consume_if_kw_skip_newline('elseif'):
            self.parse_expression()
            self.parse_body('elseif')
        if self.consume_if_kw_skip_newline('else'):
            self.parse_body('else', False)
        self.pending.append(self.pop())
    
    def parse_literal(self):
        token = self.consume()  # number or string
        if self.pending and isinstance(self.pending[-1], Expr):
            raise ZoofSyntaxError(token, 'Unexpected %s literal' % token.type)
        self.pending.append(Expr('literal', token.text))
    
    def parse_identifier(self):  # aka names/labels/symbols/identifiers
        token = self.consume(TYPES.identifier) 
        if self.pending and isinstance(self.pending[-1], Expr):
            raise ZoofSyntaxError(token, 'Unexpected identifier')
        self.pending.append(Expr('identifier', token.text))
    
    def parse_assign(self):
        token = self.consume(TYPES.assign) 
        if self.exp.kind != 'block':
            raise ZoofSyntaxError(token, 'Unexpected assignment')
        elif len(self.pending) != 1:
            raise ZoofSyntaxError(token, 'Assignment needs something to its left.')
        elif self.pending[0].kind == 'identifier':
            dest = self.pending[0]
            exp = Expr('assign', dest)
            self.pending[0] = exp
            if token.text != '=':
                # Aug assignn - wrap in an extra call
                funcname = opcallmap[token.text[0]]
                subexp = Expr('call', Expr('identifier', funcname), dest)
                exp.args.append(subexp)
                exp = subexp
            self.push(exp)
            self.parse_expression()
            self.pop()
            # current.need_arg = True  # So that we can add it when the exp is ended
        else:
            raise ZoofSyntaxError(token, 'Assignment needs identifier to its left.')

    def parse_operator(self):
        # Operators can be unary, operating on two operands, or chained
        token = self.consume(TYPES.operator)
        if not self.pending:
            # unary
            if token.text not in ('+', '-'):
                raise ZoofSyntaxError(token, 'Only + and - can be unary operators')
            self.pending.append(token.text)
        else:
            # binary
            if not isinstance(self.pending[-1], Expr):
                raise ZoofSyntaxError(token, 'Unexpected operator')
            self.pending.append(token.text)
    
    def parse_bracket(self):
        token = self.consume(TYPES.bracket)
        if token.text == '(':
            # Start of a call, expression-group or tuple
            if self.pending and isinstance(self.pending[-1], Expr):
                # call
                exp = Expr('call', self.pending[-1])
                self.pending[-1] = exp
                self.push(exp)
                self.parse_expression()
                if self.consume(TYPES.bracket).text != ')':
                    self.error('Expected closing bracket ")".')
                self.finish_pending()
                self.pop()
            else:
                # expression group or tuple
                exp = Expr('bracethingy')  # todo: dissolve this into the exp that represents the internal operator
                self.push(exp)
                self.parse_expression()
                if self.consume(TYPES.bracket).text != ')':
                    self.error('Expected closing bracket ")".')
                self.finish_pending()
                self.pop()
        
        elif token.text == '[':
            # Start of subscript - take place of last exp in chain
            if not (self.pending and isinstance(self.pending[-1], Expr)):
                raise ZoofSyntaxError(token, 'Unexpected subscript start')
            exp = Expr('index', self.pending[-1])
            self.pending[-1] = exp
            push(exp)
            self.parse_expression()
            if self.consume(TYPES.bracket).text != ']':
                self.error('Expected closing bracket "]".')
            self.finish_pending()
            self.pop()
        
        elif token.text in '{}':
            # Start or end of dict/set literal
            raise NotImplementedError()
        else:
            raise ZoofSyntaxError('Unknown bracket type %s' % token.text)


if __name__ == '__main__':
    
    EXAMPLE = """
    # asd
    a = 3
    a += 2
    if a > 2
        b = 1
    else
        b = 3
    
    # if a > 2 do b = 1 else b = 3
    
    """
    
    tokens = tokenize(EXAMPLE)
    
    p = Parser()
    ast = p.parse(tokens)
    # ast = parse(tokens)
    
    #print(ast)
    ast.show()
