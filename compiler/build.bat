@echo off
REM =====================================================================
REM build.bat
REM -----------------------------------------------------------------
REM Builds the standalone Flex/Bison artifact in this folder.
REM Requires WinFlexBison and MinGW GCC to be installed and on PATH
REM (see the main project README.md -> Windows 11 Setup, Steps 3 and 5).
REM
REM Usage (from a terminal opened INSIDE the compiler/ folder):
REM     build.bat
REM
REM This produces THREE .exe files:
REM     lexer_standalone.exe   -> Phase 1 only, prints a token table
REM     parser.exe              -> Phase 1 + Phase 2 together
REM =====================================================================

echo ============================================================
echo  Building standalone Flex lexer (Phase 1 demo)...
echo ============================================================
win_flex --wincompat -o lex_standalone.yy.c lexer.l
gcc lex_standalone.yy.c -o lexer_standalone.exe -DSTANDALONE_LEXER
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  Building Bison parser + Flex lexer together (Phase 1+2)...
echo ============================================================
bison -d parser.y
if errorlevel 1 goto :error
win_flex --wincompat -o lex.yy.c lexer.l
if errorlevel 1 goto :error
gcc parser.tab.c lex.yy.c -o parser.exe
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  Build complete!
echo ============================================================
echo   Try:  lexer_standalone.exe  ^< ..\examples\01_valid.c
echo   Try:  parser.exe            ^< ..\examples\01_valid.c
echo   Try:  parser.exe            ^< ..\examples\02_missing_semicolon.c
goto :eof

:error
echo.
echo Build failed. Make sure win_flex, bison, and gcc are all on your PATH.
echo See the main README.md -> Windows 11 Setup for installation steps.
exit /b 1
