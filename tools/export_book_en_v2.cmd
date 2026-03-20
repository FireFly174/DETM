@echo off
setlocal

rem Export EN book v2 to HTML and PDF.
rem Usage:
rem   tools\export_book_en_v2.cmd
rem   tools\export_book_en_v2.cmd draft
rem   tools\export_book_en_v2.cmd print
rem   tools\export_book_en_v2.cmd print quick

set MODE=print
if /I "%~1"=="draft" set MODE=draft
if /I "%~1"=="print" set MODE=print

set VARIANT=full
if /I "%~2"=="quick" set VARIANT=quick
if /I "%~2"=="full" set VARIANT=full

pushd "%~dp0\.."
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set EN_V2_SKIP_RENDER=1
call tools\compile_book_en_v2.cmd %MODE% %VARIANT%
set EN_V2_SKIP_RENDER=
if errorlevel 1 (
  popd
  exit /b 1
)

call tools\render_book_en_v2.cmd %MODE% %VARIANT%
if errorlevel 1 (
  popd
  exit /b 1
)

popd
endlocal
