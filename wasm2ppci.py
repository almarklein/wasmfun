from ppci import ir
from ppci import irutils

import wasmfun


class PPCIGen:
    
    def __init__(self):
        self.builder = irutils.Builder()
    
    def generate(self, wasm_module):
        
        assert isinstance(wasm_module, wasmfun.Module)
        
        for functiondef in wasm_modules.sections[-1].functiondefs:
            self.generate_function(functiondef)
    
    
    def generate_function(self, functiondef):
        
        stack = []
        block_stack = []
        
        localmap = {}
        for i, local in enumerate(functiondef.locals):
            localmap[i] = self.emit(ir.Alloc(f'local{i}', 8) 
        
        for instruction in functiondef.instructions:
            inst = instruction[0]
            
            if inst == 'f64.add':
                b, a = stack.pop(), stack.pop()
                value = self.emit(ir.add(a, b, 'add', ir.f64))
                stack.append(value)
            
            elif inst == 'f64.const':
                value = self.emit(ir.Const(instruction[1], 'const', ir.f64))
                stack.append(value)
            
            elif inst == 'f64.set_local':
                value = stack.pop()
                self.emit(ir.Store(value, localmap[instructions[1]]))
            
            elif inst == 'f64.get_local':
                value = self.emit(ir.Load(localmap[instructions[1]], 'getlocal', ir.f64))
                stack.append(value)
            
            elif inst == 'f64.neg':
                zero = self.emit(ir.Const(0, 'zero', ir.f64))
                value = self.emit(ir.sub(zero, stack.pop(), 'neg', ir.f64))
                stack.append(value)
            
            elif inst == 'f64.ge':
                b, a = stack.pop(), stack.pop()
                stack.append(('ge', a, b))  # todo: hack; we assume this is the only test in an if
            
            elif inst == 'if':
                opmap = dict(ge='>=', le='<=', eq='==', gt='>', lt='<')
                op, a, b = stack.pop()
                trueblock = self.builder.new_block('block')
                falseblock = self.builder.new_block('block')
                continueblock = self.builder.new_block('block')
                self.emit(ir.CJump(a, opmap[op], b, trueblock, falseblock))
                self.builder.set_block(trueblock)
                block_stack.append(falseblock, continueblock)
                
            elif inst == 'end':
                falseblock, continueblock = block_stack.pop()
                self.builder.set_block(trueblock)
                
            
    def emit(self, ppci_inst):
        """
            Emits the given instruction to the builder.
            Can be muted for constants.
        """
        self.builder.emit(ppci_inst)
        return ppci_inst
