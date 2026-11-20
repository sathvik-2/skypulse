@echo off
REM ============================================================
REM NimbusFlow Automated Pipeline Batch Runner for Windows
REM ============================================================

cd /d "D:\python_pipline_project"

echo ============================================================ >> logs\scheduler.log
echo [SCHEDULED RUN] %DATE% %TIME% >> logs\scheduler.log
echo ============================================================ >> logs\scheduler.log

python run_pipeline.py >> logs\scheduler.log 2>&1

echo [COMPLETED] Exit Code: %ERRORLEVEL% >> logs\scheduler.log
