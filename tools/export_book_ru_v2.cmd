@echo off
setlocal

rem Export RU book v2 to HTML (and PDF if possible).
rem Requirements:
rem   - pandoc (for HTML)
rem   - a TeX engine like xelatex (optional, for PDF)
rem   - OR Google Chrome (fallback PDF)
rem
rem Usage:
rem   tools\export_book_ru_v2.cmd
rem   tools\export_book_ru_v2.cmd draft
rem   tools\export_book_ru_v2.cmd print
rem   tools\export_book_ru_v2.cmd print quick

set MODE=print
if /I "%~1"=="draft" set MODE=draft
if /I "%~1"=="print" set MODE=print

set VARIANT=full
if /I "%~2"=="quick" set VARIANT=quick
if /I "%~2"=="full" set VARIANT=full

pushd "%~dp0\.."

rem Compile first, but skip its best-effort render so we render exactly once (and can fail hard if it fails).
set RU_V2_SKIP_RENDER=1
call tools\compile_book_ru_v2.cmd %MODE% %VARIANT%
set RU_V2_SKIP_RENDER=
if errorlevel 1 (
  popd
  exit /b 1
)

rem Ensure export produces PDF; fail if render fails.
call tools\render_book_ru_v2.cmd %MODE% %VARIANT%
if errorlevel 1 (
  popd
  exit /b 1
)

popd
endlocal
