# The `compiler/` folder — Flex & Bison reference artifact

## What this is

This folder contains a **real, standalone Flex + Bison implementation** of
Phase 1 (Lexical Analysis) and Phase 2 (Syntax Analysis) for the same
educational C subset that the web application analyzes.

- `lexer.l` — a Flex specification defining every token category
  (keywords, identifiers, constants, operators, delimiters, etc.)
- `parser.y` — a Bison grammar defining the C subset's syntax rules,
  built on top of the tokens `lexer.l` produces
- `build.bat` — one-shot Windows build script (see below)

## Why this exists, and how it relates to the web app

The **web application itself** (`backend/lexer.py`, `backend/parser.py`)
uses a **hand-written Python lexer and recursive-descent parser** instead
of calling this Flex/Bison code. That is a deliberate engineering choice,
not a shortcut — see `README.md` in the project root, section
"Architecture Decisions", for the full reasoning. In short: a live lab
demo should not depend on a separately-installed native toolchain being
perfectly configured on the exact machine you're presenting from.

This folder exists so that:

1. You have **genuine, working Flex/Bison files** to show your professor,
   satisfying the "use Flex/Bison" academic requirement literally.
2. You can **compare the two techniques side-by-side** in your viva:
   parser-generator grammar rules (`.y` file, declarative) vs.
   hand-written recursive-descent parsing (`parser.py`, imperative). Both
   implement the *same* grammar — that comparison is itself a great
   answer to "why did you choose this approach?"
3. It still **genuinely works** — you can build and run it from a
   terminal and feed it any of the `examples/*.c` files.

## How to build it (Windows 11)

You need WinFlexBison and MinGW GCC installed and on your PATH first —
see the main project `README.md` → "Windows 11 Setup", Steps 3 and 5.

Open a terminal **inside this `compiler/` folder** and run:

```
build.bat
```

This produces two programs:

| Program | What it does |
|---|---|
| `lexer_standalone.exe` | Reads C code from stdin, prints every token it recognises (Phase 1 only) |
| `parser.exe` | Reads C code from stdin, tokenizes AND checks it against the grammar (Phase 1 + 2), printing `Syntax OK` or a list of syntax errors |

Try it:

```
lexer_standalone.exe < ..\examples\01_valid.c
parser.exe < ..\examples\01_valid.c
parser.exe < ..\examples\02_missing_semicolon.c
```

## Limitations of this artifact specifically

- Its grammar covers functions, declarations, assignments, `if`/`else`,
  `while`, `return`, and expressions — it does **not** include a `for`-loop
  rule (the Python engine in `backend/parser.py` does support `for`). This
  keeps the `.y` file short enough for a beginner to read end-to-end; adding
  `for` is a good self-extension exercise if your professor asks for one.
- It does **not** perform semantic analysis, TAC generation,
  optimization, or code generation — only Phases 1 and 2. Those later
  phases are demonstrated by the Python engine in the web app.
- Its error messages are simpler (just a line number and "syntax error")
  compared to the web app's structured, AI-explained errors — Bison's
  default error recovery is intentionally minimal here to keep the
  grammar file readable for a beginner.
- It is not wired into `POST /analyze`. If you want to extend the
  project to actually call this compiled binary from Flask instead of
  the Python lexer/parser, `backend/gcc_bridge.py` shows the
  `subprocess`-based pattern you'd use to do that.
