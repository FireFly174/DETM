@echo off
setlocal

rem Clean temporary/debug artifacts produced during RU v2 book rendering.
rem Safe by default: shows what would be deleted. Use --yes to actually delete.
rem
rem Usage:
rem   tools\clean_book_ru_v2.cmd
rem   tools\clean_book_ru_v2.cmd --yes

set "ROOT=docs\book\ru_v2"
set "TMP=%ROOT%\_tmp"

if /I "%~1"=="--yes" goto :do

echo.
echo This will remove known RU v2 build TEMP/DEBUG artifacts:
echo   - %ROOT%\_compiled_v2*.pdf.tmp
echo   - %ROOT%\_compiled_v2*.tmp.pdf
echo   - %ROOT%\_compiled_v2*.pdf.tmp.pdf
echo   - %TMP%\chrome_headless_*
echo   - %TMP%\chrome_profile_*
echo   - %TMP%\chrome_test_*
echo   - %TMP%\chrome_flag_test\
echo   - %TMP%\pandoc_asset_test.*
echo.
echo To actually delete, run:
echo   tools\clean_book_ru_v2.cmd --yes
echo.
exit /b 0

:do
pushd "%~dp0\.."

rem Old/bad temp files that confuse readers (e.g. *.pdf.tmp that is not a PDF).
del /f /q "%ROOT%\_compiled_v2*.pdf.tmp" 2>nul
del /f /q "%ROOT%\_compiled_v2*.tmp.pdf" 2>nul
del /f /q "%ROOT%\_compiled_v2*.pdf.tmp.pdf" 2>nul

rem Renderer scratch (Chrome profiles, tests).
for /d %%D in ("%TMP%\\chrome_headless_*") do rmdir /s /q "%%D" >nul 2>nul
for /d %%D in ("%TMP%\\chrome_profile_*") do rmdir /s /q "%%D" >nul 2>nul
for /d %%D in ("%TMP%\\chrome_test_*") do rmdir /s /q "%%D" >nul 2>nul
if exist "%TMP%\chrome_flag_test" rmdir /s /q "%TMP%\chrome_flag_test" >nul 2>nul
del /f /q "%TMP%\pandoc_asset_test.*" 2>nul

echo.
echo Cleaned RU v2 temp/debug artifacts under %ROOT%.

popd
endlocal
