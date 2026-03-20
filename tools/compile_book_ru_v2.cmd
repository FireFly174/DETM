@echo off
setlocal enabledelayedexpansion

rem Compile RU book v2 into a single Markdown file.
rem Usage:
rem   tools\compile_book_ru_v2.cmd
rem   tools\compile_book_ru_v2.cmd draft
rem   tools\compile_book_ru_v2.cmd print
rem   tools\compile_book_ru_v2.cmd print quick

set MODE=draft
if /I "%~1"=="print" set MODE=print
if /I "%~1"=="draft" set MODE=draft

set VARIANT=full
if /I "%~2"=="quick" set VARIANT=quick
if /I "%~2"=="full" set VARIANT=full

set MANIFEST=docs\book\ru_v2\manifest_ru_v2.txt
if /I "%VARIANT%"=="quick" set MANIFEST=docs\book\ru_v2\manifest_ru_v2_quick.txt

set OUT=docs\book\ru_v2\_compiled_v2.md
if /I "%VARIANT%"=="quick" set OUT=docs\book\ru_v2\_compiled_v2_quick.md
if /I "%MODE%"=="print" set OUT=docs\book\ru_v2\_compiled_v2_print.md
if /I "%MODE%"=="print" if /I "%VARIANT%"=="quick" set OUT=docs\book\ru_v2\_compiled_v2_quick_print.md

pushd "%~dp0\.."
rem Use stdout redirection so compilation works in sandboxed environments.
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "TITLE=DETM - RU v2"
if /I "%VARIANT%"=="quick" set "TITLE=DETM - RU v2 (quick)"
set "ICON_MODE=%RU_V2_ICON_MODE%"
if not defined ICON_MODE set "ICON_MODE=auto"
python tools\compile_book_ru.py --manifest "%MANIFEST%" --mode "%MODE%" --icon-mode "%ICON_MODE%" --title "%TITLE%" --out - --report > "%OUT%"
if errorlevel 1 (
  popd
  exit /b 1
)

echo.
echo Wrote: %OUT%

rem Validate local markdown links/anchors in the compiled artifact.
rem Set RU_V2_SKIP_MD_LINK_CHECK=1 to skip (not recommended).
if /I "%RU_V2_SKIP_MD_LINK_CHECK%"=="1" goto :skip_md_link_check
python tools\check_markdown_links.py "%OUT%"
if errorlevel 1 (
  popd
  exit /b 1
)
:skip_md_link_check

rem Also render HTML/PDF so the build artifact is always up to date (with embedded images).
rem Set RU_V2_SKIP_RENDER=1 to skip rendering (useful for export scripts that render separately).
if /I "%RU_V2_SKIP_RENDER%"=="1" goto :skip_render
call tools\render_book_ru_v2.cmd %MODE% %VARIANT%
if errorlevel 1 echo WARN: render failed, leaving only Markdown/HTML artifacts.
:skip_render

popd
endlocal

