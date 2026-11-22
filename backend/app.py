"""
app.py
------
C Compiler Error Explainer - Flask backend.

This is the entry point that ties together all six compiler phases and
the RULE-BASED error explainer. It exposes a small REST API that the
frontend (frontend/script.js) calls.

THIS PROJECT CONTAINS NO AI, NO MACHINE LEARNING, AND NO EXTERNAL API
CALLS OF ANY KIND. Every piece of analysis and every explanation shown
to the user is produced by plain Python code in this project -- the
lexer, parser, semantic analyzer, and the rule database in
error_explainer.py. The application works fully offline; there is no
API key to configure anywhere.

ENDPOINTS
    GET  /health           -> simple check that the backend is running
    GET  /examples          -> list of built-in example C programs
    POST /analyze            -> run all six phases on submitted C code
    POST /explain             -> explain ONE specific error using the
                                 rule-based engine (also called
                                 internally by /analyze for every error found)

HOW TO RUN (see README.md for full Windows 11 instructions):
    python app.py
Then open frontend/index.html in your browser (or serve it with any
simple static file server).

WHY PYTHON/FLASK? (Section 4 of the spec)
The six compiler phases could in principle be written in pure C, but
Python was chosen for the web backend specifically because:
  1. It lets the SAME analysis code serve both the browser UI and the
     automated test suite (backend/tests/) without duplicating logic.
  2. Flask's built-in dev server needs zero extra installation beyond
     `pip install -r requirements.txt` -- no separate web server setup.
  3. Regular expressions and dictionaries (Python's core data types) map
     very directly onto the lexer's token patterns and the rule
     database, which keeps every phase's source code short enough for a
     beginner to read start-to-finish.
The genuine Flex/Bison implementation of Phases 1-2 lives separately in
compiler/ for the parser-generator requirement -- see compiler/README.md.
"""

import os
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS

import lexer
import parser as parser_module
import semantic
import intermediate_code
import optimizer
import code_generator
import gcc_bridge
import error_explainer
from examples import EXAMPLES

app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path=""
)

CORS(app)


@app.route("/")
def home():
    return app.send_static_file("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "C Compiler Error Explainer backend is running.",
        "ai_used": False,
        "offline": True,
        "gcc_available": gcc_bridge.is_gcc_available(),
    })


@app.route("/examples", methods=["GET"])
def get_examples():
    return jsonify({"examples": EXAMPLES})


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Runs the full six-phase pipeline on the submitted C source code.
    See Section 46 of the spec for the expected response shape.
    """
    body = request.get_json(silent=True) or {}
    source_code = body.get("code", "")
    use_gcc = bool(body.get("use_gcc", False))

    if not source_code or not source_code.strip():
        return jsonify({
            "success": False,
            "error": "empty_source",
            "message": "No C source code was submitted. Please write or load some code first.",
        }), 400

    try:
        response = run_pipeline(source_code, use_gcc=use_gcc)
        return jsonify(response)
    except Exception as exc:  # noqa: BLE001 - never let the backend crash on bad input
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "internal_error",
            "message": "Something went wrong while analyzing this code. "
                        "This is usually caused by a construct outside the "
                        "supported C subset (see README -> Limitations). "
                        f"Details: {exc}",
        }), 500


@app.route("/explain", methods=["POST"])
def explain():
    """Explain a single structured error using the rule-based engine (Section 27)."""
    body = request.get_json(silent=True) or {}
    error = body.get("error")
    if not error:
        return jsonify({"success": False, "message": "No 'error' object was provided."}), 400

    explanation = error_explainer.explain_error(error)
    return jsonify({"success": True, **explanation})


# ---------------------------------------------------------------------
# The pipeline itself
# ---------------------------------------------------------------------
def run_pipeline(source_code, use_gcc=False):
    # ---------- PHASE 1: Lexical Analysis ----------
    tokens, lexical_errors = lexer.tokenize(source_code)
    token_dicts = lexer.tokens_to_dict_list(tokens)

    # ---------- PHASE 2: Syntax Analysis ----------
    parse_tree, syntax_errors = parser_module.parse(tokens, source_code)

    # ---------- PHASE 3: Semantic Analysis ----------
    semantic_result = semantic.analyze(parse_tree, source_code)
    semantic_errors = semantic_result["errors"]
    warnings = semantic_result["warnings"]
    symbol_table = semantic_result["symbol_table"]

    all_blocking_errors = lexical_errors + syntax_errors + semantic_errors

    # ---------- PHASE 4/5/6: only run if the code is "clean enough" ----------
    # If there are lexical or syntax errors, the parse tree may be unreliable,
    # so we honestly skip TAC/optimization/codegen rather than generate
    # misleading output (Section 35: "explain why later phases may not
    # execute").
    intermediate = []
    optimization = {"before": [], "after": [], "applied": []}
    target_code = []
    skipped_reason = None

    if lexical_errors or syntax_errors:
        skipped_reason = (
            "Lexical/Syntax errors were found, so Intermediate Code, "
            "Optimization, and Code Generation were skipped. Fix the "
            "errors above first -- later phases depend on a valid parse tree."
        )
    elif semantic_errors:
        skipped_reason = (
            "Semantic errors were found (for example, an undeclared variable "
            "or a type mismatch), so Intermediate Code, Optimization, and "
            "Code Generation were skipped. Generating code for a program "
            "with unresolved semantic errors would be misleading -- fix the "
            "errors above first."
        )
    else:
        intermediate = intermediate_code.generate(parse_tree)
        optimization = optimizer.optimize(intermediate)
        target_code = code_generator.generate(optimization["after"])

    # ---------- Pipeline status for the UI ----------
    pipeline_status = build_pipeline_status(
        lexical_errors, syntax_errors, semantic_errors, bool(skipped_reason)
    )

    # ---------- Rule-based explanations for every error found (NO AI) ----------
    explained_errors = []
    for err in all_blocking_errors:
        explanation = error_explainer.explain_error(err)
        explained_errors.append({**error_explainer.normalize_error(err), "explanation": explanation})

    # ---------- Optional real GCC diagnostics (still not AI -- just GCC) ----------
    gcc_result = None
    if use_gcc:
        gcc_result = gcc_bridge.compile_with_gcc(source_code)

    overview = {
        "lines": len(source_code.split("\n")),
        "tokens": len(token_dicts),
        "symbols": len(symbol_table),
        "errors": len(all_blocking_errors),
        "warnings": len(warnings),
        "status": "Compilation Failed" if all_blocking_errors else "Compilation Analysis Successful",
    }

    return {
        "success": True,
        "overview": overview,
        "tokens": token_dicts,
        "parse_tree": parse_tree,
        "symbol_table": symbol_table,
        "intermediate_code": intermediate,
        "optimization": optimization,
        "target_code": target_code,
        "errors": explained_errors,
        "warnings": warnings,
        "pipeline_status": pipeline_status,
        "skipped_reason": skipped_reason,
        "gcc": gcc_result,
    }


def build_pipeline_status(lexical_errors, syntax_errors, semantic_errors, later_skipped):
    """
    Build the check/warning/error/pending status shown in the Compiler
    Pipeline section (Section 35 of the spec).
    """
    def status_for(has_errors, was_reached=True):
        if not was_reached:
            return "not_processed"
        return "error" if has_errors else "success"

    lexical_ok = status_for(bool(lexical_errors))
    syntax_ok = status_for(bool(syntax_errors))
    semantic_ok = status_for(bool(semantic_errors))
    later_status = "not_processed" if later_skipped else "success"

    return {
        "lexical_analysis": lexical_ok,
        "syntax_analysis": syntax_ok,
        "semantic_analysis": semantic_ok,
        "intermediate_code": later_status,
        "optimization": later_status,
        "code_generation": later_status,
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    print("=" * 60)
    print(" C Compiler Error Explainer backend starting...")
    print(" AI used: No (100% rule-based, fully offline)")
    print(f" GCC available: {gcc_bridge.is_gcc_available()}")
    print(f" Listening on: http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=debug)
