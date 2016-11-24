// Copyright (c) 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

$myPath = Split-Path $MyInvocation.MyCommand.Path -Parent

function GetEnvVar([string] $key, [scriptblock] $defaultFn) {
    if (Test-Path "Env:\$key") {
        return Get-ChildItem $Env $key
    }
    return $defaultFn.Invoke()
}

$cipdClientVer = GetEnvVar "CIPD_CLIENT_VER" { Get-Content (Join-Path $myPath -ChildPath 'cipd_client_version') -First 1 }
$cipdClientSrv = GetEnvVar "CIPD_CLIENT_SRV" { "https://chrome-infra-packages.appspot.com" }

$plat="windows"
$arch="amd64"

$url = "$cipdClientSrv/client?platform=$plat-$arch&version=$cipdClientVer"
$client = Join-Path $myPath -ChildPath ".cipd_client.exe"

if (!(Test-Path $client)) {
    echo "Bootstrapping cipd client for $plat-$arch..."
    echo "From $url"
    # TODO(iannucci): It would be really nice if there was a way to get this to
    # show progress without also completely destroying the download speed, but
    # I can't seem to find a way to do it. Patches welcome :)
    (New-Object System.Net.WebClient).DownloadFile($url, $client)
}

if ({& $client selfupdate -version "$cipdClientVer"} -ne 0) {
    Write-Host "selfupdate failed: " -ForegroundColor Red -NoNewline
    Write-Host "run ``$client selfupdate -version $cipdClientVer`` to diagnose`n" -ForegroundColor White
}

& $client @args
exit $LASTEXITCODE
