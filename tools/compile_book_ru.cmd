@echo off
setlocal enabledelayedexpansion

rem Compile RU book into a single Markdown file.
rem Usage:
rem   tools\compile_book_ru.cmd
rem   tools\compile_book_ru.cmd draft
rem   tools\compile_book_ru.cmd print

set MODE=draft
if /I "%~1"=="print" set MODE=print
if /I "%~1"=="draft" set MODE=draft

set OUT=docs\book\ru\_compiled.md
if /I "%MODE%"=="print" set OUT=docs\book\ru\_compiled_print.md

pushd "%~dp0\.."
rem Some environments (CI / sandboxed shells) disallow Python writing to files directly.
rem Use stdout redirection so compilation still works.
python tools\compile_book_ru.py --mode "%MODE%" --out - --report > "%OUT%"
if errorlevel 1 (
  popd
  exit /b 1
)
popd

echo.
echo Wrote: %OUT%
endlocal
