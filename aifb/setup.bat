@echo off
REM 10-K Whisperer - Quick Setup Script
REM This script sets up the environment and runs the app

echo.
echo ============================================
echo 10-K Whisperer - Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

if exist venv (
    echo Step 1: Using existing virtual environment...
) else (
    echo Step 1: Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Step 3: Installing dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo IMPORTANT: Before running the app, set up your API key:
echo.
echo 1. Create or update the .env file in this folder
echo 2. Add your Google API key:
echo    - Get key from: https://makersuite.google.com/app/apikeys
echo    - Add GOOGLE_AI_API_KEY=your_key_here
echo    - Optional: add GOOGLE_MODEL=gemini-2.5-flash
echo 3. Save the .env file
echo.
echo Then run the app with:
echo    venv\Scripts\python.exe -m streamlit run app.py
echo.
echo Note: The first run may download the embedding model from Hugging Face.
echo.
pause
