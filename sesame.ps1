# Sesame CLI wrapper for PowerShell
# Usage: .\sesame.ps1 get, .\sesame.ps1 list, .\sesame.ps1 add, etc.

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Activate venv
& "$ScriptDir\.venv\Scripts\Activate.ps1"

# Run CLI
python "$ScriptDir\cli.py" @Arguments
