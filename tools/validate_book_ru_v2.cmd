@echo off
setlocal enabledelayedexpansion

rem Validate RU v2 book build end-to-end.
rem Runs compile+render pipelines that already include:
rem   - markdown link/anchor check (compile stage)
rem   - html anchor check (render stage)
rem
rem Usage:
rem   tools\validate_book_ru_v2.cmd
rem   tools\validate_book_ru_v2.cmd all
rem   tools\validate_book_ru_v2.cmd full
rem   tools\validate_book_ru_v2.cmd quick

set TARGET=all
if not "%~1"=="" set TARGET=%~1

set RUN_FULL=1
set RUN_QUICK=1
if /I "%TARGET%"=="full" set RUN_QUICK=0
if /I "%TARGET%"=="quick" set RUN_FULL=0
if /I "%TARGET%"=="all" (
  set RUN_FULL=1
  set RUN_QUICK=1
)

if /I not "%TARGET%"=="all" if /I not "%TARGET%"=="full" if /I not "%TARGET%"=="quick" (
  echo Unknown target: %TARGET%
  echo Usage: tools\validate_book_ru_v2.cmd [all^|full^|quick]
  exit /b 2
)

set /a TOTAL=0
if "%RUN_FULL%"=="1" set /a TOTAL+=2
if "%RUN_QUICK%"=="1" set /a TOTAL+=2
set /a IDX=0

pushd "%~dp0\.."

echo RU v2 validate target=%TARGET% steps=%TOTAL%

if "%RUN_FULL%"=="1" call :run_step "draft/full" draft
if errorlevel 1 goto :fail
if "%RUN_FULL%"=="1" call :run_step "print/full" print
if errorlevel 1 goto :fail

if "%RUN_QUICK%"=="1" call :run_step "draft/quick" draft quick
if errorlevel 1 goto :fail
if "%RUN_QUICK%"=="1" call :run_step "print/quick" print quick
if errorlevel 1 goto :fail

echo.
echo VALIDATION OK: RU v2 (%TARGET%)
popd
endlocal
exit /b 0

:run_step
set /a IDX+=1
echo.
echo [!IDX!/!TOTAL!] %~1
call tools\compile_book_ru_v2.cmd %~2 %~3
if errorlevel 1 (
  echo.
  echo VALIDATION FAILED at step: %~1
  exit /b 1
)
exit /b 0

:fail
popd
endlocal
exit /b 1
