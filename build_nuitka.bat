@echo off
echo ==========================================
echo Starting Naina AI Backend Build with Nuitka
echo ==========================================

:: Root se python/ folder me jao (jahan main.py hai)
cd /d "%~dp0"
cd python

:: Activate virtual environment
if exist "synapse_env\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "synapse_env\Scripts\activate.bat"
) else (
    echo Warning: Virtual environment not found at python\synapse_env
)

echo Installing Nuitka...
python -m pip install nuitka zstandard

echo Running Nuitka Build...
python -m nuitka --standalone ^
    --include-package=engine ^
    --include-module=uvicorn.logging ^
    --include-module=uvicorn.loops ^
    --include-module=uvicorn.loops.auto ^
    --include-module=uvicorn.protocols.http.auto ^
    --include-module=uvicorn.protocols.websockets.auto ^
    --include-module=uvicorn.lifespan.on ^
    --include-package=openwakeword ^
    --include-package=cv2 ^
    --include-package=pygame ^
    --include-package=pyaudio ^
    --include-package=colorama ^
    --include-package=ollama ^
    --include-package=thefuzz ^
    --include-package=ultralytics ^
    --include-package=insightface ^
    --include-data-dir=known_faces=known_faces ^
    --include-data-files=chat_history.db=chat_history.db ^
    --include-data-files=vision_pro.db=vision_pro.db ^
    --assume-yes-for-downloads ^
    --output-dir=build_naina ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Nuitka build failed!
    exit /b %ERRORLEVEL%
)

if exist "synapse_env\Scripts\activate.bat" (
    call deactivate
)

echo.
echo ==========================================
echo BACKEND BUILD COMPLETE!
echo Output: python\build_naina\main.dist\
echo ==========================================
pause