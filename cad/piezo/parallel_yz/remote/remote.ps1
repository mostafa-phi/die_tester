<#
Drive the FE chain on the Linux compute host ("ssh compute", mlcuda2:
4 x Xeon 8280, 112 cores, 3 TB) from this Windows checkout.

    .\remote\remote.ps1 setup                 # once: micromamba env under ~/mostafa (10 min)
    .\remote\remote.ps1 up                    # sync this folder (sources, variants, no meshes)
    .\remote\remote.ps1 run r05 [-Threads 28] [-Sizes "0.70 0.55 0.45"] [-Solver gpu|pardiso]
    .\remote\remote.ps1 status r05            # tail the chain log
    .\remote\remote.ps1 fetch r05             # pull *.json, renders/, STEP/ back into variants/r05
    .\remote\remote.ps1 ssh                   # interactive shell in the remote folder

The host is shared: everything lives under ~/mostafa, each solve is capped at
-Threads MKL threads, nothing is installed system-wide.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("setup", "up", "run", "status", "fetch", "ssh")]
    [string]$Action,
    [Parameter(Position = 1)] [string]$Variant = "",
    [int]$Threads = 28,
    [string]$Sizes = "0.70 0.55",
    [ValidateSet("gpu", "pardiso")] [string]$Solver = "gpu",
    [string]$Host_ = "compute",
    [string]$Python = "C:\Users\$env:USERNAME\pythonEnvs\pic-env\Scripts\python.exe"
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSScriptRoot          # .../cad/piezo/parallel_yz
$remoteDir = "~/mostafa/die_tester/cad/piezo/parallel_yz"

function Remote([string]$cmd) { ssh -o BatchMode=yes $Host_ $cmd }

switch ($Action) {
    "setup" {
        scp -o BatchMode=yes "$PSScriptRoot\remote_env.sh" "${Host_}:~/mostafa/remote_env.sh"
        Remote "mkdir -p ~/mostafa && cd ~/mostafa && nohup bash remote_env.sh > env_install.log 2>&1 < /dev/null & echo launched; echo 'follow with: ssh compute tail -f ~/mostafa/env_install.log'"
    }
    "up" {
        # A zip, not tar: OneDrive marks directories read-only and Windows tar
        # records that as dr-xr-xr-x, which GNU tar then refuses to fill.
        $zip = Join-Path $env:TEMP "parallel_yz_sync.zip"
        & $Python "$PSScriptRoot\pack.py" $zip
        Remote "mkdir -p $remoteDir/.."
        scp -o BatchMode=yes $zip "${Host_}:/tmp/parallel_yz_sync.zip"
        Remote "cd $remoteDir/.. && python3 -m zipfile -e /tmp/parallel_yz_sync.zip . && rm /tmp/parallel_yz_sync.zip && du -sh parallel_yz"
    }
    "run" {
        if (-not $Variant) { throw "run needs a variant name" }
        Remote "cd $remoteDir && PIEZO_SOLVER=$Solver nohup bash remote/run_chain.sh $Variant $Threads $Sizes > /dev/null 2>&1 < /dev/null & echo launched $Variant with solver $Solver"
    }
    "status" {
        if (-not $Variant) { throw "status needs a variant name" }
        Remote "cd $remoteDir/variants/$Variant/work 2>/dev/null && cat chain.log && for f in static_h* modal_*; do echo --- `$f; grep -v 'parse tags' `$f 2>/dev/null | grep -v '^$' | tail -2; done; cat /proc/loadavg"
    }
    "fetch" {
        if (-not $Variant) { throw "fetch needs a variant name" }
        $dst = Join-Path $here "variants\$Variant"
        New-Item -ItemType Directory -Force $dst | Out-Null
        $zip = Join-Path $env:TEMP "parallel_yz_fetch.zip"
        Remote "cd $remoteDir/variants/$Variant && rm -f /tmp/parallel_yz_fetch.zip && python3 -m zipfile -c /tmp/parallel_yz_fetch.zip *.json renders STEP work/*.log"
        scp -o BatchMode=yes "${Host_}:/tmp/parallel_yz_fetch.zip" $zip
        Expand-Archive -Force $zip $dst
        Remove-Item $zip
        Get-ChildItem $dst -Recurse -File | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-2) } | Select-Object -ExpandProperty FullName
    }
    "ssh" { ssh -t $Host_ "cd $remoteDir && exec bash -l" }
}
