"""
Parser for the experimental WIP Zoof lang. It takes the tokens produced
by the tokenizer and converts them in an abstract syntax tree (AST) in the
form of nested expression objects, which can be compiled to WASM.
"""

import os

from zf_tokenizer import tokenize, TYPES


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


# ---------------------


opcallmap = {'+': 'add', '-': 'subtract', '*': 'mult', '/': 'div',
             '==': 'equals', '>': 'gt', '<': 'lt',
             }

# ops for which multiple args can be combined into a single call with > 2 args
multiops = 'add', 'subtract', 'mult', 'div'


def _resolve_expressions(expression_chain):
    """ Given a chain of intermittend expressions and operators, resolve it
    into single expression by taking priority rules into account.
    """
    chain = expression_chain.copy()
    for ops in [('*', '/'), ('+', '-'), ('==', '>', '<', '>=', '<=')]:
        i = 0
        while i < len(chain):
            if chain[i] in ops:
                funcname = opcallmap[chain[i]]
                if i == 0:
                    # unary
                    assert isinstance(chain[i+1], Expr)
                    e = Expr('call', Expr('identifier', funcname), chain[i+1])
                    chain = [e] + chain[2:]
                    i += 1
                elif (funcname in multiops and chain[i-1].kind == 'call' and
                      chain[i-1].args[0].kind == 'identifier' and chain[i-1].args[0].args[0] == funcname):
                    # binary +
                    chain[i-1].args.append(chain[i+1])
                    chain = chain[:i] + chain[i+2:]
                    i + 1
                else:
                    # binary
                    assert isinstance(chain[i-1], Expr)
                    assert isinstance(chain[i+1], Expr)
                    e = Expr('call', Expr('identifier', funcname), chain[i-1], chain[i+1])
                    chain = chain[:i-1] + [e] + chain[i+2:]
                    i += 0
            else:
                i += 1
    assert len(chain) == 1 and isinstance(chain[0], Expr)
    return chain[0]


def parse(tokens):
    """ Parse a series of tokens into an AST. The leaf nodes often/always/sometimes?
    are the tokens.
    """
    
    # A queue for unfinished expressions. Can contain single expressions, or a
    # chain of interleaves expressions and operators. Is resolved into a single
    # expression when its "ended".
    expression_chain = []
    
    # List of expressions for the current "block"
    expressions = []
    
    # Root element, a block of expressions
    root = Expr('block')
    
    # The stack of expressions and expression chains
    stack = [(root, None, None)]
    
    # current_exp = None  # to collect tokens until they form an expression
    await_one_exp = False  # When collecting stuff after if, for, etc.
    
    def finish_exp():
        """ Resolve expression chain and add to expressions.
        """
        # nonlocal current_exp
        if expression_chain:
            expressions.append(_resolve_expressions(expression_chain))
        expression_chain.clear()
        # current_exp = None
    
    def push(e):
        """ Push expression on stack (plus the expression_chain and expressions
        that it is part of).
        """
        nonlocal expressions, expression_chain
        assert isinstance(e, Expr)
        stack.append((e, expression_chain, expressions))
        expressions = []
        expression_chain = []
    
    def pop():
        """ Pop expression from stack and restore expressions and expression chain.
        """
        nonlocal expressions, expression_chain
        # assert len(expressions) == 0 and len(expression_chain) == 0
        e, expression_chain, expressions = stack.pop(-1)
        return e
    
    def peek(i=1):
        return stack[-i][0]
    
    for i, token in enumerate(tokens):
        
        if token.type == TYPES.endofstatement:
            finish_exp()
            # Handle the few expressions that are actually statements (assignments and imports)
            exp = peek()
            if exp.kind == 'assign':  # also for import
                if len(expressions) != 1:
                    raise ZoofSyntaxError(token, 'Assign must have one expression to its right.')
                if len(exp.args) == 2 and exp.args[1].kind == 'call':  # += or other
                    exp.args[1].args.append(expressions[0])
                else:
                    exp.args.append(expressions[0])
                pop()
                finish_exp()
        
        elif token.type == TYPES.assign:
            # Assignment
            if peek().kind != 'block':
                raise ZoofSyntaxError(token, 'Unexpected assignment')
            elif not expression_chain:
                raise ZoofSyntaxError(token, 'Assignment needs something to its left.')
            elif expression_chain[0].kind == 'identifier':
                exp = Expr('assign', expression_chain[0])
                if token.text != '=':
                    funcname = opcallmap[token.text[0]]
                    subexp = Expr('call', Expr('identifier', funcname), expression_chain[0])
                    exp.args.append(subexp)
                expression_chain[0] = exp  # end arg is given in endofstatement handler
                push(exp)
            else:
                raise ZoofSyntaxError(token, 'Assignment needs identifier to its left.')
        
        elif token.type == TYPES.operator:
            # Operators, can be unary, operating on two operands, or chained
            if not expression_chain:
                # unary
                if token.text not in ('+', '-'):
                    raise ZoofSyntaxError(token, 'Only + and - can be unary operators')
                expression_chain.append(token.text)
            else:
                # binary
                if not isinstance(expression_chain[-1], Expr):
                    raise ZoofSyntaxError(token, 'Unexpected operator')
                expression_chain.append(token.text)
        
        elif token.type in ('number', 'string', 'multilinestring'):
            if expression_chain and isinstance(expression_chain[-1], Expr):
                raise ZoofSyntaxError(token, 'Unexpected %s literal' % token.type)
            expression_chain.append(Expr('literal', token.text))
        
        elif token.type == TYPES.identifier:  # todo: rename identifier to symbol
            if expression_chain and isinstance(expression_chain[-1], Expr):
                raise ZoofSyntaxError(token, 'Unexpected identifier')
            expression_chain.append(Expr('identifier', token.text))
        
        elif token.type == TYPES.bracket:
            
            if token.text == '(':
                # Start of a call, expression-group or tuple
                if expression_chain and isinstance(expression_chain[-1], Expr):
                    # call
                    exp = Expr('call', expression_chain[-1])
                    expression_chain[-1] = exp
                    push(exp)
                else:
                    # expression group or tuple
                    exp = Expr('bracethingy')
                    push(exp)
            elif token.text == ')':
                # End of call, expression group, tuple
                exp = peek()
                if exp.kind == 'call':
                    assert len(exp.args) == 1
                    finish_exp()
                    if len(expressions) != 1:
                        raise ZoofSyntaxError(token, 'Call must contain exactly one expression')
                    exp.args.append(expressions[0])
                    pop()
                elif exp.kind == 'bracethingy':
                    finish_exp()
                    if len(expressions) != 1:
                        raise ZoofSyntaxError(token, 'Brace group must have exactly one expression')
                    e = expressions[0]
                    pop()
                    expression_chain.append(e)
                else:
                    raise ZoofSyntaxError('Unexpected and brace')
            
            elif token.text == '[':
                # Start of subscript
                if not (expression_chain and isinstance(expression_chain[-1], Expr)):
                    raise ZoofSyntaxError(token, 'Unexpected subscript start')
                exp = Expr('index', expression_chain[-1])
                expression_chain[-1] = exp
                push(exp)
            elif token.text == ']':
                # End of subscript
                exp = peek()
                if not exp.kind != 'index':
                    raise ZoofSyntaxError(token, 'Unexpected subscript end')
                assert len(exp.args) == 1
                finish_exp()
                if len(expressions) != 1:
                    raise ZoofSyntaxError(token, 'Subscript must contain exactly one expression')
                exp.args.append(expressions[0])
                pop()
            
            elif token.text in '{}':
                # Start or end of dict/set literal
                raise NotImplementedError()
            else:
                raise ZoofSyntaxError('Unknown bracket type %s' % token.text)
        
        elif token.type == TYPES.attr:
            # Attribute access. We don't call it an operator
            raise NotImplementedError()
        
        elif token.type == TYPES.sep:
            # Separator for tuples and function arguments
            raise NotImplementedError()
        
        elif token.type == TYPES.keyword:
            kw = token.text
            
            if kw == 'if':
                if expression_chain:
                    raise ZoofSyntaxError(token, 'Unexpected if-start')
                exp = Expr('if')
                expression_chain.append(exp)
                push(exp)
            
            elif kw == 'else':
                exp = peek()
                if exp.kind != 'block':
                     raise ZoofSyntaxError(token, 'Unexpected else')
                if exp is root:
                    raise ZoofSyntaxError(token, 'Exepected end')
                # Handle block
                finish_exp()
                exp.args.extend(expressions)
                pop()
                # What was this block for?
                exp = peek()
                if exp.kind != 'if':
                    raise ZoofSyntaxError(token, 'Can only use else in if-expression')
                # Start a new block for the else
                elsebody = Expr('block')
                exp.args.append(elsebody)
                push(elsebody)
            
            elif kw == 'for':
                assert False
            
            elif kw == 'do':
                exp = peek()
                if exp.kind == 'if':
                    # Finish test
                    finish_exp()
                    if not len(expressions) == 1:
                        raise ZoofSyntaxError(token, 'If-expression requires 1 test expression')
                    exp.args.append(expressions[0])
                    # Prepare body
                    body = Expr('block')
                    exp.args.append(body)
                    push(body)
                else:
                    assert False, 'dont know ' + exp.kind
            
            elif kw == 'end':
                exp = peek()
                if exp.kind == 'block':
                    if exp is root:
                        raise ZoofSyntaxError('Exepected end')
                    # Handle block
                    finish_exp()
                    exp.args.extend(expressions)
                    pop()
                    # What was this block for?
                    exp = peek()
                    assert exp.kind in ('if', 'for', 'while')  # ...
                    pop()
                else:
                    raise ZoofSyntaxError(token, 'Unmatched end, missing do?')
            
            else:
                raise ZoofSyntaxError(token, 'Unexpected keyword %s' % kw)
        
        elif token.type == TYPES.comment:
            pass  # no action needed
        
        # Fails
        elif token.type == TYPES.unknown:
            raise ZoofSyntaxError(token, 'Unknown token')
        elif token.type.startswith('unterminated_'):
            raise ZoofSyntaxError(token, token.type)
        else:
            raise ZoofSyntaxError(token, 'No support for %s token' % token.type)
    
    # Wrap up
    if len(stack) > 1:
        raise ZoofSyntaxError(token, 'Unterminated block, missing end?')
    assert len(stack) == 1
    assert not root.args
    finish_exp()
    root.args.extend(expressions)
    return root


if __name__ == '__main__':
    
    EXAMPLE = """
    # asd
    a = 3
    a += 2
    if a > 2 do
        b = 1
    else
        b = 3
    end
    
    """
   
    tokens = tokenize(EXAMPLE)
    ast = parse(tokens)
    #print(ast)
    ast.show()
