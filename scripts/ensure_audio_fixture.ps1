$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path (Split-Path -Parent $projectRoot) "fleetbase-runtime"
$envFile = Join-Path $projectRoot ".env.fleetbase.local"
$waybill = "12345678"

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing local Fleetbase environment file: $envFile"
}

$settings = @{}
foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
        $settings[$matches[1]] = $matches[2].Trim('"', "'")
    }
}

$baseUrl = $settings["FLEETBASE_URL"]
$apiKey = $settings["FLEETBASE_API_KEY"]
if (-not $baseUrl -or -not $apiKey) {
    throw "FLEETBASE_URL and FLEETBASE_API_KEY must be configured"
}

$uri = [Uri]$baseUrl
if ($uri.Host -notin @("localhost", "127.0.0.1", "::1")) {
    throw "Refusing to seed a non-local Fleetbase instance: $($uri.Host)"
}

$lookupSql = "SELECT COUNT(*) FROM tracking_numbers WHERE tracking_number='$waybill';"
$existing = docker compose --project-directory $runtimeRoot exec -T database sh -lc `
    'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -N -e "$1"' `
    -- $lookupSql
if ($LASTEXITCODE -ne 0) {
    throw "Unable to check the local Fleetbase fixture"
}
if (($existing | Select-Object -Last 1).Trim() -eq "1") {
    Write-Output @{ waybill = $waybill; created = $false; status = "already_exists" }
    exit 0
}

$headers = @{ Authorization = "Bearer $apiKey"; Accept = "application/json" }
$body = @{
    pickup = @{
        name = "LiveKit audio test pickup"
        street1 = "1 Synthetic Test Street"
        latitude = 1.2966
        longitude = 103.8520
    }
    dropoff = @{
        name = "LiveKit audio test dropoff"
        street1 = "2 Synthetic Test Street"
        latitude = 1.3048
        longitude = 103.8318
    }
    meta = @{ source = "livekit-audio-simulation"; synthetic = $true }
    notes = "Synthetic local-only order for LiveKit audio regression"
} | ConvertTo-Json -Depth 6

$order = Invoke-RestMethod -Method Post -Uri "$($baseUrl.TrimEnd('/'))/v1/orders" `
    -Headers $headers -ContentType "application/json" -Body $body
$orderId = [string]$order.id
if ($orderId -notmatch '^order_[A-Za-z0-9]+$') {
    throw "Fleetbase returned an unexpected order id"
}

$renameSql = @"
START TRANSACTION;
UPDATE tracking_numbers t
JOIN orders o ON o.tracking_number_uuid=t.uuid
SET t.tracking_number='$waybill'
WHERE o.public_id='$orderId'
  AND JSON_UNQUOTE(JSON_EXTRACT(o.meta, '$.source'))='livekit-audio-simulation';
SELECT ROW_COUNT();
COMMIT;
"@
$updated = docker compose --project-directory $runtimeRoot exec -T database sh -lc `
    'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -N -e "$1"' `
    -- $renameSql
if ($LASTEXITCODE -ne 0 -or ($updated | Select-Object -Last 1).Trim() -ne "1") {
    throw "Created $orderId but failed to assign the synthetic tracking number"
}

Write-Output @{ waybill = $waybill; order_id = $orderId; created = $true; status = "ready" }
