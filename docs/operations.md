# Operational Guidance

## HTTP resilience configuration

The API layer uses a typed `HttpClient` with exponential backoff and jitter when communicating with the packaged FastAPI worker. The defaults are:

| Setting | Configuration key | Default |
| --- | --- | --- |
| Base address | `AIClient:BaseAddress` | `http://localhost:8088` |
| Request timeout | `AIClient:TimeoutSeconds` | `30` seconds |
| Maximum retries | `AIClient:RetryCount` | `3` attempts |
| Initial delay | `AIClient:RetryBaseDelaySeconds` | `1` second |

Retries use an exponential strategy with a small random jitter. Each retry attempt is logged with a warning similar to:

```
Retry 2/3 for http://localhost:8088/invoices/extract after 00:00:03.1234567. Reason: 503 (ServiceUnavailable)
```

Override the defaults by adding the following to `appsettings.Production.json` (or the environment of your choice):

```json
{
  "AIClient": {
    "BaseAddress": "http://inference-host:8088",
    "TimeoutSeconds": 60,
    "RetryCount": 5,
    "RetryBaseDelaySeconds": 1.5
  }
}
```

> The retry base delay is multiplied by `2^(attempt-1)` before a sub-second jitter is applied. A `RetryCount` of 5 with the default base delay yields waits of approximately 1s, 2s, 4s, 8s, and 16s.

## Windows watchdog for the FastAPI worker

A PowerShell installer is available at `dotnet/Watchdog/Install-AIInvoiceWatchdog.ps1` to keep the packaged FastAPI executable running on Windows hosts.

### Installation

1. Copy the FastAPI executable (for example `ai-invoice-service.exe`) to its target directory.
2. Open an elevated PowerShell prompt (`Run as administrator`).
3. Execute the installer, providing the executable path:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   .\Install-AIInvoiceWatchdog.ps1 -ExecutablePath "C:\Program Files\AIInvoice\ai-invoice-service.exe"
   ```

   Optional parameters:

   - `-TaskName` – Scheduled task name (default `AIInvoiceFastAPIWatchdog`).
   - `-CheckIntervalSeconds` – Polling interval; values below 5 seconds are coerced to 5.
   - `-LogDirectory` – Location for watchdog logs (default `%ProgramData%\AIInvoice\Logs`).
   - `-FirewallRuleName` – Base name for firewall rules.
   - `-Force` – Replace existing scheduled tasks and firewall rules if they already exist.

4. The script copies itself to `%ProgramData%\AIInvoice\AIInvoiceWatchdog.ps1`, creates inbound/outbound firewall rules for the executable, registers a SYSTEM-level scheduled task, and starts the watchdog immediately.

### What the watchdog does

- Monitors the process list for the specified executable every `CheckIntervalSeconds`.
- Restarts the executable if it is not running.
- Logs lifecycle events to `watchdog.log` inside the chosen log directory.
- Runs under the `SYSTEM` account with the highest privileges and has no execution time limit.

### Verifying the installation

Run the following commands from an elevated PowerShell session:

```powershell
Get-ScheduledTask -TaskName AIInvoiceFastAPIWatchdog | Format-List *
Get-NetFirewallRule -DisplayName "AIInvoice FastAPI*"
Get-Content "$env:ProgramData\AIInvoice\Logs\watchdog.log" -Tail 20
```

To update the executable path or other parameters, rerun the installer with `-Force`.

### Running the watchdog loop manually

For troubleshooting, the loop can be started in the foreground:

```powershell
.\Install-AIInvoiceWatchdog.ps1 -RunWatchdog -ExecutablePath "C:\Program Files\AIInvoice\ai-invoice-service.exe" -CheckIntervalSeconds 15
```

Press `Ctrl+C` to stop the foreground loop.
