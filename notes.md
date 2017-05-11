
Getting the hang of WASM ...

## Links

* http://webassembly.org/docs/
* https://webassembly.github.io/spec
* http://blog.mikaellundin.name/2016/06/19/creating-a-webassembly-binary-and-running-it-in-a-browser.html
* https://rsms.me/wasm-intro
* http://cultureofdevelopment.com/blog/build-your-first-thing-with-web-assembly/
* https://gist.github.com/cure53/f4581cee76d2445d8bd91f03d4fa7d3b

## WASM is pretty neat

What I find interesting about WASM is that it is made to run without
needing any (classic) compilation steps. To do so, it has an
import/export system for dynamic linking and linking with the host system.

This e.g. allows a new programming language to let the host provide
stuff like logging, math ops, regexp, etc.

## Tools

There are tools like binaryen (takes an IR and compiles it to WASM, making many optimizations)
but these are C++ projects that are hard to comple on Windows, and I like the idea of using
a precompiled platform (e.g. the browser) and generating wasm without needing compilation (or tools
that need compilation). For now I use Python to generate the wasm, but at some point, if
we have a language that transpiles to wasm, we can make it self-hosting.

## Text vs binary format

WASM comes with a text and binary format. The x.wasm extension is for
the binary format, x.wat is the text format. The browser can only read
the binary.

There ought to be a 1-to-1 relationship between the WASM text format
and the binary format. However, it looks like there are multiple
variants of the text format. Perhaps its still under heavy change. Also,
the relation is not so direct that you can map "fields" 1-on-1; there
is some compilation/interpretation needed.

## Approach

I (partly) implemented an internal representation of (binary) WASM that
can be exported to a .wasm file. One can write WASM directly (in Python)
using the classes of this internal representation. Or one can use it
as a compilation target (i.e. use it as the target AST) for new/toy
languages.

