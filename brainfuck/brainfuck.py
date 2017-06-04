"""
Create a Brainfuck to WASM compiler. Brainfuck is an esoteric language with
a very simple syntax, but is very hard to program in. It is turing complete
though, and uses heap-allocated memory, making it a nice exercise.
"""

import wasmtools as wt


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
    
    module = wt.Module(
        wt.TypeSection(
            wt.FunctionSig([]),  # start func
            wt.FunctionSig(['i32']),  # imported func to write chars
            ),
        wt.ImportSection(
            wt.Import('js', 'stdout_write_charcode', 'function', 1),
            ),
        wt.FunctionSection(0),
        wt.MemorySection((1, 1)),  # 1 page of 64KiB > 30000 minimum for Brainfuck
        wt.StartSection(1),
        wt.CodeSection(
            wt.FunctionDef(['i32'], *instructions)),
        wt.DataSection(),  # no initial data
        )
    return module


## Example code


EXAMPLE1 = """
[ This program prints "Hello World!" and a newline to the screen, its
  length is 106 active command characters. [It is not the shortest.]

  This loop is an "initial comment loop", a simple way of adding a comment
  to a BF program such that you don't have to worry about any command
  characters. Any ".", ",", "+", "-", "<" and ">" characters are simply
  ignored, the "[" and "]" characters just have to be balanced. This
  loop and the commands it contains are ignored because the current cell
  defaults to a value of 0; the 0 value causes this loop to be skipped.
]
++++++++               Set Cell #0 to 8
[
    >++++               Add 4 to Cell #1; this will always set Cell #1 to 4
    [                   as the cell will be cleared by the loop
        >++             Add 2 to Cell #2
        >+++            Add 3 to Cell #3
        >+++            Add 3 to Cell #4
        >+              Add 1 to Cell #5
        <<<<-           Decrement the loop counter in Cell #1
    ]                   Loop till Cell #1 is zero; number of iterations is 4
    >+                  Add 1 to Cell #2
    >+                  Add 1 to Cell #3
    >-                  Subtract 1 from Cell #4
    >>+                 Add 1 to Cell #6
    [<]                 Move back to the first zero cell you find; this will
                        be Cell #1 which was cleared by the previous loop
    <-                  Decrement the loop Counter in Cell #0
]                       Loop till Cell #0 is zero; number of iterations is 8

The result of this is:
Cell No :   0   1   2   3   4   5   6
Contents:   0   0  72 104  88  32   8
Pointer :   ^

>>.                     Cell #2 has value 72 which is 'H'
>---.                   Subtract 3 from Cell #3 to get 101 which is 'e'
+++++++..+++.           Likewise for 'llo' from Cell #3
>>.                     Cell #5 is 32 for the space
<-.                     Subtract 1 from Cell #4 for 87 to give a 'W'
<.                      Cell #3 was set to 'o' from the end of 'Hello'
+++.------.--------.    Cell #3 for 'rl' and 'd'
>>+.                    Add 1 to Cell #5 gives us an exclamation point
>++.                    And finally a newline from Cell #6
"""


EXAMPLE2 = """
[Generate the fibonacci number sequence, (for numbers under 100). Taken from
http://esoteric.sange.fi/brainfuck/bf-source/prog/fibonacci.txt
]
+++++++++++ number of digits to output
> #1
+ initial number
>>>> #5
++++++++++++++++++++++++++++++++++++++++++++ (comma)
> #6
++++++++++++++++++++++++++++++++ (space)
<<<<<< #0
[
  > #1
  copy #1 to #7
  [>>>>>>+>+<<<<<<<-]>>>>>>>[<<<<<<<+>>>>>>>-]

  <
  divide #7 by 10 (begins in #7)
  [
    >
    ++++++++++  set the divisor #8
    [
      subtract from the dividend and divisor
      -<-
      if dividend reaches zero break out
        copy dividend to #9
        [>>+>+<<<-]>>>[<<<+>>>-]
        set #10
        +
        if #9 clear #10
        <[>[-]<[-]]
        if #10 move remaining divisor to #11
        >[<<[>>>+<<<-]>>[-]]
      jump back to #8 (divisor possition)
      <<
    ]
    if #11 is empty (no remainder) increment the quotient #12
    >>> #11
    copy to #13
    [>>+>+<<<-]>>>[<<<+>>>-]
    set #14
    +
    if #13 clear #14
    <[>[-]<[-]]
    if #14 increment quotient
    >[<<+>>[-]]
    <<<<<<< #7
  ]

  quotient is in #12 and remainder is in #11
  >>>>> #12
  if #12 output value plus offset to ascii 0
  [++++++++++++++++++++++++++++++++++++++++++++++++.[-]]
  subtract #11 from 10
  ++++++++++  #12 is now 10
  < #11
  [->-<]
  > #12
  output #12 even if it's zero
  ++++++++++++++++++++++++++++++++++++++++++++++++.[-]
  <<<<<<<<<<< #1

  check for final number
  copy #0 to #3
  <[>>>+>+<<<<-]>>>>[<<<<+>>>>-]
  <- #3
  if #3 output (comma) and (space)
  [>>.>.<<<[-]]
  << #1

  [>>+>+<<<-]>>>[<<<+>>>-]<<[<+>-]>[<+>-]<<<-
]
"""


if __name__ == '__main__':
    
    wasm = brainfuck2wasm(EXAMPLE1)
    print('nbytes:', len(wasm.to_binary()))
    wt.produce_example_html('brainfuck1.html', EXAMPLE1, wasm.to_binary())
    
    wt.produce_example_html('brainfuck2.html', EXAMPLE1, brainfuck2wasm(EXAMPLE2).to_binary())
    
    
    