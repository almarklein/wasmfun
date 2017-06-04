# pywasm
Getting the hang of WASM - generate WASM from Python

This is basically me fooling around with WASM to get a feel for it and seeing
if/how I can put it to actual use.


## How to use this code

You can browse the code on Github, the readme's of most subdirs have links to
html pages that show a piece of code, run the WASM that was produced
from it, and show the output.

To play with this yourself, clone the repository and add the root directory
to your `PYTHONPATH`. Needs Python 3.x.


## What is WASM?

WASM, short for WebAssembly, is a low level description of a program. It is
an intermediate representation (IR) that programs can be compiled to, and
subsequently be translated to native instuctions by a WASM virual machine, like
the browser. It is not dissimilar from LLVM IR, but is targeted to be able to
run in browsers.

Check out the links below for (much) more info.

WASM comes with a text and binary format. The x.wasm extension is for
the binary format, x.wat is the text format. The browser can only read
the binary.

There ought to be a 1-to-1 relationship between the WASM text format
and the binary format. However, it looks like there are currently multiple
variants of the text format floating around in the web. Perhaps its
still under change. Also, the relation is not so direct that you can
map "fields" 1-on-1; there is some compilation/interpretation needed.
This is why I don't work with the text format in this code.


## WASM is pretty darn cool

WASM is primarily made to allow programs written in C/C++ to be run on the web.
They already could, sort of, via ASM.js, but WASM makes this much more
well-defined and faster (in terms of load time and run-time performance).

But that's not why I find it so interesting. I'm looking at WASM as a
compilation target for dynamic languages, like Python, or perhaps new
languages. Because WASM must be able to run in the browser, it has some
interesting features w.r.t. ease of distribution, safety, etc.

It's important to realize that although WASM is designed to be able to
run in the browser, it has no dependencies on anything "web". Running on 
the desktop, or mobile devices, or ... is an equally important goal of WASM.
This means that any language compiled to WASM can basically run anywhere.
This means that any language compiled to WASM can basically run anywhere. I
intentionally repeated that sentence because its really a big thing!
Most modern browsers already support WASM, and there are already projects
that can run it on desktop too, or e.g. in the JVM.

WASM is inherently safe and has no way (by itself) to e.g. access the
file system. Functionality like this is provided by the host environment via
an import mechanism, the same that is used to dynamically link multiple WASM
modules together. This makes a clear separation. E.g. code on the web can
access the DOM, code on desktop can access the file system. Also, new 
programming languages can piggy back on the host environment by letting it
provide functionality for e.g. logging, math, regexp, etc.

Another nice feature (observed by [Rasmus Andersson](https://rsms.me/wasm-intro))
is that WASM can also be interpreted/emulated instead of being compiled to
machince code. Although it will be much slower, it allows for awesome debugging
capabilities. Basically, debug like you do with Python, with a language that's
nearly as fast as C.


## In this repo

**wasmtools:**
I (partly) implemented an internal representation of (binary) WASM that
can be exported to a .wasm file. One can write WASM directly (in Python)
using the classes of this internal representation. Or one can use it
as a compilation target (i.e. use it as the target AST) for new/toy
languages.

**play_manual:**
Using the above tool, you can manually write apps in "raw WASM". A bit
tedious, but it works!

**play_calc:**
Implementation of a *real* simple "programming language" that basically acts
like a calculator, which is compiled to WASM.

**brainfuck**
A compiler of brainfuck to WASM.

**zoof1:**
An experimental language with a very friendly syntax that compiles to WASM.
The parsing and compiling is implemented in Python, but it could eventually
be self-hosting, which is when it starts to be come real interesting ...


## Links

Official and most generally useful:
    
* Official docs: http://webassembly.org/docs/
* Official spec: https://webassembly.github.io/spec
* Curated list of awesome WASM things: https://github.com/mbasso/awesome-wasm

Some posts that I found useful:

* http://blog.mikaellundin.name/2016/06/19/creating-a-webassembly-binary-and-running-it-in-a-browser.html
* https://rsms.me/wasm-intro
* https://gist.github.com/cure53/f4581cee76d2445d8bd91f03d4fa7d3b
