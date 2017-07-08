@echo off
setlocal
if not defined EDITOR set EDITOR=notepad
set PATH=%~dp0${GIT_BIN_DIR}\cmd;%~dp0;%PATH%
"%~dp0${GIT_BIN_DIR}\${GIT_PROGRAM}" %*
