""" Build HTML examples for the simple Python to WASM compiler.
"""

import os
import wasmfun as wf
from simplepy import simplepy2wasm


for fname in os.listdir('.'):
    if fname.startswith('example') and fname.endswith('.py'):
        
        code = open(fname, 'rb').read().decode()
        wasm = simplepy2wasm(code)
        
        print('%s nbytes: %i' %(fname, len(wasm.to_binary())))
        wasm_name = fname.replace('example', 'simplepy').replace('.py', '.html')
        wf.produce_example_html(wasm_name, code, wasm.to_binary())
