"""
tests/test_pipeline.py
------------------------
Automated test suite for C Compiler Error Explainer (Section 53 of the spec).

Uses Python's built-in `unittest` module -- no extra install required
beyond what's already in requirements.txt. This formalizes the 10 test
cases documented in docs/test_cases.md into something you can actually
run and show your professor.

Note: nothing in this file (or the project) touches the network, an API
key, or any AI service -- every test below runs fully offline.

HOW TO RUN (from the backend/ folder, with the venv active):
    python -m unittest discover -s tests -v

Or run this file directly:
    python tests/test_pipeline.py
"""

import os
import sys
import unittest

# Make the parent backend/ folder importable when running this file directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lexer
import parser as parser_module
import semantic
import intermediate_code
import optimizer
import code_generator
import error_explainer
from examples import EXAMPLES


def _example(example_id):
    return next(e for e in EXAMPLES if e["id"] == example_id)["code"]


def _run_all_phases(source_code):
    """A trimmed-down version of app.run_pipeline() that doesn't need Flask,
    so this test suite has no dependency on flask/flask-cors being importable."""
    tokens, lexical_errors = lexer.tokenize(source_code)
    parse_tree, syntax_errors = parser_module.parse(tokens, source_code)
    semantic_result = semantic.analyze(parse_tree, source_code)
    semantic_errors = semantic_result["errors"]

    result = {
        "tokens": lexer.tokens_to_dict_list(tokens),
        "lexical_errors": lexical_errors,
        "parse_tree": parse_tree,
        "syntax_errors": syntax_errors,
        "semantic_errors": semantic_errors,
        "symbol_table": semantic_result["symbol_table"],
        "warnings": semantic_result["warnings"],
        "intermediate_code": [],
        "optimization": {"before": [], "after": [], "applied": []},
        "target_code": [],
    }

    if not lexical_errors and not syntax_errors and not semantic_errors:
        tac = intermediate_code.generate(parse_tree)
        opt = optimizer.optimize(tac)
        target = code_generator.generate(opt["after"])
        result["intermediate_code"] = tac
        result["optimization"] = opt
        result["target_code"] = target

    return result


class TestPhase1Lexical(unittest.TestCase):
    def test_valid_program_has_no_lexical_errors(self):
        r = _run_all_phases(_example("01_valid"))
        self.assertEqual(r["lexical_errors"], [])
        self.assertGreater(len(r["tokens"]), 0)

    def test_invalid_character_is_flagged(self):
        r = _run_all_phases(_example("07_invalid_character"))
        self.assertEqual(len(r["lexical_errors"]), 1)
        self.assertEqual(r["lexical_errors"][0]["error_type"], "Lexical Error")

    def test_keyword_vs_identifier_classification(self):
        tokens, _ = lexer.tokenize("int main() { return 0; }")
        kinds = {t.lexeme: t.token_type for t in tokens}
        self.assertEqual(kinds["int"], "KEYWORD")
        self.assertEqual(kinds["main"], "IDENTIFIER")
        self.assertEqual(kinds["return"], "KEYWORD")


class TestPhase2Syntax(unittest.TestCase):
    def test_valid_program_has_no_syntax_errors(self):
        r = _run_all_phases(_example("01_valid"))
        self.assertEqual(r["syntax_errors"], [])

    def test_missing_semicolon_detected_with_correct_line(self):
        r = _run_all_phases(_example("02_missing_semicolon"))
        self.assertEqual(len(r["syntax_errors"]), 1)
        self.assertEqual(r["syntax_errors"][0]["line"], 4)
        self.assertEqual(r["syntax_errors"][0]["expected"], ";")

    def test_missing_closing_brace_detected(self):
        r = _run_all_phases(_example("03_missing_brace"))
        self.assertEqual(len(r["syntax_errors"]), 1)

    def test_multiple_errors_recovers_and_finds_more_than_one(self):
        r = _run_all_phases(_example("08_multiple_errors"))
        self.assertGreaterEqual(len(r["syntax_errors"]), 3)


class TestPhase3Semantic(unittest.TestCase):
    def test_valid_program_has_no_semantic_errors(self):
        r = _run_all_phases(_example("01_valid"))
        self.assertEqual(r["semantic_errors"], [])
        self.assertGreater(len(r["symbol_table"]), 0)

    def test_undeclared_variable_detected(self):
        r = _run_all_phases(_example("04_undeclared_variable"))
        self.assertGreaterEqual(len(r["semantic_errors"]), 1)
        self.assertTrue(any("has not been declared" in e["message"] for e in r["semantic_errors"]))

    def test_duplicate_declaration_detected(self):
        r = _run_all_phases(_example("05_duplicate_declaration"))
        self.assertEqual(len(r["semantic_errors"]), 1)
        self.assertIn("already declared", r["semantic_errors"][0]["message"])

    def test_type_mismatch_detected(self):
        r = _run_all_phases(_example("06_type_mismatch"))
        self.assertEqual(len(r["semantic_errors"]), 1)
        self.assertIn("Type mismatch", r["semantic_errors"][0]["message"])

    def test_symbol_table_records_function_and_variables(self):
        r = _run_all_phases(_example("01_valid"))
        names = {s["name"] for s in r["symbol_table"]}
        self.assertIn("main", names)
        self.assertIn("x", names)


class TestPipelineSkipping(unittest.TestCase):
    """Section 10: later phases must be honestly skipped when earlier ones fail."""

    def test_syntax_error_skips_later_phases(self):
        r = _run_all_phases(_example("02_missing_semicolon"))
        self.assertEqual(r["intermediate_code"], [])
        self.assertEqual(r["target_code"], [])

    def test_semantic_error_skips_later_phases(self):
        r = _run_all_phases(_example("04_undeclared_variable"))
        self.assertEqual(r["intermediate_code"], [])
        self.assertEqual(r["target_code"], [])

    def test_clean_program_runs_all_six_phases(self):
        r = _run_all_phases(_example("09_tac_expression"))
        self.assertEqual(r["lexical_errors"], [])
        self.assertEqual(r["syntax_errors"], [])
        self.assertEqual(r["semantic_errors"], [])
        self.assertGreater(len(r["intermediate_code"]), 0)
        self.assertGreater(len(r["target_code"]), 0)


class TestPhase4IntermediateCode(unittest.TestCase):
    def test_operator_precedence_in_tac(self):
        # x = a + b * c  must compute b*c BEFORE adding a (multiplication
        # binds tighter), so the multiplication temp must be generated first.
        r = _run_all_phases(_example("09_tac_expression"))
        codes = [i["code"] for i in r["intermediate_code"] if i["kind"] == "assign"]
        mul_index = next(i for i, c in enumerate(codes) if "*" in c)
        add_index = next(i for i, c in enumerate(codes) if " + " in c)
        self.assertLess(mul_index, add_index, "multiplication must be computed before the addition that uses it")


class TestPhase5Optimization(unittest.TestCase):
    def test_constant_folding(self):
        r = _run_all_phases(_example("10_optimization"))
        techniques = {a["technique"] for a in r["optimization"]["applied"]}
        self.assertTrue(any("Constant Folding" in t for t in techniques))

    def test_constant_propagation(self):
        r = _run_all_phases(_example("10_optimization"))
        techniques = {a["technique"] for a in r["optimization"]["applied"]}
        self.assertTrue(any("Constant Propagation" in t for t in techniques))

    def test_dead_code_elimination_removes_unused_temps(self):
        r = _run_all_phases(_example("10_optimization"))
        techniques = {a["technique"] for a in r["optimization"]["applied"]}
        self.assertIn("Dead Code Elimination", techniques)
        # No temporary (t1, t2, ...) should survive as an assignment target
        # in the final optimized code for this particular example.
        after_targets = [i["code"].split("=")[0].strip() for i in r["optimization"]["after"] if i["kind"] == "assign"]
        self.assertFalse(any(t.startswith("t") and t[1:].isdigit() for t in after_targets))

    def test_algebraic_simplification_removes_add_zero(self):
        tac = [{"code": "y = x + 0", "line": 1, "kind": "assign"}]
        result, applied = optimizer._pass_algebraic_simplification(tac, [])
        self.assertEqual(result[0]["code"], "y = x")
        self.assertEqual(applied[0]["technique"], "Algebraic Simplification")


class TestPhase6CodeGeneration(unittest.TestCase):
    def test_target_code_is_generated_for_valid_program(self):
        r = _run_all_phases(_example("01_valid"))
        self.assertGreater(len(r["target_code"]), 0)
        instructions = [i["instruction"] for i in r["target_code"]]
        self.assertTrue(any(i.startswith("LOAD") for i in instructions))
        self.assertTrue(any(i.startswith("STORE") for i in instructions))


class TestRuleBasedErrorExplainer(unittest.TestCase):
    """
    Section 26-28: the Error Explainer must be entirely rule-based -- no
    AI, no network call, nothing to configure. Every test below runs
    with no internet connection whatsoever and still passes.
    """

    def test_every_rule_has_the_required_fields(self):
        # Section 28: every rule in the database must have exactly this
        # shape, so the Explanation Generator can never crash on a
        # missing field.
        required_fields = {"error_type", "phase", "message", "explanation", "solution", "example", "tip"}
        for error_code, rule in error_explainer.ERROR_RULES.items():
            self.assertTrue(required_fields.issubset(rule.keys()),
                             f"Rule '{error_code}' is missing one of {required_fields}")

    def test_missing_semicolon_matches_the_correct_rule(self):
        error = {
            "phase": "Syntax Analysis", "error_type": "Syntax Error", "line": 4,
            "message": "expected ';' but found 'return'", "source_line": "    int x = 10",
            "expected": ";", "actual": "return",
        }
        explanation = error_explainer.explain_error(error)
        self.assertEqual(explanation["error_code"], "MISSING_SEMICOLON")
        self.assertEqual(explanation["source"], "rule_based")
        self.assertIn("semicolon", explanation["explanation"].lower())
        for key in ("explanation", "reason", "solution", "corrected_code", "tip"):
            self.assertIn(key, explanation)
            self.assertTrue(explanation[key])  # never blank

    def test_undeclared_variable_extracts_the_variable_name(self):
        error = {
            "phase": "Semantic Analysis", "error_type": "Semantic Error", "line": 3,
            "message": "'y' has not been declared.", "source_line": "y = 10;",
        }
        explanation = error_explainer.explain_error(error)
        self.assertEqual(explanation["error_code"], "UNDECLARED_VARIABLE")
        self.assertIn("'y'", explanation["explanation"])

    def test_unknown_error_message_falls_back_to_a_generic_rule_not_a_crash(self):
        # An error shape the classifier has never seen before must still
        # produce a complete, non-blank explanation via the GENERIC_* rules
        # -- the explainer must never show a blank panel.
        error = {
            "phase": "Semantic Analysis", "error_type": "Semantic Error", "line": 9,
            "message": "some future error message the rules don't specifically recognise",
        }
        explanation = error_explainer.explain_error(error)
        self.assertEqual(explanation["error_code"], "GENERIC_SEMANTIC")
        for key in ("explanation", "reason", "solution", "corrected_code", "tip"):
            self.assertTrue(explanation[key])

    def test_normalize_error_strips_to_fixed_structured_shape(self):
        # normalize_error() must strip everything down to the fixed
        # structured shape the explainer is designed around (Section 26's
        # "Structured Error Object").
        raw = {
            "phase": "Semantic Analysis", "error_type": "Semantic Error", "line": 3,
            "message": "'y' has not been declared.", "source_line": "y = 10;",
            "some_extra_field_that_should_be_dropped": "irrelevant",
        }
        normalized = error_explainer.normalize_error(raw)
        self.assertNotIn("some_extra_field_that_should_be_dropped", normalized)
        self.assertEqual(set(normalized.keys()),
                          {"language", "phase", "error_type", "line", "column",
                           "message", "source_line", "expected", "actual"})

    def test_no_network_or_api_related_imports_in_error_explainer(self):
        # A structural guarantee that this module never grew a dependency
        # on requests/urllib/sockets/an API key -- keeping it honestly
        # rule-based, not just rule-based "by convention".
        import inspect
        source = inspect.getsource(error_explainer)
        for forbidden in ("import requests", "import urllib", "api_key", "API_KEY", "anthropic", "openai"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
