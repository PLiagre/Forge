# Atelier de Citadelle-Guerre.
#   powershell -File outils/atelier.ps1 soldats      # fabriquer les soldats dans Blender (fabrique/sorties)
#   powershell -File outils/atelier.ps1 construire   # soldats, pipeline, vallée, scène
#   powershell -File outils/atelier.ps1 joueur       # construire + joueur Windows
#   powershell -File outils/atelier.ps1 mesurer      # joueur + preuves des jalons 1 à 4, avec leurs contre-épreuves
#   powershell -File outils/atelier.ps1 ouvrir       # ouvrir l'éditeur
param([Parameter(Mandatory)][ValidateSet('soldats','construire','joueur','mesurer','ouvrir')][string]$action,
      [int]$soldats = 10000)

$ErrorActionPreference = 'Stop'
$racine = Split-Path $PSScriptRoot -Parent
$projet = Join-Path $racine 'unity'
$unity = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
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

# Les soldats : modelés, posés et cuits par Blender, sans interface.
function Soldats {
    $sortie = Join-Path $racine 'fabrique\sorties'
    $log = Join-Path $logs 'soldats.log'
    $p = Start-Process $blender -ArgumentList @('-b','--python-exit-code','1','--python',"`"$racine\fabrique\soldats.py`"",'--',"`"$sortie`"") -Wait -PassThru -NoNewWindow -RedirectStandardOutput $log
    if ($p.ExitCode -ne 0) { Write-Host "Échec de Blender. Journal : $log"; exit 1 }
    Select-String -Path $log -Pattern '\[Soldats\]' | ForEach-Object { $_.Line }
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
    'soldats'    { Soldats }
    'construire' { Soldats; Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire' }
    'joueur'     { Soldats; Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire'; Unity-Batch 'Guerre.EditeurOutils.Construire.Joueur' 'joueur' }
    'mesurer' {
        Soldats; Unity-Batch 'Guerre.EditeurOutils.Construire.Tout' 'construire'; Unity-Batch 'Guerre.EditeurOutils.Construire.Joueur' 'joueur'
        $echecs = 0

        # Jalons 1 et 3 : la foule animée, à 60 images/s.
        $r = Lancer (Join-Path $racine 'sorties\mesure') @('-guerre-mesure') 'mesure.json'
        if ($null -eq $r) { exit 1 }
        $r.vues | ForEach-Object { '{0,-22} p95 {1,6:N2} ms  médiane {2,6:N2} ms  {3,6:N0} i/s' -f $_.nom, $_.p95_ms, $_.mediane_ms, $_.fps_moyen }
        "soldats {0}/{1}, déplacement moyen {2:N1} m, pixels changés par les soldats {3:P1}, par l'animation {4:P2}, triangles par soldat {5}" -f $r.soldats_presents, $r.soldats_demandes, $r.deplacement_moyen_m, $r.pixels_changes_par_les_soldats, $r.pixels_changes_par_l_animation, ($r.triangles_par_soldat -join '/')
        "jalons 1 et 3 : $($r.statut) $($r.motifs -join ' | ')"
        if ($r.statut -ne 'valide') { $echecs++ }
        # Une preuve qui ne peut pas échouer ne prouve rien : un soldat retiré doit la faire rougir.
        $s = Lancer (Join-Path $racine 'sorties\mesure-sabotage') @('-guerre-mesure','-guerre-sabotage') 'mesure.json'
        if ($null -eq $s -or $s.statut -ne 'echec') { Write-Host 'La contre-épreuve du jalon 1 n''a pas échoué : la mesure ne prouve rien.'; $echecs++ }
        else { "contre-épreuve 1 : échec attendu obtenu ($($s.motifs -join ' | '))" }
        # Le shader privé de son animation cuite : la preuve de l'animation doit rougir.
        $a = Lancer (Join-Path $racine 'sorties\mesure-sans-animation') @('-guerre-mesure','-guerre-sans-animation') 'mesure.json'
        if ($null -eq $a -or $a.soldats_animes) { Write-Host 'Sans animation, la preuve de l''animation n''a pas échoué : elle ne prouve rien.'; $echecs++ }
        else { "contre-épreuve 3 (sans animation) : échec attendu obtenu ($($a.motifs -join ' | '))" }

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

        # Jalon 4 : la mêlée. Le plus profond doit repousser l'autre, dans les deux sens.
        $m = Lancer (Join-Path $racine 'sorties\essai-melee') @('-guerre-essai-melee') 'essai-melee.json'
        if ($null -eq $m) { exit 1 }
        $m.duels | ForEach-Object { '{0,-16} {1} contre {2} rangs : ligne {3,6:N1} m, morts {4}/{5}, contact max {6}, ennemis à {7:N2} m au plus près, fatigue {8:P0}' -f $_.nom, $_.rangs_bleus, $_.rangs_rouges, $_.recul_de_la_ligne_m, $_.morts_bleus, $_.morts_rouges, $_.contacts_max, $_.distance_min_ennemis_m, $_.fatigue_moyenne }
        "jalon 4 : $($m.statut) $($m.motifs -join ' | ')"
        if ($m.statut -ne 'valide') { $echecs++ }
        # Si les rangs arrière ne poussent plus, la profondeur ne doit plus rien donner.
        $mc = Lancer (Join-Path $racine 'sorties\essai-melee-sans-poussee') @('-guerre-essai-melee','-guerre-sans-poussee') 'essai-melee.json'
        if ($null -eq $mc -or $mc.statut -ne 'echec') { Write-Host 'Sans la poussée des rangs arrière, l''essai de mêlée n''a pas échoué : il ne prouve rien.'; $echecs++ }
        else { "contre-épreuve 4 (sans poussée) : échec attendu obtenu ($($mc.motifs -join ' | '))" }

        if ($echecs -gt 0) { exit 1 }
    }
}
