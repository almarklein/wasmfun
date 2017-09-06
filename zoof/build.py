""" Build HTML examples for the Zoof to WASM compiler.
"""

import wasmfun as wf

from zf_tokenizer import tokenize
from zf_parser import parse
from zf_codegen import compile


EXAMPLE = """
max = 10001
n = 0
i = -1
t0 = perf_counter()

loop while n < max
    i = i + 1
    
    if i <= 1
        continue  # nope
    elseif i == 2
        n = n + 1
    else
        gotit = 1
        # loop j in 2..i//2 + 1
        j = 2
        loop while j < i / 2 + 1
            j += 1
            if i % j == 0
                gotit = 0
                break
        if gotit == 1
            n = n + 1

print(perf_counter() - t0)
print(i)
"""

tokens = tokenize(EXAMPLE, __file__, 59)
ast = parse(tokens)
ast.show()
print('---')
wasm = compile(ast)
wasm.show()
print('nbytes:', len(wasm.to_bytes()))


wf.run_wasm_in_node(wasm)
wf.export_wasm_example('zoof1.html', EXAMPLE, wasm)
