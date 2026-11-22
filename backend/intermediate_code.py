"""
intermediate_code.py
---------------------
PHASE 4: INTERMEDIATE CODE GENERATION

This module converts the parse tree into THREE ADDRESS CODE (TAC), a
simple intermediate representation where every instruction has AT MOST
one operator and up to three "addresses" (operands), e.g.:

    x = a + b * c
        becomes
    t1 = b * c
    t2 = a + t1
    x  = t2

WHY INTERMEDIATE CODE?
Three Address Code sits between the source language (C) and the target
machine code. It is simple enough to optimize easily (Phase 5) and
general enough to translate into many different target architectures
(Phase 6). Real compilers such as GCC and LLVM use similar (though far
more sophisticated) intermediate representations internally.

SCOPE OF THIS IMPLEMENTATION:
We generate TAC for declarations with initializers, assignments, and
standalone function calls (e.g. printf(...)), wherever they appear in a
function body -- including inside if/while/for bodies. We do NOT generate
labels/jumps for if/while/for control flow itself; that is a well-known
"next step" for a compiler course and is called out explicitly in the
project's documented limitations (see README -> Limitations) so nothing
is silently missing.
"""


class TACInstruction:
    def __init__(self, code, line=None, kind="assign"):
        self.code = code      # e.g. "t1 = b * c"
        self.line = line      # originating source line, for traceability
        self.kind = kind      # "assign" | "call" | "note"

    def to_dict(self):
        return {"code": self.code, "line": self.line, "kind": self.kind}


class TACGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_count = 0

    def _new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def _emit(self, code, line=None, kind="assign"):
        self.instructions.append(TACInstruction(code, line, kind))

    # -----------------------------------------------------------------
    def generate_for_function(self, function):
        self._emit(f"; --- function {function['name']} ---", function.get("line"), kind="note")
        for stmt in function.get("body", []):
            self._generate_statement(stmt)
        return self.instructions

    # -----------------------------------------------------------------
    def _generate_statement(self, stmt):
        if stmt is None:
            return
        kind = stmt.get("type")

        if kind == "Declaration":
            if stmt.get("init") is not None:
                result_place = self._generate_expr(stmt["init"], stmt.get("line"))
                self._emit(f"{stmt['var_name']} = {result_place}", stmt.get("line"))
            else:
                self._emit(f"; declare {stmt['var_type']} {stmt['var_name']}", stmt.get("line"), kind="note")

        elif kind == "Assignment":
            result_place = self._generate_expr(stmt["value"], stmt.get("line"))
            self._emit(f"{stmt['var_name']} = {result_place}", stmt.get("line"))

        elif kind in ("FunctionCall", "ExprStatement"):
            self._generate_expr(stmt.get("value"), stmt.get("line"), as_statement=True)

        elif kind == "Return":
            if stmt.get("value") is not None:
                result_place = self._generate_expr(stmt["value"], stmt.get("line"))
                self._emit(f"return {result_place}", stmt.get("line"))
            else:
                self._emit("return", stmt.get("line"))

        elif kind == "If":
            self._emit(f"; if ({_label(stmt.get('condition'))})  -- control flow not expanded (educational scope)",
                        stmt.get("line"), kind="note")
            self._generate_statement(stmt.get("then"))
            if stmt.get("else") is not None:
                self._emit("; else", stmt.get("line"), kind="note")
                self._generate_statement(stmt.get("else"))

        elif kind == "While":
            self._emit(f"; while ({_label(stmt.get('condition'))})  -- control flow not expanded (educational scope)",
                        stmt.get("line"), kind="note")
            self._generate_statement(stmt.get("body"))

        elif kind == "For":
            self._emit("; for (...)  -- control flow not expanded (educational scope)",
                        stmt.get("line"), kind="note")
            self._generate_statement(stmt.get("body"))

        elif kind == "Block":
            for inner in stmt.get("children", []):
                self._generate_statement(inner)

    # -----------------------------------------------------------------
    def _generate_expr(self, expr, line, as_statement=False):
        """
        Recursively flatten an expression into TAC instructions.
        Returns the "place" (a variable name, constant, or temp) that
        holds the expression's result.
        """
        if expr is None:
            return ""
        t = expr.get("type")

        if t in ("Num", "Str", "Char"):
            return expr["value"]
        if t == "Var":
            return expr["name"]

        if t == "UnaryOp":
            operand_place = self._generate_expr(expr["operand"], line)
            temp = self._new_temp()
            self._emit(f"{temp} = {expr['op']}{operand_place}", line)
            return temp

        if t == "BinOp":
            left_place = self._generate_expr(expr["left"], line)
            right_place = self._generate_expr(expr["right"], line)
            temp = self._new_temp()
            self._emit(f"{temp} = {left_place} {expr['op']} {right_place}", line)
            return temp

        if t == "Call":
            arg_places = [self._generate_expr(a, line) for a in expr.get("args", [])]
            call_text = f"call {expr['name']}, {', '.join(arg_places) if arg_places else ''}".rstrip(", ")
            if as_statement:
                self._emit(call_text, line, kind="call")
                return ""
            temp = self._new_temp()
            self._emit(f"{temp} = {call_text}", line, kind="call")
            return temp

        return "?"


def _label(expr):
    from parser import expr_to_string
    return expr_to_string(expr)


def generate(parse_tree):
    """
    Generate TAC for every function in the program.
    Returns a list of instruction dicts (with a note line separating
    functions), for display in the Intermediate Code tab.
    """
    generator = TACGenerator()
    for function in parse_tree.get("children", []):
        generator.generate_for_function(function)
    return [i.to_dict() for i in generator.instructions]
