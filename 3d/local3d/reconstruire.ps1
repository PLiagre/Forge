param(
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe',
    [string]$Unity = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe',
    [switch]$AvecUnity
)
$ErrorActionPreference = 'Stop'
$atelierRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $atelierRoot
try {
    & py local3d/preparer_textures.py
    if ($LASTEXITCODE -ne 0) { throw 'Préparation des textures en échec.' }
    & $Blender --background --python-exit-code 1 --python local3d/construire_v1.py
    if ($LASTEXITCODE -ne 0) { throw 'Construction Blender en échec.' }
    & $Blender --background --python-exit-code 1 --python local3d/verifier_v1.py
    if ($LASTEXITCODE -ne 0) { throw 'Vérification Blender en échec.' }
    if ($AvecUnity) {
        & py local3d/preparer_unity.py
        if ($LASTEXITCODE -ne 0) { throw 'Préparation Unity en échec.' }
        $unityArgs = @('-batchmode','-quit','-projectPath',('"' + $atelierRoot + '\unity"'),
            '-executeMethod','ForgeLocal3D.VillageV1Builder.Build','-logFile',('"' + $PSScriptRoot + '\unity-build.log"'))
        $process = Start-Process -FilePath $Unity -ArgumentList $unityArgs -WindowStyle Hidden -PassThru -Wait
        if ($process.ExitCode -ne 0) { throw 'Import Unity en échec. Voir local3d/unity-build.log.' }
    }
} finally { Pop-Location }
