param(
  [string]$ProjectDir = "."
)

$db = Join-Path $ProjectDir "database.db"
if (!(Test-Path $db)) {
  Write-Error "database.db não encontrado em $ProjectDir"
  exit 1
}

$backupDir = Join-Path $ProjectDir "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$dest = Join-Path $backupDir "database_$ts.db"
Copy-Item -Path $db -Destination $dest -Force

Write-Output "Backup criado: $dest"

