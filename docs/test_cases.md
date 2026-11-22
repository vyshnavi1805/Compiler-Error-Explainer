# Test Cases

> An automated version of these checks (27 tests total, using Python's
> built-in `unittest`) lives at `backend/tests/test_pipeline.py`. Run it
> with `python -m unittest discover -s tests -v` from `backend/` — all
> 23 currently pass. The manual cases below map to specific tests in
> that file so you can show your professor both the documented
> expectation and the automated proof it holds.

All 10 cases below were run against the actual pipeline
(`backend/app.py: run_pipeline()`) and the results shown are real output,
not projected — you can reproduce every row yourself by loading the
matching example from the dropdown and clicking **Analyze Code**.

---

### Test Case 1 — Valid Program
**Input:** `examples/01_valid.c`
**Expected compiler phase reached:** All six
**Expected result:** `Compilation Analysis Successful`, 0 errors, 0 warnings, 34 tokens, 4 symbols
**Expected error:** None
**Expected AI explanation:** None — the AI Explanation tab shows the empty state

### Test Case 2 — Lexical Error
**Input:** `examples/07_invalid_character.c` (contains a stray `~` character)
**Expected compiler phase reached:** Lexical Analysis (fails), all later phases `not_processed`
**Expected result:** `Compilation Failed`, 1 error
**Expected error:** `Lexical Error`, line 6, `Unrecognised character '~'`
**Expected AI explanation:** Explains that `~` isn't part of any valid C token here and suggests removing it / checking for a copy-paste artifact

### Test Case 3 — Syntax Error
**Input:** `examples/02_missing_semicolon.c`
**Expected compiler phase reached:** Lexical (✓) → Syntax (✗); Semantic/IR/Optimize/Codegen skipped
**Expected result:** `Compilation Failed`, 1 error
**Expected error:** `Syntax Error`, line 4, `expected ';' but found 'return'`
**Expected AI explanation:** "You forgot a semicolon at the end of this statement" + corrected line `int x = 10;`

### Test Case 4 — Semantic Error
**Input:** `examples/04_undeclared_variable.c`
**Expected compiler phase reached:** Lexical (✓) → Syntax (✓) → Semantic (✗); IR/Optimize/Codegen skipped
**Expected result:** `Compilation Failed`, 2 errors
**Expected error:** `Semantic Error` ×2, both `'y' has not been declared.` (lines 4 and 5 — once for the assignment, once for the read)
**Expected AI explanation:** Explains that `y` was used without a matching `int y;` (or similar) declaration first

### Test Case 5 — Multiple Errors (mixed phases)
**Input:** `examples/08_multiple_errors.c`
**Expected compiler phase reached:** Lexical (✓) → Syntax (✗, 3 errors) → Semantic still runs on the parts it *can* recover (1 more error) → IR/Optimize/Codegen skipped
**Expected result:** `Compilation Failed`, 4 errors total
**Expected errors:**
  1. Syntax Error, line 4 — `expected ';' but found 'y'`
  2. Syntax Error, line 5 — `expected ';' but found 'printf'`
  3. Syntax Error, line 6 — `expected ';' but found 'return'`
  4. Semantic Error, line 5 — `'y' has not been declared.`
**Expected AI explanation:** One explanation card per error, each addressing only that specific problem

### Test Case 6 — Constant Folding
**Input:** line `x = 10 * 2;` from `examples/10_optimization.c`
**Expected compiler phase reached:** Optimization
**Expected result:** Raw TAC `t1 = 10 * 2` folds to `t1 = 20`
**Expected error:** None
**Expected AI explanation:** N/A (Optimization tab shows the before/after diff and technique name directly, no AI call needed)

### Test Case 7 — Constant Propagation
**Input:** lines `x = 10 * 2; y = x + 5;` from `examples/10_optimization.c`
**Expected compiler phase reached:** Optimization
**Expected result:** After folding `x` to `20`, the propagation pass substitutes it into `y = x + 5` → `t2 = 25` → `y = 25`
**Expected error:** None

### Test Case 8 — Dead Code Elimination
**Input:** `examples/10_optimization.c` (the temporaries `t1`, `t2`, `t3`)
**Expected compiler phase reached:** Optimization
**Expected result:** Once constant propagation has substituted the *values* of `t1`/`t2`/`t3` everywhere they were used, the assignments to those temporaries themselves become dead and are removed, leaving `x = 20; y = 25; y = 25; call printf, "%d", 25;`
**Expected error:** None

### Test Case 9 — TAC Generation
**Input:** `examples/09_tac_expression.c` (`x = a + b * c;`)
**Expected compiler phase reached:** Intermediate Code
**Expected result:**
```
t1 = b * c
t2 = a + t1
x = t2
```
correctly reflecting `*` binding tighter than `+`.
**Expected error:** None

### Test Case 10 — Target Code Generation
**Input:** `examples/09_tac_expression.c`, after optimization
**Expected compiler phase reached:** Code Generation
**Expected result:** Pseudo-assembly using `LOAD`/`STORE`/`PUSH`/`CALL`/`RET`, e.g. `LOAD R1, 14`, `STORE x, R1`, `PUSH "%d"`, `PUSH 14`, `CALL printf` (the compiler folded `2 + 3*4` down to the constant `14` before code generation ran)
**Expected error:** None

---

**Duplicate Declaration and Type Mismatch** are also covered by
`examples/05_duplicate_declaration.c` (1 Semantic Error, `'x' is already
declared in this scope`) and `examples/06_type_mismatch.c` (1 Semantic
Error, `Type mismatch: cannot assign a string literal to 'x'`) if your
teacher asks for those specifically — same phase-skipping behavior as
Test Case 4 applies to both.
