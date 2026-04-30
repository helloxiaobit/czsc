@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "APP_FILE=%ROOT_DIR%examples\recursive_multi_level_app.py"

if not exist "%APP_FILE%" (
  echo Cannot find app file: %APP_FILE%
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Please install Python and make it available in PATH.
  exit /b 1
)

python -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('streamlit') else 1)" >nul 2>nul
if errorlevel 1 (
  echo Streamlit not installed. Installing from pip...
  python -m pip install -U streamlit
  if errorlevel 1 (
    echo pip install streamlit failed. Please run: python -m pip install -U streamlit
    exit /b 1
  )
)

cd /d "%ROOT_DIR%"
python -m streamlit run examples\recursive_multi_level_app.py --server.port 8501
if errorlevel 1 (
  echo App failed to start. Common fix: python -m pip install -r requirements.txt
  exit /b 1
)

endlocal
