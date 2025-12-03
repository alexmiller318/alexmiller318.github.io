# Utilities

## remove-zoom-db-files.ps1
Use this PowerShell script to delete Zoom data files whose extensions include `db` from the current user's roaming
AppData directory.

### Usage
1. Open PowerShell.
2. Navigate to the folder containing `remove-zoom-db-files.ps1`.
3. Run the script:
   ```powershell
   .\remove-zoom-db-files.ps1
   ```

The script will report whether the Zoom folder was found and list each file it deletes. Files are removed from
`$env:APPDATA\Zoom` and matching is limited to extensions that contain `db` (for example `.db`, `.db-wal`, `.db-journal`).
