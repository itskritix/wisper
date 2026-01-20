' Wisper Launcher - Runs without console window
' Double-click this file or create a shortcut to it

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Wisper"
WshShell.Run "D:\Wisper\venv\Scripts\pythonw.exe main.py", 0, False
