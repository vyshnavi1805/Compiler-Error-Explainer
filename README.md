<<<<<<< HEAD
# C Compiler Error Explainer

**Compiler Design Lab — Educational Compiler Analysis Tool**

> A real, working compiler-analysis system for a C subset — six classic
> compiler phases, hand-written in Python — with a **100% rule-based**
> error explanation layer on top. **No AI, no machine learning, no API
> key, no internet connection required, anywhere in this project.**

---

## 1. Description

C Compiler Error Explainer takes a C program, runs it through six
genuine compiler phases (Lexical Analysis → Syntax Analysis → Semantic
Analysis → Intermediate Code Generation → Optimization → Code
Generation), and shows every phase's output in a browser UI. Whenever a
phase finds an error, a **rule-based Error Explainer** — a fixed
database of hand-written rules matched against the compiler's own
structured output — explains *what happened, why it's a problem, and
how to fix it*, in language a first-year CSE student can follow.

This project deliberately contains **no AI component of any kind**: no
OpenAI, no Claude, no Gemini, no machine learning model, no chatbot, no
API key, and no dependency on internet access. Every explanation is
produced by ordinary Python `if`/`dict` logic you can read start to
finish in `backend/error_explainer.py`.

## 2. Objectives

- Demonstrate all six phases of a compiler on real, if simplified, C code.
- Detect and clearly explain lexical, syntax, and semantic errors.
- Generate genuine Three-Address Code, apply real optimization passes, and
  emit a simplified target/assembly representation.
- Explain every detected error using **predefined, rule-based logic** —
  never AI, never a guess, never an invented problem.
- Run entirely offline, with zero configuration, immediately after
  `pip install`.

## 3. Features

- Six-phase pipeline with a visual status strip (done / error / pending
  per phase)
- Token table, parse tree, symbol table, TAC, before/after optimization
  diff, and pseudo-assembly — each in its own tab
- Multiple-error detection with panic-mode syntax recovery
- A structured **Error Explanation** panel driven entirely by the rule
  database in `error_explainer.py` — no AI, no network call
- Optional real-GCC diagnostics panel, shown side-by-side, if `gcc` is on
  your PATH (still not AI — just the real compiler, for comparison)
- A genuine, separately-buildable Flex/Bison implementation of Phases 1–2
  in `compiler/`, for the academic parser-generator requirement
- 10 built-in example programs covering valid code, every error category,
  multiple simultaneous errors, TAC, and optimization
- An **About** tab with editable student/course placeholders for your
  submission

## 4. The Six Compiler Phases

| # | Phase | Implemented in | What it demonstrates |
|---|---|---|---|
| 1 | Lexical Analysis | `backend/lexer.py` (+ `compiler/lexer.l`) | Regex-based tokenizer: keywords, identifiers, constants, operators, delimiters, comments, preprocessor directives |
| 2 | Syntax Analysis | `backend/parser.py` (+ `compiler/parser.y`) | Recursive-descent parser with panic-mode error recovery; builds a parse tree |
| 3 | Semantic Analysis | `backend/semantic.py`, `backend/symbol_table.py` | Undeclared-variable, duplicate-declaration, and type-mismatch checks over a scoped symbol table |
| 4 | Intermediate Code | `backend/intermediate_code.py` | Three-Address Code (TAC) generation from the parse tree |
| 5 | Optimization | `backend/optimizer.py` | Constant folding, constant propagation, algebraic simplification, dead-code elimination |
| 6 | Code Generation | `backend/code_generator.py` | Simplified pseudo-assembly (LOAD/STORE/ADD/... on a small register file) |

If an earlier phase fails, later phases are **honestly skipped** rather
than run on unreliable data — the UI explains why.

## 5. Architecture

```text
Browser (frontend/)  --HTTP-->  Flask backend (backend/app.py)
     index.html                      │
     script.js  <──JSON──            ├── lexer.py            (Phase 1)
     style.css                       ├── parser.py            (Phase 2)
                                      ├── semantic.py + symbol_table.py (Phase 3)
                                      ├── intermediate_code.py (Phase 4)
                                      ├── optimizer.py         (Phase 5)
                                      ├── code_generator.py    (Phase 6)
                                      ├── gcc_bridge.py        (optional real-GCC panel, still no AI)
                                      └── error_explainer.py   (rule-based ONLY — no AI, no network)
```

**Why hand-written Python instead of only Flex/Bison for the live demo?**
A live lab demo should not depend on a native toolchain (WinFlexBison +
MinGW) being flawlessly configured on the exact machine you present from.
So the web app's six phases are a genuine, hand-written Python
implementation (regex lexing and recursive-descent parsing are standard,
legitimate compiler techniques — not a shortcut), while `compiler/`
ships a **real, separately buildable** Flex/Bison implementation of
Phases 1–2 for you to show your professor and compare side-by-side. See
`compiler/README.md` for the full reasoning.

**Why Python/Flask for the backend?** (Section 4 of the spec)
1. It lets the same phase modules serve both the browser UI and the
   automated test suite (`backend/tests/`) without duplicating logic.
2. Flask's built-in dev server needs nothing beyond
   `pip install -r requirements.txt` — no separate web server to set up.
3. Regular expressions and dictionaries (Python's core data types) map
   directly onto the lexer's token patterns and the rule database,
   keeping every phase short enough for a beginner to read end-to-end.
The actual compiler concepts — tokens, grammar, symbol tables, TAC,
optimization, code generation — are language-independent; Python is only
the *implementation* language for the web version, not the language
being analyzed (that's always C). The genuine Flex/Bison C implementation
of Phases 1–2 lives separately in `compiler/`.

## 6. Technologies

- **Backend:** Python 3.10+, Flask, flask-cors — that's the entire dependency list
- **Frontend:** HTML, CSS, vanilla JavaScript, [CodeMirror](https://codemirror.net/5/) (via CDN — no build step)
- **Error Explainer:** Pure Python dictionaries — no AI library, no ML framework, no API client
- **Academic artifact:** Flex + Bison (WinFlexBison on Windows), GCC/MinGW
- **OS target:** Windows 11 (also runs on macOS/Linux — only `compiler/build.bat` is Windows-specific)

## 7. Requirements

- [VS Code](https://code.visualstudio.com/)
- [Python 3.10+](https://www.python.org/downloads/) (**check "Add python.exe to PATH" during install**)
- A modern browser (Chrome, Edge, Firefox)
- *Optional:* [MinGW-w64 GCC](https://winlibs.com/) — only needed for the real-GCC comparison panel
- *Optional:* [WinFlexBison](https://github.com/lexxmark/winflexbison) — only needed to build `compiler/`

No API key, no account, and no internet connection is required for any
part of this project to run.

## 8. Installation & Windows 11 Setup (step-by-step)

> If a command differs between **PowerShell** and **Command Prompt**, both
> are given. VS Code's built-in terminal is PowerShell by default — that's
> the easiest option, so use that unless told otherwise.

### Step 1 — Install VS Code
Download from https://code.visualstudio.com/, run the installer, accept
the defaults.

### Step 2 — Install Python
Download from https://www.python.org/downloads/. **During install, tick
"Add python.exe to PATH"** — this is the #1 cause of "python is not
recognized" errors. Verify it worked by opening a **new** terminal and
running:
```powershell
python --version
```
You should see something like `Python 3.12.x`.

### Step 3 — Install GCC/MinGW *(optional — only for the real-GCC panel)*
1. Download the "GCC + MinGW-w64" build from https://winlibs.com/ (get the
   release with POSIX threads, UCRT runtime).
2. Extract the zip somewhere permanent, e.g. `C:\mingw64`.
3. Add `C:\mingw64\bin` to your PATH (see Step 4 for how to edit PATH).
4. Verify: open a **new** terminal and run `gcc --version`.

### Step 4 — Configure a PATH entry (how-to, referenced by Steps 3 & 5)
1. Press `Win`, type **"Environment Variables"**, open *"Edit the system
   environment variables"*.
2. Click **Environment Variables…**.
3. Under **User variables**, select `Path` → **Edit** → **New**.
4. Paste the folder path (e.g. `C:\mingw64\bin`) → **OK** on every dialog.
5. **Close and reopen** any terminal/VS Code window — PATH changes don't
   apply to already-open terminals.

### Step 5 — Install Flex/Bison *(optional — only to build `compiler/`)*
The easiest path on Windows is **WinFlexBison**:
1. Download the latest release zip from
   https://github.com/lexxmark/winflexbison/releases.
2. Extract to e.g. `C:\winflexbison`.
3. Add `C:\winflexbison` to PATH (see Step 4).
4. Verify: `win_flex --version` and `win_bison --version`.

### Step 6 — Configure Flex/Bison PATH
Already covered by Step 5.3 above — just confirm both commands work in a
**new** terminal before moving on.

### Step 7 — Create/open the project folder
Unzip the project anywhere, e.g. `C:\Projects\C-Compiler-Error-Explainer`.
In VS Code: **File → Open Folder…** → select that folder.

### Step 8 — Create a virtual environment *(if Flask is used — see §6)*
Open a terminal in VS Code (`` Ctrl+` ``), then:
```powershell
cd backend
python -m venv venv
```
Activate it:
```powershell
# PowerShell
venv\Scripts\Activate.ps1

# Command Prompt
venv\Scripts\activate.bat
```
> If PowerShell blocks the activation script with a "running scripts is
> disabled" error, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again.

You'll know it worked because the prompt now starts with `(venv)`.

### Step 9 — Install dependencies
With the venv active:
```powershell
pip install -r requirements.txt
```
This installs exactly two packages: Flask and flask-cors. Nothing else —
no AI SDK, no `.env` file, no key to configure.

### Step 10 — Run the backend
Still inside `backend/`, with the venv active:
```powershell
python app.py
```
You should see:
```
C Compiler Error Explainer backend starting...
AI used: No (100% rule-based, fully offline)
Listening on: http://127.0.0.1:5000
```
Leave this terminal running.

### Step 11 — Open the frontend
The frontend is a plain static site — no build step. Just open
`frontend/index.html` directly in your browser (double-click it in File
Explorer, or right-click → **Open with** → your browser). The header
should show a green **"Backend Ready"** status pill, plus a permanent
**"100% Offline · No AI"** badge, within a second.

> Alternative: in VS Code, install the **"Live Server"** extension, right
> click `frontend/index.html` → **"Open with Live Server"**. Either
> method works — the app only needs `backend/app.py` running underneath.

### Step 12 — Load an example and analyze
Use the **Select Example** dropdown, pick any of the 10 built-in
programs, and click **Analyze Code**.

## 8b. Running the automated test suite

An automated test suite (`backend/tests/test_pipeline.py`, 27 tests, pure
`unittest` — no extra install needed) exercises all six phases, every
error category, phase-skipping behavior, and the rule-based Error
Explainer — including a structural test that asserts the explainer module
contains no network/API-related code at all. With the venv active, from
`backend/`:
```powershell
python -m unittest discover -s tests -v
```
All 27 should report `ok`.

## 9. How the Error Explainer works (100% rule-based, Section 26)

```text
C source code
     │
     ▼
Lexer / Parser / Semantic Analyzer   ← the REAL analysis happens here
     │
     ▼
Structured error object
  { "phase": "...", "error_type": "...", "line": N, "message": "...", "source_line": "..." }
     │
     ▼
Error Analyzer          (error_explainer.explain_error)
     │
     ▼
Error Classifier         (_classify: raw error -> ERROR_CODE, e.g. "MISSING_SEMICOLON")
     │
     ▼
Error Rule Matcher        (ERROR_RULES[error_code], with a generic fallback per phase)
     │
     ▼
Explanation Generator      (_render: fills the rule's template with THIS error's own line/name)
     │
     ▼
Suggested Fix
```

Every rule in `ERROR_RULES` (see `backend/error_explainer.py`) is a plain
Python dictionary with `error_type`, `phase`, `message`, `explanation`,
`solution`, `example`, and `tip` fields — exactly the structure described
in Section 28 of the spec. There is no AI call, no external request, and
nothing to configure: the same input always produces the same
explanation, which makes the whole system easy to test (see
`backend/tests/test_pipeline.py`) and easy to demonstrate offline.

## 10. Example usage

1. Load **Example 2 — Missing Semicolon** from the dropdown.
2. Click **Analyze Code**.
3. The pipeline strip shows Lexical done, Syntax failed, Semantic/IR/
   Optimize/Codegen pending.
4. Open the **Errors** tab → click the syntax error → the **Error
   Explanation** tab shows the matched rule code (`MISSING_SEMICOLON`),
   what happened, why, the fix, and a beginner tip.

## 11. Limitations (please read before your viva)

- This is an **educational compiler for a subset of C** (see supported
  keywords/constructs below) — it is **not** a replacement for GCC/Clang
  and does not implement the full C standard.
- **Arrays are not implemented** in the lexer/parser/semantic analyzer —
  the spec allows arrays "where practical," and supporting them correctly
  across all six phases (declarations, indexing, bounds, TAC, codegen)
  was judged too large an addition for a lab-scope tool without
  introducing untested bugs. This is documented honestly rather than
  silently omitted — a good candidate for the "Future Improvements"
  section of your report.
- Optimization passes (constant folding, propagation, algebraic
  simplification, dead-code elimination) are **educational**, not
  industrial-grade — no register allocation theory, no loop optimization.
- The generated target code is a **simplified pseudo-assembly**, not real
  x86/ARM machine code.
- TAC generation covers declarations, assignments, expressions, and
  function calls in full; `if`/`while`/`for` bodies are recursed into, but
  their *control flow itself* is not expanded into labels/conditional
  jumps (the TAC tab shows a `; if (...) -- control flow not expanded`
  comment instead).
- The rule database covers a fixed, documented set of error patterns
  (see `ERROR_RULES` in `error_explainer.py`); an error that doesn't
  match a specific rule still gets a complete, honest generic explanation
  via the phase-level fallback rule — it never shows a blank panel, but a
  very unusual error may get a more general explanation than a highly
  specific one.
- The standalone Bison grammar (`compiler/parser.y`) covers a slightly
  smaller subset than the Python engine (no `for`-loops) — see
  `compiler/README.md`.

**Supported C subset:** `#include`, `int/float/double/char/void`, `if/else`,
`while`, `for` *(Python engine only)*, `return`, variable declarations,
assignment, arithmetic/relational/logical expressions, function calls
(`printf`/`scanf`-style), blocks `{ }`.
**Not supported:** structs/unions, pointers, arrays, `switch`, multi-file
programs, the preprocessor beyond `#include` recognition, and most of the
standard library beyond `printf`/`scanf` call syntax.

## 12. Future improvements

- Array support (declaration, indexing, bounds checking) across all six phases
- Block-level (not just function-level) scoping in the symbol table
- A real control-flow graph view for `if`/`while`/`for`
- Wiring `compiler/parser.exe` into `/analyze` as a selectable engine
- Expanding `ERROR_RULES` with more specific rules as new patterns are found

## 13. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `python` not recognized | Reinstall Python with "Add to PATH" checked, then open a **new** terminal |
| Frontend shows "Backend Offline" | `python app.py` isn't running, or it's on a different port than `API_BASE` in `frontend/script.js` |
| `ModuleNotFoundError: flask` | You forgot to activate the venv, or forgot `pip install -r requirements.txt` |
| `gcc`/`win_flex`/`win_bison` "not recognized" | PATH wasn't updated, or you didn't open a **new** terminal after editing PATH (Step 4) |
| CORS error in browser console | Make sure you're opening `frontend/index.html` as a file/Live Server, and the backend is running — `flask-cors` handles the rest |
| Port 5000 already in use | Set the `PORT` environment variable before running, e.g. `set PORT=5001 && python app.py`, and update `API_BASE` in `frontend/script.js` to match |

## 14. Project structure

See `docs/` for viva questions, a presentation outline, a report-ready
write-up, and 10 documented test cases — everything you need to
demonstrate and defend this project.

```text
C-Compiler-Error-Explainer/
├── frontend/            HTML/CSS/JS UI (no build step)
├── backend/              Flask app + all six compiler phases + rule-based explainer
│   └── tests/               Automated test suite (27 tests, `python -m unittest`)
├── compiler/               Standalone Flex/Bison academic artifact
├── examples/                10 built-in C example programs
├── docs/                     Viva questions, slides outline, report, test cases, demo script
├── run.bat                    One-click: activate venv + start Flask on Windows
└── README.md                  You are here
```

---

*C Compiler Error Explainer — built for a university Compiler Design
Lab. Contains no AI. Not a replacement for a real C compiler.*
=======
# Compiler-Error-Explainer
An educational compiler visualizer that exposes each phase of the compilation pipeline—from lexical tokens and ASTs to intermediate representation and assembly—making compiler theory tangible.
>>>>>>> 0bd0d3c95a9d04095aac6621b808bacfe255b58b
