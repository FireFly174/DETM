@echo off
setlocal

rem Render RU book v2 Markdown to HTML and PDF (self-contained).
rem Expects docs\book\ru_v2\_compiled_v2*.md to already exist.
rem Usage:
rem   tools\render_book_ru_v2.cmd
rem   tools\render_book_ru_v2.cmd draft
rem   tools\render_book_ru_v2.cmd print
rem   tools\render_book_ru_v2.cmd print quick

set MODE=print
if /I "%~1"=="draft" set MODE=draft
if /I "%~1"=="print" set MODE=print

set VARIANT=full
if /I "%~2"=="quick" set VARIANT=quick
if /I "%~2"=="full" set VARIANT=full

pushd "%~dp0\.."

set IN=docs\book\ru_v2\_compiled_v2.md
if /I "%MODE%"=="print" set IN=docs\book\ru_v2\_compiled_v2_print.md
if /I "%VARIANT%"=="quick" set IN=docs\book\ru_v2\_compiled_v2_quick.md
if /I "%MODE%"=="print" if /I "%VARIANT%"=="quick" set IN=docs\book\ru_v2\_compiled_v2_quick_print.md

set "PANDOC="
for /f "delims=" %%P in ('where pandoc 2^>nul') do set "PANDOC=%%P"
if not defined PANDOC if exist "%LOCALAPPDATA%\Pandoc\pandoc.exe" set "PANDOC=%LOCALAPPDATA%\Pandoc\pandoc.exe"
if not defined PANDOC if exist "%ProgramFiles%\Pandoc\pandoc.exe" set "PANDOC=%ProgramFiles%\Pandoc\pandoc.exe"
if not defined PANDOC if exist "%ProgramFiles(x86)%\Pandoc\pandoc.exe" set "PANDOC=%ProgramFiles(x86)%\Pandoc\pandoc.exe"
if not defined PANDOC (
  echo.
  echo pandoc not found. Skipping HTML/PDF render.
  echo Tip: install pandoc and re-run this script.
  popd
  exit /b 0
)

set OUT_HTML=%IN:.md=.html%
rem Embed local assets (images, etc.) into HTML so the resulting PDF is self-contained.
rem Note: on Windows pandoc uses ';' as the path separator for --resource-path.
set "BOOK_TITLE=DETM - RU v2"
if /I "%VARIANT%"=="quick" set "BOOK_TITLE=DETM - RU v2 (quick)"
if /I "%MODE%"=="draft" set "BOOK_TITLE=%BOOK_TITLE% (draft)"
"%PANDOC%" "%IN%" --from gfm --to html5 --standalone --embed-resources --metadata title="%BOOK_TITLE%" --metadata lang=ru --resource-path="docs/book/ru_v2;docs/book/ru_v2/assets;." --output "%OUT_HTML%"
if errorlevel 1 goto :fail

echo.
echo Wrote: %OUT_HTML%

set OUT_PDF=%IN:.md=.pdf%
for %%I in ("%OUT_HTML%") do set "OUT_HTML_ABS=%%~fI"
for %%I in ("%OUT_PDF%") do set "OUT_PDF_ABS=%%~fI"
set "OUT_PDF_TMP=%OUT_PDF_ABS%.tmp.pdf"

set "BROWSER="
for /f "delims=" %%C in ('where chrome 2^>nul') do set "BROWSER=%%C"
if not defined BROWSER if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER for /f "delims=" %%E in ('where msedge 2^>nul') do set "BROWSER=%%E"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined BROWSER goto :try_browser
goto :try_xelatex

:try_browser
rem Use a deterministic profile directory to avoid leaving many chrome_headless_* folders behind
rem when the process is interrupted. We still clean it before and after each run.
set "CHROME_PROFILE=docs\\book\\ru_v2\\_tmp\\chrome_profile_%MODE%_%VARIANT%"
if not exist "docs\\book\\ru_v2\\_tmp" mkdir "docs\\book\\ru_v2\\_tmp" >nul 2>nul
if exist "%CHROME_PROFILE%" rmdir /s /q "%CHROME_PROFILE%" >nul 2>nul
if exist "%CHROME_PROFILE%" (
  rem If the directory can't be removed (e.g. locked by another process),
  rem fall back to a random profile directory to keep rendering working.
  set "CHROME_PROFILE=docs\\book\\ru_v2\\_tmp\\chrome_headless_%RANDOM%"
)
if not exist "%CHROME_PROFILE%" mkdir "%CHROME_PROFILE%" >nul 2>nul
for %%I in ("%CHROME_PROFILE%") do set "CHROME_PROFILE_ABS=%%~fI"
if exist "%OUT_PDF_TMP%" del /f /q "%OUT_PDF_TMP%" >nul 2>nul
rem NOTE: disable Chrome print headers/footers (date + file:/// url) for clean PDFs.
rem Chrome's "new" headless has been observed to ignore the no-header flag in some setups,
rem so we intentionally use the classic headless mode here.
"%BROWSER%" --headless --disable-gpu --no-first-run --no-default-browser-check --disable-crash-reporter --disable-features=Crashpad,ChromeCrashpadHandler --user-data-dir="%CHROME_PROFILE_ABS%" --no-sandbox --print-to-pdf-no-header --print-to-pdf="%OUT_PDF_TMP%" "%OUT_HTML_ABS%" > "docs\\book\\ru_v2\\_tmp\\chrome_render_%MODE%_%VARIANT%.log" 2>&1
if not exist "%OUT_PDF_TMP%" goto :chrome_fail
for %%I in ("%OUT_PDF_TMP%") do set "TMP_SIZE=%%~zI"
if not defined TMP_SIZE goto :chrome_fail
if %TMP_SIZE% LSS 50000 goto :chrome_fail
move /y "%OUT_PDF_TMP%" "%OUT_PDF_ABS%" >nul
if exist "%CHROME_PROFILE%" rmdir /s /q "%CHROME_PROFILE%" >nul 2>nul
echo Wrote: %OUT_PDF%
popd
endlocal
exit /b 0

:chrome_fail
if exist "%OUT_PDF_TMP%" del /f /q "%OUT_PDF_TMP%" >nul 2>nul
if exist "%CHROME_PROFILE%" rmdir /s /q "%CHROME_PROFILE%" >nul 2>nul
echo.
echo Browser PDF export failed (or produced invalid PDF). Trying xelatex...

:try_xelatex
rem Pandoc's LaTeX route requires converting SVG images to PDF (usually via rsvg-convert).
rem Since this book embeds SVG assets, fail fast with a clear message if conversion tooling is missing.
where rsvg-convert >nul 2>nul
if errorlevel 1 (
  echo.
  echo rsvg-convert not found. Cannot export PDF via xelatex when the book contains SVG images.
  echo Tip: install Google Chrome or Microsoft Edge recommended, or install rsvg-convert and re-run.
  popd
  exit /b 1
)
where xelatex >nul 2>nul
if not errorlevel 1 goto :have_xelatex
echo.
echo xelatex not found. Cannot export PDF.
echo Tip: install a LaTeX distribution (TeX Live / MiKTeX), or install Google Chrome for the fallback exporter.
popd
exit /b 1

:have_xelatex
if exist "%OUT_PDF_TMP%" del /f /q "%OUT_PDF_TMP%" >nul 2>nul
"%PANDOC%" "%IN%" --from gfm --resource-path="docs/book/ru_v2;docs/book/ru_v2/assets;." --pdf-engine=xelatex --output "%OUT_PDF_TMP%"
if errorlevel 1 goto :fail_pdf
if not exist "%OUT_PDF_TMP%" goto :fail_pdf
for %%I in ("%OUT_PDF_TMP%") do set "TMP_SIZE=%%~zI"
if not defined TMP_SIZE goto :fail_pdf
if %TMP_SIZE% LSS 50000 goto :fail_pdf
move /y "%OUT_PDF_TMP%" "%OUT_PDF_ABS%" >nul
echo Wrote: %OUT_PDF%
popd
endlocal
exit /b 0

:fail_pdf
echo.
echo PDF render failed.
if exist "%OUT_PDF_TMP%" del /f /q "%OUT_PDF_TMP%" >nul 2>nul
popd
exit /b 1

:fail
popd
exit /b 1

