"""
Playing with WASM by manually writing it using our Python classes.

This is just a simple demo to demonstrate defining functions in WASM,
as well as importing functions from the host environment and using then
in WASM.
"""

import wasmtools as wt


root = wt.Module(
    wt.TypeSection(
        wt.FunctionSig(['f64']),  # import alert func
        wt.FunctionSig(['f64']),  # import write func (could share the sig)
        wt.FunctionSig(['f64', 'f64'], ['f64']), # add func
        wt.FunctionSig([]),  # start func
        ),
    wt.ImportSection(
        wt.Import('js', 'alert', 'function', 0),
        wt.Import('js', 'stdout_write', 'function', 1),
        ),
    wt.FunctionSection(2, 3),
    wt.ExportSection(
        wt.Export('add', 'function', 2),
        ),
    wt.StartSection(3),
    wt.CodeSection(
        wt.FunctionDef([], 
            ('f64.const', 42), ('call', 1),  # write 42
            # ('f64.const', 1337), ('call', 0),  # alert 1337
            ('get_local', 0), ('get_local', 1), ('f64.add'),
            ),
        wt.FunctionDef(['f64'],  # start func
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
wt.hexdump(bb)

wt.produce_example_html(__file__[:-3] + '.html', root.to_text(), bb)
