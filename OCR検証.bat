@echo off
cd /d %~dp0
if "%~1"=="" (
  echo PDFまたは画像ファイルをこのbatのアイコンにドラッグ＆ドロップしてください。
  pause
  exit /b
)
python paddle_test.py %1
pause
