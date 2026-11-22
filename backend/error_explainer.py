"""
error_explainer.py
--------------------
THE ERROR EXPLAINER — this project's main feature.

IMPORTANT: This is a 100% RULE-BASED system. There is NO AI, NO machine
learning, and NO external API call anywhere in this file (or anywhere in
the project). Every explanation shown to the user comes from a fixed
database of hand-written rules, matched against the structured error
object that the real compiler phases (lexer.py / parser.py / semantic.py)
already produced.

PIPELINE (Section 26 of the spec):

    C Code
      |
      v
    Compiler Phases (lexer/parser/semantic)  <- detect the REAL problem
      |
      v
    Structured Error Object
      |
      v
    Error Analyzer         (this file: explain_error())
      |
      v
    Error Classifier        (_classify: turns the raw error into an ERROR_CODE)
      |
      v
    Error Rule Matcher       (ERROR_RULES[error_code], with a generic fallback)
      |
      v
    Explanation Generator     (_render: fills the rule's template with THIS
      |                        error's specific line/lexeme/names)
      v
    Suggested Fix

Because the explanation is entirely template-based, it works identically
whether the machine has internet access or not -- there is nothing to
configure, no key to enter, and no network call to fail.
"""

import re

# ---------------------------------------------------------------------
# THE RULE DATABASE (Section 28 of the spec)
# ---------------------------------------------------------------------
# Every rule is a plain Python dictionary with exactly these fields:
#   error_type    "Lexical Error" | "Syntax Error" | "Semantic Error" | "Warning"
#   phase         which compiler phase raises this
#   message       a template for the one-line message (Python .format() style)
#   explanation   "What happened?" in beginner language
#   solution      "How can I fix it?"
#   example       a short before/after C snippet
#   tip           a beginner tip to avoid the mistake in future
#
# {placeholders} inside message/explanation/solution/example are filled in
# by _render() using the specific error's own data (line, lexeme, name, ...).
# The dictionary KEY itself is the error_code (e.g. "MISSING_SEMICOLON").
# ---------------------------------------------------------------------

ERROR_RULES = {

    # ----------------------- LEXICAL ERRORS -----------------------
    "INVALID_CHARACTER": {
        "error_type": "Lexical Error",
        "phase": "Lexical Analysis",
        "message": "Invalid character '{lexeme}'.",
        "explanation": "The lexer encountered the character '{lexeme}' on line "
                        "{line}, which is not valid anywhere in the supported C "
                        "syntax -- it isn't part of any keyword, identifier, "
                        "number, string, operator, or delimiter.",
        "solution": "Remove or replace the character '{lexeme}'. This is often "
                     "caused by copy-pasting code from a website that uses "
                     "different quote marks, dashes, or symbols than plain ASCII.",
        "example": "Before:  int x = 10 {lexeme} 20;\nAfter:   int x = 10 + 20;",
        "tip": "If your code was copied from a PDF, Word document, or web page, "
               "retype the punctuation by hand -- smart quotes and special dashes "
               "look almost identical to normal ones but are different characters.",
    },
    "UNTERMINATED_STRING": {
        "error_type": "Lexical Error",
        "phase": "Lexical Analysis",
        "message": "Unterminated string literal near line {line}.",
        "explanation": "A string literal (text inside double quotes) was opened "
                        "with a '\"' but never closed with a matching '\"' before "
                        "the end of the line.",
        "solution": "Add the missing closing double-quote '\"' at the end of the "
                     "string.",
        "example": 'Before:  printf("Hello);\nAfter:   printf("Hello");',
        "tip": "Count your quote marks -- every opening \" needs exactly one "
               "matching closing \" on the same line.",
    },
    "INVALID_NUMBER": {
        "error_type": "Lexical Error",
        "phase": "Lexical Analysis",
        "message": "Malformed numeric literal near line {line}.",
        "explanation": "The characters here don't form a valid C number -- for "
                        "example, a number with two decimal points like "
                        "'12.34.56' is not a valid float or integer.",
        "solution": "Make sure each number has at most one decimal point.",
        "example": "Before:  float f = 12.34.56;\nAfter:   float f = 12.34;",
        "tip": "If you meant to write two separate numbers, add an operator or "
               "punctuation between them.",
    },

    # ----------------------- SYNTAX ERRORS -----------------------
    "MISSING_SEMICOLON": {
        "error_type": "Syntax Error",
        "phase": "Syntax Analysis",
        "message": "Missing semicolon ';' after line {line}.",
        "explanation": "The statement on line {line} does not end with a "
                        "semicolon. In C, most statements -- declarations, "
                        "assignments, function calls, return statements -- must "
                        "end with ';' so the compiler knows where one statement "
                        "stops and the next begins.",
        "solution": "Add a semicolon ';' at the end of the statement shown "
                     "above.",
        "example": "Before:  int x = 10\nAfter:   int x = 10;",
        "tip": "After writing any line inside a function body, glance back at "
               "the end of it and ask: does this line need a semicolon?",
    },
    "MISSING_CLOSING_PAREN": {
        "error_type": "Syntax Error",
        "phase": "Syntax Analysis",
        "message": "Missing closing parenthesis ')' near line {line}.",
        "explanation": "An opening '(' was found, but its matching closing ')' "
                        "is missing before the statement ends.",
        "solution": "Add the missing ')' to close the parenthesis.",
        "example": 'Before:  printf("%d", x;\nAfter:   printf("%d", x);',
        "tip": "Every '(' needs exactly one matching ')'. In a long expression, "
               "count them from left to right if you're not sure which one is "
               "missing.",
    },
    "MISSING_OPENING_PAREN": {
        "error_type": "Syntax Error",
        "phase": "Syntax Analysis",
        "message": "Missing opening parenthesis '(' near line {line}.",
        "explanation": "A construct that requires parentheses around its "
                        "condition (like 'if' or 'while') is missing its "
                        "opening '('.",
        "solution": "Add '(' right after the keyword, before the condition.",
        "example": "Before:  if x > 10) {{\nAfter:   if (x > 10) {{",
        "tip": "'if', 'while', and 'for' always need their condition wrapped "
               "in parentheses: if (...), while (...), for (...).",
    },
    "MISSING_BRACE": {
        "error_type": "Syntax Error",
        "phase": "Syntax Analysis",
        "message": "Missing closing brace '}}' for a block opened before line {line}.",
        "explanation": "A block was opened with '{{' but never closed with a "
                        "matching '}}' before the file ended.",
        "solution": "Add the missing '}}' to close the block.",
        "example": "Before:  int main() {{\n             int x = 10;\n"
                    "After:   int main() {{\n             int x = 10;\n         }}",
        "tip": "Every '{{' needs exactly one matching '}}'. In VS Code, click "
               "right after a brace -- it highlights the matching one, which "
               "makes it easy to spot a missing pair.",
    },
    "UNEXPECTED_TOKEN": {
        "error_type": "Syntax Error",
        "phase": "Syntax Analysis",
        "message": "Unexpected token '{actual}' on line {line} (expected {expected}).",
        "explanation": "The parser expected to see '{expected}' at this point in "
                        "the program, based on C's grammar rules, but instead "
                        "found '{actual}'.",
        "solution": "Check line {line} against the surrounding code -- you're "
                     "likely missing '{expected}', or have an extra/misplaced "
                     "token nearby.",
        "example": "Compare this line against a similar, correct line elsewhere "
                    "in your program.",
        "tip": "Syntax errors often cascade -- fixing the FIRST one reported and "
               "re-analyzing frequently makes several later errors disappear "
               "too.",
    },

    # ----------------------- SEMANTIC ERRORS -----------------------
    "UNDECLARED_VARIABLE": {
        "error_type": "Semantic Error",
        "phase": "Semantic Analysis",
        "message": "Variable '{name}' has not been declared.",
        "explanation": "The identifier '{name}' is used on line {line}, but no "
                        "matching declaration (like 'int {name};') appears "
                        "earlier in the same scope. C requires every variable "
                        "to be declared with a type before it is used.",
        "solution": "Add a declaration for '{name}' before this line, with the "
                     "correct type.",
        "example": "Before:  {name} = 10;\nAfter:   int {name};\n         {name} = 10;",
        "tip": "Declare every variable at (or near) the top of the block where "
               "you first use it -- it's easier to keep track of than "
               "declaring things scattered across a function.",
    },
    "DUPLICATE_DECLARATION": {
        "error_type": "Semantic Error",
        "phase": "Semantic Analysis",
        "message": "Variable '{name}' has already been declared in this scope.",
        "explanation": "'{name}' was declared once already (see the earlier "
                        "line noted in the message), and line {line} tries to "
                        "declare it again in the SAME scope. C does not allow "
                        "the same name to be declared twice in one scope.",
        "solution": "Remove the second declaration, or rename the second "
                     "variable if you actually meant to introduce a new, "
                     "different variable.",
        "example": "Before:  int {name};\n         int {name};\n"
                    "After:   int {name};\n         {name} = 5;  // reuse it, don't redeclare",
        "tip": "If you want two different variables, give them two different "
               "names -- reusing a name for something new is a common source "
               "of duplicate-declaration errors.",
    },
    "TYPE_MISMATCH": {
        "error_type": "Semantic Error",
        "phase": "Semantic Analysis",
        "message": "Type mismatch: cannot assign this value to '{name}'.",
        "explanation": "'{name}' was declared with one type, but the value "
                        "assigned to it on line {line} is a different, "
                        "incompatible type (for example, assigning text to a "
                        "number).",
        "solution": "Either assign a value of the correct type to '{name}', or "
                     "change {name}'s declared type to match the value you "
                     "want to store.",
        "example": "Before:  int {name};\n         {name} = \"Hello\";\n"
                    "After:   char {name}[20];\n         strcpy({name}, \"Hello\");",
        "tip": "int/float/double hold numbers; char (or an array of char) "
               "holds text. Mixing the two is one of the most common "
               "beginner semantic errors.",
    },
    "INVALID_OPERATION": {
        "error_type": "Semantic Error",
        "phase": "Semantic Analysis",
        "message": "Invalid operation on line {line}: incompatible operand types.",
        "explanation": "This expression combines two values whose types don't "
                        "work together with the given operator -- for example, "
                        "using '+' between a number and a piece of text.",
        "solution": "Make sure both sides of the operator are compatible types "
                     "(both numbers, or both text handled with a text function "
                     "like strcat, not '+').",
        "example": 'Before:  x = 10 + "hello";\nAfter:   x = 10 + 5;',
        "tip": "C does not overload '+' for text like some other languages "
               "do -- you cannot 'add' a string to a number.",
    },

    # ----------------------- GENERIC FALLBACKS -----------------------
    # Used only if a detected error doesn't match any specific rule above --
    # this guarantees the explainer NEVER shows a blank or broken panel.
    "GENERIC_LEXICAL": {
        "error_type": "Lexical Error",
        "phase": "Lexical Analysis",
        "message": "{message}",
        "explanation": "The lexer could not turn part of line {line} into a "
                        "valid token.",
        "solution": "Check line {line} for typos or unsupported characters.",
        "example": "Compare the flagged character against valid C syntax.",
        "tip": "Lexical errors are almost always a single stray or mistyped "
               "character.",
    },
    "GENERIC_SYNTAX": {
        "error_type": "Syntax Error",
        "phase": "Syntax Analysis",
        "message": "{message}",
        "explanation": "The parser could not match line {line} against any "
                        "valid C grammar rule in the supported subset.",
        "solution": "Compare this line against the C grammar rules in "
                     "compiler/parser.y, or against a working example program.",
        "example": "See the example programs in the Examples dropdown for "
                    "correctly-structured statements.",
        "tip": "Fix the earliest-reported error first -- later errors are often "
               "just consequences of it.",
    },
    "GENERIC_SEMANTIC": {
        "error_type": "Semantic Error",
        "phase": "Semantic Analysis",
        "message": "{message}",
        "explanation": "Line {line} is grammatically valid C, but violates a "
                        "meaning-related rule (such as declaration-before-use "
                        "or type compatibility).",
        "solution": "Re-check the declaration, type, and scope of every name "
                     "used on line {line}.",
        "example": "Check the Symbol Table tab to see how each name was "
                    "declared.",
        "tip": "The Symbol Table tab shows exactly what the compiler believes "
               "about every variable's type and scope -- it's the fastest way "
               "to debug a semantic error.",
    },
}


# ---------------------------------------------------------------------
# Error Classifier -- turns a raw structured error into an ERROR_CODE
# ---------------------------------------------------------------------
def _classify(raw_error):
    """
    Look at the phase / message / expected-token of a structured error and
    decide which rule in ERROR_RULES applies. This is plain pattern
    matching on data the compiler phases already computed -- no guessing,
    no invented information, no AI.
    """
    phase = raw_error.get("phase", "")
    message = (raw_error.get("message") or "").lower()
    expected = (raw_error.get("expected") or "").strip()

    if phase == "Lexical Analysis":
        if "unterminated" in message or "unclosed" in message:
            return "UNTERMINATED_STRING"
        if "invalid" in message and "number" in message:
            return "INVALID_NUMBER"
        if "character" in message or "unrecognised" in message or "unrecognized" in message:
            return "INVALID_CHARACTER"
        return "GENERIC_LEXICAL"

    if phase == "Syntax Analysis":
        if expected == ";":
            return "MISSING_SEMICOLON"
        if expected == ")":
            return "MISSING_CLOSING_PAREN"
        if expected == "(":
            return "MISSING_OPENING_PAREN"
        if expected == "}":
            return "MISSING_BRACE"
        if expected:
            return "UNEXPECTED_TOKEN"
        return "GENERIC_SYNTAX"

    if phase == "Semantic Analysis":
        if "has not been declared" in message:
            return "UNDECLARED_VARIABLE"
        if "already declared" in message:
            return "DUPLICATE_DECLARATION"
        if "type mismatch" in message:
            return "TYPE_MISMATCH"
        if "invalid operation" in message:
            return "INVALID_OPERATION"
        return "GENERIC_SEMANTIC"

    return "GENERIC_SYNTAX"


# ---------------------------------------------------------------------
# Explanation Generator -- fills a rule's template with THIS error's data
# ---------------------------------------------------------------------
def _extract_name(raw_error):
    """
    Pull the variable/identifier name out of a semantic error message, since
    semantic.py reports messages like "'x' has not been declared." rather
    than a separate structured 'name' field.
    """
    message = raw_error.get("message") or ""
    m = re.search(r"'([^']+)'", message)
    return m.group(1) if m else "<name>"


def _render(rule, raw_error):
    fields = {
        "line": raw_error.get("line", "?"),
        "column": raw_error.get("column") if raw_error.get("column") is not None else "-",
        "lexeme": raw_error.get("lexeme", "?"),
        "expected": raw_error.get("expected") or "?",
        "actual": raw_error.get("actual") or "?",
        "name": _extract_name(raw_error),
        "message": raw_error.get("message", ""),
    }
    rendered = {}
    for key in ("message", "explanation", "solution", "example", "tip"):
        template = rule.get(key, "")
        try:
            rendered[key] = template.format(**fields)
        except (KeyError, IndexError):
            rendered[key] = template  # if a placeholder is missing, show the raw template rather than crash
    return rendered


# ---------------------------------------------------------------------
# Public API used by app.py
# ---------------------------------------------------------------------
def normalize_error(raw_error, language="C"):
    """Ensure every error (lexical/syntax/semantic) has the exact same shape."""
    return {
        "language": language,
        "phase": raw_error.get("phase"),
        "error_type": raw_error.get("error_type"),
        "line": raw_error.get("line"),
        "column": raw_error.get("column"),
        "message": raw_error.get("message"),
        "source_line": raw_error.get("source_line", ""),
        "expected": raw_error.get("expected"),
        "actual": raw_error.get("actual"),
    }


def explain_error(raw_error):
    """
    THE main entry point (Section 26): Error Analyzer -> Classifier ->
    Rule Matcher -> Explanation Generator -> Suggested Fix.

    100% rule-based -- no AI call, no network, nothing to configure.

    Returns a dict:
        {
          "error_code": "MISSING_SEMICOLON",
          "error_type": "Syntax Error",
          "explanation": "...", "reason": "...", "solution": "...",
          "corrected_code": "...", "example": "...", "tip": "...",
          "source": "rule_based"
        }
    """
    error_code = _classify(raw_error)
    rule = ERROR_RULES[error_code]
    rendered = _render(rule, raw_error)

    return {
        "error_code": error_code,
        "error_type": rule["error_type"],
        "explanation": rendered["explanation"],
        "reason": rendered["message"],       # "why did it happen" == the precise rule message
        "solution": rendered["solution"],
        "corrected_code": rendered["example"],
        "example": rendered["example"],
        "tip": rendered["tip"],
        "source": "rule_based",
    }


def explain_all(errors):
    """Explain a list of structured errors, returning one explanation per error."""
    return [dict(**normalize_error(e), explanation=explain_error(e)) for e in errors]
