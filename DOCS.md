# Documentation of wasmfun 0.1

## Utility functions

#### function `inspect_bytes_at(bb, offset)`
Inspect bytes at the specified offset.


#### function `hexdump(bb)`
Do a hexdump of the given bytes.


#### function `export_wasm_example(filename, code, wasm)`
Generate an html file for the given code and wasm module.


#### function `run_wasm_in_node(wasm)`
Load a WASM module in node.
Just make sure that your module has a main function.



## Module building classes

#### class `Field()`
Representation of a field in the WASM S-expression.


#### class `Module(*sections)`
Field representing a module; the toplevel unit of code.


#### class `Section()`
Base class for module sections.


#### class `TypeSection(*functionsigs)`
Defines signatures of functions that are either imported or defined in this module.


#### class `ImportSection(*imports)`
Defines the things to be imported in a module.


#### class `FunctionSection(*indices)`
Declares for each function defined in this module which signature is
associated with it. The items in this sections match 1-on-1 with the items
in the code section.


#### class `TableSection()`
Define stuff provided by the host system that WASM can use/reference,
but cannot be expressed in WASM itself.


#### class `MemorySection(*entries)`
Declares initial (and max) sizes of linear memory, expressed in
WASM pages (64KiB). Only one default memory can exist in the MVP.


#### class `GlobalSection()`
Defines the globals in a module.


#### class `ExportSection(*exports)`
Defines the names that this module exports.


#### class `StartSection(index)`
Provide the index of the function to call at init-time. The func must
have zero params and return values.


#### class `ElementSection()`
What is this again?


#### class `CodeSection(*functiondefs)`
The actual code for a module, one CodeSection per function.


#### class `DataSection(*chunks)`
Initialize the linear memory.
Note that the initial contents of linear memory are zero.


#### class `Import(modname, fieldname, kind, type)`
Import objects (from other wasm modules or from the host environment).
The type argument is an index in the type-section (signature) for funcs
and a string type for table, memory and global.


#### class `Export(name, kind, index)`
Export an object defined in this module. The index is the index
in the corresponding index space (e.g. for functions this is the
function index space which is basically the concatenation of
functions in the import and type sections).


#### class `FunctionSig(params=(), returns=())`
Defines the signature of a WASM module that is imported or defined in
this module.


#### class `FunctionDef(locals, *instructions)`
The definition (of the body) of a function. The instructions can be
Instruction instances or strings/tuples describing the instruction.


#### class `Instruction(type, *args)`
Class for all instruction fields. Can have nested instructions, which
really just come after it (so it only allows semantic sugar for blocks and loops.



## WASM opcodes

See `wasmfun.I` for an autocompletable structure representing all opcodes.

* `unreachable`
* `nop`
* `block`
* `loop`
* `if`
* `else`
* `end`
* `br`
* `br_if`
* `br_table`
* `return`
* `call`
* `call_indirect`
* `drop`
* `select`
* `get_local`
* `set_local`
* `tee_local`
* `get_global`
* `set_global`
* `i32.load`
* `i64.load`
* `f32.load`
* `f64.load`
* `i32.load8_s`
* `i32.load8_u`
* `i32.load16_s`
* `i32.load16_u`
* `i64.load8_s`
* `i64.load8_u`
* `i64.load16_s`
* `i64.load16_u`
* `i64.load32_s`
* `i64.load32_u`
* `i32.store8`
* `i32.store16`
* `i32.store`
* `i64.store`
* `f32.store`
* `f64.store`
* `current_memory`
* `grow_memory`
* `i32.const`
* `i64.const`
* `f32.const`
* `f64.const`
* `i32.eqz`
* `i32.eq`
* `i32.ne`
* `i32.lt_s`
* `i32.lt_u`
* `i32.gt_s`
* `i32.gt_u`
* `i32.le_s`
* `i32.le_u`
* `i32.ge_s`
* `i32.ge_u`
* `i64.eqz`
* `i64.eq`
* `i64.ne`
* `i64.lt_s`
* `i64.lt_u`
* `i64.gt_s`
* `i64.gt_u`
* `i64.le_s`
* `i64.le_u`
* `i64.ge_s`
* `i64.ge_u`
* `f32.eq`
* `f32.ne`
* `f32.lt`
* `f32.gt`
* `f32.le`
* `f32.ge`
* `f64.eq`
* `f64.ne`
* `f64.lt`
* `f64.gt`
* `f64.le`
* `f64.ge`
* `i32.clz`
* `i32.ctz`
* `i32.popcnt`
* `i32.add`
* `i32.sub`
* `i32.mul`
* `i32.div_s`
* `i32.div_u`
* `i32.rem_s`
* `i32.rem_u`
* `i32.and`
* `i32.or`
* `i32.xor`
* `i32.shl`
* `i32.shr_s`
* `i32.shr_u`
* `i32.rotl`
* `i32.rotr`
* `i64.clz`
* `i64.ctz`
* `i64.popcnt`
* `i64.add`
* `i64.sub`
* `i64.mul`
* `i64.div_s`
* `i64.div_u`
* `i64.rem_s`
* `i64.rem_u`
* `i64.and`
* `i64.or`
* `i64.xor`
* `i64.shl`
* `i64.shr_s`
* `i64.shr_u`
* `i64.rotl`
* `i64.rotr`
* `f32.abs`
* `f32.neg`
* `f32.ceil`
* `f32.floor`
* `f32.trunc`
* `f32.nearest`
* `f32.sqrt`
* `f32.add`
* `f32.sub`
* `f32.mul`
* `f32.div`
* `f32.min`
* `f32.max`
* `f32.copysign`
* `f64.abs`
* `f64.neg`
* `f64.ceil`
* `f64.floor`
* `f64.trunc`
* `f64.nearest`
* `f64.sqrt`
* `f64.add`
* `f64.sub`
* `f64.mul`
* `f64.div`
* `f64.min`
* `f64.max`
* `f64.copysign`
* `i32.wrap_i64`
* `i32.trunc_s_f32`
* `i32.trunc_u_f32`
* `i32.trunc_s_f64`
* `i32.trunc_u_f64`
* `i64.extend_s_i32`
* `i64.extend_u_i32`
* `i64.trunc_s_f32`
* `i64.trunc_u_f32`
* `i64.trunc_s_f64`
* `i64.trunc_u_f64`
* `f32.convert_s_i32`
* `f32.convert_u_i32`
* `f32.convert_s_i64`
* `f32.convert_u_i64`
* `f32.demote_f64`
* `f64.convert_s_i32`
* `f64.convert_u_i32`
* `f64.convert_s_i64`
* `f64.convert_u_i64`
* `f64.promote_f32`
* `i32.reinterpret_f32`
* `i64.reinterpret_f64`
* `f32.reinterpret_i32`
* `f64.reinterpret_i64`
