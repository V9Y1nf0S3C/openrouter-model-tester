@echo off
:: Move to the folder where this script is located
cd /d "%~dp0"

:: Set the custom title for the Command Prompt window
title OpenRouter GUI

:: Run the python script
python gui.py

echo.
echo -----------------------------------
echo Process finished. Press any key to close...

:: Copy "Hello World" to the clipboard (equivalent to pbcopy)
:: echo Hello World | clip

:: Keep the window open until a key is pressed
pause >nul