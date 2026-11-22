"""
parser.py
---------
PHASE 2: SYNTAX ANALYSIS

This module checks whether the token stream produced by lexer.py follows
the grammar rules of the C subset we support (see Section 33 of the
project spec), and builds a PARSE TREE that later phases use.

TECHNIQUE: Recursive Descent Parsing
Each grammar rule becomes a Python method. A method for rule "A -> B C"
simply calls the method for B, then the method for C. This is the same
technique taught in every compiler design course, and it is exactly what
you would hand-write if you were not using a parser generator like Bison.
(This project also ships a real Bison grammar in compiler/parser.y for
comparison — see compiler/README.md.)

ERROR RECOVERY STRATEGY ("error insertion"):
When an expected token (like ';', ')' or '}') is missing, we do NOT crash.
We record a structured syntax error (with line/column/expected/actual) and
then *pretend* the token was there and keep parsing from the same
position. This mirrors how real compilers keep going after one mistake so
they can report multiple errors in a single pass (Section 31).

The grammar we support:

    program        := (function_def)*
    function_def   := type_spec IDENTIFIER '(' param_list? ')' block
    param_list     := param (',' param)*
    param          := type_spec IDENTIFIER
    block          := '{' statement* '}'
    statement      := declaration | assignment | if_stmt | while_stmt
                     | for_stmt | return_stmt | expr_stmt | block
    declaration    := type_spec IDENTIFIER ('=' expr)? ';'
    assignment     := IDENTIFIER '=' expr ';'
    if_stmt        := 'if' '(' expr ')' statement ('else' statement)?
    while_stmt     := 'while' '(' expr ')' statement
    for_stmt       := 'for' '(' simple? ';' expr? ';' simple? ')' statement
    return_stmt    := 'return' expr? ';'
    expr_stmt      := expr ';'
    expr           := logical_or
    logical_or     := logical_and ('||' logical_and)*
    logical_and    := equality ('&&' equality)*
    equality       := relational (('=='|'!=') relational)*
    relational     := additive (('<'|'>'|'<='|'>=') additive)*
    additive       := term (('+'|'-') term)*
    term           := factor (('*'|'/'|'%') factor)*
    factor         := ('-'|'!')? primary
    primary        := INT_CONST | FLOAT_CONST | STRING | CHAR
                     | IDENTIFIER ('(' args? ')')?
                     | '(' expr ')'
"""

TYPE_KEYWORDS = {"int", "float", "double", "char", "void"}


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens, source_code):
        # Preprocessor tokens are shown in the Token tab but are not part
        # of the statement grammar, so we filter them out before parsing.
        self.tokens = [t for t in tokens if t.token_type != "PREPROCESSOR"]
        self.pos = 0
        self.source_code = source_code
        self.errors = []

    # -----------------------------------------------------------------
    # Low-level helpers
    # -----------------------------------------------------------------
    def _current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _peek_lexeme(self):
        tok = self._current()
        return tok.lexeme if tok else "end of file"

    def _peek_line(self):
        tok = self._current()
        if tok:
            return tok.line
        return self.tokens[-1].line if self.tokens else 1

    def at_end(self):
        return self.pos >= len(self.tokens)

    def _advance(self):
        tok = self._current()
        self.pos += 1
        return tok

    def _check(self, lexeme=None, token_type=None):
        tok = self._current()
        if tok is None:
            return False
        if lexeme is not None and tok.lexeme != lexeme:
            return False
        if token_type is not None and tok.token_type != token_type:
            return False
        return True

    def _match(self, *lexemes):
        if self._current() is not None and self._current().lexeme in lexemes:
            return self._advance()
        return None

    def _source_line_text(self, line_number):
        lines = self.source_code.split("\n")
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return ""

    def _record_error(self, expected, message=None, line=None):
        """
        Record a syntax error WITHOUT consuming the current token
        (error-insertion recovery, see module docstring).
        """
        actual = self._peek_lexeme()
        if line is None:
            line = self._peek_line()
        self.errors.append({
            "phase": "Syntax Analysis",
            "error_type": "Syntax Error",
            "line": line,
            "column": None,
            "expected": expected,
            "actual": actual,
            "message": message or f"expected '{expected}' but found '{actual}'",
            "source_line": self._source_line_text(line),
        })

    def _expect(self, lexeme):
        """Expect a specific punctuation/keyword token; recover if missing."""
        if self._check(lexeme=lexeme):
            return self._advance()

        # For terminators (';', ')', '}') the missing token "belongs" right
        # after the previous token, so we report the line where it should
        # have appeared rather than the line of whatever comes next -- this
        # matches how the error is shown in the UI (pointing at YOUR line,
        # not the following statement).
        line = None
        if lexeme in (";", ")", "}", "(") and self.pos > 0:
            line = self.tokens[self.pos - 1].line
        self._record_error(expected=lexeme, line=line)
        return None

    def _expect_type(self, token_type, human_name):
        if self._check(token_type=token_type):
            return self._advance()
        self._record_error(expected=human_name)
        return None

    # -----------------------------------------------------------------
    # Entry point
    # -----------------------------------------------------------------
    def parse_program(self):
        functions = []
        while not self.at_end():
            start_pos = self.pos
            if self._check(token_type="KEYWORD") and self._current().lexeme in TYPE_KEYWORDS:
                functions.append(self._function_def())
            else:
                # Unexpected token at top level; report and skip it so we
                # always make forward progress (prevents infinite loops).
                self._record_error(
                    expected="a function definition (e.g. 'int main() {{ ... }}')",
                    message=f"Unexpected token '{self._peek_lexeme()}' at top level",
                )
                self._advance()

            if self.pos == start_pos:  # safety net: force progress
                self._advance()

        return {"type": "Program", "label": "Program", "children": functions}

    # -----------------------------------------------------------------
    # Functions
    # -----------------------------------------------------------------
    def _function_def(self):
        line = self._peek_line()
        return_type_tok = self._advance()  # type keyword already checked by caller
        name_tok = self._expect_type("IDENTIFIER", "function name")
        func_name = name_tok.lexeme if name_tok else "<unknown>"

        self._expect("(")
        params = self._param_list()
        self._expect(")")

        body = self._block()

        return {
            "type": "Function",
            "label": func_name,
            "return_type": return_type_tok.lexeme,
            "name": func_name,
            "line": line,
            "params": params,
            "children": [
                {"type": "ReturnType", "label": return_type_tok.lexeme, "children": []},
                {"type": "Parameters", "label": "Parameters",
                 "children": [{"type": "Param", "label": f"{p['type']} {p['name']}", "children": []} for p in params]},
                {"type": "Body", "label": "Body", "children": body["children"]},
            ],
            "body": body["children"],
        }

    def _param_list(self):
        params = []
        if self._check(lexeme=")"):
            return params
        while True:
            if self._check(token_type="KEYWORD") and self._current().lexeme in TYPE_KEYWORDS:
                type_tok = self._advance()
                name_tok = self._expect_type("IDENTIFIER", "parameter name")
                params.append({
                    "type": type_tok.lexeme,
                    "name": name_tok.lexeme if name_tok else "<unknown>",
                    "line": type_tok.line,
                })
            else:
                break
            if self._match(","):
                continue
            break
        return params

    # -----------------------------------------------------------------
    # Blocks & statements
    # -----------------------------------------------------------------
    def _block(self):
        self._expect("{")
        statements = []
        while not self._check(lexeme="}") and not self.at_end():
            start_pos = self.pos
            stmt = self._statement()
            if stmt is not None:
                statements.append(stmt)
            if self.pos == start_pos:  # safety net: avoid infinite loop
                self._advance()

        if not self._check(lexeme="}"):
            self._record_error(expected="}", message="Missing closing brace '}' for block")
        else:
            self._advance()

        return {"type": "Block", "label": "Block", "children": statements}

    def _statement(self):
        tok = self._current()
        if tok is None:
            return None

        if tok.token_type == "KEYWORD" and tok.lexeme in TYPE_KEYWORDS:
            return self._declaration()
        if tok.token_type == "KEYWORD" and tok.lexeme == "if":
            return self._if_stmt()
        if tok.token_type == "KEYWORD" and tok.lexeme == "while":
            return self._while_stmt()
        if tok.token_type == "KEYWORD" and tok.lexeme == "for":
            return self._for_stmt()
        if tok.token_type == "KEYWORD" and tok.lexeme == "return":
            return self._return_stmt()
        if tok.lexeme == "{":
            return self._block()
        if (tok.token_type == "IDENTIFIER"
                and self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos + 1].lexeme == "="):
            return self._assignment()

        # Fallback: a bare expression statement, e.g. a function call like printf(...);
        return self._expr_stmt()

    def _declaration(self):
        line = self._peek_line()
        type_tok = self._advance()
        name_tok = self._expect_type("IDENTIFIER", "variable name")
        var_name = name_tok.lexeme if name_tok else "<unknown>"

        init_expr = None
        if self._match("="):
            init_expr = self._expr()

        self._expect(";")

        label = f"{type_tok.lexeme} {var_name}"
        if init_expr is not None:
            label += f" = {expr_to_string(init_expr)}"

        return {
            "type": "Declaration",
            "label": label,
            "var_type": type_tok.lexeme,
            "var_name": var_name,
            "init": init_expr,
            "line": line,
            "children": [],
        }

    def _assignment(self):
        line = self._peek_line()
        name_tok = self._advance()
        var_name = name_tok.lexeme
        self._expect("=")
        value_expr = self._expr()
        self._expect(";")

        return {
            "type": "Assignment",
            "label": f"{var_name} = {expr_to_string(value_expr)}",
            "var_name": var_name,
            "value": value_expr,
            "line": line,
            "children": [],
        }

    def _if_stmt(self):
        line = self._peek_line()
        self._advance()  # 'if'
        self._expect("(")
        condition = self._expr()
        self._expect(")")
        then_branch = self._statement()
        else_branch = None
        if self._match("else"):
            else_branch = self._statement()

        children = [
            {"type": "Condition", "label": expr_to_string(condition), "children": []},
            {"type": "Then", "label": "Then", "children": [then_branch] if then_branch else []},
        ]
        if else_branch is not None:
            children.append({"type": "Else", "label": "Else", "children": [else_branch]})

        return {
            "type": "If", "label": f"if ({expr_to_string(condition)})",
            "condition": condition, "then": then_branch, "else": else_branch,
            "line": line, "children": children,
        }

    def _while_stmt(self):
        line = self._peek_line()
        self._advance()  # 'while'
        self._expect("(")
        condition = self._expr()
        self._expect(")")
        body = self._statement()

        return {
            "type": "While", "label": f"while ({expr_to_string(condition)})",
            "condition": condition, "body": body, "line": line,
            "children": [
                {"type": "Condition", "label": expr_to_string(condition), "children": []},
                {"type": "Body", "label": "Body", "children": [body] if body else []},
            ],
        }

    def _for_stmt(self):
        line = self._peek_line()
        self._advance()  # 'for'
        self._expect("(")

        init = None
        if not self._check(lexeme=";"):
            init = self._for_simple_stmt()
        self._expect(";")

        condition = None
        if not self._check(lexeme=";"):
            condition = self._expr()
        self._expect(";")

        update = None
        if not self._check(lexeme=")"):
            update = self._for_simple_stmt()
        self._expect(")")

        body = self._statement()

        label = f"for ({'' if init is None else expr_to_string(init.get('value') or init.get('init'))}; " \
                f"{'' if condition is None else expr_to_string(condition)}; " \
                f"{'' if update is None else expr_to_string(update.get('value') or update.get('init'))})"

        return {
            "type": "For", "label": label, "init": init, "condition": condition,
            "update": update, "body": body, "line": line,
            "children": [
                {"type": "Init", "label": "Init", "children": [init] if init else []},
                {"type": "Condition", "label": expr_to_string(condition) if condition else "", "children": []},
                {"type": "Update", "label": "Update", "children": [update] if update else []},
                {"type": "Body", "label": "Body", "children": [body] if body else []},
            ],
        }

    def _for_simple_stmt(self):
        """A declaration or assignment WITHOUT the trailing semicolon, used inside for(...)."""
        tok = self._current()
        line = self._peek_line()
        if tok.token_type == "KEYWORD" and tok.lexeme in TYPE_KEYWORDS:
            type_tok = self._advance()
            name_tok = self._expect_type("IDENTIFIER", "variable name")
            var_name = name_tok.lexeme if name_tok else "<unknown>"
            init_expr = None
            if self._match("="):
                init_expr = self._expr()
            return {"type": "Declaration", "var_type": type_tok.lexeme,
                    "var_name": var_name, "init": init_expr, "line": line, "children": []}
        else:
            name_tok = self._advance()
            var_name = name_tok.lexeme
            self._expect("=")
            value_expr = self._expr()
            return {"type": "Assignment", "var_name": var_name, "value": value_expr,
                    "line": line, "children": []}

    def _return_stmt(self):
        line = self._peek_line()
        self._advance()  # 'return'
        value = None
        if not self._check(lexeme=";"):
            value = self._expr()
        self._expect(";")
        return {
            "type": "Return",
            "label": f"return {expr_to_string(value)}" if value is not None else "return",
            "value": value, "line": line, "children": [],
        }

    def _expr_stmt(self):
        line = self._peek_line()
        value = self._expr()
        self._expect(";")
        node_type = "FunctionCall" if value and value.get("type") == "Call" else "ExprStatement"
        return {
            "type": node_type,
            "label": expr_to_string(value),
            "value": value, "line": line, "children": [],
        }

    # -----------------------------------------------------------------
    # Expressions (precedence climbing)
    # -----------------------------------------------------------------
    def _expr(self):
        return self._logical_or()

    def _logical_or(self):
        node = self._logical_and()
        while self._check(lexeme="||"):
            op = self._advance().lexeme
            right = self._logical_and()
            node = {"type": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _logical_and(self):
        node = self._equality()
        while self._check(lexeme="&&"):
            op = self._advance().lexeme
            right = self._equality()
            node = {"type": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _equality(self):
        node = self._relational()
        while self._current() and self._current().lexeme in ("==", "!="):
            op = self._advance().lexeme
            right = self._relational()
            node = {"type": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _relational(self):
        node = self._additive()
        while self._current() and self._current().lexeme in ("<", ">", "<=", ">="):
            op = self._advance().lexeme
            right = self._additive()
            node = {"type": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _additive(self):
        node = self._term()
        while self._current() and self._current().lexeme in ("+", "-"):
            op = self._advance().lexeme
            right = self._term()
            node = {"type": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _term(self):
        node = self._factor()
        while self._current() and self._current().lexeme in ("*", "/", "%"):
            op = self._advance().lexeme
            right = self._factor()
            node = {"type": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _factor(self):
        if self._current() and self._current().lexeme in ("-", "!"):
            op = self._advance().lexeme
            operand = self._factor()
            return {"type": "UnaryOp", "op": op, "operand": operand}
        return self._primary()

    def _primary(self):
        tok = self._current()
        if tok is None:
            self._record_error(expected="an expression", message="Unexpected end of file inside an expression")
            return {"type": "Error", "label": "?"}

        if tok.token_type == "INT_CONSTANT":
            self._advance()
            return {"type": "Num", "value": tok.lexeme, "value_type": "int"}
        if tok.token_type == "FLOAT_CONSTANT":
            self._advance()
            return {"type": "Num", "value": tok.lexeme, "value_type": "float"}
        if tok.token_type == "STRING_LITERAL":
            self._advance()
            return {"type": "Str", "value": tok.lexeme}
        if tok.token_type == "CHAR_LITERAL":
            self._advance()
            return {"type": "Char", "value": tok.lexeme}
        if tok.token_type == "IDENTIFIER":
            self._advance()
            if self._check(lexeme="("):
                self._advance()
                args = []
                if not self._check(lexeme=")"):
                    args.append(self._expr())
                    while self._match(","):
                        args.append(self._expr())
                self._expect(")")
                return {"type": "Call", "name": tok.lexeme, "args": args, "line": tok.line}
            return {"type": "Var", "name": tok.lexeme, "line": tok.line}
        if tok.lexeme == "(":
            self._advance()
            inner = self._expr()
            self._expect(")")
            return inner

        self._record_error(expected="an expression", message=f"Unexpected token '{tok.lexeme}' in expression")
        self._advance()
        return {"type": "Error", "label": tok.lexeme}


# -----------------------------------------------------------------------
# Expression -> human-readable string (used for parse-tree labels and TAC)
# -----------------------------------------------------------------------
def expr_to_string(node):
    if node is None:
        return ""
    t = node.get("type")
    if t == "Num":
        return node["value"]
    if t == "Str":
        return node["value"]
    if t == "Char":
        return node["value"]
    if t == "Var":
        return node["name"]
    if t == "BinOp":
        return f"{expr_to_string(node['left'])} {node['op']} {expr_to_string(node['right'])}"
    if t == "UnaryOp":
        return f"{node['op']}{expr_to_string(node['operand'])}"
    if t == "Call":
        args = ", ".join(expr_to_string(a) for a in node.get("args", []))
        return f"{node['name']}({args})"
    if t == "Error":
        return node.get("label", "?")
    return "?"


def parse(tokens, source_code):
    """Convenience wrapper used by app.py."""
    parser = Parser(tokens, source_code)
    tree = parser.parse_program()
    return tree, parser.errors
