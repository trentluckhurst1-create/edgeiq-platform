Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

python ".\scripts\audit_edgeiq_remaining_beta_autonomous_completion_v1.py"
Get-Content ".\public\data\edgeiq_remaining_beta_autonomous_completion_v1_audit.txt"
