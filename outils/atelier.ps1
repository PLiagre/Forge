# Atelier de Citadelle-Guerre.
#   powershell -File outils/atelier.ps1 construire   # pipeline, vallée, scène
#   powershell -File outils/atelier.ps1 joueur       # construire + joueur Windows
#   powershell -File outils/atelier.ps1 mesurer      # joueur + preuves des jalons 1 et 2, avec leurs contre-épreuves
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

# Le joueur compilé, lancé avec un mode d'essai ; renvoie son rapport JSON.
function Lancer([string]$dossier, [string[]]$extra, [string]$fichier) {
    $exe = Join-Path $racine 'sorties\joueur\Citadelle-Guerre.exe'
    $arguments = @('-screen-width','1920','-screen-height','1080','-screen-fullscreen','0','-guerre-sortie',"`"$dossier`"",'-guerre-soldats',"$soldats",'-logFile',"`"$dossier\joueur.log`"") + $extra
    if (Test-Path $dossier) { Remove-Item $dossier -Recurse -Force }
    New-Item -ItemType Directory -Force $dossier | Out-Null
    Start-Process $exe -ArgumentList $arguments -Wait | Out-Null
    $rapport = Join-Path $dossier $fichier
    if (-not (Test-Path $rapport)) { Write-Host "Pas de rapport : $dossier\joueur.log"; return $null }
    return (Get-Content $rapport -Raw -Encoding utf8 | ConvertFrom-Json)
}

switch ($action) {
    'ouvrir'     { Start-Process $unity -ArgumentList @('-projectPath',"`"$projet`"") }
    'construire' { Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire' }
    'joueur'     { Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire'; Unity-Batch 'Guerre.EditeurOutils.Construire.Joueur' 'joueur' }
    'mesurer' {
        Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire'; Unity-Batch 'Guerre.EditeurOutils.Construire.Joueur' 'joueur'
        $echecs = 0

        # Jalon 1 : la foule, à 60 images/s.
        $r = Lancer (Join-Path $racine 'sorties\mesure') @('-guerre-mesure') 'mesure.json'
        if ($null -eq $r) { exit 1 }
        $r.vues | ForEach-Object { '{0,-22} p95 {1,6:N2} ms  médiane {2,6:N2} ms  {3,6:N0} i/s' -f $_.nom, $_.p95_ms, $_.mediane_ms, $_.fps_moyen }
        "soldats {0}/{1}, déplacement moyen {2:N1} m, pixels changés par les soldats {3:P1}" -f $r.soldats_presents, $r.soldats_demandes, $r.deplacement_moyen_m, $r.pixels_changes_par_les_soldats
        "jalon 1 : $($r.statut) $($r.motifs -join ' | ')"
        if ($r.statut -ne 'valide') { $echecs++ }
        # Une preuve qui ne peut pas échouer ne prouve rien : un soldat retiré doit la faire rougir.
        $s = Lancer (Join-Path $racine 'sorties\mesure-sabotage') @('-guerre-mesure','-guerre-sabotage') 'mesure.json'
        if ($null -eq $s -or $s.statut -ne 'echec') { Write-Host 'La contre-épreuve du jalon 1 n''a pas échoué : la mesure ne prouve rien.'; $echecs++ }
        else { "contre-épreuve 1 : échec attendu obtenu ($($s.motifs -join ' | '))" }

        # Jalon 2 : les ordres et les corps.
        $o = Lancer (Join-Path $racine 'sorties\essai-ordres') @('-guerre-essai-ordres') 'essai-ordres.json'
        if ($null -eq $o) { exit 1 }
        $o.formations | ForEach-Object { '{0} files : front {1:N1} m pour {2:N1} m, {3:P0} à leur place, {4:N0} s' -f $_.files, $_.largeur_mesuree, $_.largeur_attendue, $_.a_sa_place, $_.secondes }
        'obstacle : {0:P0} passés au travers, distance minimale {1:N2} m' -f $o.obstacle.traversee_max, $o.obstacle.distance_min_m
        "jalon 2 : $($o.statut) $($o.motifs -join ' | ')"
        if ($o.statut -ne 'valide') { $echecs++ }
        $oc = Lancer (Join-Path $racine 'sorties\essai-ordres-sans-corps') @('-guerre-essai-ordres','-guerre-sans-corps') 'essai-ordres.json'
        if ($null -eq $oc -or $oc.statut -ne 'echec') { Write-Host 'Sans les corps, l''essai des ordres n''a pas échoué : il ne prouve rien.'; $echecs++ }
        else { "contre-épreuve 2 (sans les corps) : échec attendu obtenu ($($oc.motifs -join ' | '))" }

        if ($echecs -gt 0) { exit 1 }
    }
}
