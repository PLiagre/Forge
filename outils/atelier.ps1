# Atelier de Citadelle-Guerre.
#   powershell -File outils/atelier.ps1 construire   # pipeline, vallée, scène
#   powershell -File outils/atelier.ps1 joueur       # construire + joueur Windows
#   powershell -File outils/atelier.ps1 mesurer      # joueur + mesure du jalon 1 + contre-épreuve
#   powershell -File outils/atelier.ps1 ouvrir       # ouvrir l'éditeur
param([Parameter(Mandatory)][ValidateSet('construire','joueur','mesurer','ouvrir')][string]$action,
      [int]$soldats = 10000)

$ErrorActionPreference = 'Stop'
$racine = Split-Path $PSScriptRoot -Parent
$projet = Join-Path $racine 'unity'
$unity = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'
$logs = Join-Path $racine 'sorties\logs'
New-Item -ItemType Directory -Force $logs | Out-Null

function Unity-Batch([string]$methode, [string]$nom) {
    $verrou = Join-Path $projet 'Temp\UnityLockfile'
    if ((Test-Path $verrou) -and -not (Get-Process Unity -ErrorAction SilentlyContinue)) { Remove-Item $verrou -Force }
    $log = Join-Path $logs "$nom.log"
    $p = Start-Process $unity -ArgumentList @('-batchmode','-quit','-projectPath',"`"$projet`"",'-executeMethod',$methode,'-logFile',"`"$log`"") -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { Write-Host "Échec de Unity ($($p.ExitCode)). Journal : $log"; Select-String -Path $log -Pattern 'error CS|Exception|\[Construire\]' | Select-Object -First 30 | ForEach-Object { $_.Line }; exit 1 }
    Select-String -Path $log -Pattern '\[Construire\]' | ForEach-Object { $_.Line }
}

function Mesurer([string]$dossier, [string[]]$extra) {
    $exe = Join-Path $racine 'sorties\joueur\Citadelle-Guerre.exe'
    $arguments = @('-screen-width','1920','-screen-height','1080','-screen-fullscreen','0','-guerre-mesure','-guerre-sortie',"`"$dossier`"",'-guerre-soldats',"$soldats",'-logFile',"`"$dossier\joueur.log`"") + $extra
    if (Test-Path $dossier) { Remove-Item $dossier -Recurse -Force }
    New-Item -ItemType Directory -Force $dossier | Out-Null
    $p = Start-Process $exe -ArgumentList $arguments -Wait -PassThru
    $rapport = Join-Path $dossier 'mesure.json'
    if (-not (Test-Path $rapport)) { Write-Host "Pas de rapport : $dossier\joueur.log"; return $null }
    return (Get-Content $rapport -Raw -Encoding utf8 | ConvertFrom-Json)
}

switch ($action) {
    'ouvrir'     { Start-Process $unity -ArgumentList @('-projectPath',"`"$projet`"") }
    'construire' { Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire' }
    'joueur'     { Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire'; Unity-Batch 'Guerre.EditeurOutils.Construire.Joueur' 'joueur' }
    'mesurer' {
        Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire'; Unity-Batch 'Guerre.EditeurOutils.Construire.Joueur' 'joueur'
        $r = Mesurer (Join-Path $racine 'sorties\mesure') @()
        if ($null -eq $r) { exit 1 }
        $r.vues | ForEach-Object { '{0,-22} p95 {1,6:N2} ms  médiane {2,6:N2} ms  {3,6:N0} i/s' -f $_.nom, $_.p95_ms, $_.mediane_ms, $_.fps_moyen }
        "soldats {0}/{1}, déplacement moyen {2:N1} m, pixels changés par les soldats {3:P1}" -f $r.soldats_presents, $r.soldats_demandes, $r.deplacement_moyen_m, $r.pixels_changes_par_les_soldats
        "statut : $($r.statut) $($r.motifs -join ' | ')"
        # Une mesure qui ne peut pas échouer ne prouve rien : un soldat retiré doit la faire rougir.
        $s = Mesurer (Join-Path $racine 'sorties\mesure-sabotage') @('-guerre-sabotage')
        if ($null -eq $s -or $s.statut -ne 'echec') { Write-Host 'La contre-épreuve n''a pas échoué : la mesure ne prouve rien.'; exit 1 }
        "contre-épreuve : échec attendu obtenu ($($s.motifs -join ' | '))"
        if ($r.statut -ne 'valide') { exit 1 }
    }
}
