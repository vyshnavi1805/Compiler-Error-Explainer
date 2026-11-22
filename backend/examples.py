"""
examples.py
-----------
Section 30 of the spec: at least 10 built-in example programs, covering a
valid program, one error of each major kind, an example with multiple
simultaneous errors, an example suited to TAC generation, and an example
suited to optimization. These are served to the frontend's "Load Example"
dropdown via GET /examples, and also saved as plain .c files under
examples/ for manual testing outside the web app (e.g. with real GCC).
"""

EXAMPLES = [
    {
        "id": "01_valid",
        "title": "1. Valid Program",
        "description": "A clean, fully correct C program. Every phase should complete successfully.",
        "code": """#include <stdio.h>

int main() {
    int x = 10;
    int y = 20;
    int sum = x + y;
    printf("%d", sum);
    return 0;
}
""",
    },
    {
        "id": "02_missing_semicolon",
        "title": "2. Missing Semicolon",
        "description": "A classic syntax error: a statement is missing its terminating ';'.",
        "code": """#include <stdio.h>

int main() {
    int x = 10
    return 0;
}
""",
    },
    {
        "id": "03_missing_brace",
        "title": "3. Missing Closing Brace",
        "description": "The function body is never closed with a '}'.",
        "code": """#include <stdio.h>

int main() {
    int x = 10;
    printf("%d", x);
""",
    },
    {
        "id": "04_undeclared_variable",
        "title": "4. Undeclared Variable",
        "description": "A variable is used without ever being declared.",
        "code": """#include <stdio.h>

int main() {
    y = 10;
    printf("%d", y);
    return 0;
}
""",
    },
    {
        "id": "05_duplicate_declaration",
        "title": "5. Duplicate Declaration",
        "description": "The same variable name is declared twice in the same scope.",
        "code": """#include <stdio.h>

int main() {
    int x;
    int x;
    printf("%d", x);
    return 0;
}
""",
    },
    {
        "id": "06_type_mismatch",
        "title": "6. Type Mismatch",
        "description": "A string literal is assigned into an int variable.",
        "code": """#include <stdio.h>

int main() {
    int x;
    x = "Hello";
    printf("%d", x);
    return 0;
}
""",
    },
    {
        "id": "07_invalid_character",
        "title": "7. Invalid Character",
        "description": "A stray character the C language does not recognise (a lexical error).",
        "code": """#include <stdio.h>

int main() {
    int x = 10;
    int y = 20;
    ~
    printf("%d", x + y);
    return 0;
}
""",
    },
    {
        "id": "08_multiple_errors",
        "title": "8. Multiple Errors",
        "description": "Several missing semicolons AND an undeclared variable, all in one program.",
        "code": """#include <stdio.h>

int main() {
    int x
    y = 10
    printf("%d", x)
    return 0;
}
""",
    },
    {
        "id": "09_tac_expression",
        "title": "9. Expression for TAC",
        "description": "A good expression for watching Three Address Code generation in action.",
        "code": """#include <stdio.h>

int main() {
    int a = 2;
    int b = 3;
    int c = 4;
    int x;
    x = a + b * c;
    printf("%d", x);
    return 0;
}
""",
    },
    {
        "id": "10_optimization",
        "title": "10. Optimization Showcase",
        "description": "Triggers constant folding, constant propagation, and algebraic simplification.",
        "code": """#include <stdio.h>

int main() {
    int x;
    int y;
    x = 10 * 2;
    y = x + 5;
    y = y + 0;
    printf("%d", y);
    return 0;
}
""",
    },
]
