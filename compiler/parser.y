/* =====================================================================
   parser.y
   -----------------------------------------------------------------
   A REAL Bison grammar for the same educational C subset used by the
   Python engine in backend/parser.py (Section 35 of the project spec).
   This is a genuine, buildable parser-generator artifact you can show
   your professor alongside the hand-written Python recursive-descent
   parser -- same grammar rules, different tool.

   BUILD (see build.bat for the full one-shot script):
       bison -d parser.y
       win_flex lexer.l
       gcc parser.tab.c lex.yy.c -o parser.exe -lfl
       parser.exe < ..\examples\01_valid.c

   On success it prints "Syntax OK". On a grammar violation, Bison's
   yyerror() below prints the line number and a message, similar in
   spirit to the syntax errors shown in the web UI.
   ===================================================================== */

%{
#include <stdio.h>
#include <stdlib.h>

int yylex(void);
extern int yylineno;
void yyerror(const char *msg);

int syntax_error_count = 0;
%}

%union {
    int ival;
    double dval;
    char *sval;
}

%token <sval> ID STRING_LIT CHAR_LIT
%token <ival> INT_CONST
%token <dval> FLOAT_CONST

%token INT FLOAT DOUBLE CHAR VOID
%token IF ELSE WHILE FOR RETURN
%token EQ NEQ LE GE AND OR

/* Precedence: lowest to highest, so expressions parse the same way a
   real C compiler would (e.g. * binds tighter than +). Note: '=' does
   NOT need a precedence entry here -- assignment is its own statement
   rule (ID '=' expr ';'), not part of the expr grammar, so it never
   competes with these operators. */
%left OR
%left AND
%left EQ NEQ
%left '<' '>' LE GE
%left '+' '-'
%left '*' '/' '%'
%right UMINUS '!'
%nonassoc IFX
%nonassoc ELSE

%%

program:
      function_list
    ;

function_list:
      function_list function
    | function
    ;

function:
      type_spec ID '(' opt_params ')' block
        { printf("Parsed function '%s'\n", $2); }
    ;

opt_params:
      /* empty */
    | param_list
    ;

param_list:
      param_list ',' param
    | param
    ;

param:
      type_spec ID
    ;

type_spec:
      INT | FLOAT | DOUBLE | CHAR | VOID
    ;

block:
      '{' stmt_list '}'
    ;

stmt_list:
      /* empty */
    | stmt_list stmt
    ;

stmt:
      declaration
    | assignment
    | if_stmt
    | while_stmt
    | return_stmt
    | expr_stmt
    | block
    ;

declaration:
      type_spec ID ';'
    | type_spec ID '=' expr ';'
    ;

assignment:
      ID '=' expr ';'
    ;

if_stmt:
      IF '(' expr ')' stmt %prec IFX
    | IF '(' expr ')' stmt ELSE stmt
    ;

while_stmt:
      WHILE '(' expr ')' stmt
    ;

return_stmt:
      RETURN ';'
    | RETURN expr ';'
    ;

expr_stmt:
      expr ';'
    ;

opt_args:
      /* empty */
    | arg_list
    ;

arg_list:
      arg_list ',' expr
    | expr
    ;

expr:
      expr '+' expr
    | expr '-' expr
    | expr '*' expr
    | expr '/' expr
    | expr '%' expr
    | expr EQ expr
    | expr NEQ expr
    | expr '<' expr
    | expr '>' expr
    | expr LE expr
    | expr GE expr
    | expr AND expr
    | expr OR expr
    | '-' expr %prec UMINUS
    | '!' expr
    | '(' expr ')'
    | ID '(' opt_args ')'
    | ID
    | INT_CONST
    | FLOAT_CONST
    | STRING_LIT
    | CHAR_LIT
    ;

%%

void yyerror(const char *msg) {
    syntax_error_count++;
    fprintf(stderr, "SYNTAX ERROR on line %d: %s\n", yylineno, msg);
}

int main(int argc, char **argv) {
    printf("C Compiler Error Explainer - standalone Bison parser (Phase 1 + Phase 2 demo)\n");
    int result = yyparse();
    if (syntax_error_count == 0 && result == 0) {
        printf("\nSyntax OK -- the program matches the supported C grammar.\n");
        return 0;
    }
    printf("\n%d syntax error(s) found.\n", syntax_error_count);
    return 1;
}
