# ===========================================
# Full Automated Test Suite with Logging
# ===========================================

chcp 65001 | Out-Null
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Timestamp for unique log names
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

Write-Host "=== Testing all API endpoints... $timestamp ==="

# Ensure logs folder exists
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# ======================================================
# 1️⃣ DICOM Test
# ======================================================
$dicom_log = "logs/dicom_result_$timestamp.json"
Write-Host "`n[1] Testing DICOM..."
curl.exe -s -F "file=@sample.dcm" http://192.168.29.86:8000/predict/dicom | Out-File -Encoding utf8 $dicom_log
Write-Host "✅ Saved: $dicom_log"

# ======================================================
# 2️⃣ X-RAY Test
# ======================================================
$xray_log = "logs/xray_result_$timestamp.json"
Write-Host "`n[2] Testing X-ray..."
curl.exe -s -F "file=@your_xray.jpg" http://192.168.29.86:8000/predict/xray | Out-File -Encoding utf8 $xray_log
Write-Host "✅ Saved: $xray_log"

# ======================================================
# 3️⃣ Lab Report Test
# ======================================================
$lab_log = "logs/lab_result_$timestamp.json"
Write-Host "`n[3] Testing Lab Report..."
curl.exe -s -F "file=@lab_photo.jpg" http://192.168.29.86:8000/predict/lab | Out-File -Encoding utf8 $lab_log
Write-Host "✅ Saved: $lab_log"

# ======================================================
# 4️⃣ Text Reasoning Test
# ======================================================
$text_log = "logs/text_result_$timestamp.json"
Write-Host "`n[4] Testing Text Reasoning..."
curl.exe -s -H "Content-Type: application/json" --data-binary "@text_input.json" http://192.168.29.86:8000/predict/text | Out-File -Encoding utf8 $text_log
Write-Host "✅ Saved: $text_log"

# ======================================================
# 5️⃣ Health Check
# ======================================================
$health_log = "logs/health_check_$timestamp.json"
Write-Host "`n[5] Checking API Health..."
curl.exe -s http://192.168.29.86:8000/health | Out-File -Encoding utf8 $health_log
Write-Host "✅ Saved: $health_log"

# ======================================================
Write-Host "`n✅ All tests executed successfully!"
Write-Host "Check logs in: logs/"


