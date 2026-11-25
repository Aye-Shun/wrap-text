# Wrap Text

Wrap Text reflows plain-text paragraphs to a chosen line width. It reads a file or standard input and writes the result to standard output, leaving input files alone. The included garden notice is synthetic.

Build with a C17 compiler, Make, and Python 3 for the tests:

```sh
make
./build/wrap-text --width 32 samples/note.txt
printf 'a short note for the notice board' | ./build/wrap-text --width 16
```

The second command prints:

```text
a short note for
the notice board
```

The default width is 72; `--width` accepts 1–240. A single newline joins lines within a paragraph. Blank or whitespace-only lines separate paragraphs with one blank output line. Leading and trailing blank paragraphs are removed. Spaces, tabs, vertical tabs, and form feeds normalize to one separating space. LF, CRLF, and lone CR line endings are accepted. Nonempty output ends with a newline; empty input produces none.

A bounded word prefix lets the program stream words of any length without allocating their full contents. Words wider than the limit stay whole on their own line, so the width is a target, not a hard maximum. Only printable ASCII and whitespace are supported; Unicode, NUL, and other control bytes are rejected. Errors can leave partial output.

Run `make test` for CLI and file-safety checks, or `make sanitize` for AddressSanitizer and UndefinedBehaviorSanitizer.
