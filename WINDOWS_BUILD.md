# Windows Build & Deployment Guide
## Chema Steel Weight Report

---

## What you will get

Running `build.bat` produces a single file:

```
installer_output\ChemaSteelWeightReport_Setup_v2.0.exe
```

Double-clicking this file on any Windows PC installs the app like any
professional program — Start Menu entry, Desktop shortcut, and an entry
in **"Add or Remove Programs"** for clean uninstallation.

---

## Prerequisites (do this once on the build PC)

### 1. Python 3.10+
Download from https://www.python.org/downloads/  
During installation: **tick "Add Python to PATH"** before clicking Install Now.

### 2. Inno Setup 6 (free)
Download from https://jrsoftware.org/isdl.php  
Run the installer — use all default options.

---

## Building the installer

1. Copy the entire project folder to your Windows PC (e.g. `C:\ChemaSteelApp\`)

2. Open **Command Prompt** and navigate to the folder:
   ```
   cd C:\ChemaSteelApp
   ```

3. Run the build script:
   ```
   build.bat
   ```

   The script will:
   - Install Python dependencies automatically
   - Build the exe with PyInstaller (~5-10 min first time)
   - Compile the Windows installer with Inno Setup

4. When complete you will see:
   ```
   installer_output\ChemaSteelWeightReport_Setup_v2.0.exe
   ```

---

## Installing on a target PC

1. Copy `ChemaSteelWeightReport_Setup_v2.0.exe` to the target PC
2. Double-click it and follow the wizard
3. The installer will:
   - Install the app to `C:\Program Files\Chema Steel Weight Report\`
   - Copy the database + logo to `C:\ProgramData\ChemaSteelWeightReport\data\`
   - Create a **Desktop shortcut**
   - Create a **Start Menu** entry
   - Register in **Add or Remove Programs**

---

## Where data is stored (after installation)

| Item | Location |
|------|----------|
| Application files | `C:\Program Files\Chema Steel Weight Report\` |
| Database (products, history, settings) | `C:\ProgramData\ChemaSteelWeightReport\data\steel_calculator.db` |
| Company logo | `C:\ProgramData\ChemaSteelWeightReport\data\chema_logo.jpeg` |
| Generated PDF reports | Wherever the user saves them (Desktop by default) |

> The database in `ProgramData` is shared across all Windows user accounts
> on the same machine and survives app updates.

---

## First-run configuration

Launch the app and go to **Administration -> Settings** to fill in:

| Setting | Value |
|---------|-------|
| Company Name | Chema Steel and Hardware Ltd |
| Company Address | Juja Town, Marga House, Ground Floor, Opposite Juja Police Station, Thika |
| Phone | 0700-095 362 / 0721-605 016 |
| Contacts Bar | Naomy: 0740 191281 / Nyambura: 0708 095662 / Wanjiku: 0707 043038 / Judy: 0743 699140 |
| Logo Path | Leave blank — auto-loaded from ProgramData |

The 297 steel products are already in the database from installation.

---

## Updating product weights later

1. Go to **Administration -> Product Master -> Import from Excel**
2. Select the updated inventory `.xlsx` file
3. Weights update immediately — no rebuild or reinstall needed

---

## Rebuilding after code changes

Just run `build.bat` again — it cleans the previous build automatically.
The new `Setup.exe` replaces the old one in `installer_output\`.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `python` not found in cmd | Re-install Python and tick "Add to PATH" |
| Inno Setup not found | Install from https://jrsoftware.org/isdl.php |
| App crashes on launch | Run `ChemaSteelWeightReport.exe` from cmd to see the error message |
| Logo missing from PDFs | Settings -> set Logo Path to `C:\ProgramData\ChemaSteelWeightReport\data\chema_logo.jpeg` |
| Database error | Delete `C:\ProgramData\ChemaSteelWeightReport\data\steel_calculator.db` and relaunch |
| Want to uninstall | Windows Settings -> Apps -> "Chema Steel Weight Report" -> Uninstall |
