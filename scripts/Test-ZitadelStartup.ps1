[CmdletBinding()]
param(
  [string]$ServiceLassoApiUrl = "http://127.0.0.1:18085",
  [string]$ZitadelUrl = "https://localhost:18084",
  [Parameter(Mandatory)]
  [string]$RootCaPath
)

$ErrorActionPreference = "Stop"
$ZitadelUrl = $ZitadelUrl.TrimEnd('/')
$RootCaPath = (Resolve-Path -LiteralPath $RootCaPath -ErrorAction Stop).Path

function Assert-Condition([bool]$Condition, [string]$Message) {
  if (-not $Condition) { throw $Message }
}

function Get-TrustedPage([string]$Uri, [string]$Description, [bool]$FollowRedirects = $false) {
  $bodyPath = [IO.Path]::GetTempFileName()
  try {
    $arguments = @('--ssl-no-revoke', '--cacert', $RootCaPath, '--silent', '--show-error', '--max-time', '15', '--output', $bodyPath, '--write-out', '%{http_code}|%{url_effective}')
    if ($FollowRedirects) { $arguments += @('--location', '--max-redirs', '3', '--cookie', '') }
    $result = & curl.exe @arguments $Uri
    Assert-Condition ($LASTEXITCODE -eq 0) "$Description failed TLS verification or could not be loaded."
    $parts = ([string]$result) -split '\|', 2
    Assert-Condition ($parts.Count -eq 2 -and $parts[0] -match '^\d{3}$') "$Description returned no HTTP status."
    return [pscustomobject]@{ Status = [int]$parts[0]; Url = [uri]$parts[1]; Body = [IO.File]::ReadAllText($bodyPath) }
  } finally {
    Remove-Item -LiteralPath $bodyPath -ErrorAction SilentlyContinue
  }
}

$serviceResponse = Invoke-RestMethod -Uri "$ServiceLassoApiUrl/api/services" -TimeoutSec 10
$zitadel = @($serviceResponse.services | Where-Object { $_.id -eq "zitadel" }) | Select-Object -First 1
Assert-Condition ($null -ne $zitadel) "Service Lasso did not discover the zitadel service."
Assert-Condition ($zitadel.lifecycle.running -eq $true) "ZITADEL is not running according to Service Lasso."
Assert-Condition ($zitadel.health.healthy -eq $true) "ZITADEL is not healthy according to Service Lasso."

$ready = Get-TrustedPage "$ZitadelUrl/debug/ready" "ZITADEL readiness"
Assert-Condition ($ready.Status -eq 200 -and $ready.Body.Trim().Trim('"') -eq "ok") "ZITADEL readiness did not return ok."
$http2Result = & node (Join-Path $PSScriptRoot "Test-ZitadelHttp2.mjs") $RootCaPath $ZitadelUrl
Assert-Condition ($LASTEXITCODE -eq 0) "ZITADEL did not serve readiness over trusted HTTP/2."
$http2 = $http2Result | ConvertFrom-Json
Assert-Condition ($http2.outcome -eq "verified" -and $http2.protocol -eq "h2") "ZITADEL HTTP/2 verification failed."

$discoveryPage = Get-TrustedPage "$ZitadelUrl/.well-known/openid-configuration" "ZITADEL OIDC discovery"
$discovery = $discoveryPage.Body | ConvertFrom-Json
Assert-Condition ($discoveryPage.Status -eq 200 -and $discovery.issuer -eq $ZitadelUrl) "OIDC discovery returned an unexpected issuer."
foreach ($property in @("authorization_endpoint", "token_endpoint", "jwks_uri")) {
  Assert-Condition (([string]$discovery.$property).StartsWith($ZitadelUrl + "/")) "OIDC discovery returned $property outside the expected local issuer."
}

$console = Get-TrustedPage "$ZitadelUrl/ui/console/" "ZITADEL console"
Assert-Condition ($console.Status -eq 200 -and $console.Body -match "<title>ZITADEL.*Management Console</title>" -and $console.Body -match "<cnsl-root") "ZITADEL console did not return its shell."
$mainScript = [regex]::Match($console.Body, '<script src="([^"]*main-[^"]+\.js)" type="module"></script>')
Assert-Condition ($mainScript.Success) "ZITADEL console shell has no module entrypoint."
$module = Get-TrustedPage ([uri]::new($console.Url, $mainScript.Groups[1].Value)).AbsoluteUri "ZITADEL console module"
Assert-Condition ($module.Status -eq 200 -and $module.Body.Length -gt 0) "ZITADEL console module is unavailable."

$environmentPage = Get-TrustedPage "$ZitadelUrl/ui/console/assets/environment.json" "ZITADEL console environment"
$consoleClientId = [string](($environmentPage.Body | ConvertFrom-Json).clientid)
Assert-Condition (-not [string]::IsNullOrWhiteSpace($consoleClientId)) "ZITADEL console environment has no client id."
$verifierBytes = [byte[]]::new(32); [Security.Cryptography.RandomNumberGenerator]::Fill($verifierBytes)
$challenge = [Convert]::ToBase64String([Security.Cryptography.SHA256]::HashData($verifierBytes)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$callback = [uri]::EscapeDataString("$ZitadelUrl/ui/console/auth/callback")
$authorizeUrl = "$ZitadelUrl/oauth/v2/authorize?client_id=$([uri]::EscapeDataString($consoleClientId))&redirect_uri=$callback&response_type=code&scope=openid&state=service-lasso-startup-smoke&code_challenge=$challenge&code_challenge_method=S256"
$login = Get-TrustedPage $authorizeUrl "ZITADEL console authorization" $true
Assert-Condition ($login.Status -eq 200 -and $login.Url.AbsolutePath -eq "/ui/login/login" -and $login.Body -match '<title>Welcome Back!</title>' -and $login.Body -match '<input') "ZITADEL authorization did not reach the Login V1 form."

[pscustomobject]@{ outcome = "verified"; checks = @("service-lasso-health", "zitadel-readiness", "trusted-http2", "oidc-discovery", "console-shell", "console-module", "authorization-login-form"); issuer = $discovery.issuer; console = "$ZitadelUrl/ui/console/"; loginPath = $login.Url.AbsolutePath } | ConvertTo-Json -Compress
