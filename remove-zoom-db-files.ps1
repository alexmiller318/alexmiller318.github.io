<#
.SYNOPSIS
Removes Zoom data files whose extensions contain "db" from the user's roaming profile.

.DESCRIPTION
Locates the Zoom folder inside the current user's roaming AppData directory and deletes any files with
"db" in their extension (for example .db, .db-wal, .db-journal). Outputs progress messages to indicate
what was removed and if no matching files are found.
#>

$zoomPath = Join-Path $env:APPDATA 'Zoom'

if (-not (Test-Path -Path $zoomPath -PathType Container)) {
    Write-Host "Zoom roaming folder not found at '$zoomPath'. Nothing to clean."
    exit 0
}

$targets = Get-ChildItem -Path $zoomPath -File -Recurse |
    Where-Object { $_.Extension -like '*db*' }

if (-not $targets) {
    Write-Host "No files with 'db' in the extension were found in '$zoomPath'."
    exit 0
}

foreach ($file in $targets) {
    Write-Host "Deleting $($file.FullName)"
    Remove-Item -LiteralPath $file.FullName -Force
}

Write-Host "Deleted $($targets.Count) file(s) with 'db' in the extension from '$zoomPath'."
