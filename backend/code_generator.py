"""
code_generator.py
------------------
PHASE 6: CODE GENERATION

This module translates the OPTIMIZED Three Address Code into a simple,
made-up pseudo-assembly language: LOAD, STORE, ADD, SUB, MUL, DIV, MOD,
NEG, PUSH, CALL, RET.

IMPORTANT (see Section 9 of the spec):
This is an EDUCATIONAL target representation, not real x86/ARM machine
code. A production compiler backend also has to perform register
allocation across the whole function, instruction scheduling, calling
convention handling, and target-specific peephole optimization -- all of
which are far beyond the scope of a lab project. The goal here is to
show the CONCEPT of "intermediate code -> target code" clearly.

We use exactly two working registers, R1 and R2, reset for every TAC
line. This mirrors the worked example in the project spec:

    t1 = b * c        ->   LOAD R1, b
                            LOAD R2, c
                            MUL R1, R2
                            STORE t1, R1
"""

import re

ASSIGN_RE = re.compile(r"^(\S+)\s*=\s*(.+)$")
BINOP_RE = re.compile(r"^(\S+)\s*([+\-*/%])\s*(\S+)$")
UNARY_RE = re.compile(r"^([-!])(\S+)$")
CALL_RE = re.compile(r"^call\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$")

OP_TO_MNEMONIC = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL",
    "/": "DIV",
    "%": "MOD",
}


def generate(optimized_tac):
    """
    Args:
        optimized_tac: list of instruction dicts (the "after" list from optimizer.optimize())

    Returns:
        list of dicts: [{"instruction": "LOAD R1, b", "line": <source line or None>}, ...]
    """
    output = []

    def emit(text, line):
        output.append({"instruction": text, "line": line})

    for instr in optimized_tac:
        line = instr.get("line")
        code = instr["code"]

        if instr["kind"] == "note":
            emit(f"; {code.lstrip('; ').strip()}", line)
            continue

        if code.startswith("return"):
            value = code[len("return"):].strip()
            if value:
                emit(f"LOAD R1, {value}", line)
                emit("RET R1", line)
            else:
                emit("RET", line)
            continue

        m = ASSIGN_RE.match(code)

        # A standalone call statement (e.g. "call printf, x") has no '=' target.
        if instr["kind"] == "call" and not m:
            call_match = CALL_RE.match(code)
            if call_match:
                _emit_call(call_match, emit, line)
                continue
        if not m:
            emit(f"; {code}", line)
            continue

        target, rhs = m.group(1), m.group(2)

        call_in_rhs = CALL_RE.match(rhs)
        if call_in_rhs:
            _emit_call(call_in_rhs, emit, line)
            emit(f"STORE {target}, R1", line)
            continue

        bm = BINOP_RE.match(rhs)
        um = UNARY_RE.match(rhs)

        if bm:
            left, op, right = bm.group(1), bm.group(2), bm.group(3)
            mnemonic = OP_TO_MNEMONIC.get(op, "OP")
            emit(f"LOAD R1, {left}", line)
            emit(f"LOAD R2, {right}", line)
            emit(f"{mnemonic} R1, R2", line)
            emit(f"STORE {target}, R1", line)
        elif um:
            op, operand = um.group(1), um.group(2)
            emit(f"LOAD R1, {operand}", line)
            if op == "-":
                emit("NEG R1", line)
            else:
                emit("NOT R1", line)
            emit(f"STORE {target}, R1", line)
        else:
            # Simple copy: target = value
            emit(f"LOAD R1, {rhs}", line)
            emit(f"STORE {target}, R1", line)

    return output


def _emit_call(call_match, emit, line):
    name = call_match.group(1)
    args_text = call_match.group(2).strip()
    args = [a.strip() for a in args_text.split(",") if a.strip()] if args_text else []
    for arg in args:
        emit(f"PUSH {arg}", line)
    emit(f"CALL {name}", line)
