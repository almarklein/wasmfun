"""
Code generator for the experimental WIP Zoof lang. It takes the AST produced
by the parser and converts it to WASM.
"""

import wasmfun as wf

from zf_tokenizer import tokenize
from zf_parser import Expr, parse


# todo: eventually this should produce WASM more directly (without first going
# through wasmtools), at least for the instructions.


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
    
    # Create Module context. This will do an initial pass to get all
    # funciton definitions (and indices) straight.
    m = ModuleContext(ast)
    
    # Compile all the things
    for context in m.all_functions:
        context.compile()
    
    module = m.to_wasm()
    return module


##

# todo: can we add line number info to expressions?
class ZoofCompilerError(SyntaxError):
    pass



class BaseContext:
    
    def __init__(self, body):
        assert isinstance(body, Expr) and body.kind == 'block'
        self._body = body
        
        self._expressions = []
        self._functions = []
        self.instructions = []
        
        self.names = {}
        self._name_counter = 0
        self._block_stack = []
    
    def name_idx(self, name):
        if name not in self.names:
            self.names[name] = self._name_counter
            self._name_counter += 1
        return self.names[name]
    
    def push_block(self, kind):
        assert kind in ('if', 'loop')
        self._block_stack.append(kind)
    
    def pop_block(self, kind):
        assert self._block_stack.pop(-1) == kind
    
    def get_block_level(self):
        for i, kind in enumerate(reversed(self._block_stack)):
            if kind in ('loop'):
                return i
    
    def add_function(self, ctx):
        assert isinstance(ctx, FunctionContext)
        self._functions.append(ctx)  # [ctx.name] = ctx
    
    # def get_function_idx(self, name):
    #     if name in self._functions:
    #         return self._functions[name]._idx
    #     else:
    #         raise NotImplementedError('todo: also look in parent context')
    
    def _collect_functions(self, expr):
        """ Walk the ast in search of functions, which we collect into
        a FunctionContext.
        """
        
        # todo: this pass should also resolve imports and globals
        
        if expr.kind == 'func':
            raise NotImplementedError()
        elif expr.kind == 'block':
            new_expressions = []
            for sub_expr in expr.args:
                if sub_expr.kind == 'func':
                    # todo: the function might use nonlocals, which might be globals
                    func_ctx = FunctionContext(self, sub_expr)
                    self.add_function(func_ctx)
                else:
                    new_expressions.append(sub_expr)
                    self._collect_functions(sub_expr)
            expr.args = new_expressions
        else:
            for sub_expr in expr.args:
                self._collect_functions(sub_expr)
    
    def compile(self):
        for expr in self._body.args:
            _compile_expr(expr, self, False)


class ModuleContext(BaseContext):
    """ Keep track of module-level things, like globals and functions.
    """
    
    def __init__(self, expr):
        super().__init__(expr)
        
        self._imported_globals = []
        self._globals = []
        self._imported_functions = dict(print=0, perf_counter=1)
        
        self._collect_functions(self._body)
        self._collect_all_functions_and_assign_ids()
    
    def _collect_all_functions_and_assign_ids(self):
        
        # todo: mmm, the wf.Module class can resolve names to indices for us
        # -> or is it better to do it here?
        
        # Now collect all functions defined in this module
        contexts = [self]
        count = len(self._imported_functions)
        all_functions = [self]
        while len(contexts) > 0:
            ctx = contexts.pop(0)
            for sub in ctx._functions:
                contexts.append(sub)
                all_functions.append(sub)
                sub._idx = count
                count += 1
        self.all_functions = all_functions
    
    def to_wasm(self):
        """ Create wasm Module object.
        """
        # This is also the main function
        locals = ['f64' for i in self.names]
        main_func = wf.Function('$main', [], [], locals, self.instructions)
        
        # Add imported funcs
        funcs = []
        funcs.append(wf.ImportedFuncion('print_ln', ['f64'], [], 'js', 'print_ln'))
        funcs.append(wf.ImportedFuncion('perf_counter', [], ['f64'], 'js', 'perf_counter'))
        
        # Add main funcs and other funcs
        funcs.append(main_func)
        for ctx in self.all_functions[1:]:
            funcs.append(ctx.to_wasm())
        
        # Compose module
        return wf.Module(*funcs)


class FunctionContext(BaseContext):
    """ A context keeps track of things while we walk the AST tree.
    Each context represents a block-expression, e.g. the main scope or
    a function definition.
    """
    
    def __init__(self, parent, expr):
        assert isinstance(parent, BaseContext)
        assert expr.kind == 'func'
        super().__init__(expr.args[1])
        
        self._parent = parent  # parent context
        self._name = expr.token.text

        # Init index, is set by the module
        self._idx = -1
        
        # Init return type
        self._ret_types = None
        
        # Process args
        self._arg_types = []
        for arg in expr.args[0].args:
            self.name_idx(arg)
            self._arg_types.append('f64')
        
        self._collect_functions(self._body)

    def set_return_type(self, ret_types):
        # todo: we should check the rt of every branch
        rt = tuple(ret_types)
        if self._ret_types is not None:
            assert rt == self._ret_types
        else:
            self._ret_types = rt
    
    def to_wasm(self):
        """ Create wasm Function object.
        """
        arg_types = self._arg_types
        ret_types = self._ret_types or []
        locals = ['f64' for i in self.names]
        
        return wf.Function(self._name, arg_types, ret_types, locals, self.instructions)


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
        ctx.push_block('if')
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
                if expr.args[2].kind == 'block':
                    for e in expr.args[2].args:
                        _compile_expr(e, ctx, False)
                else:
                    _compile_expr(expr.args[2], ctx, False)
        ctx.instructions.append(('end', ))
        ctx.pop_block('if')
    
    elif expr.kind == 'loop':
        
        # Init blocks - (outer block for break)
        ctx.push_block('loop')
        for i in [('block', 'emptyblock'), ('loop', 'emptyblock')]:
            ctx.instructions.append(i)
        
        if len(expr.args) == 1:
            # loop-inf
            for e in expr.args[1].args:
                _compile_expr(e, ctx, False)
        elif len(expr.args) == 2:
            # loop-while
            _compile_expr(expr.args[0], ctx, True)  # test
            ctx.instructions.append('i32.eqz')  # negate
            ctx.instructions.append(('br_if', 1))
            for e in expr.args[1].args:
                _compile_expr(e, ctx, False)
            ctx.instructions.append(('br', 0))  # loop
        elif len(expr.args) == 3:
            # loop-in
            raise NotImplementedError()
        else:
            assert False, 'Unexpected number of args in loop expression.'
        
        # Close loop
        for i in [('end'), ('end')]:
            ctx.instructions.append(i)
        ctx.pop_block('loop')
    
    elif expr.kind == 'continue':
        # branch to loop-block, i.e. beginning of the loop
        ctx.instructions.append(('br', ctx.get_block_level()))
    
    elif expr.kind == 'break':
        # branch to block that surrounds the loop, i.e. after the loop
        ctx.instructions.append(('br', ctx.get_block_level() + 1))
    
    elif expr.kind == 'func':
        assert False, 'We have collected func nodes'
    
    elif expr.kind == 'return':
        assert len(expr.args) == 1, 'The WASM v1 only supports 1 output arg'
        for ret_arg in expr.args:
            _compile_expr(ret_arg, ctx, True)
        ctx.instructions.append(('return', ))
        ctx.set_return_type(['f64' for name in expr.args])
    else:
        raise RuntimeError('Unknown expression kind %r' % expr.kind)


PRINT_FUNC_ID = 0
PERF_COUNTER_FUNC_ID = 1

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
        ii = []
        if len(expr.args) == 3:
            _compile_expr(expr.args[1], ctx, True)
            _compile_expr(expr.args[2], ctx, True)
        elif len(expr.args) == 2:
            ii.append(('f64.const', 0))
            _compile_expr(expr.args[1], ctx, True)
        ii.append('f64.sub')
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
    
    elif name == 'mod':
        # todo: this is fragile. E.g. for negative numbers
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
         # push again
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
        ii = []
        ii.append(('f64.div'))
        ii.append(('f64.floor'))
        ii.append(('f64.mul'))  # consumes last right
        ii.append(('f64.sub'))  # consumes last left
    
    elif name in ('eq', 'gt', 'lt', 'ge', 'le'):
        _compile_expr(expr.args[1], ctx, True)
        _compile_expr(expr.args[2], ctx, True)
        ii = ['f64.' + name]
        if not push_stack:
            ii.append('drop')
    
    elif name == 'print':  # Provided by host
        if nargs != 1:
            raise RuntimeError('Print needs exactly one argument')
        _compile_expr(expr.args[1], ctx, True)
        ii = [('call', PRINT_FUNC_ID)]
    elif name == 'perf_counter':  # Provided by host
        if nargs != 0:
            raise RuntimeError('perf_counter needs exactly zero arguments')
        ii = [('call', PERF_COUNTER_FUNC_ID)]
    
    else:
        for arg in expr.args[1:]:
            _compile_expr(arg, ctx, True)
        ii = [('call', name)]  # name, or idx? where to resolve function indices?
        
        # raise RuntimeError('Unknown function %r' % name)
    
    ctx.instructions.extend(ii)
