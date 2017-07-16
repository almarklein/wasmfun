# Zoof lang

This is a very preliminary, very much WIP, and above all, very experimental
implementation of a programming language that compiles directly to WASM.

## Examples

(best to open in new tab)

* <a href="http://htmlpreview.github.io/?https://github.com/almarklein/wasmfun/blob/master/zoof1/zoof1.html" target="_blank">
  Zoof example 1</a>

## Status

It can tokenize and parse part of the intended syntax. But the syntax has not
been fully decided on. The only value will be float at first.


## Next steps / dreaming out loud

* If-expressions, for-loops, etc.
* Functions
* Modules
* More types like Text, Array and Int.
* A (initially simple) type system for custom types.
* Make it self hosting (do the tokenization, parsing and compiling in
  the lang itself).

When it is self-hosting, the host environment can provide a function
to load new modules, which would allow making this a JITted dynamic
language. Quite similar to Julia, except targeting WASM, and having the
implementation fully* in the language itself (except for some basics
provided by the host env).

What you'd have then is a fast (super-fast compared to Python, though
probably not quite as fast as Julia) language that's real easy to work
with and that runs nearly anywhere. The precise functionality depends
on the host environment. E.g. access to DOM, Canvas, webGL in a browser.
Access to the file system and loading clibs in desktop apps, special
API's on mobile devices, and APIS to switch lights and read sensors on
microprocessors.


## Design guidelines

Syntax:

* The syntax should be simple, consistent, easy to read, and easy to remember.
* The number of keywords should be minimal.
* Keywords should not "take away" common names (like "type").
  Prepositions (e.g. for, with) work better than nouns.
* Special chars should be avoided for program flow. For data
  (literal arrays/dicts) it's more ok.
* 1 way to define a function, also anonymous
* 1 way to use if expressions, also for one-liners and if-assignments
* 1 way to use for-loops, also for one-liners and comprehensions


### Imports


### Type system


### Scoping

What is the use of soft local scope if it does not prevent accidental overwriting?

