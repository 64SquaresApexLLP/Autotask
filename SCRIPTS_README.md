# AutoTask — Scripts Reference

This document covers all `.bat` and `.ps1` scripts in the project root.

---

## Overview

| Script | Type | Purpose |
|---|---|---|
| `start_app.bat` | BAT | Quick-start both services in separate terminal windows |
| `run_backend.bat` | BAT | Start the backend server only |
| `run_frontend.bat` | BAT | Start the frontend preview server only |
| `install_services.ps1` | PowerShell | Install backend + frontend as persistent Windows Services (auto-start on boot) |
| `uninstall_services.ps1` | PowerShell | Remove the Windows Services created by `install_services.ps1` |

---

## BAT Scripts

### `start_app.bat` — Quick Start

Launches both the backend and frontend in **separate CMD windows**. No installation required — just double-click or run from a terminal.

```bat
start_app.bat
```

**What it does:**
1. Starts the FastAPI backend (uvicorn) on port **8001**
2. Runs `npm run build` then starts the Vite preview server on port **5173**

**Access the app:**
- Backend API: `http://13.202.236.112:8001`
- Frontend: `http://13.202.236.112:5173`

> **Note:** Closing either terminal window stops that service. This method does not survive reboots. Use `install_services.ps1` for a permanent setup.

---

### `run_backend.bat` — Backend Only

Starts only the FastAPI/uvicorn backend server.

```bat
run_backend.bat
```

- Serves on `0.0.0.0:8001`
- Uses the project's `.venv` Python environment

---

### `run_frontend.bat` — Frontend Only

Starts only the Vite preview server for the built frontend.

```bat
run_frontend.bat
```

- Serves on `0.0.0.0:5173`
- Runs `vite preview` from the local `node_modules` — requires `npm run build` to have been run first

---

## PowerShell Scripts

> **All PowerShell scripts must be run as Administrator.**
> Right-click PowerShell → "Run as Administrator", then navigate to the project root.

---

### `install_services.ps1` — Install Windows Services

Registers the backend and frontend as **Windows Services** using [NSSM (Non-Sucking Service Manager)](https://nssm.cc). Services are configured to:

- Start automatically on system boot
- Restart automatically on crash
- Write logs to `C:\Autotask\Autotask\logs\`

```powershell
.\install_services.ps1
```

**What it does, step by step:**

1. **Downloads NSSM** automatically if not present at `C:\nssm\nssm.exe`
2. **Checks prerequisites** — Python venv, uvicorn, Node.js, and npm must all be available
3. **Builds the frontend** — runs `npm install` and `npm run build` in the `frontend/` directory
4. **Creates `logs/`** directory at the project root
5. **Installs `AutoTaskBackend` service** — runs uvicorn on port 8001
6. **Installs `AutoTaskFrontend` service** — runs `vite preview` on port 5173
7. **Starts both services** and prints their status

**Services installed:**

| Service Name | Executable | Port | Log File |
|---|---|---|---|
| `AutoTaskBackend` | `.venv\Scripts\uvicorn.exe` | 8001 | `logs\backend.log` |
| `AutoTaskFrontend` | `frontend\node_modules\.bin\vite.cmd` | 5173 | `logs\frontend.log` |

**Prerequisites before running:**

```powershell
# Create the Python virtual environment
python -m venv .venv

# Install Python dependencies
.venv\Scripts\pip install -r requirements.txt

# Ensure uvicorn is installed
.venv\Scripts\pip install "uvicorn[standard]"
```

Node.js and npm must also be installed and available in `PATH`.

**Managing services after installation:**

```powershell
# Check status
Get-Service AutoTaskBackend, AutoTaskFrontend

# Stop services
Stop-Service AutoTaskBackend
Stop-Service AutoTaskFrontend

# Start services
Start-Service AutoTaskBackend
Start-Service AutoTaskFrontend

# Remove services
.\uninstall_services.ps1
```

---

### `uninstall_services.ps1` — Remove Windows Services

Stops and removes the `AutoTaskBackend` and `AutoTaskFrontend` Windows Services.

```powershell
.\uninstall_services.ps1
```

**What it does:**
- Iterates over both service names
- Stops each service if running
- Removes each service via NSSM

> This does **not** delete any project files, logs, or the NSSM binary — only the service registrations are removed.

---

## Quick Decision Guide

```
Need to test quickly?
  → start_app.bat

Want the app to survive reboots and auto-restart on crashes?
  → install_services.ps1  (run as Administrator)

Want to remove the permanent services?
  → uninstall_services.ps1  (run as Administrator)
```
