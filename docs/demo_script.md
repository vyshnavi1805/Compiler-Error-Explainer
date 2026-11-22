# Demo Scenario & Script

A ~4-5 minute walkthrough you can run live for your professor. Left column
is what to click; right column is roughly what to say.

| Step | Action | What to say |
|---|---|---|
| 1 | Open `frontend/index.html` with `backend/app.py` already running | "This is C Compiler Error Explainer — it runs a C program through the six phases of a compiler, and explains any errors it finds using a rule-based engine. There's no AI anywhere in this project — it runs completely offline." |
| 2 | Click **Select Example** → **"2. Missing Semicolon"** | "I'll load an example with a deliberate syntax error." |
| 3 | Click **Analyze Code** | "The backend just ran the code through the lexer, parser, and semantic analyzer." |
| 4 | Point at the **Compiler Pipeline** strip | "You can see Lexical Analysis passed, but Syntax Analysis failed — and because syntax failed, Intermediate Code, Optimization, and Code Generation were honestly skipped, since generating those from a broken parse tree would be misleading." |
| 5 | Click the **Tokens** tab | "Phase 1 broke the source into these tokens — keywords, identifiers, constants, operators — each with its line and column." |
| 6 | Click the **Errors** tab, then click the error card | "Phase 2 caught a missing semicolon on line 4 and recorded exactly what was expected versus what it found." |
| 7 | Click the **Error Explanation** tab | "This structured error was matched against a rule database — see the rule code at the top, like MISSING_SEMICOLON — and the matching rule's template fills in the specific line and text for this error. What happened, why it's a problem, how to fix it, and the corrected line, all from predefined logic — no AI, no guessing, no network call." |
| 8 | Load **"9. Expression for TAC"**, click **Analyze Code** | "This one is valid, so all six phases run. Here's the Intermediate Code tab —" |
| 9 | Click **Intermediate Code** tab | "— real Three-Address Code, temporaries and all, correctly respecting that `*` binds tighter than `+`." |
| 10 | Load **"10. Optimization Showcase"**, click **Analyze Code**, open **Optimization** tab | "And here you can see the four optimization passes: constant folding, constant propagation, algebraic simplification, and dead-code elimination — before and after, with the technique labeled for each change." |
| 11 | Click **Target Code** tab | "Finally, Phase 6 emits a simplified pseudo-assembly from the optimized code — this is deliberately not real x86, it's an educational target representation." |
| 12 | *(Optional)* tick **"Also compile with real GCC"**, re-analyze | "If GCC is installed, we can also show real GCC's diagnostics side-by-side, just for comparison — it's never required for the app to work." |

### If asked "why didn't you just use Flex/Bison for everything?"
Open `compiler/parser.y` and `compiler/lexer.l`: "These are real, buildable
Flex and Bison files implementing the same grammar — I can build and run
them from a terminal. I used a hand-written Python engine for the *live*
demo so it doesn't depend on a native toolchain being perfectly configured
on whichever machine I'm presenting from, but the parser-generator
implementation is right here and does the same job."

### If asked "how do you know the explainer isn't secretly using AI?"
Open `backend/error_explainer.py` and scroll through `ERROR_RULES`:
"Every explanation comes from this dictionary — plain Python data, no
imports beyond the standard library `re` module. You can unplug the
internet entirely and every tab still works identically, because nothing
here ever makes a network call."
