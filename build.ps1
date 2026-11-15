$start = Get-Location
Set-Location $PSScriptRoot

uv sync

uv run pyinstaller `
  --onefile --windowed --icon `
  ".\assets\sprites\logo.png" `
  --add-data ".\assets;assets" `
  ".\src\swappy_bird\__main__.py"
Move-Item -Force ".\dist\__main__.exe" ".\swappy_bird.exe"
Write-Host "Build complete. Executable is at $PSScriptRoot\swappy_bird.exe"

Set-Location $start
