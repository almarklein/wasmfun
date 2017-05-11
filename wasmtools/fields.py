"""
The field classes to represent a WASM program.
"""

from io import BytesIO
from struct import pack as spack

from ._opcodes import OPCODES


LANG_TYPES = {
    'i32': b'\x7f',
    'i64': b'\x7e',
    'f32': b'\x7d',
    'f64': b'\x7c',
    'anyfunc': b'\x70',
    'func': b'\x60',
    'block': b'\x40',  # pseudo type for representing an empty block_type
    }


def packf64(x):
    return spack('<d', x)


def packu32(x):
    return spack('<I', x)


def packstr(x):
    bb = x.encode('utf-8')
    return packvu32(len(bb)) + bb


def packvs64(x):
    bb = signed_leb128_encode(x)
    assert len(bb) <= 8
    return bb


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


def signed_leb128_encode(value):
    bb = []
    if value < 0:
        unsignedRefValue = (1 - value) * 2
    else:
        unsignedRefValue = value * 2
    while True:
        byte = value & 0x7F
        value >>= 7
        unsignedRefValue >>= 7
        if unsignedRefValue != 0:
            byte = byte | 0x80
        bb.append(byte)
        if unsignedRefValue == 0:
            break
    return bytes(bb)


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
    in the corresponding index space (e.g. for functions this is the
    function index space which is basically the concatenation of
    functions in the import and type sections).
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
            elif isinstance(arg, (float, int)):
                if self.type.startswith('f64.'):
                    f.write(packf64(arg))
                elif self.type.startswith('i64.'):
                    f.write(packvs64(arg))
                elif self.type.startswith('i') or self.type.startswith('f'):
                    raise RuntimeError('Únsupported instruction arg for %s' % self.type)
                else:
                    f.write(packvu32(arg))
            else:
                raise TypeError('Unknown instruction arg %r' % arg)  # todo: e.g. constants



# Collect field classes
__all__ = [name for name in globals()
           if isinstance(globals()[name], type) and issubclass(globals()[name], Field)]
