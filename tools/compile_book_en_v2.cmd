@echo off
setlocal

rem Compile EN book v2 into a single Markdown file.
rem Usage:
rem   tools\compile_book_en_v2.cmd
rem   tools\compile_book_en_v2.cmd draft
rem   tools\compile_book_en_v2.cmd print
rem   tools\compile_book_en_v2.cmd print quick

set MODE=%1
if "%MODE%"=="" set MODE=draft
set VARIANT=%2
if "%VARIANT%"=="" set VARIANT=full

set MANIFEST=docs\book\en_v2\manifest_en_v2.txt
if /I "%VARIANT%"=="quick" set MANIFEST=docs\book\en_v2\manifest_en_v2_quick.txt

set OUT=docs\book\en_v2\_compiled_v2.md
if /I "%VARIANT%"=="quick" set OUT=docs\book\en_v2\_compiled_v2_quick.md
if /I "%MODE%"=="print" set OUT=docs\book\en_v2\_compiled_v2_print.md
if /I "%MODE%"=="print" if /I "%VARIANT%"=="quick" set OUT=docs\book\en_v2\_compiled_v2_quick_print.md

set TITLE=DETM Book (EN v2)
if /I "%VARIANT%"=="quick" set TITLE=DETM Book (EN v2 quick)
if /I "%MODE%"=="draft" set TITLE=%TITLE% [draft]

python tools\compile_book_ru.py --manifest "%MANIFEST%" --mode "%MODE%" --title "%TITLE%" --out - --report > "%OUT%"
if errorlevel 1 goto :eof

echo Wrote %OUT%