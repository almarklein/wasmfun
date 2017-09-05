""" Build HTML examples for the Zoof to WASM compiler.
"""

import wasmfun as wf

from zf_tokenizer import tokenize
from zf_parser import parse
from zf_codegen import compile


EXAMPLE = """
# asd
a = 2 + 3 + 1
b = 9 - 3 * 2 + 2
b += 31
print(a + b)

c = 2
if a > 25
    c = 3
else
    c = 4
print(c)

d = if a > 25 do 2 else 4
print(d)
print(if a > 25 do 20 else 40)
"""

tokens = tokenize(EXAMPLE, __file__, 11)
ast = parse(tokens)
ast.show()
print('---')
wasm = compile(ast)
wasm.show()
print('nbytes:', len(wasm.to_bytes()))


wf.run_wasm_in_node(wasm)
wf.export_wasm_example('zoof1.html', EXAMPLE, wasm)
