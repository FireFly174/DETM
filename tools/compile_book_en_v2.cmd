@echo off
setlocal enabledelayedexpansion

rem Compile EN book v2 into a single Markdown file.
rem Usage:
rem   tools\compile_book_en_v2.cmd
rem   tools\compile_book_en_v2.cmd draft
rem   tools\compile_book_en_v2.cmd print
rem   tools\compile_book_en_v2.cmd print quick

set MODE=draft
if /I "%~1"=="print" set MODE=print
if /I "%~1"=="draft" set MODE=draft

set VARIANT=full
if /I "%~2"=="quick" set VARIANT=quick
if /I "%~2"=="full" set VARIANT=full

set MANIFEST=docs\book\en_v2\manifest_en_v2.txt
if /I "%VARIANT%"=="quick" set MANIFEST=docs\book\en_v2\manifest_en_v2_quick.txt

set OUT=docs\book\en_v2\_compiled_v2.md
if /I "%VARIANT%"=="quick" set OUT=docs\book\en_v2\_compiled_v2_quick.md
if /I "%MODE%"=="print" set OUT=docs\book\en_v2\_compiled_v2_print.md
if /I "%MODE%"=="print" if /I "%VARIANT%"=="quick" set OUT=docs\book\en_v2\_compiled_v2_quick_print.md

set TITLE=DETM Book (EN v2)
if /I "%VARIANT%"=="quick" set TITLE=DETM Book (EN v2 quick)
if /I "%MODE%"=="draft" set TITLE=%TITLE% [draft]

pushd "%~dp0\.."
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
python tools\compile_book_ru.py --manifest "%MANIFEST%" --mode "%MODE%" --title "%TITLE%" --out - --report > "%OUT%"
if errorlevel 1 (
  popd
  exit /b 1
)

echo.
echo Wrote: %OUT%

rem Also render HTML/PDF so artifacts stay synchronized.
rem Set EN_V2_SKIP_RENDER=1 to skip rendering.
if /I "%EN_V2_SKIP_RENDER%"=="1" goto :skip_render
call tools\render_book_en_v2.cmd %MODE% %VARIANT%
if errorlevel 1 echo WARN: render failed, leaving Markdown artifact.
:skip_render

popd
endlocal
