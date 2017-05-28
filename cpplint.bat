@echo off
setlocal

:: Ensure that "depot_tools" is somewhere in PATH so this tool can be used
:: standalone, but allow other PATH manipulations to take priority.
PATH=%PATH%;%~dp0

call python "%~dp0cpplint.py" %*
