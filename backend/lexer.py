"""
lexer.py
--------
PHASE 1: LEXICAL ANALYSIS

This module turns raw C source code into a stream of TOKENS.

WHAT IS A TOKEN?
A token is the smallest meaningful unit of a program: a keyword, an
identifier (variable/function name), a number, an operator, a piece of
punctuation, etc. Lexical analysis is the process of scanning the raw
character stream and grouping characters into these meaningful units.

HOW THIS WORKS:
We build ONE big regular expression made of many named groups (one group
per token category). Python's `re` module lets us ask "which named group
matched?" for each match, which tells us the token category. We scan the
source from left to right, matching this master regex repeatedly.

This mirrors exactly what a tool like Flex does internally: Flex also
compiles a set of regular expressions into a single scanner. The
`compiler/lexer.l` file in this project shows the same logic expressed as
real Flex rules, if you want to compare the two approaches.
"""

import re

# ---------------------------------------------------------------------
# 1. Define the C keywords we support (see Section 33 - supported subset)
# ---------------------------------------------------------------------
KEYWORDS = {
    "int", "float", "double", "char", "void",
    "if", "else", "while", "for", "return",
    "break", "continue",
}

# ---------------------------------------------------------------------
# 2. Master token specification.
#    ORDER MATTERS: earlier patterns are tried first, so put more specific
#    / longer patterns before shorter ones (e.g. "==" before "=").
# ---------------------------------------------------------------------
TOKEN_SPEC = [
    ("PREPROCESSOR",  r"\#\s*include\s*[<\"][^>\"\n]+[>\"]"),
    ("COMMENT_MULTI",  r"/\*.*?\*/"),
    ("COMMENT_SINGLE", r"//[^\n]*"),
    ("WHITESPACE",     r"[ \t]+"),
    ("NEWLINE",        r"\n"),
    ("STRING_LITERAL", r'"([^"\\]|\\.)*"'),
    ("CHAR_LITERAL",   r"'([^'\\]|\\.)'"),
    ("FLOAT_CONSTANT",  r"\d+\.\d+([eE][+-]?\d+)?[fF]?"),
    ("INT_CONSTANT",    r"\d+"),
    ("IDENTIFIER",      r"[A-Za-z_][A-Za-z0-9_]*"),
    # Multi-character operators MUST come before single-character ones.
    ("OPERATOR", r"==|!=|<=|>=|&&|\|\||\+\+|--|\+=|-=|\*=|/=|[+\-*/%=<>!]"),
    ("DELIMITER", r"[(){}\[\];,]"),
    ("UNKNOWN", r"."),  # anything else = lexical error
]

MASTER_REGEX = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC),
    re.DOTALL,
)


class Token:
    def __init__(self, lexeme, token_type, category, line, column):
        self.lexeme = lexeme
        self.token_type = token_type      # e.g. KEYWORD, IDENTIFIER, OPERATOR
        self.category = category          # human-friendly label for the UI
        self.line = line
        self.column = column

    def to_dict(self):
        return {
            "lexeme": self.lexeme,
            "token": self.token_type,
            "category": self.category,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self):
        return f"Token({self.token_type}, {self.lexeme!r}, line={self.line})"


# Human-friendly category names shown in the UI's Token table.
CATEGORY_LABELS = {
    "KEYWORD": "Keyword",
    "IDENTIFIER": "Identifier",
    "INT_CONSTANT": "Integer Constant",
    "FLOAT_CONSTANT": "Float Constant",
    "STRING_LITERAL": "String Literal",
    "CHAR_LITERAL": "Character Literal",
    "OPERATOR": "Operator",
    "DELIMITER": "Delimiter",
    "PREPROCESSOR": "Preprocessor Directive",
}


def tokenize(source_code):
    """
    Convert C source code into a list of Token objects.

    Returns:
        tokens (list[Token]): every meaningful token, in order.
        lexical_errors (list[dict]): any characters that could not be
            recognised as part of a valid token.
    """
    tokens = []
    lexical_errors = []

    line = 1
    line_start = 0  # index into source_code where the current line begins

    for match in MASTER_REGEX.finditer(source_code):
        kind = match.lastgroup
        lexeme = match.group()
        column = match.start() - line_start + 1

        if kind == "NEWLINE":
            line += 1
            line_start = match.end()
            continue

        if kind in ("WHITESPACE", "COMMENT_SINGLE"):
            continue

        if kind == "COMMENT_MULTI":
            # Multi-line comments can span several lines; keep line count correct.
            line += lexeme.count("\n")
            if "\n" in lexeme:
                line_start = match.end() - (len(lexeme) - lexeme.rfind("\n") - 1)
            continue

        if kind == "UNKNOWN":
            lexical_errors.append({
                "phase": "Lexical Analysis",
                "error_type": "Lexical Error",
                "line": line,
                "column": column,
                "message": f"Unrecognised character '{lexeme}'",
                "source_line": _get_source_line(source_code, line),
                "lexeme": lexeme,
            })
            continue

        if kind == "IDENTIFIER" and lexeme in KEYWORDS:
            token_type = "KEYWORD"
            category = "Keyword"
        else:
            token_type = kind
            category = CATEGORY_LABELS.get(kind, kind)

        tokens.append(Token(lexeme, token_type, category, line, column))

    return tokens, lexical_errors


def _get_source_line(source_code, line_number):
    """Utility: return the raw text of a given 1-indexed line number."""
    lines = source_code.split("\n")
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]
    return ""


def tokens_to_dict_list(tokens):
    return [t.to_dict() for t in tokens]
