"""
optimizer.py
------------
PHASE 5: CODE OPTIMIZATION

IMPORTANT (see Section 8 of the spec and README -> Limitations):
These are EDUCATIONAL optimizations meant to demonstrate the core ideas
taught in a Compiler Design course. They are intentionally simple and do
NOT represent the full sophistication of an industrial optimizer such as
GCC's -O2/-O3 pipeline (which does data-flow analysis, register
allocation, loop transformations, vectorization, and much more).

We implement four classic, well-known optimizations that operate directly
on the Three Address Code (TAC) produced by intermediate_code.py:

    1. Constant Folding        10 * 2        -> 20
    2. Constant Propagation    x = 10; y=x+5 -> x = 10; y = 15
    3. Algebraic Simplification  y + 0       -> y
    4. Dead Code Elimination   unused temporaries are removed

Because our TAC is stored as plain text lines like "t1 = a + b", we use
small regular expressions to recognise and rewrite patterns -- exactly
the same idea a real optimizer uses, just operating on text instead of
an in-memory graph, which keeps the logic easy to follow for a beginner.
"""

import re

ASSIGN_RE = re.compile(r"^(\S+)\s*=\s*(.+)$")
BINOP_RE = re.compile(r"^(\S+)\s*([+\-*/%])\s*(\S+)$")
UNARY_RE = re.compile(r"^([-!])(\S+)$")
NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
TEMP_RE = re.compile(r"\bt\d+\b")


def _is_number(text):
    return bool(NUMBER_RE.match(text))


def _fold_constants(a, op, b):
    """Evaluate a simple binary op on two numeric literals. Returns str or None."""
    try:
        is_float = "." in a or "." in b
        x = float(a) if is_float else int(a)
        y = float(b) if is_float else int(b)
        if op == "+":
            result = x + y
        elif op == "-":
            result = x - y
        elif op == "*":
            result = x * y
        elif op == "/":
            if y == 0:
                return None
            result = x / y if is_float else int(x / y)
        elif op == "%":
            if y == 0:
                return None
            result = x % y
        else:
            return None
        return str(result)
    except (ValueError, ZeroDivisionError):
        return None


def optimize(tac_instructions):
    """
    Run all four optimization passes over the TAC.

    Args:
        tac_instructions: list of dicts as produced by intermediate_code.generate()

    Returns:
        {
          "before": [...],            # original TAC (unchanged, for comparison)
          "after": [...],              # optimized TAC
          "applied": [ {line, technique, before, after}, ... ]
        }
    """
    before = [dict(i) for i in tac_instructions]
    working = [dict(i) for i in tac_instructions]
    applied = []

    working, applied = _pass_constant_propagation_and_folding(working, applied)
    working, applied = _pass_algebraic_simplification(working, applied)
    working, applied = _pass_dead_code_elimination(working, applied)

    return {"before": before, "after": working, "applied": applied}


def _pass_constant_propagation_and_folding(instructions, applied):
    """
    Single forward scan:
      - track which variables/temps currently hold a KNOWN constant value
      - substitute known constants into each instruction's right-hand side
      - fold the result if it becomes a pure constant expression
    """
    known_constants = {}
    result = []

    for instr in instructions:
        if instr["kind"] == "note":
            result.append(instr)
            continue

        original_code = instr["code"]
        m = ASSIGN_RE.match(instr["code"])

        if not m:
            # Lines with no "target = ..." shape (e.g. "call printf, y" or
            # "return y") can still benefit from substituting any
            # already-known constants into their text, even though there is
            # nothing to fold or track as a new constant.
            new_code = original_code
            changed = False
            for name, value in known_constants.items():
                pattern = re.compile(rf"\b{re.escape(name)}\b")
                if pattern.search(new_code):
                    new_code = pattern.sub(value, new_code)
                    changed = True
            if changed:
                applied.append({
                    "line": instr.get("line"),
                    "technique": "Constant Propagation",
                    "before": original_code,
                    "after": new_code,
                })
            result.append({"code": new_code, "line": instr.get("line"), "kind": instr["kind"]})
            continue

        target, rhs = m.group(1), m.group(2)
        new_rhs = rhs
        changed_by_propagation = False

        # Substitute any known-constant variable name with its value.
        for name, value in known_constants.items():
            pattern = re.compile(rf"\b{re.escape(name)}\b")
            if pattern.search(new_rhs):
                new_rhs = pattern.sub(value, new_rhs)
                changed_by_propagation = True

        # Try to fold the (possibly substituted) rhs into a single constant.
        folded = None
        bm = BINOP_RE.match(new_rhs)
        um = UNARY_RE.match(new_rhs)
        if bm and _is_number(bm.group(1)) and _is_number(bm.group(3)):
            folded = _fold_constants(bm.group(1), bm.group(2), bm.group(3))
        elif um and _is_number(um.group(2)):
            if um.group(1) == "-":
                folded = str(-float(um.group(2)) if "." in um.group(2) else -int(um.group(2)))

        new_code = f"{target} = {folded if folded is not None else new_rhs}"

        if folded is not None:
            known_constants[target] = folded
            applied.append({
                "line": instr.get("line"),
                "technique": "Constant Folding" + (" + Constant Propagation" if changed_by_propagation else ""),
                "before": original_code,
                "after": new_code,
            })
        elif _is_number(new_rhs):
            # e.g. "x = 20" after substitution with no operator to fold
            known_constants[target] = new_rhs
            if changed_by_propagation:
                applied.append({
                    "line": instr.get("line"),
                    "technique": "Constant Propagation",
                    "before": original_code,
                    "after": new_code,
                })
        else:
            # target is reassigned to something non-constant -> no longer a known constant
            known_constants.pop(target, None)
            if changed_by_propagation:
                applied.append({
                    "line": instr.get("line"),
                    "technique": "Constant Propagation",
                    "before": original_code,
                    "after": new_code,
                })

        result.append({"code": new_code, "line": instr.get("line"), "kind": instr["kind"]})

    return result, applied


def _pass_algebraic_simplification(instructions, applied):
    """
    Simplify obviously redundant algebraic patterns:
        x + 0 -> x      0 + x -> x
        x - 0 -> x
        x * 1 -> x      1 * x -> x
        x * 0 -> 0      0 * x -> 0
    """
    result = []
    for instr in instructions:
        if instr["kind"] != "assign":
            result.append(instr)
            continue

        m = ASSIGN_RE.match(instr["code"])
        if not m:
            result.append(instr)
            continue

        target, rhs = m.group(1), m.group(2)
        bm = BINOP_RE.match(rhs)
        new_rhs = rhs
        simplified = False

        if bm:
            left, op, right = bm.group(1), bm.group(2), bm.group(3)
            if op == "+" and right == "0":
                new_rhs, simplified = left, True
            elif op == "+" and left == "0":
                new_rhs, simplified = right, True
            elif op == "-" and right == "0":
                new_rhs, simplified = left, True
            elif op == "*" and right == "1":
                new_rhs, simplified = left, True
            elif op == "*" and left == "1":
                new_rhs, simplified = right, True
            elif op == "*" and (right == "0" or left == "0"):
                new_rhs, simplified = "0", True

        new_code = f"{target} = {new_rhs}"
        if simplified:
            applied.append({
                "line": instr.get("line"),
                "technique": "Algebraic Simplification",
                "before": instr["code"],
                "after": new_code,
            })
        result.append({"code": new_code, "line": instr.get("line"), "kind": instr["kind"]})

    return result, applied


def _pass_dead_code_elimination(instructions, applied):
    """
    Remove assignments to TEMPORARY variables (t1, t2, ...) that are never
    read by any later instruction. We deliberately restrict this to
    temporaries -- eliminating user-named variables would require full
    liveness analysis across the whole function (including calls like
    printf that "use" a variable just by naming it), which is out of
    scope for an educational tool. This still safely demonstrates the
    concept: after constant folding/propagation collapses a chain of
    temporaries, the now-unused temps are cleanly removed.
    """
    # Collect every temp name that is *read* anywhere (on the right-hand side,
    # or inside a call's argument list).
    used_temps = set()
    for instr in instructions:
        m = ASSIGN_RE.match(instr["code"])
        rhs_text = m.group(2) if m else instr["code"]
        used_temps.update(TEMP_RE.findall(rhs_text))

    result = []
    for instr in instructions:
        m = ASSIGN_RE.match(instr["code"])
        if instr["kind"] == "assign" and m:
            target = m.group(1)
            if TEMP_RE.match(target) and target not in used_temps:
                applied.append({
                    "line": instr.get("line"),
                    "technique": "Dead Code Elimination",
                    "before": instr["code"],
                    "after": "(removed - unused temporary)",
                })
                continue  # skip = remove this instruction
        result.append(instr)

    return result, applied
