@echo off
echo ==========================================
echo Starting Naina AI Backend Build with Nuitka
echo ==========================================

cd /d "%~dp0"
cd python\engine

:: Activate virtual environment
if exist "..\synapse_env\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "..\synapse_env\Scripts\activate.bat"
) else (
    echo Warning: Virtual environment not found!
)

echo Installing Nuitka...
python -m pip install nuitka zstandard

echo Running Nuitka Build...
python -m nuitka --standalone ^
    --follow-imports ^
    --include-module=uvicorn.logging ^
    --include-module=uvicorn.loops ^
    --include-module=uvicorn.loops.auto ^
    --include-module=uvicorn.protocols.http.auto ^
    --include-module=uvicorn.protocols.websockets.auto ^
    --include-module=uvicorn.lifespan.on ^
    --include-package=openwakeword ^
    --include-package=cv2 ^
    --include-package-data=language_tags ^ REM New lines as you said
--include-data-dir=path\to\your\venv\Lib\site-packages\language_tags\data=language_tags\data
    --include-package=pygame ^
    --include-package=pyaudio ^
    --include-package=colorama ^
    --include-package=ollama ^
    --include-package=thefuzz ^
    --include-package=ultralytics ^
    --include-package=insightface ^
    --assume-yes-for-downloads ^
    --include-package=apscheduler ^
    --output-dir=build_naina ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Nuitka build failed!
    exit /b %ERRORLEVEL%
)

if exist "..\synapse_env\Scripts\activate.bat" (
    call deactivate
)

echo.
echo ==========================================
echo BACKEND BUILD COMPLETE!
echo Output: python\engine\build_naina\main.dist\
echo ==========================================
pause
tree /A