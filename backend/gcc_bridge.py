"""
gcc_bridge.py
-------------
OPTIONAL FEATURE (Section 34 of the spec): "Real GCC diagnostics"

This module is completely optional and never required for the app to
work. If GCC is installed and available on the system PATH, we can send
the user's C code to the real GCC compiler and show its actual error
output side-by-side with our own educational analysis. If GCC is not
installed, this module simply reports that gracefully and the rest of
the application continues to work exactly as before (see error handling
requirements in Section 40).

We deliberately do NOT let GCC replace the six educational phases -- it
is only an extra "real compiler says..." panel for realism.
"""

import shutil
import subprocess
import tempfile
import os
import re

GCC_DIAGNOSTIC_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+):\s*(?P<level>error|warning):\s*(?P<message>.+)$"
)


def is_gcc_available():
    return shutil.which("gcc") is not None


def compile_with_gcc(source_code, timeout_seconds=10):
    """
    Attempt to compile the given C source with the real GCC compiler.

    Returns a dict:
        {
          "available": bool,
          "success": bool,
          "raw_output": str,
          "diagnostics": [ {level, line, column, message}, ... ]
        }
    """
    if not is_gcc_available():
        return {
            "available": False,
            "success": False,
            "raw_output": "GCC was not found on this system's PATH.",
            "diagnostics": [],
        }

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = os.path.join(tmp_dir, "program.c")
        output_path = os.path.join(tmp_dir, "program.out")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        try:
            result = subprocess.run(
                ["gcc", source_path, "-o", output_path, "-Wall"],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {
                "available": True,
                "success": False,
                "raw_output": "GCC compilation timed out.",
                "diagnostics": [],
            }

        diagnostics = []
        for line in result.stderr.splitlines():
            match = GCC_DIAGNOSTIC_RE.match(line.strip())
            if match:
                diagnostics.append({
                    "level": match.group("level"),
                    "line": int(match.group("line")),
                    "column": int(match.group("column")),
                    "message": match.group("message"),
                })

        return {
            "available": True,
            "success": result.returncode == 0,
            "raw_output": result.stderr,
            "diagnostics": diagnostics,
        }
