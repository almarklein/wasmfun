# Simplepy

This is a compiler that can compile a very strict subset of Python (in
which the only types are floats) to WASM.

## Examples

(best to open in new tab)

* <a href="http://htmlpreview.github.io/?https://github.com/almarklein/wasmfun/blob/master/simplepy/simplepy1.html" target="_blank">
  Simplepy example 1</a>
* <a href="http://htmlpreview.github.io/?https://github.com/almarklein/wasmfun/blob/master/simplepy/simplepy2.html" target="_blank">
  Simplepy example 2</a>


## Timings

This implementation is just complete enough to implement simple numeric algorithms,
such as an algorithm to find the 10001 st prime. This allows for some basic
timing measurements:
    
* On CPython, the code takes 30 s.
* On Pypy, it takes 2 s
* The same code, compiled to WASM takes 1.1 s in Chrome/Brave, and 3.9 in Firefox.
* Equivalent code in Julia takes 2.3 s.

To interpret these results we should keep in mind that Julia has many
types, and the algorithm operates on integers (and perhaps some floats
as well), while the WASM code consists only of floats. Also, I am not
familia with Julia at all, so the code might just be inefficient (please
let me know!). It does show that WASM performance is in the same
ballpark as Julia/LLVM and thus also C++ (as we might expect).
