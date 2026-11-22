"""
symbol_table.py
----------------
A simple, beginner-friendly Symbol Table implementation for the
Semantic Analysis phase of C Compiler Error Explainer.

WHAT IS A SYMBOL TABLE?
A symbol table is a data structure a compiler uses to keep track of every
identifier (variable name, function name, etc.) that appears in a program:
what its type is, which scope it belongs to, and where it was declared.

HOW SCOPE IS HANDLED HERE:
We use a simple *stack of dictionaries*.
- The bottom of the stack is always the "global" scope.
- Every time we enter a function body, we push a new dictionary (a new scope)
  onto the stack.
- Every time we leave a function body, we pop that dictionary off.
- When searching for a symbol, we look from the TOP of the stack (innermost
  scope) down to the BOTTOM (global scope). This mimics how real C scoping
  rules work: a local variable can "shadow" a global one.

This is intentionally simple (no block-level {} scoping inside a function,
just function-level scoping) because the goal is to teach the CONCEPT of a
symbol table clearly, not to build a production-grade C compiler.
"""


class Symbol:
    """Represents a single entry in the symbol table."""

    def __init__(self, name, sym_type, scope, line, kind="variable"):
        self.name = name
        self.sym_type = sym_type    # e.g. "int", "float", "function"
        self.scope = scope          # e.g. "global" or a function name
        self.line = line            # line number where it was declared
        self.kind = kind            # "variable" or "function"

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.sym_type,
            "scope": self.scope,
            "line": self.line,
            "kind": self.kind,
        }


class SymbolTable:
    """
    A stack-based symbol table.

    self.scopes is a list of dicts.
        self.scopes[0]  -> global scope
        self.scopes[-1] -> current (innermost) scope
    """

    def __init__(self):
        # Start with just the global scope.
        self.scopes = [{"__name__": "global"}]
        # We keep a flat, ordered history of every symbol ever inserted
        # (including ones whose scope has since closed) so the UI can show
        # a complete table, exactly like Section 6 of the requirements asks.
        self.all_symbols = []

    # ---------------------------------------------------------------
    # Scope management
    # ---------------------------------------------------------------
    def enter_scope(self, scope_name):
        """Push a new scope onto the stack (e.g. when entering a function)."""
        self.scopes.append({"__name__": scope_name})

    def exit_scope(self):
        """Pop the current scope off the stack (e.g. leaving a function)."""
        if len(self.scopes) > 1:
            self.scopes.pop()

    def current_scope_name(self):
        return self.scopes[-1]["__name__"]

    # ---------------------------------------------------------------
    # Insertion
    # ---------------------------------------------------------------
    def insert(self, name, sym_type, line, kind="variable"):
        """
        Insert a new symbol into the CURRENT (innermost) scope.

        Returns:
            (success: bool, existing_symbol_or_None)

        If a symbol with the same name already exists in the CURRENT scope,
        insertion fails (this is how we detect duplicate declarations).
        """
        current = self.scopes[-1]
        if name in current:
            return False, current[name]

        symbol = Symbol(name, sym_type, self.current_scope_name(), line, kind)
        current[name] = symbol
        self.all_symbols.append(symbol)
        return True, None

    # ---------------------------------------------------------------
    # Lookup
    # ---------------------------------------------------------------
    def lookup(self, name):
        """
        Search for a symbol starting from the innermost scope outward to
        the global scope. Returns the Symbol if found, else None.
        """
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def is_declared_in_current_scope(self, name):
        return name in self.scopes[-1]

    # ---------------------------------------------------------------
    # Export for the UI / JSON API
    # ---------------------------------------------------------------
    def export(self):
        """Return the full symbol table as a list of dicts, in declaration order."""
        return [s.to_dict() for s in self.all_symbols]
