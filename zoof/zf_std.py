"""
Zoof standard functions. Mostly operators for now.
"""

STD = """

func sub1(a) {
    @@wasm.f64.const(0.0)
    @@wasm.get_local(a)
    return @@wasm.f64.sub()
}
func sub(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    return @@wasm.f64.sub()
}
func add(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    return @@wasm.f64.add()
}
func lt(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    return @@wasm.f64.lt()
}
func le(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    return @@wasm.f64.le()
}
func eq(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    return @@wasm.f64.eq()
}
func div(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    return @@wasm.f64.div()
}
func mul(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    return @@wasm.f64.mul()
}
func mod(a, b) {
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    @@wasm.get_local(a)
    @@wasm.get_local(b)
    @@wasm.f64.div()
    @@wasm.f64.floor()
    @@wasm.f64.mul()
    return @@wasm.f64.sub()
}
"""
