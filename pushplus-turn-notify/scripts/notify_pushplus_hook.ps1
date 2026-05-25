param(
  [ValidateSet("completed", "review", "permission", "blocked")]
  [string] $Event = "permission",

  [string] $Summary = "Codex needs confirmation",

  [string] $SummaryZh,

  [string] $Details = "A Codex session is waiting for user approval to continue.",

  [string] $DetailsZh,

  [string] $WorkingDirectory = (Get-Location).Path,

  [switch] $DryRun
)

$ErrorActionPreference = "Stop"

function Join-CodePoints {
  param([int[]] $CodePoints)

  return -join ($CodePoints | ForEach-Object { [char] $_ })
}

if (-not $SummaryZh) {
  $SummaryZh = "Codex " + (Join-CodePoints @(0x9700, 0x8981, 0x786e, 0x8ba4))
}

if (-not $DetailsZh) {
  $DetailsZh = "Codex " + (Join-CodePoints @(0x4f1a, 0x8bdd, 0x6b63, 0x5728, 0x7b49, 0x5f85, 0x7528, 0x6237, 0x6279, 0x51c6, 0x4ee5, 0x7ee7, 0x7eed, 0x3002))
}

$scriptDir = Split-Path -Parent $PSCommandPath
$notifyScript = Join-Path $scriptDir "notify_pushplus_event.py"

if (-not (Test-Path -LiteralPath $notifyScript)) {
  throw "notify_pushplus_event.py not found at $notifyScript"
}

$pythonCommands = @(
  @{ Command = "python"; PrefixArgs = @() },
  @{ Command = "python3"; PrefixArgs = @() },
  @{ Command = "py"; PrefixArgs = @("-3") }
)

$conda = Get-Command conda -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conda) {
  try {
    $condaInfoRaw = & conda info --envs --json 2>$null
    if ($LASTEXITCODE -eq 0 -and $condaInfoRaw) {
      $condaInfo = $condaInfoRaw | ConvertFrom-Json
      foreach ($envPath in $condaInfo.envs) {
        if ((Split-Path -Leaf $envPath) -ne "py310") {
          continue
        }
        $pythonPath = Join-Path $envPath "python.exe"
        if (Test-Path -LiteralPath $pythonPath) {
          $pythonCommands += @{ Command = $pythonPath; PrefixArgs = @() }
        }
      }
    }
  } catch {
  }
}

foreach ($candidate in $pythonCommands) {
  $command = $candidate.Command
  $isAbsolute = [System.IO.Path]::IsPathRooted($command)
  if ($isAbsolute) {
    if (-not (Test-Path -LiteralPath $command)) {
      continue
    }
    $python = $command
  } else {
    $resolved = Get-Command $command -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $resolved) {
      continue
    }
    $python = $resolved.Source
  }

  $notifyArgs = @(
    $notifyScript,
    $Event,
    "--summary",
    $Summary,
    "--summary-zh",
    $SummaryZh,
    "--details",
    $Details,
    "--details-zh",
    $DetailsZh,
    "--pwd",
    $WorkingDirectory
  )
  if ($DryRun) {
    $notifyArgs += "--dry-run"
  }

  & $python @($candidate.PrefixArgs) @notifyArgs
  if ($LASTEXITCODE -eq 0) {
    exit 0
  }
}

throw "No usable Python interpreter found for PushPlus notification hook."
