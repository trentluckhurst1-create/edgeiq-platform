param(
    [string]$BaseUrl = "http://127.0.0.1:4173/?dev-bypass=1",
    [string]$OutputDir = "",
    [string]$PassLabel = "before",
    [int]$DebugPort = 9223,
    [int]$SettleMilliseconds = 2600
)

$ErrorActionPreference = "Stop"

function Get-EdgePath {
    $candidates = @(
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Microsoft Edge not found."
}

function Receive-CdpMessage {
    param([System.Net.WebSockets.ClientWebSocket]$Socket)

    $buffer = New-Object byte[] 8192
    $segment = [System.ArraySegment[byte]]::new($buffer)
    $stream = New-Object System.IO.MemoryStream

    while ($true) {
        $result = $Socket.ReceiveAsync($segment, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult()
        if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
            throw "CDP socket closed unexpectedly."
        }
        $stream.Write($buffer, 0, $result.Count)
        if ($result.EndOfMessage) {
            break
        }
    }

    $json = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
    $stream.Dispose()
    return $json | ConvertFrom-Json
}

function Send-CdpCommand {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [int]$Id,
        [string]$Method,
        [hashtable]$Params
    )

    $payload = @{
        id     = $Id
        method = $Method
        params = $Params
    } | ConvertTo-Json -Depth 50 -Compress

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $segment = [System.ArraySegment[byte]]::new($bytes)
    $Socket.SendAsync(
        $segment,
        [System.Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()
}

function Invoke-Cdp {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [ref]$NextId,
        [string]$Method,
        [hashtable]$Params
    )

    $id = $NextId.Value
    $NextId.Value = $id + 1
    Send-CdpCommand -Socket $Socket -Id $id -Method $Method -Params $Params

    while ($true) {
        $message = Receive-CdpMessage -Socket $Socket
        if ($null -ne $message.id -and [int]$message.id -eq $id) {
            return $message
        }
    }
}

function Wait-HttpJson {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri $Url -TimeoutSec 5
            if ($response) {
                return $response
            }
        } catch {
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Timed out waiting for $Url"
}

function Wait-ReadyState {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [ref]$NextId,
        [int]$TimeoutSeconds = 15
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $result = Invoke-Cdp -Socket $Socket -NextId $NextId -Method "Runtime.evaluate" -Params @{
            expression    = "document.readyState"
            returnByValue = $true
            awaitPromise  = $true
        }
        if ($result.result.result.value -eq "complete") {
            return
        }
        Start-Sleep -Milliseconds 400
    }
}

function Wait-ForDataHydration {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [ref]$NextId,
        [int]$Milliseconds
    )

    Start-Sleep -Milliseconds $Milliseconds

    [void](Invoke-Cdp -Socket $Socket -NextId $NextId -Method "Runtime.evaluate" -Params @{
        expression    = @"
(async () => {
  await new Promise((resolve) => setTimeout(resolve, $Milliseconds));
  return document.body ? document.body.innerText.length : 0;
})();
"@
        returnByValue = $true
        awaitPromise  = $true
    })
}

function Set-ActiveTab {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [ref]$NextId,
        [string]$TabName,
        [int]$Milliseconds
    )

    $expression = @"
localStorage.setItem('edgeiq_active_tab', '$TabName');
location.reload();
'$TabName';
"@

    [void](Invoke-Cdp -Socket $Socket -NextId $NextId -Method "Runtime.evaluate" -Params @{
        expression    = $expression
        returnByValue = $true
        awaitPromise  = $true
    })

    Start-Sleep -Milliseconds 1200
    Wait-ReadyState -Socket $Socket -NextId $NextId
    Wait-ForDataHydration -Socket $Socket -NextId $NextId -Milliseconds $Milliseconds
}

function Capture-Png {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [ref]$NextId,
        [string]$Path
    )

    $shot = Invoke-Cdp -Socket $Socket -NextId $NextId -Method "Page.captureScreenshot" -Params @{
        format      = "png"
        fromSurface = $true
    }
    $bytes = [Convert]::FromBase64String($shot.result.data)
    [System.IO.File]::WriteAllBytes($Path, $bytes)
}

function Capture-TextSnapshot {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [ref]$NextId,
        [string]$Path
    )

    $text = Invoke-Cdp -Socket $Socket -NextId $NextId -Method "Runtime.evaluate" -Params @{
        expression    = "document.body ? document.body.innerText.slice(0, 16000) : ''"
        returnByValue = $true
        awaitPromise  = $true
    }
    $value = [string]($text.result.result.value)
    Set-Content -Path $Path -Value $value -Encoding UTF8
}

if (-not $OutputDir) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmm"
    $OutputDir = Join-Path (Join-Path (Join-Path $PSScriptRoot "..\outputs\ui_audit") "racing_dashboard_$stamp") $PassLabel
} else {
    $OutputDir = Join-Path $OutputDir $PassLabel
}

$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$edgePath = Get-EdgePath
$profileDir = Join-Path $env:TEMP ("edgeiq-racing-cdp-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $profileDir -Force | Out-Null

$edgeArgs = @(
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--window-size=1600,1200",
    "--remote-debugging-port=$DebugPort",
    "--user-data-dir=$profileDir",
    $BaseUrl
)

$edgeProc = Start-Process -FilePath $edgePath -ArgumentList $edgeArgs -PassThru -WindowStyle Hidden

try {
    $targets = Wait-HttpJson -Url "http://127.0.0.1:$DebugPort/json/list" -TimeoutSeconds 20
    $pageTarget = $targets | Where-Object { $_.type -eq "page" -and $_.url -like "$BaseUrl*" } | Select-Object -First 1
    if (-not $pageTarget) {
        throw "No page target found for $BaseUrl"
    }

    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    $socket.ConnectAsync([Uri]$pageTarget.webSocketDebuggerUrl, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $nextId = 1

    [void](Invoke-Cdp -Socket $socket -NextId ([ref]$nextId) -Method "Page.enable" -Params @{})
    [void](Invoke-Cdp -Socket $socket -NextId ([ref]$nextId) -Method "Runtime.enable" -Params @{})
    Wait-ReadyState -Socket $socket -NextId ([ref]$nextId)
    Wait-ForDataHydration -Socket $socket -NextId ([ref]$nextId) -Milliseconds $SettleMilliseconds

    $tabs = @("OVERVIEW", "INTELLIGENCE", "MARKET", "TRACKING", "RESULTS")
    foreach ($tab in $tabs) {
        Set-ActiveTab -Socket $socket -NextId ([ref]$nextId) -TabName $tab -Milliseconds $SettleMilliseconds
        $prefix = "{0}_{1}" -f ([array]::IndexOf($tabs, $tab) + 1).ToString("00"), $tab.ToLower()
        Capture-Png -Socket $socket -NextId ([ref]$nextId) -Path (Join-Path $OutputDir "$prefix.png")
        Capture-TextSnapshot -Socket $socket -NextId ([ref]$nextId) -Path (Join-Path $OutputDir "$prefix.txt")
    }

    $socket.Dispose()
    Write-Output $OutputDir
}
finally {
    if ($edgeProc -and -not $edgeProc.HasExited) {
        Stop-Process -Id $edgeProc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -Path $profileDir -Recurse -Force -ErrorAction SilentlyContinue
}
