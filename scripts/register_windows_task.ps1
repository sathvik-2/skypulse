# PowerShell script to register daily automated pipeline run in Windows Task Scheduler
$TaskName = "NimbusFlowWeatherPipeline"
$Action = New-ScheduledTaskAction -Execute "D:\python_pipline_project\scripts\run_pipeline.bat"
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:00AM"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Write-Host "Registering Scheduled Task: $TaskName to run daily at 8:00 AM..." -ForegroundColor Cyan

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Daily Weather ETL Data Pipeline Ingestion" -Force

Write-Host "✅ Scheduled Task successfully registered in Windows Task Scheduler!" -ForegroundColor Green
Write-Host "To view or manage it, open 'Task Scheduler' from Windows Start menu." -ForegroundColor Yellow
