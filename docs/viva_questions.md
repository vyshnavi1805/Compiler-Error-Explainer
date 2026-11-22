# Viva Questions & Answers (42)

Short, memorizable answers, grouped by topic and tied to this project
where relevant.

## Compiler fundamentals

**1. What is a compiler?**
A program that translates source code written in one language (here, a C
subset) into another form (here, TAC and pseudo-assembly), typically
checking it for correctness along the way.

**2. What is an interpreter, and how does it differ from a compiler?**
An interpreter executes source code directly, statement by statement,
without producing a separate target program. A compiler translates the
whole program first, then it (or something else) runs the translated
output.

**3. What are the six phases of a compiler?**
Lexical Analysis, Syntax Analysis, Semantic Analysis, Intermediate Code
Generation, Code Optimization, Code Generation — each implemented as its
own module in `backend/`.

**4. Which phases form the "front end" vs "back end"?**
Front end: Lexical, Syntax, Semantic Analysis, and IR generation (machine
independent). Back end: Optimization and Code Generation (closer to the
target machine).

**5. What is the symbol table used for across phases?**
It's built during Semantic Analysis but conceptually shared: it records
every identifier's name, type, scope, and declaration line so later
phases (and error messages) can refer back to it.

## Lexical analysis

**6. What is a token?**
The smallest meaningful unit of source code — a keyword, identifier,
constant, operator, or delimiter.

**7. What is a lexeme, and how does it differ from a token?**
The lexeme is the actual text matched (e.g. `x`); the token is its
category (e.g. `IDENTIFIER`). One token type can match many lexemes.

**8. What technique does `backend/lexer.py` use to tokenize?**
A single master regular expression built from named groups, one per
token category, scanned left-to-right with Python's `re.finditer`.

**9. Why must multi-character operators like `==` be listed before `=`
in the token specification?**
Regex alternation matches the first pattern that fits, so if `=` were
checked first, `==` would incorrectly be tokenized as two separate `=`
tokens instead of one `==` token.

**10. What are regular expressions used for in lexical analysis?**
They describe the character patterns of each token category (e.g. an
identifier is a letter/underscore followed by letters/digits/underscores).

**11. What is a DFA/NFA, and how does it relate to a lexer?**
A Deterministic/Nondeterministic Finite Automaton is the theoretical
machine that recognizes a regular language. Tools like Flex compile
regular expressions into a DFA internally; our Python lexer achieves the
same result using Python's built-in regex engine instead of hand-building
a DFA.

**12. What is a lexical error, with an example from this project?**
A character that cannot be part of any valid token, e.g. a stray `~` or
`@` — see `examples/07_invalid_character.c`.

**13. What role does `yylineno` play in the Flex file?**
It's a built-in Flex option that automatically tracks the current line
number, used for line-numbered error messages.

## Syntax analysis

**14. What is a Context-Free Grammar (CFG)?**
A set of production rules describing how valid programs can be built from
smaller pieces (e.g. `statement := declaration | assignment | ...`), used
to define a language's syntax.

**15. What parsing technique does `backend/parser.py` use?**
Recursive descent: each grammar rule is implemented as a Python method
that calls the methods for the rules it references.

**16. What is a parse tree?**
A tree representation of how the grammar rules were applied to derive the
input program — visible in the "Parse Tree" tab.

**17. How does this project achieve operator precedence in expressions
(e.g. `*` before `+`)?**
Precedence climbing: `_expr()` calls `_logical_or()`, which calls
`_logical_and()`, ... down to `_term()` (`*`/`/`/`%`) and `_additive()`
(`+`/`-`) — lower-precedence operators wrap higher-precedence ones.

**18. What is error recovery, and what strategy does this project use?**
Continuing to parse after an error instead of stopping. This project uses
"error insertion": when an expected token like `;` is missing, it records
the error and pretends the token was there, so parsing continues and
later errors can still be found (see `examples/08_multiple_errors.c`).

**19. What does Bison generate, and how does it relate to `parser.y`?**
Bison reads a grammar specification (`.y` file) and generates C code for
an LALR parser. `compiler/parser.y` is a real, buildable Bison grammar for
the same language this project's Python parser handles.

**20. What is the "dangling else" problem, and how is it handled in
`compiler/parser.y`?**
Ambiguity over which `if` an `else` belongs to when `if`s are nested
without braces. Resolved with Bison precedence declarations (`%nonassoc
IFX` / `%nonassoc ELSE`), which tell Bison to always attach `else` to the
nearest unmatched `if`.

## Semantic analysis

**21. What does semantic analysis check that syntax analysis cannot?**
Meaning, not just structure — e.g. whether a variable was declared before
use, whether types are compatible — things a CFG alone can't express.

**22. What is an undeclared variable error, with an example?**
Using an identifier that was never declared, e.g. `y = 10;` with no prior
`int y;` — see `examples/04_undeclared_variable.c`.

**23. What is a duplicate declaration error?**
Declaring the same identifier twice in the same scope — see
`examples/05_duplicate_declaration.c`.

**24. What is a type mismatch error, with an example?**
Assigning a value of an incompatible type, e.g. `int x; x = "hello";` —
see `examples/06_type_mismatch.c`.

**25. How does this project distinguish an error from a warning?**
Errors block later phases (e.g. undeclared variable); warnings are
informational only (e.g. assigning a `float` into an `int`, which is
legal C but loses precision) and don't stop the pipeline.

## Symbol table & scope

**26. How are symbols inserted into the symbol table?**
`SymbolTable.insert(name, type, line, kind)` adds a `Symbol` to the
dictionary at the top of the current scope stack, after checking it isn't
already declared there.

**27. How are symbols searched/looked up?**
`SymbolTable.lookup(name)` searches from the innermost (top-of-stack)
scope outward to the global scope, so local names correctly shadow
global ones.

**28. How is scope handled in this project?**
A stack of dictionaries — one dictionary per function; entering a
function pushes a new scope, leaving it pops that scope.

**29. How are duplicate declarations detected?**
By checking `is_declared_in_current_scope(name)` before inserting — if
true, it's a duplicate in *this* scope (shadowing a global name in an
inner scope is still allowed).

## Intermediate code & optimization

**30. What is Three-Address Code (TAC)?**
An intermediate representation where every instruction has at most one
operator and three operands (e.g. `t1 = b * c`), making it easy to
optimize and later translate to target code.

**31. Why is intermediate code useful?**
It's machine-independent, simplifies optimization (working on TAC once
instead of every target architecture separately), and separates
front-end concerns (language semantics) from back-end ones (target
machine).

**32. What is constant folding?**
Evaluating constant expressions at compile time instead of at runtime,
e.g. `10 * 2` → `20`.

**33. What is constant propagation?**
Substituting a variable's known constant value into later uses of that
variable, e.g. once `x = 20` is known, `y = x + 5` becomes `y = 25`.

**34. What is dead code elimination?**
Removing computations whose results are never used — in this project,
temporaries left behind after constant propagation has replaced every use
of them.

**35. What is algebraic simplification, with an example?**
Simplifying expressions using algebraic identities without needing both
operands to be constants, e.g. `y + 0` → `y`, `x * 1` → `x`.

## Code generation & tooling

**36. What does the code generator in this project produce?**
A simplified pseudo-assembly (`LOAD`, `STORE`, `ADD`, `CALL`, etc.) over
a small fixed register file — an educational target representation, not
real machine code.

**37. What's the difference between this project's target code and what
GCC produces?**
GCC generates real, architecture-specific machine code (x86/ARM) with
full register allocation, instruction selection, and calling conventions;
this project's output is a simplified teaching model of the same idea.

**38. How does this project use real GCC, if at all?**
Optionally: `backend/gcc_bridge.py` can shell out to `gcc` (if installed)
and parse its stderr diagnostics into the same structured-error shape as
the other phases, shown as a side-by-side comparison panel — never a
requirement.

## Rule-based error explainer & project design

**39. Why doesn't this project use AI to explain errors?**
Two reasons: the course requirement explicitly excludes AI, and a
rule-based design keeps every explanation fully transparent and
testable — the same error always produces the exact same explanation,
and that behavior can be verified with ordinary unit tests instead of
trusting a black-box model.

**40. How does the rule-based Error Explainer decide which explanation to show?**
A five-stage pipeline in `error_explainer.py`: the raw structured error
is classified into a fixed `error_code` (e.g. `MISSING_SEMICOLON`) by
`_classify()` based on its phase, message, and expected/actual tokens;
that code is looked up in the `ERROR_RULES` dictionary; and the matched
rule's message/explanation/solution/example/tip templates are filled in
with that specific error's own line number and names by `_render()`.

**41. What happens if an error doesn't match any specific rule?**
It falls through to a generic, phase-level rule (`GENERIC_LEXICAL`,
`GENERIC_SYNTAX`, or `GENERIC_SEMANTIC`) that still produces a complete,
non-blank explanation using the error's own phase and message — the
explainer is designed to never show an empty panel, even for an error
shape the rule database wasn't specifically written for.

**42. How would you prove to your professor that no AI is being used?**
Open `backend/error_explainer.py` and show that its only import is
Python's standard `re` module — no HTTP client, no API key, no external
library. You can also disconnect the internet entirely and demonstrate
that every tab, including error explanations, still works identically.
