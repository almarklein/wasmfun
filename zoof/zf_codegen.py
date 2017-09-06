"""
Code generator for the experimental WIP Zoof lang. It takes the AST produced
by the parser and converts it to WASM.
"""

import wasmfun as wf

from zf_tokenizer import tokenize
from zf_parser import Expr, parse


# todo: eventually this should produce WASM more directly (without first going
# through wasmtools), at least for the instructions.


# todo: can we add line number info to expressions?
class ZoofCompilerError(SyntaxError):
    pass


class Context:
    """ A context keeps track of things while we walk the AST tree.
    """
    
    def __init__(self):
        self.instructions = []
        self.names = {}
        self._name_counter = 0
    
    def name_idx(self, name):
        if name not in self.names:
            self.names[name] = self._name_counter
            self._name_counter += 1
        return self.names[name]


def compile(code):
    """ Compile Zoof code (in the form of a string, a list of tokens, or an Expr
    object) to a WASM module.
    """
    if isinstance(code, str):
        code = tokenize(code)
    if isinstance(code, list):
        code = parse(code)
    if isinstance(code, Expr):
        return generate_code(code)
    else:
        raise TypeError('compile() needs code as string, list of tokens, or Exp.')


def generate_code(ast):
    """ Compile expressions (that make up an AST) to WASM instuctions.
    """
    assert isinstance(ast, Expr)
    assert ast.kind == 'block'
    ctx = compile_func(ast)
    locals = ['f64' for i in ctx.names]
    
    module = wf.Module(
        wf.ImportedFuncion('print_ln', ['f64'], [], 'js', 'print_ln'),
        wf.Function('$main', [], [], locals, ctx.instructions),
        )
    
    return module


def compile_func(expr):
    """ Compile a single function.
    """
    assert expr.kind == 'block'
    ctx = Context()
    
    for e in expr.args:
        _compile_expr(e, ctx, False)
    
    return ctx


def _compile_expr(expr, ctx, push_stack=True):
    """ Compile a single expression.
    """
    if expr.kind == 'assign':
        # Get name index to store value
        assert expr.args[0].kind == 'identifier'
        name = expr.args[0].token.text
        name_idx = ctx.name_idx(name)
        # Compute value
        _compile_expr(expr.args[1], ctx, True)
        # Store it
        if push_stack:
            ctx.instructions.append(('tee_local', name_idx))
        else:
            ctx.instructions.append(('set_local', name_idx))
    
    elif expr.kind == 'call':
        _compile_call(expr, ctx, push_stack)
    
    elif expr.kind == 'identifier':
        name = expr.token.text
        ctx.instructions.append(('get_local', ctx.names[name]))
    
    elif expr.kind == 'literal':
        value = float(expr.token.text)
        ctx.instructions.append(('f64.const', value))
    
    elif expr.kind == 'if':
        # Run test
        _compile_expr(expr.args[0], ctx, True)
        # Branch + body
        if push_stack:
            ctx.instructions.append(('if', 'f64'))
        else:
            ctx.instructions.append(('if', 'emptyblock'))
        assert len(expr.args) in (2, 3)
        if push_stack:
            if len(expr.args) == 2:
                raise ZoofCompilerError('A result-producing if-expression needs an else clause.')
            if len(expr.args[1].args) == 0 or len(expr.args[2].args) == 0:
                raise ZoofCompilerError('A result-producing if-expression needs nonempty body and else clauses')
            for e in expr.args[1].args[:-1]:
                _compile_expr(e, ctx, False)
            _compile_expr(expr.args[1].args[-1], ctx, True)
            ctx.instructions.append(('else', ))
            for e in expr.args[2].args[:-1]:
                _compile_expr(e, ctx, False)
            _compile_expr(expr.args[2].args[-1], ctx, True)
        else:
            for e in expr.args[1].args:
                _compile_expr(e, ctx, False)
            if len(expr.args) == 3:
                ctx.instructions.append(('else', ))
                for e in expr.args[2].args:
                    _compile_expr(e, ctx, False)
        ctx.instructions.append(('end', ))
    else:
        raise RuntimeError('Unknown expression kind %r' % e.kind)

PRINT_FUNC_ID = 0

def _compile_call(expr, ctx, push_stack=True):
    """ This is sort of our stdlib, later this could look up the call
    in the defined functions as well.
    """
    assert expr.args[0].kind == 'identifier'
    name = expr.args[0].token.text
    nargs = len(expr.args) - 1  # subtract name of fuction
    
    if name == 'add':  # todo: add can have more than 2 values
        for arg in expr.args[1:]:
            _compile_expr(arg, ctx, True)
        ii = ['f64.add'] * (nargs - 1)
        if not push_stack:
            ii.append('drop')
    
    elif name == 'sub':
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
        ii = ['f64.sub']
        if not push_stack:
            ii.append('drop')
    
    elif name == 'mul':
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
        ii = ['f64.mul']
        if not push_stack:
            ii.append('drop')
        
    elif name == 'div':
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
        ii = ['f64.div']
        if not push_stack:
            ii.append('drop')
    
    elif name == 'gt':
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
        ii = ['f64.gt']
        if not push_stack:
            ii.append('drop')
    
    elif name == 'lt':
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
        ii = ['f64.lt']
        if not push_stack:
            ii.append('drop')
    
    elif name == 'print':  # Provided by host
        if nargs != 1:
            raise RuntimeError('Print needs exactly one argument')
        _compile_expr(expr.args[1], ctx, True)
        ii = [('call', PRINT_FUNC_ID)]
    else:
        raise RuntimeError('Unknown function %r' % name)
    ctx.instructions.extend(ii)
