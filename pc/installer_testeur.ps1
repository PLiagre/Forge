# Inscrit la tache planifiee "ForgeTesteur" : le passage du testeur, lance dans la session Windows ouverte du
# proprietaire, la seule ou le jeu a un ecran. Elle n'a aucun horaire : seul le runner de la chaine la demarre
# (testeur-pc.yml), quand une etape n'a plus de lot ouvert. Elle tourne sans fenetre (conhost --headless), avec les
# droits ordinaires du compte, et ne demande ni elevation ni mot de passe. Rejouable : elle se remplace.
#
#   pc\Installer_Testeur.cmd            inscrire, ou reinscrire
#   pc\Installer_Testeur.cmd -Retirer   la retirer
param([switch]$Retirer)
$ErrorActionPreference = "Stop"
$nom = "ForgeTesteur"
if ($Retirer) {
    Unregister-ScheduledTask -TaskName $nom -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "tache $nom retiree"
    exit 0
}
# Le lanceur est celui de la copie de la chaine que le runner tient sur master : il suit le depot sans reinscription.
$lanceur = "D:\Forge\.atelier\pilote-testeur\pc\Testeur.cmd"
$action = New-ScheduledTaskAction -Execute "conhost.exe" -Argument "--headless cmd.exe /c `"$lanceur`""
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
# Un seul passage a la fois ; trois heures au plus, puis Windows l'arrete.
$reglages = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName $nom -Action $action -Principal $principal -Settings $reglages -Force `
    -Description "Forge : le testeur joue le build fige d'une etape dans la session ouverte. Demarree par le runner de la chaine, jamais par un horaire." | Out-Null
Write-Output "tache $nom inscrite pour $env:USERDOMAIN\$env:USERNAME : $lanceur"
Write-Output "elle ne part que si cette session Windows est ouverte et non verrouillee"
