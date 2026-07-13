@echo off
REM XER File Parser - Windows Batch Script
REM
REM This script provides convenient access to XER parser commands
REM Usage: xer.bat load CONSTRUCTION.xer
REM        xer.bat projects
REM        xer.bat tasks
REM        xer.bat summary
REM        xer.bat export output.txt

python cli.py %*
