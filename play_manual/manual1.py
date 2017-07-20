"""
Playing with WASM by manually writing it using our Python classes.

This is just a simple demo to demonstrate defining functions in WASM,
as well as importing functions from the host environment and using then
in WASM.
"""

import wasmfun as wf

I = wf.I


instructions = [
    ('loop', 'emptyblock'),
        # write iter
        ('get_local', 0), ('call', 1),
        # Increase iter
        ('f64.const', 1), ('get_local', 0), ('f64.add'),
        ('tee_local', 0), ('f64.const', 10),
        ('f64.lt'), ('br_if', 0),
    ('end'),
    ]


# These instructions are equivalent. The latter might be easier to write thanks
# to autocompletion, but the former looks nicer IMO
instructions = [
    (I.loop, 'emptyblock'),
        (I.get_local, 0), (I.call, 'print_ln'),
        (I.f64.const, 1), (I.get_local, 0), (I.f64.add),
        (I.tee_local, 0), (I.f64.const, 10),
        (I.f64.lt), (I.br_if, 0),
    (I.end)
    ]


# Compose functions into a module
root = wf.Module(
    wf.ImportedFuncion('alert', ['f64'], [], 'js', 'alert'),
    wf.ImportedFuncion('print_ln', ['f64'], [], 'js', 'print_ln'),
    wf.Function('add', params=['f64', 'f64'], returns=['f64'], locals=[],
                instructions=[('get_local', 0), ('get_local', 1), ('f64.add')],
                ),
    wf.Function('$main', params=[], returns=[], locals=['f64'],
                instructions=instructions),
    )


# For reference, one could also write it like this, using an explicit TypeSection
# and CodeSection. It needs more work to get the binding right, which in the above
# is done automatically.
#
# root = wf.Module(
#     wf.TypeSection(
#         wf.FunctionSig(['f64']),  # import alert func
#         wf.FunctionSig(['f64']),  # import write func (could share the sig)
#         wf.FunctionSig(['f64', 'f64'], ['f64']), # add func
#         wf.FunctionSig([]),  # start func
#         ),
#     wf.ImportSection(
#         wf.Import('js', 'alert', 'function', 0),
#         wf.Import('js', 'print_ln', 'function', 1),
#         ),
#     wf.FunctionSection(2, 3),
#     wf.ExportSection(
#         wf.Export('add', 'function', 2),
#         ),
#     wf.StartSection(3),
#     wf.CodeSection(
#         wf.FunctionDef([], 
#             ('f64.const', 42), ('call', 1),  # write 42
#             ('get_local', 0), ('get_local', 1), ('f64.add'),
#             ),
#         wf.FunctionDef(['f64'], *instructions), # start func
#         ),
#     )


print(root)
root.show()

bb = root.to_bytes()
print(bb)
wf.hexdump(bb)

wf.run_wasm_in_node(root)
wf.export_wasm_example(__file__[:-3] + '.html', root.to_text(), root)
