# XER File Parser - PowerShell Script
#
# This script provides convenient access to XER parser commands from PowerShell
# Usage: .\xer.ps1 load CONSTRUCTION.xer
#        .\xer.ps1 projects
#        .\xer.ps1 tasks
#        .\xer.ps1 summary
#        .\xer.ps1 export output.txt

param([string]$Command, [string[]]$Arguments)

python cli.py $Command $Arguments
