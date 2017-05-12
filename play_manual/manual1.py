"""
Playing with WASM by manually writing it using our Python classes.

This is just a simple demo to demonstrate defining functions in WASM,
as well as importing functions from the host environment and using then
in WASM.
"""

import os

from wasmtools import *


root = Module(
    TypeSection(
        FunctionSig(['f64']),  # import alert func
        FunctionSig(['f64']),  # import write func (could share the sig)
        FunctionSig(['f64', 'f64'], ['f64']), # add func
        FunctionSig([]),  # start func
        ),
    ImportSection(
        Import('js', 'alert', 'function', 0),
        Import('js', 'stdout_write', 'function', 1),
        ),
    FunctionSection(2, 3),
    ExportSection(
        Export('add', 'function', 2),
        ),
    StartSection(3),
    CodeSection(
        FunctionDef([], 
            Instruction('f64.const', 42), Instruction('call', 1),  # write 42
            # Instruction('f64.const', 1337), Instruction('call', 0),  # alert 1337
            Instruction('get_local', 0), Instruction('get_local', 1), Instruction('f64.add'),
            ),
        FunctionDef(['f64'],  # start func
            ('loop', 'emptyblock'),
                # write iter
                ('get_local', 0), ('call', 1),
                # Increase iter
                ('f64.const', 1), ('get_local', 0), ('f64.add'),
                ('tee_local', 0), ('f64.const', 10),
                ('f64.lt'), ('br_if', 0),
                ('end'),
            ),
        ),
    )


print(root)
root.show()

bb = root.to_binary()
print(bb)
hexdump(bb)

insert_wasm_into_html(__file__[:-3] + '.html', bb)
