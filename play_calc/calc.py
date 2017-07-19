"""
A toy language that can process a series of calculations, as in a calculator.
Intended as a simple example how code can be tokenized, turned into AST
and then translated into WASM instructions.
"""

import wasmfun as wf


class Token:
    pass


class OpToken(Token):
    def __init__(self, value):
        self.value = value
        self.operand = None


class NumberToken(Token):
    def __init__(self, value):
        self.value = value
    
    
def tokenize(text):
    """ Generate tokens from a piece of code.
    """
    tokens = []
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        if line[0] not in '+-*/':
            raise SyntaxError('Each line must start with an operator.')
        tokens.append(OpToken(line[0]))
        rest = line[1:].lstrip()
        if not rest.isnumeric():
            raise SyntaxError('Each line must end with a number.')
        tokens.append(NumberToken(float(rest)))
    return tokens


def parse(tokens):
    """ Parse tokens to create AST. The AST is stack-based, because we
    know that the target is a stack machine. We could actually generate
    the WASM from the tokens directly, but we include this step for
    completeness, since more complex languages will need it.
    """
    ast = []
    i = 0
    while i < len(tokens):
        token1 = tokens[i]
        token2 = tokens[i + 1]
        assert isinstance(token1, OpToken)
        assert isinstance(token2, NumberToken)
        token1.operand = token2
        ast.append(token1)
        i += 2
    return ast


def wasmify(ast):
    """ Turn ast of this toy language into WASM.
    """
    # Generate WASM instructions from the ast
    instructions = [('f64.const', 0)]  # the initial value of the number is zero
    for op in ast:
        instructions.append(('f64.const', op.operand.value))
        if op.value == '+':
            instructions.append(('f64.add'))
        elif op.value == '-':
            instructions.append(('f64.sub'))
        elif op.value == '*':
            instructions.append(('f64.mul'))
        elif op.value == '/':
            instructions.append(('f64.div'))
    
    # Add call to print the result
    instructions.append(('call', 0))
    
    # Put instructions in a the main function of a WASM module
    module = wf.Module(
        wf.TypeSection(
            wf.FunctionSig([]),  # start func
            wf.FunctionSig(['f64']),  # import write func
            ),
        wf.ImportSection(
            wf.Import('js', 'print_ln', 'function', 1),
            ),
        wf.FunctionSection(0),
        wf.StartSection(1),
        wf.CodeSection(
            wf.FunctionDef([], *instructions))
        )
    return module


def compile(text):
    """ Compile the text into WASM binary.
    """
    return wasmify(parse(tokenize(text)))



EXAMPLE1 = """
+10
-2 # can have comments

# empty lines

*7
/ 2 # can have space
- 7
* 2
"""


EXAMPLE2 = """
# Income
+10
+12
+3
+8

# Costs
-8
-4
-2
-6
"""


if __name__ == '__main__':
    wf.run_wasm_in_node(compile(EXAMPLE1))
    wf.export_wasm_example('calc1.html', EXAMPLE1, compile(EXAMPLE1))
    wf.run_wasm_in_node(compile(EXAMPLE2))
    wf.export_wasm_example('calc2.html', EXAMPLE2, compile(EXAMPLE2))
