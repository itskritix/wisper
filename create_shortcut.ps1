$ws = New-Object -ComObject WScript.Shell
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = "$startup\Wisper.lnk"
$s = $ws.CreateShortcut($shortcutPath)
$s.TargetPath = "D:\Wisper\run_hidden.vbs"
$s.WorkingDirectory = "D:\Wisper"
$s.Description = "Wisper Speech to Text"
$s.Save()
Write-Host "Startup shortcut created at: $shortcutPath"
