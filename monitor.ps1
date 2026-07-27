param([string]$OutFile = "monitor_out.csv", [int]$IntervalSec = 5)

$out = Join-Path $PSScriptRoot $OutFile
"timestamp,cpu_pct,ram_used_mb,ram_total_mb,ram_pct,disk_write_kb_s" | Out-File $out -Encoding utf8

Write-Host "[monitor] Kayit basladi → $out  (Ctrl+C ile durdur)"

while ($true) {
    $ts      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    $cpu     = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average

    $os      = Get-CimInstance Win32_OperatingSystem
    $ramTotal = [math]::Round($os.TotalVisibleMemorySize / 1024, 0)
    $ramFree  = [math]::Round($os.FreePhysicalMemory / 1024, 0)
    $ramUsed  = $ramTotal - $ramFree
    $ramPct   = [math]::Round($ramUsed / $ramTotal * 100, 1)

    $diskW   = 0
    $disk    = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfDisk_PhysicalDisk -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -eq "_Total" }
    if ($disk) { $diskW = [math]::Round($disk.DiskWriteBytesPersec / 1024, 1) }

    "$ts,$cpu,$ramUsed,$ramTotal,$ramPct,$diskW" | Out-File $out -Append -Encoding utf8
    Write-Host "$ts  CPU:$cpu%  RAM:$ramUsed/$ramTotal MB ($ramPct%)  DiskW:$diskW KB/s"

    Start-Sleep -Seconds $IntervalSec
}
