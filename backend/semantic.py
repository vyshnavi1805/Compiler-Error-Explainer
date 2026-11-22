"""
semantic.py
-----------
PHASE 3: SEMANTIC ANALYSIS

Syntax analysis only checks whether code follows the GRAMMAR of C. It has
no idea whether a variable was actually declared, or whether you are
trying to assign a string into an int. That is the job of semantic
analysis.

This module walks the parse tree produced by parser.py and, using the
SymbolTable class from symbol_table.py, checks for:

    1. Undeclared variables      (used before being declared)
    2. Duplicate declarations    (same name declared twice in one scope)
    3. Type mismatches           (e.g. int x; x = "hello";)
    4. Invalid operations        (e.g. 10 + "hello")

Every problem found is turned into a structured dictionary with the same
shape as lexical/syntax errors, so error_explainer.py can treat all three
phases uniformly.
"""

from symbol_table import SymbolTable

# A very small, educational type-compatibility model.
# Real C has implicit numeric promotion rules (int -> float -> double);
# we keep just enough of that here to teach the concept without pretending
# to implement the full C standard.
NUMERIC_TYPES = {"int", "float", "double", "char"}


class SemanticAnalyzer:
    def __init__(self, parse_tree, source_code):
        self.tree = parse_tree
        self.source_code = source_code
        self.symbol_table = SymbolTable()
        self.errors = []
        self.warnings = []

    # -----------------------------------------------------------------
    def analyze(self):
        for function in self.tree.get("children", []):
            self._analyze_function(function)
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "symbol_table": self.symbol_table.export(),
        }

    # -----------------------------------------------------------------
    def _source_line_text(self, line_number):
        lines = self.source_code.split("\n")
        if line_number and 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return ""

    def _add_error(self, line, message, error_type="Semantic Error"):
        self.errors.append({
            "phase": "Semantic Analysis",
            "error_type": error_type,
            "line": line,
            "column": None,
            "message": message,
            "source_line": self._source_line_text(line),
        })

    def _add_warning(self, line, message):
        self.warnings.append({
            "phase": "Semantic Analysis",
            "error_type": "Warning",
            "line": line,
            "column": None,
            "message": message,
            "source_line": self._source_line_text(line),
        })

    # -----------------------------------------------------------------
    def _analyze_function(self, function):
        name = function.get("name", "<unknown>")
        line = function.get("line", 1)

        # Register the function itself in the GLOBAL scope so it can be
        # called from elsewhere (and so duplicate function names are caught).
        ok, existing = self.symbol_table.insert(
            name, function.get("return_type", "int"), line, kind="function"
        )
        if not ok:
            self._add_error(
                line,
                f"Function '{name}' is already declared "
                f"(previous declaration at line {existing.line}).",
                error_type="Semantic Error",
            )

        self.symbol_table.enter_scope(name)
        for param in function.get("params", []):
            self.symbol_table.insert(param["name"], param["type"], param["line"], kind="variable")

        for stmt in function.get("body", []):
            self._analyze_statement(stmt)

        self.symbol_table.exit_scope()

    # -----------------------------------------------------------------
    def _analyze_statement(self, stmt):
        if stmt is None:
            return
        kind = stmt.get("type")

        if kind == "Declaration":
            self._analyze_declaration(stmt)
        elif kind == "Assignment":
            self._analyze_assignment(stmt)
        elif kind in ("FunctionCall", "ExprStatement"):
            self._infer_type(stmt.get("value"), stmt.get("line"))
        elif kind == "Return":
            if stmt.get("value") is not None:
                self._infer_type(stmt["value"], stmt.get("line"))
        elif kind == "If":
            self._infer_type(stmt.get("condition"), stmt.get("line"))
            self._analyze_statement(stmt.get("then"))
            self._analyze_statement(stmt.get("else"))
        elif kind == "While":
            self._infer_type(stmt.get("condition"), stmt.get("line"))
            self._analyze_statement(stmt.get("body"))
        elif kind == "For":
            self._analyze_statement(stmt.get("init"))
            if stmt.get("condition") is not None:
                self._infer_type(stmt["condition"], stmt.get("line"))
            self._analyze_statement(stmt.get("update"))
            self._analyze_statement(stmt.get("body"))
        elif kind == "Block":
            for inner in stmt.get("children", []):
                self._analyze_statement(inner)

    # -----------------------------------------------------------------
    def _analyze_declaration(self, stmt):
        name = stmt["var_name"]
        var_type = stmt["var_type"]
        line = stmt["line"]

        if self.symbol_table.is_declared_in_current_scope(name):
            existing = self.symbol_table.lookup(name)
            self._add_error(
                line,
                f"'{name}' is already declared in this scope "
                f"(previous declaration at line {existing.line}).",
                error_type="Semantic Error",
            )
        else:
            self.symbol_table.insert(name, var_type, line, kind="variable")

        if stmt.get("init") is not None:
            value_type = self._infer_type(stmt["init"], line)
            self._check_type_compatibility(var_type, value_type, name, line)

    def _analyze_assignment(self, stmt):
        name = stmt["var_name"]
        line = stmt["line"]
        symbol = self.symbol_table.lookup(name)

        if symbol is None:
            self._add_error(line, f"'{name}' has not been declared.", error_type="Semantic Error")
            var_type = None
        else:
            var_type = symbol.sym_type

        value_type = self._infer_type(stmt["value"], line)
        if var_type is not None:
            self._check_type_compatibility(var_type, value_type, name, line)

    # -----------------------------------------------------------------
    def _check_type_compatibility(self, var_type, value_type, name, line):
        if value_type is None:
            return  # already reported (e.g. undeclared identifier)

        if var_type in NUMERIC_TYPES and value_type == "string":
            self._add_error(
                line,
                f"Type mismatch: cannot assign a string literal to '{name}', "
                f"which has type '{var_type}'.",
                error_type="Semantic Error",
            )
        elif var_type == "char" and value_type not in ("char", "int"):
            self._add_warning(
                line,
                f"Assigning a value of type '{value_type}' to char variable '{name}' "
                f"may lose information.",
            )
        elif var_type in ("int",) and value_type == "float":
            self._add_warning(
                line,
                f"Assigning a float value to int variable '{name}' will truncate "
                f"the decimal part.",
            )

    # -----------------------------------------------------------------
    def _infer_type(self, expr, line):
        """
        Walk an expression and (a) verify every identifier used is declared,
        and (b) return a best-effort type string ('int', 'float', 'string',
        'char', or None if unknown/erroneous) used for compatibility checks.
        """
        if expr is None:
            return None
        t = expr.get("type")

        if t == "Num":
            return expr.get("value_type", "int")
        if t == "Str":
            return "string"
        if t == "Char":
            return "char"
        if t == "Var":
            symbol = self.symbol_table.lookup(expr["name"])
            if symbol is None:
                self._add_error(
                    expr.get("line", line),
                    f"'{expr['name']}' has not been declared.",
                    error_type="Semantic Error",
                )
                return None
            return symbol.sym_type
        if t == "Call":
            for arg in expr.get("args", []):
                self._infer_type(arg, expr.get("line", line))
            # We don't model return types of arbitrary functions; printf/scanf
            # style calls are treated as void/int for our purposes.
            return "int"
        if t == "UnaryOp":
            return self._infer_type(expr["operand"], line)
        if t == "BinOp":
            left_type = self._infer_type(expr["left"], line)
            right_type = self._infer_type(expr["right"], line)
            if left_type == "string" or right_type == "string":
                if expr["op"] not in ("==", "!="):
                    self._add_error(
                        line,
                        f"Invalid operation: cannot use operator '{expr['op']}' "
                        f"between a string and a numeric value "
                        f"('{expr_side_label(expr['left'])}' {expr['op']} "
                        f"'{expr_side_label(expr['right'])}').",
                        error_type="Semantic Error",
                    )
                return None
            if left_type is None or right_type is None:
                return None
            if "float" in (left_type, right_type) or "double" in (left_type, right_type):
                return "float"
            return left_type
        return None


def expr_side_label(node):
    from parser import expr_to_string
    return expr_to_string(node)


def analyze(parse_tree, source_code):
    analyzer = SemanticAnalyzer(parse_tree, source_code)
    result = analyzer.analyze()
    return result
