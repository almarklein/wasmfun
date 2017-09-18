""" Build HTML examples for the Zoof to WASM compiler.
"""

import wasmfun as wf

from zf_tokenizer import tokenize
from zf_parser import parse
from zf_codegen import compile


EXAMPLE = """
func find_nt_prime(n)
{
    count = 0
    i = -1
    
    loop while count < n
        i = i + 1
        
        if i <= 1 do continue  # nope
        elseif i == 2 do count = count + 1
        else
            gotit = 1
            # loop j in 2..i//2 + 1
            j = 2
            loop while j < i / 2 + 1
                j += 1
                if i % j == 0
                    gotit = 0
                    break
            if gotit == 1 do count = count + 1
    return i
}

t0 = perf_counter()
result = find_nt_prime(10001)
print(perf_counter() - t0)
print(result)
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
