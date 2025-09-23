param(
  [string]$ExePath = "C:\ai\ai_invoice_api.exe",
  [string]$HealthUrl = "http://127.0.0.1:8088/health",
  [int]$CheckEverySec = 30
)

Function Test-Health {
  try { (Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 }
  catch { $false }
}

Write-Host "AI Watchdog starting..."
while ($true) {
  if (-not (Test-Health)) {
    Write-Host "Health failed. Starting service..."
    Start-Process -FilePath $ExePath -WindowStyle Hidden
    Start-Sleep -Seconds 5
  }
  Start-Sleep -Seconds $CheckEverySec
}
