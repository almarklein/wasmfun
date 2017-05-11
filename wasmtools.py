"""
Tools for dealing with WASM in Python
"""

import re
import os
from io import BytesIO
from struct import pack as spack


endtoken = re.compile(r'[\ \)]')
skipws = re.compile(r'\S')


def packu32(x):
    return spack('<I', x)


def packstr(x):
    bb = x.encode('utf-8')
    return packvu32(len(bb)) + bb


def packvu32(x):
    bb = unsigned_leb128_encode(x)
    assert len(bb) <= 4
    return bb


def packvu7(x):
    bb = unsigned_leb128_encode(x)
    assert len(bb) == 1
    return bb


def packvu1(x):
    bb = unsigned_leb128_encode(x)
    assert len(bb) == 1
    return bb


def unsigned_leb128_encode(value):
    bb = []  # ints, really
    while True:
        byte = value & 0x7F
        value >>= 7
        if value != 0:
            byte = byte | 0x80
        bb.append(byte)
        if value == 0:
            break
    return bytes(bb)


LANG_TYPES = {
    'i32': b'\x7f',
    'i64': b'\x7e',
    'f32': b'\x7d',
    'f64': b'\x7c',
    'anyfunc': b'\x70',
    'func': b'\x60',
    'block': b'\x40',  # pseudo type for representing an empty block_type
    }

# Ignored 32bit opcodes (for now)
OPCODES = {
    'unreachable':0x00,
    'nop':0x01,
    'block':0x02,
    'loop':0x03,
    'if':0x04,
    'else':0x05,
    'end':0x0b,
    'br':0x0c,
    'br_if':0x0d,
    'br_table':0x0e,
    'return':0x0f,
    
    'call':0x10,
    'call_indirect':0x11,
    
    'drop':0x1a,
    'select':0x1b,
    
    'get_local':0x20,
    'set_local':0x21,
    'tee_local':0x22,
    'get_global':0x23,
    'set_global':0x24,
    
    'i64.load':0x29,
    'f64.load':0x2b,
    'i64.load8_s':0x30,
    'i64.load8_u':0x31,
    'i64.load16_s':0x32,
    'i64.load16_u':0x33,
    'i64.load32_s':0x34,
    'i64.load32_u':0x35,
    'i64.store':0x37,
    'f64.store':0x39,
    'current_memory':0x3f,
    'grow_memory':0x40,
    
    'i64.const':0x42,
    'f64.const':0x44,
    
    'i64.eqz':0x50,
    'i64.eq':0x51,
    'i64.ne':0x52,
    'i64.lt_s':0x53,
    'i64.lt_u':0x54,
    'i64.gt_s':0x55,
    'i64.gt_u':0x56,
    'i64.le_s':0x57,
    'i64.le_u':0x58,
    'i64.ge_s':0x59,
    'i64.ge_u':0x5a,
    'f64.eq':0x61,
    'f64.ne':0x62,
    'f64.lt':0x63,
    'f64.gt':0x64,
    'f64.le':0x65,
    'f64.ge':0x66,
    
    'i64.clz':0x79,
    'i64.ctz':0x7a,
    'i64.popcnt':0x7b,
    'i64.add':0x7c,
    'i64.sub':0x7d,
    'i64.mul':0x7e,
    'i64.div_s':0x7f,
    'i64.div_u':0x80,
    'i64.rem_s':0x81,
    'i64.rem_u':0x82,
    'i64.and':0x83,
    'i64.or':0x84,
    'i64.xor':0x85,
    'i64.shl':0x86,
    'i64.shr_s':0x87,
    'i64.shr_u':0x88,
    'i64.rotl':0x89,
    'i64.rotr':0x8a,
    'f64.abs':0x99,
    'f64.neg':0x9a,
    'f64.ceil':0x9b,
    'f64.floor':0x9c,
    'f64.trunc':0x9d,
    'f64.nearest':0x9e,
    'f64.sqrt':0x9f,
    'f64.add':0xa0,
    'f64.sub':0xa1,
    'f64.mul':0xa2,
    'f64.div':0xa3,
    'f64.min':0xa4,
    'f64.max':0xa5,
    'f64.copysign':0xa6,
    
    'i64.trunc_s/f64':0xb0,
    'i64.trunc_u/f64':0xb1,
    'f64.convert_s/i64':0xb9,
    'f64.convert_u/i64':0xba,
    'i64.reinterpret/f64':0xbd,
    'f64.reinterpret/i64':0xbf,
    }


class Field:
    """Representation of a field in the WASM S-expression.
    """
    
    __slots__ = []
    
    def __repr__(self):
        return '<%s-field>' % self.__class__.__name__

    def to_binary(self):
        f = BytesIO()
        self.to_file(f)
        return f.getvalue()
    
    def to_file(self, f):
        raise NotImplementedError()
    
    def _get_sub_text(self, subs, multiline=False):
        # Collect sub texts
        texts = []
        charcount = 0
        haslf = False
        for sub in subs:
            if isinstance(sub, Field):
                text = sub.to_text()
            else:
                text = repr(sub)
            charcount += len(text)
            texts.append(text)
            haslf = haslf or '\n' in text
        # Put on one line or multiple lines
        if multiline or haslf or charcount > 70:
            lines = []
            for text in texts:
                for line in text.splitlines():
                    lines.append(line)
            lines = ['    ' + line for line in lines]
            return '\n'.join(lines)
        else:
            return ', '.join(texts)
    
    def show(self):
        print(self.to_text())


class Module(Field):
    """ Field representing a module; the toplevel unit of code.
    """
    
    __slots__ = ['sections']
    
    def __init__(self, *sections):
        for section in sections:
            assert isinstance(section, Section)
        self.sections = sections

    def to_text(self):
        return 'Module(\n' + self._get_sub_text(self.sections, True) + '\n)'
    
    def to_file(self, f):
        f.write(b'\x00asm')
        f.write(packu32(1))  # version, must be 1 for now
        for section in self.sections:
            section.to_file(f)


## Section fields


class Section(Field):
    """Base class for module sections.
    """
    
    __slots__ = []
    id = -1
    
    def to_text(self):
        return '%s()' % self.__class__.__name__
    
    def to_file(self, f):
        f2 = BytesIO()
        self.get_binary_section(f2)
        payload = f2.getvalue()
        id = self.id
        assert id >= 0
        # Write it all
        f.write(packvu7(id))
        f.write(packvu32(len(payload)))
        if id == 0:  # custom section for debugging, future, or extension
            type = self.__cass__.__name__.lower().split('section')[0]
            f.write(pack_str(type))
        f.write(payload)
    
    def get_binary_section(self, f):
        raise NotImplementedError()  # Sections need to implement this


class TypeSection(Section):
    """ Defines signatures of functions that are either imported or defined in this module.
    """
    
    __slots__ = ['functionsigs']
    id = 1
    
    def __init__(self, *functionsigs):
        for i, functionsig in enumerate(functionsigs):
            assert isinstance(functionsig, FunctionSig)
            functionsig.index = i  # so we can resolve the index in Import objects
        self.functionsigs = functionsigs
    
    def to_text(self):
        return 'TypeSection(\n' + self._get_sub_text(self.functionsigs, True) + '\n)'
    
    def get_binary_section(self, f):
        f.write(packvu32(len(self.functionsigs)))  # count
        for functionsig in self.functionsigs:
            functionsig.to_file(f)


class ImportSection(Section):
    
    __slots__ = ['imports']
    id = 2
    
    def __init__(self, *imports):
        for imp in imports:
            assert isinstance(imp, Import)
        self.imports = imports
    
    def to_text(self):
        return 'ImportSection(\n' + self._get_sub_text(self.imports, True) + '\n)'
    
    def get_binary_section(self, f):
        f.write(packvu32(len(self.imports)))  # count
        for imp in self.imports:
            imp.to_file(f)


class FunctionSection(Section):
    """ Declares for each function defined in this module which signature is
    associated with it. The items in this sections match 1-on-1 with the items
    in the code section.
    """
    
    __slots__ = ['indices']
    id = 3
    
    def __init__(self, *indices):
        for i in indices:
            assert isinstance(i, int)
        self.indices = indices  # indices in the Type section
    
    def to_text(self):
        return 'FunctionSection(' + ', '.join([str(i) for i in self.indices]) + ')'
    
    def get_binary_section(self, f):
        f.write(packvu32(len(self.indices)))
        for i in self.indices:
            f.write(packvu32(i))


class TableSection(Section):
    
    __slots__ = []
    id = 4


class MemorySection(Section):
    
    __slots__ = []
    id = 5


class GlobalSection(Section):
    
    __slots__ = []
    id = 6


class ExportSection(Section):
    
    __slots__ = ['exports']
    id = 7
    
    def __init__(self, *exports):
        for export in exports:
            assert isinstance(export, Export)
        self.exports = exports
    
    def to_text(self):
        return 'ExportSection(\n' + self._get_sub_text(self.exports, True) + '\n)'
    
    def get_binary_section(self, f):
        f.write(packvu32(len(self.exports)))
        for export in self.exports:
            export.to_file(f)
    

class StartSection(Section):
    
    __slots__ = []
    id = 8


class ElementSection(Section):
    
    __slots__ = []
    id = 9


class CodeSection(Section):
    
    __slots__ = ['functiondefs']
    id = 10
    
    def __init__(self, *functiondefs):
        for functiondef in functiondefs:
            assert isinstance(functiondef, FunctionDef)
        self.functiondefs = functiondefs
    
    def to_text(self):
        return 'CodeSection(\n' + self._get_sub_text(self.functiondefs, True) + '\n)'
    
    def get_binary_section(self, f):
        f.write(packvu32(len(self.functiondefs)))
        for functiondef in self.functiondefs:
            functiondef.to_file(f)


class DataSection(Section):
    
    __slots__ = []
    id = 11


## Non-section fields


class Import(Field):
    """ Import objects (from other wasm modules or from the host environment).
    The type argument is an index in the type-section (signature) for funcs
    and a string type for table, memory and global.
    """
    
    __slots__ = ['modname', 'fieldname', 'kind', 'type']
    
    def __init__(self, modname, fieldname, kind, type):
        self.modname = modname
        self.fieldname = fieldname
        self.kind = kind
        self.type = type  # the signature-index for funcs, the type for table, memory or global
    
    def to_text(self):
        return 'Import(%r, %r, %r, %r)' % (self.modname, self.fieldname, self.kind, self.type)
    
    def to_file(self, f):
        f.write(packstr(self.modname))
        f.write(packstr(self.fieldname))
        if self.kind == 'function':
            f.write(b'\x00')
            f.write(packvu32(self.type))
        else:
            raise RuntimeError('Can only import functions for now')


class Export(Field):
    """ Export an object defined in this module. The index is the index
    in the corresponding index space (e.g. the function-section for functions.
    """
    
    __slots__ = ['name', 'kind', 'index']
    
    def __init__(self, name, kind, index):
        self.name = name
        self.kind = kind
        self.index = index
    
    def to_text(self):
        return 'Export(%r, %r, %i)' % (self.name, self.kind, self.index)
    
    def to_file(self, f):
        f.write(packstr(self.name))
        if self.kind == 'function':
            f.write(b'\x00')
            f.write(packvu32(self.index))
        else:
            raise RuntimeError('Can only export functions for now')


class FunctionSig(Field):
    
    __slots__ = ['params', 'returns', 'index']
    
    def __init__(self, params=(), returns=()):
        self.params = params
        self.returns = returns
        self.index = None
    
    def to_text(self):
        return 'FunctionSig(%r, %r)' % (list(self.params), list(self.returns))
    
    def to_file(self, f):
        f.write(b'\x60')  # form -> nonfunctions may also be supported in the future
        f.write(packvu32(len(self.params)))  # params
        for paramtype in self.params:
            f.write(LANG_TYPES[paramtype])
        f.write(packvu1(len(self.returns)))  # returns
        for rettype in self.returns:
            f.write(LANG_TYPES[rettype])


class FunctionDef(Field):
    """ The definition (of the body) of a function.
    """
    
    __slots__ = ['locals', 'instructions']
    
    def __init__(self, locals, *instructions):
        for loc in locals:
            assert isinstance(local, str)  # valuetype
        self.locals = locals
        for instruction in instructions:
            assert isinstance(instruction, Instruction)
        self.instructions = instructions
    
    def to_text(self):
        s = 'FunctionDef(' + str(list(self.locals)) + '\n'
        s += self._get_sub_text(self.instructions, True)
        s += '\n)'
        return s
    
    def to_file(self, f):
        
        # todo: Collect locals by type
        local_entries = []  # list of (count, type) tuples
        
        f3 = BytesIO()
        f3.write(packvu32(len(local_entries)))  # number of local-entries in this func
        for localentry in local_entries:
            f3.write(packvu32(localentry[0]))  # number of locals of this type
            f3.write(LANG_TYPES[localentry[1]])
        for instruction in self.instructions:
            instruction.to_file(f3)
        f3.write(b'\x0b')  # end
        body = f3.getvalue()
        f.write(packvu32(len(body)))  # number of bytes in body
        f.write(body)


class Instruction(Field):
    """ Class for all instruction fields.
    """
    
    __slots__ = ['type', 'args']
    
    def __init__(self, type, *args):
        self.type = type.lower()
        self.args = args
    
    def __repr__(self):
        return '<Instruction %s>' % self.type
    
    def to_text(self):
        subtext = self._get_sub_text(self.args)
        if '\n' in subtext:
            return 'Instruction(' + repr(self.type) + ',\n' + subtext + '\n)'
        else:
            return 'Instruction(' + repr(self.type) + ', ' + subtext + ')'
    
    def to_file(self, f):
        if self.type not in OPCODES:
            raise TypeError('Unknown instruction %r' % self.type)
        
        # todo: I think that instructions either have subinstructions or data, not both, so this could be optimized
        
        # Sub-instructions come before (they manipulate the stack)
        for arg in self.args:
            if isinstance(arg, Field):
                arg.to_file(f)
            elif isinstance(arg, int):
                pass  # f.write(packvu32(arg))
            else:
                raise TypeError('Unknown instruction arg %r' % arg)  # todo: e.g. constants
        
        # Our instruction
        f.write(bytes([OPCODES[self.type]]))
        
        # Data comes after
        for arg in self.args:
            if isinstance(arg, Field):
                pass # arg.to_file(f)
            elif isinstance(arg, int):
                f.write(packvu32(arg))
            else:
                raise TypeError('Unknown instruction arg %r' % arg)  # todo: e.g. constants


## API


def parse(text):
    """ Parse WASM text code (.wat) to an internal tree representation.
    """
    
    # Strip comments and whitespace
    lines = text.splitlines()
    lines = [line.split(';;')[0].strip() for line in lines]
    lines = [line for line in lines if line]
    text = ' '.join(lines)
    
    assert text.startswith('(')
    i = endtoken.search(text, 1).start()
    root = Field(text[1:i])
    stack = [root]
    
    while True:
        if text[i] == ' ':
            i += 1
            continue  # extra ws
        
        elif text[i] == '(':
            # Open new Field
            i2 = endtoken.search(text, i + 1).start()
            field = Field(text[i+1:i2])
            stack[-1].args.append(field)
            stack.append(field)
            i = i2
        
        elif text[i] == ')':
            # Close a field
            popped = stack.pop(-1)
            if not stack:
                assert i == len(text) - 1
                break
            else:
                i += 1
        else:
            # Add arg to field
            i2 = endtoken.search(text, i).start()
            stack[-1].args.append(text[i:i2])
            i = i2
    
    # todo: could return list of fields if we allow parsing snippets (i.e. not modules)
    return root


def inspect(bb, offset):
    """ For debugging.
    """
    start = max(0, offset - 16)
    end = offset + 16
    bytes2show = bb[start:end]
    bytes2skip = bb[start:offset]
    text_offset = len(repr(bytes2skip))
    print(bytes2show)
    print('|'.rjust(text_offset))


def hexdump(bb):
    i = 0
    line = 0
    while i < len(bb):
        ints = [hex(j)[2:].rjust(2, '0') for j in bb[i:i+16]]
        print(str(line).rjust(8, '0'), *ints, sep=' ')
        i += 16
        line += 1


if __name__ == '__main__':
    
    code = """
    (module ;; start the module
    (import "foo" "bar") ;; import foo.bar
    (func $bar (call_import 0 )) ;; map bar()
    (export "f" 0) ;; export bar()
    )
    """
    
    hex_alert = """00 61 73 6d 01 00 00 00  01 08 02 60 01 7f 00 60
                   00 00 02 08 01 02 6a 73  01 5f 00 00 03 02 01 01
                   08 01 01 0a 09 01 07 00  41 b9 0a 10 00 0b"""
    hex_alert = bytes([int(x, 16) for x in hex_alert.split(' ') if x])
    
    root = Module(
        TypeSection(
            FunctionSig(['f64']),  # import alert func
            FunctionSig(['f64', 'f64'], ['f64']), # add func
            ),
        ImportSection(
            Import('foo', 'bar', 'function', 0),
            ),
        FunctionSection(1),
        ExportSection(
            Export('add', 'function', 0),
            ),
        CodeSection(
            FunctionDef([], 
                Instruction('f64.add', Instruction('get_local', 0), Instruction('get_local', 1)),
                )
            ),
        )
    
    print(root)
    root.show()
    bb = root.to_binary()
    print(bb)
    hexdump(bb)
    with open(os.path.dirname(__file__) + '/test.wasm', 'wb') as f:
        f.write(bb)
