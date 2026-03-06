param(
  [string]$ProjectDir = ".",
  [string]$PythonExe = "python",
  [string]$TaskName = "MonitorFiscalNCM",
  [string]$DailyAt = "08:00"
)

$action = New-ScheduledTaskAction -Execute $PythonExe -Argument "monitor_fiscal.py" -WorkingDirectory (Resolve-Path $ProjectDir)
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Executa monitor fiscal de NCM diariamente"

Write-Output "Tarefa '$TaskName' registrada para $DailyAt"

