#!/usr/bin/env pwsh
<#
.SYNOPSIS
Wrapper for the Tauri maintenance agent on Windows PowerShell.
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    $Args
)
$script = Join-Path $PSScriptRoot "tauri_agent.py"
& python $script @Args
