"""
Script to generate simple docs for the wasmfun lib.
"""

import os
import inspect

import wasmfun as wf


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def make_sig(fun, name):
    args, varargs, varkw, defaults = inspect.getargspec(fun)
    # prepare defaults
    if defaults is None:
        defaults = ()
    defaults = list(reversed(defaults))
    # make list (back to forth)
    args2 = []
    ismethod = args[0] == 'self'
    for i in range(len(args) - ismethod):
        arg = args.pop()
        if i < len(defaults):
            args2.insert(0, "%s=%s" % (arg, defaults[i]))
        else:
            args2.insert(0, arg)
    # append varargs and kwargs
    if varargs:
        args2.append("*" + varargs)
    if varkw:
        args2.append("**" + varkw)
    return "%s(%s)" % (name, ", ".join(args2) )


def get_docstring(fun):
    # assumes 4-space indentation for now.
    lines = []
    doc = '    ' + fun.__doc__.strip()
    for line in doc.splitlines():
        lines.append(line[4:])
    lines.append('')
    return '\n'.join(lines)


lines = ['# Documentation of wasmfun ' + wf.__version__, '']


## Utilities

lines += ['## Utility functions', '']

for name in wf.util.__all__:
    fun = getattr(wf.util, name)
    lines.append('#### function `%s`' % make_sig(fun, fun.__name__))
    lines.append(get_docstring(fun))
    lines.append('')

lines.append('')


## Module building classes

lines += ['## Module building classes', '']

for name in wf.fields.__all__:
    cls = getattr(wf.fields, name)
    lines.append('#### class `%s`' % make_sig(cls.__init__, cls.__name__))
    lines.append(get_docstring(cls))
    lines.append('')

lines.append('')


## OPCODES

lines += ['## WASM opcodes', '']
lines += ['See `wasmfun.I` for an autocompletable structure representing all opcodes.', '']

for key in wf.OPCODES:
    lines.append('* `%s`' % key)

lines.append('')


## Generate

if __name__ == '__main__':
    
    with open(os.path.join(ROOT_DIR, 'DOCS.md'), 'wb') as f:
        text = '\n'.join(lines)
        f.write(text.encode())
