"""
Create a Brainfuck to WASM compiler. Brainfuck is an esoteric language with
a very simple syntax, but is very hard to program in. It is turing complete
though, and uses heap-allocated memory, making it a nice exercise.
"""

import wasmfun as wf


def _commands2instructions(commands):
    """ Compile brainfuck commands to WASM instructions (as tuples).
    """
    # The i32.load8_u instruction takes one values from the stack (the address),
    # and i32.store8 and takes two (address and value). Both instructions take
    # two arguments, 2**alignment (i.e. 0 means 1 byte alignment) and address offset.
    
    instructions = []
    while commands:
        c = commands.pop(0)
        if c == '>':
            instructions += [('get_local', 0), ('i32.const', 1), ('i32.add'), ('set_local', 0)]
        elif c == '<':
            instructions += [('get_local', 0), ('i32.const', 1), ('i32.sub'), ('set_local', 0)]
        elif c == '+':
            instructions += [('get_local', 0), ('get_local', 0),  # once for the read, once for the write
                             ('i32.load8_u', 0, 0),
                             ('i32.const', 1), ('i32.add'), ('i32.store8', 0, 0)]
        elif c == '-':
            instructions += [('get_local', 0), ('get_local', 0),  # once for the read, once for the write
                             ('i32.load8_u', 0, 0),
                             ('i32.const', 1), ('i32.sub'), ('i32.store8', 0, 0)]
        elif c == '.':
            instructions += [('get_local', 0), ('i32.load8_u', 0, 0), ('call', 0)]
        elif c == ',':
            # We don't support input, just set to zero
            instructions += [('get_local', 0), ('i32.const', 0), ('i32.store8', 0, 0)]
        elif c == '[':
            instructions += [('block', 'emptyblock'),
                                # if current data point == 0 goto end of block
                                ('get_local', 0), ('i32.load8_u', 0, 0), ('i32.const', 0), ('i32.eq'), ('br_if', 0),
                                ('loop', 'emptyblock'),
                                    ] + _commands2instructions(commands ) + [
                                    # if current data point > 0 goto start of block
                                    ('get_local', 0), ('i32.load8_u', 0, 0), ('i32.const', 0), ('i32.ne'), ('br_if', 0),
                                ('end'),
                             ('end')]
        elif c == ']':
            break
        else:
            raise ValueError('Unknown Brainfuck command: %r' % c)
    
    return instructions


def brainfuck2wasm(code):
    """ Compile brainfuck code to a WASM module.
    """
    commands = [c for c in code if c in '><+-.,[]']
    
    instructions = _commands2instructions(commands)
    
    module = wf.Module(
        wf.ImportedFuncion('print_charcode', ['i32'], [], 'js', 'print_charcode'),
        wf.Function('$main', [], [], ['i32'], instructions),
        wf.MemorySection((1, 1)),  # 1 page of 64KiB > 30000 minimum for Brainfuck
        wf.DataSection(),  # no initial data
        )
    return module
