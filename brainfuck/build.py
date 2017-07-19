""" Build HTML examples for the Brainfuck to WASM compiler.
"""

import os
import wasmfun as wf
from brainfuck import brainfuck2wasm


for fname in os.listdir('.'):
    if fname.startswith('example') and fname.endswith('.bf'):
        
        code = open(fname, 'rb').read().decode()
        wasm = brainfuck2wasm(code)
        
        print('%s nbytes: %i' %(fname, len(wasm.to_bytes())))
        wasm_name = fname.replace('example', 'brainfuck').replace('.bf', '.html')
        wf.export_wasm_example(wasm_name, code, wasm)
        wf.run_wasm_in_node(wasm)
