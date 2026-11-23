param([string]$Action = "sonde", [string]$Gestes = "", [int]$Attente = 35,
      [string]$Build = $env:FORGE_TESTEUR_BUILD, [string]$Sortie = $env:FORGE_TESTEUR_SORTIE)
# L'outil de jeu du testeur : il joue un build fige comme un joueur le lance (son lanceur embarque, sans taille
# d'ecran imposee), par la seule fenetre du jeu.
#   -Action sonde    le bureau est-il libre ? (LIBRE, ou OCCUPE et sa raison) ; ne lance rien ;
#   -Action lancer   demarre le lanceur du build et attend la fenetre ;
#   -Action gestes   joue une liste de gestes dans la fenetre du jeu deja ouverte ;
#   -Action fermer   ferme le jeu ; son lanceur arrete le service du monde.
# Le build et le dossier des photos viennent de l'environnement : celui qui joue ne les choisit pas.
#
# Le PC est celui du proprietaire, qui s'en sert. L'outil ne lance donc rien tant qu'il est au clavier (une
# entree depuis moins de FORGE_TESTEUR_INACTIVITE secondes), qu'une application tient tout l'ecran, que la
# session est verrouillee ou qu'un Forge tourne deja. Une fois le jeu ouvert, aucun geste ni photo ne part si la
# fenetre du jeu n'est pas au premier plan, et tout s'arrete des qu'une main autre que la sienne a touche la
# souris ou change de fenetre. Les textes rendus sont sans accent : PowerShell 5.1 lit ce fichier en ANSI.
$ErrorActionPreference = "Stop"
if (-not $Build -or -not $Sortie) { Write-Output "ECHEC : FORGE_TESTEUR_BUILD et FORGE_TESTEUR_SORTIE ne sont pas poses"; exit 2 }
$exe = Join-Path $Build "Forge.exe"
$inactivite = 600; if ($env:FORGE_TESTEUR_INACTIVITE -match '^\d+$') { $inactivite = [int]$env:FORGE_TESTEUR_INACTIVITE }
$plafond = 60; if ($env:FORGE_TESTEUR_GESTES_MAX -match '^\d+$') { $plafond = [int]$env:FORGE_TESTEUR_GESTES_MAX }
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class Bureau {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] public struct ENTREE { public uint cb; public uint t; }
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int n);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint de, uint vers, bool attacher);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern bool GetLastInputInfo(ref ENTREE e);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, int d, UIntPtr e);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint f, UIntPtr e);
    // L'instant de la derniere entree (clavier ou souris) de la session, en millisecondes depuis son demarrage.
    public static uint DerniereEntree() { ENTREE e = new ENTREE(); e.cb = 8; GetLastInputInfo(ref e); return e.t; }
    public static double SecondesSansEntree() { return unchecked((uint)Environment.TickCount - DerniereEntree()) / 1000.0; }
}
"@
Add-Type -AssemblyName System.Drawing
[Bureau]::SetProcessDPIAware() | Out-Null

function Devant {
    $f = [Bureau]::GetForegroundWindow(); $id = 0; [Bureau]::GetWindowThreadProcessId($f, [ref]$id) | Out-Null
    $r = New-Object Bureau+RECT; [Bureau]::GetWindowRect($f, [ref]$r) | Out-Null
    $nom = ""; try { $nom = (Get-Process -Id $id -ErrorAction Stop).ProcessName } catch { }
    $plein = ($r.L -le 0) -and ($r.T -le 0) -and ($r.R -ge [Bureau]::GetSystemMetrics(0)) -and ($r.B -ge [Bureau]::GetSystemMetrics(1))
    return [pscustomobject]@{ Fenetre = $f; Processus = $nom; PleinEcran = $plein }
}
# La fenetre du jeu au premier plan. Windows le refuse a un processus qui n'a pas recu la derniere entree, et le
# testeur est lance par une tache de fond : il s'attache donc a la file d'entree de la fenetre qui est devant,
# puis, si cela ne suffit pas, presse Alt, qui lui donne ce droit. A n'appeler que quand le bureau est libre.
function Mettre-Devant($h) {
    if ([Bureau]::GetForegroundWindow() -eq $h) { return $true }
    if ([Bureau]::IsIconic($h)) { [Bureau]::ShowWindow($h, 9) | Out-Null }
    [Bureau]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 300
    if ([Bureau]::GetForegroundWindow() -eq $h) { return $true }
    $id = 0; $autre = [Bureau]::GetWindowThreadProcessId([Bureau]::GetForegroundWindow(), [ref]$id); $moi = [Bureau]::GetCurrentThreadId()
    [Bureau]::AttachThreadInput($moi, $autre, $true) | Out-Null
    [Bureau]::BringWindowToTop($h) | Out-Null; [Bureau]::SetForegroundWindow($h) | Out-Null
    [Bureau]::AttachThreadInput($moi, $autre, $false) | Out-Null; Start-Sleep -Milliseconds 300
    if ([Bureau]::GetForegroundWindow() -eq $h) { return $true }
    [Bureau]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero); [Bureau]::SetForegroundWindow($h) | Out-Null; [Bureau]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 300
    return ([Bureau]::GetForegroundWindow() -eq $h)
}
function Jeu { Get-Process -Name Forge -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 -and $_.Path -eq $exe } | Select-Object -First 1 }
# Pourquoi le bureau n'est pas libre pour lancer le jeu ; vide s'il l'est.
function Occupation {
    if (Get-Process -Name LogonUI -ErrorAction SilentlyContinue) { return "la session Windows est verrouillee" }
    $forge = @(Get-Process -Name Forge -ErrorAction SilentlyContinue)
    if ($forge | Where-Object { $_.SessionId -eq [Diagnostics.Process]::GetCurrentProcess().SessionId }) { return "un Forge.exe tourne deja sur ce bureau" }
    if ($forge) { return "un Forge.exe tourne deja, lance par un passage de la chaine" }
    if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { return "le port 8000 est pris : un service du monde tourne" }
    $d = Devant
    if ($d.PleinEcran -and ($d.Processus -notin @("Forge", "explorer", ""))) { return ($d.Processus + " occupe tout l'ecran") }
    $repos = Repos-Du-Proprietaire
    if ($repos -lt $inactivite) { return ("le proprietaire est au clavier (derniere entree il y a " + $repos + " s ; il en faut " + $inactivite + ")") }
    return ""
}
# La main du testeur, gardee d'un appel a l'autre : l'instant de sa derniere entree, la place ou il a laisse le
# curseur, et l'instant de la derniere entree du proprietaire avant qu'il joue. Windows compte les gestes du
# testeur comme des entrees : sans cette memoire, il se prendrait lui-meme pour le proprietaire.
$main = Join-Path $env:TEMP "forge-testeur-main.txt"
function Lire-La-Main { if (Test-Path $main) { $m = @((Get-Content $main) -split " "); if ($m.Count -ge 4) { return $m } }; return @(0, 0, 0, 0) }
function Noter-La-Main([string]$duProprietaire = "") {
    if (-not $duProprietaire) { $duProprietaire = (Lire-La-Main)[3] }
    $p = New-Object Bureau+POINT; [Bureau]::GetCursorPos([ref]$p) | Out-Null
    Set-Content -Path $main -Value ("" + [Bureau]::DerniereEntree() + " " + $p.X + " " + $p.Y + " " + $duProprietaire)
}
# Les secondes ecoulees depuis la derniere entree du proprietaire : si la derniere entree de la session est celle
# du testeur, c'est l'entree d'avant qui compte.
function Repos-Du-Proprietaire {
    $t = [Bureau]::DerniereEntree(); $m = Lire-La-Main
    if ([string]$t -eq [string]$m[0] -and [uint32]$m[3] -gt 0) { $t = [uint32]$m[3] }
    return [int](([long]([Environment]::TickCount -band 0xFFFFFFFFL) - [long]$t) / 1000)
}

if ($Action -eq "sonde") {
    $raison = Occupation
    if ($raison) { Write-Output ("OCCUPE : " + $raison); exit 4 }
    Write-Output ("LIBRE : devant, " + (Devant).Processus + " ; sans entree du proprietaire depuis " + (Repos-Du-Proprietaire) + " s"); exit 0
}

if ($Action -eq "lancer") {
    $raison = Occupation
    if ($raison) { Write-Output ("OCCUPE : " + $raison + " ; le jeu n'est pas lance"); exit 4 }
    if (-not (Test-Path $exe)) { Write-Output ("ECHEC : pas de build a " + $exe); exit 2 }
    # La derniere entree avant le lancement : celle du proprietaire, ou celle du testeur s'il relance le jeu.
    $avant = [Bureau]::DerniereEntree(); $m = Lire-La-Main
    $duProprietaire = [string]$avant; if ([string]$avant -eq [string]$m[0] -and [uint32]$m[3] -gt 0) { $duProprietaire = [string]$m[3] }
    New-Item -ItemType Directory -Force (Join-Path $Sortie "publication") | Out-Null
    # Les memes arguments que le Jouer.cmd du build : son lanceur embarque, la carte, le jeu sans taille d'ecran imposee.
    $source = Join-Path $Build "source"
    $lanceur = Start-Process -FilePath py -ArgumentList @("`"$source\pc\jouer.py`"", "--carte", "--", "`"$exe`"") -WorkingDirectory $source -PassThru -WindowStyle Hidden -RedirectStandardOutput "$Sortie\lanceur.txt" -RedirectStandardError "$Sortie\lanceur-erreurs.txt"
    Set-Content -Path "$Sortie\lanceur.pid" -Value $lanceur.Id
    $jeu = $null
    for ($i = 0; $i -lt 90 -and -not $jeu; $i++) { Start-Sleep -Seconds 1; $jeu = Jeu }
    if (-not $jeu) { Write-Output "ECHEC : la fenetre du jeu n'est pas venue"; Get-Content "$Sortie\lanceur-erreurs.txt" -ErrorAction SilentlyContinue | Select-Object -Last 5; exit 2 }
    Start-Sleep -Seconds $Attente
    # Le proprietaire a pu revenir pendant le lancement, ou rien n'y a touche au clavier ni a la souris : le jeu ne
    # lui prend alors pas le premier plan.
    $d = Devant
    if ([Bureau]::DerniereEntree() -ne $avant -or ($d.PleinEcran -and ($d.Processus -notin @("Forge", "explorer", "")))) { Write-Output ("OCCUPE : le proprietaire est revenu pendant le lancement (devant : " + $d.Processus + "). Ne joue pas : ferme le jeu."); exit 4 }
    $devant = Mettre-Devant $jeu.MainWindowHandle
    $r = New-Object Bureau+RECT; [Bureau]::GetClientRect($jeu.MainWindowHandle, [ref]$r) | Out-Null
    Noter-La-Main $duProprietaire
    if (-not $devant) { Write-Output ("ECHEC : le jeu est ouvert mais " + (Devant).Processus + " garde le premier plan. Ferme le jeu."); exit 2 }
    Write-Output ("LANCE : fenetre " + ($r.R - $r.L) + "x" + ($r.B - $r.T) + " ; devant : " + (Devant).Processus)
    exit 0
}

if ($Action -eq "fermer") {
    Get-Process -Name Forge -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 5
    $id = Get-Content "$Sortie\lanceur.pid" -ErrorAction SilentlyContinue
    if ($id -and (Get-Process -Id $id -ErrorAction SilentlyContinue)) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    Write-Output "FERME ; port 8000 pris : $([bool](Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue))"
    exit 0
}

if ($Action -ne "gestes") { Write-Output "action inconnue : $Action"; exit 1 }
$jeu = Jeu
if (-not $jeu) { Write-Output "ECHEC : le jeu n'est pas ouvert"; exit 2 }
$h = $jeu.MainWindowHandle
$laissee = Lire-La-Main
# Une autre main que la sienne : une entree est arrivee depuis son dernier geste, et le curseur n'est plus ou il
# l'avait laisse, ou la fenetre du jeu n'est plus devant. Il ne reprend alors rien.
function Reprise-Par-Le-Proprietaire {
    if ([Bureau]::DerniereEntree() -eq [uint32]$script:laissee[0]) { return $false }
    $p = New-Object Bureau+POINT; [Bureau]::GetCursorPos([ref]$p) | Out-Null
    $bouge = ([Math]::Abs($p.X - [int]$script:laissee[1]) -gt 4) -or ([Math]::Abs($p.Y - [int]$script:laissee[2]) -gt 4)
    return $bouge -or ([Bureau]::GetForegroundWindow() -ne $h)
}
function Pret {
    if ([Bureau]::GetForegroundWindow() -eq $h) { return $true }
    $d = Devant
    if ($d.PleinEcran -and ($d.Processus -notin @("Forge", "explorer", ""))) { return $false }
    # Reprendre le premier plan peut couter une pression d'Alt : c'est une entree du testeur, il la retient.
    $pris = Mettre-Devant $h
    if ($pris) { Retenir }
    return $pris
}
function Retenir { Noter-La-Main; $script:laissee = Lire-La-Main }
function Origine { $p = New-Object Bureau+POINT; [Bureau]::ClientToScreen($h, [ref]$p) | Out-Null; return $p }
$jpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
$qualite = New-Object System.Drawing.Imaging.EncoderParameters 1
$qualite.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality, [long]85)
# La photo que le testeur regarde (PNG), et sa copie legere pour la publication (JPEG).
function Ranger($image, [string]$nom, [string]$taille) {
    if ($nom -notmatch '^[A-Za-z0-9_-]+$') { Write-Output "nom de photo refuse : $nom (lettres, chiffres, - et _)"; return }
    $image.Save("$Sortie\$nom.png"); $image.Save("$Sortie\publication\$nom.jpg", $jpeg, $qualite)
    Write-Output "PHOTO $Sortie\$nom.png $taille"
}
function Photo([string]$nom) {
    $r = New-Object Bureau+RECT; [Bureau]::GetClientRect($h, [ref]$r) | Out-Null; $p = Origine
    $b = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T); $g = [System.Drawing.Graphics]::FromImage($b)
    $g.CopyFromScreen($p.X, $p.Y, 0, 0, $b.Size); Ranger $b $nom "$($r.R - $r.L)x$($r.B - $r.T)"; $g.Dispose(); $b.Dispose()
}
# Un morceau de la fenetre a sa taille reelle, pour lire un petit texte.
function Rogner([int]$x, [int]$y, [int]$l, [int]$ht, [string]$nom) {
    $p = Origine; $b = New-Object System.Drawing.Bitmap $l, $ht; $g = [System.Drawing.Graphics]::FromImage($b)
    $g.CopyFromScreen($p.X + $x, $p.Y + $y, 0, 0, $b.Size); Ranger $b $nom "${l}x${ht}"; $g.Dispose(); $b.Dispose()
}
function Point([int]$x, [int]$y) { $p = Origine; [Bureau]::SetCursorPos($p.X + $x, $p.Y + $y) | Out-Null; Start-Sleep -Milliseconds 150 }
# Les gestes d'un joueur se comptent : au plafond, il ne reste que regarder.
$compte = Join-Path $Sortie "gestes.txt"
$joues = 0; if (Test-Path $compte) { $joues = [int](Get-Content $compte) }
$comptes = @("clic", "droit", "double", "molette", "touche", "tenir", "glisser")
# Chaque geste : "clic x y", "droit x y", "double x y", "molette x y crans", "touche code", "tenir code ms",
# "glisser x0 y0 x1 y1", "survol x y", "attendre s", "photo nom", "rogner x y l h nom".
foreach ($geste in ($Gestes -split ";" | Where-Object { $_.Trim() })) {
    $m = $geste.Trim() -split "\s+"
    if ($m[0] -ne "attendre") {
        if (Reprise-Par-Le-Proprietaire) { Write-Output ("ARRET au geste '" + $geste.Trim() + "' : le proprietaire a repris la main. Ne joue plus : ferme le jeu et rends ton rapport avec ce que tu as."); exit 5 }
        if (-not (Pret)) { Write-Output ("ARRET au geste '" + $geste.Trim() + "' : " + (Devant).Processus + " est au premier plan. Ne joue plus : ferme le jeu et rends ton rapport avec ce que tu as."); exit 5 }
    }
    if ($m[0] -in $comptes) {
        if ($joues -ge $plafond) { Write-Output ("FINI : " + $joues + " gestes joues, c'est le plafond. Le geste '" + $geste.Trim() + "' n'est pas parti. Ferme le jeu et rends ton rapport."); exit 6 }
        $joues++; Set-Content -Path $compte -Value $joues
    }
    switch ($m[0]) {
        "clic" { Point ([int]$m[1]) ([int]$m[2]); [Bureau]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60; [Bureau]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero) }
        "droit" { Point ([int]$m[1]) ([int]$m[2]); [Bureau]::mouse_event(8, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60; [Bureau]::mouse_event(16, 0, 0, 0, [UIntPtr]::Zero) }
        "double" { Point ([int]$m[1]) ([int]$m[2]); foreach ($k in 1, 2) { [Bureau]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 50; [Bureau]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 110 } }
        "survol" { Point ([int]$m[1]) ([int]$m[2]); [Bureau]::mouse_event(1, 1, 0, 0, [UIntPtr]::Zero) }
        "molette" { Point ([int]$m[1]) ([int]$m[2]); $crans = [int]$m[3]; $pas = [Math]::Sign($crans) * 120; for ($k = 0; $k -lt [Math]::Abs($crans); $k++) { [Bureau]::mouse_event(0x800, 0, 0, $pas, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80 } }
        "touche" { $c = [Convert]::ToByte($m[1], 16); [Bureau]::keybd_event(0, $c, 0x8, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80; [Bureau]::keybd_event(0, $c, 0xA, [UIntPtr]::Zero) }
        "tenir" { $c = [Convert]::ToByte($m[1], 16); [Bureau]::keybd_event(0, $c, 0x8, [UIntPtr]::Zero); Start-Sleep -Milliseconds ([int]$m[2]); [Bureau]::keybd_event(0, $c, 0xA, [UIntPtr]::Zero) }
        # La carte lit le deplacement brut de la souris : le glisse part en mouvements relatifs, bouton tenu.
        "glisser" { Point ([int]$m[1]) ([int]$m[2]); [Bureau]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80; $dx = ([int]$m[3] - [int]$m[1]) / 10; $dy = ([int]$m[4] - [int]$m[2]) / 10; for ($k = 1; $k -le 10; $k++) { [Bureau]::mouse_event(1, [int]$dx, [int]$dy, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 40 }; [Bureau]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero) }
        "attendre" { Start-Sleep -Seconds ([int]$m[1]) }
        "photo" { Photo $m[1] }
        "rogner" { Rogner ([int]$m[1]) ([int]$m[2]) ([int]$m[3]) ([int]$m[4]) $m[5] }
        default { Write-Output "geste inconnu : $geste" }
    }
    Start-Sleep -Milliseconds 400
    # Seul un geste du testeur deplace sa main : une attente ou une photo ne couvrent pas une entree du proprietaire.
    if ($m[0] -in $comptes -or $m[0] -eq "survol") { Retenir }
}
Write-Output ("FAIT ; gestes joues : " + $joues + " sur " + $plafond)
