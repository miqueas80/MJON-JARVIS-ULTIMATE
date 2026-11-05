#Requires -Version 5.1
<#
Build an integration-preview, bootable Windows 11 x64 ISO from original Microsoft
media. NOT the finished MJON graphical shell. No TPM bypass, no activation and
no Microsoft ISO download/redistribution; the input is locally supplied.
Requires Microsoft ADK Deployment Tools and adequate free disk.
#>
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$WindowsIso,
 [Parameter(Mandatory=$true)][string]$ExpectedWindowsSha256,
 [Parameter(Mandatory=$true)][string]$PayloadDirectory,
 [Parameter(Mandatory=$true)][string]$OutputIso,
 [string]$ExtractedSourceDirectory,
 [switch]$PreflightOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function RequireFile([string]$p) {
 if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Archivo inexistente: $p" }
}
function GetOscdimg {
 $found = Get-Command oscdimg.exe -ErrorAction SilentlyContinue
 if ($found) { return $found.Source }
 $pf86 = [Environment]::GetFolderPath('ProgramFilesX86')
 $paths = @(
  (Join-Path $pf86 'Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe'),
  (Join-Path $env:ProgramFiles 'Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe')
 )
 foreach ($p in $paths) { if (Test-Path -LiteralPath $p) { return $p } }
 throw 'Falta oscdimg.exe: instalá Windows ADK (Deployment Tools) oficial.'
}
function RootOfIso([string]$path) {
 $v = Get-DiskImage -ImagePath $path | Get-Volume | Where-Object { $_.DriveLetter } | Select-Object -First 1
 if (-not $v) { throw 'La ISO montada no tiene letra de unidad.' }
 return "$($v.DriveLetter):\"
}
function GetSevenZip {
 $names = @('7z.exe','7zz.exe','7za.exe')
 foreach ($name in $names) {
  $command = Get-Command $name -ErrorAction SilentlyContinue
  if ($command) { return $command.Source }
 }
 $path = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
 if (Test-Path -LiteralPath $path -PathType Leaf) { return $path }
 throw 'Falta 7-Zip. Instalá 7-Zip desde https://www.7-zip.org/ para comprobar la ISO sin unidad virtual.'
}
function VerifyOutputWith7Zip([string]$isoFile, [string]$expectedHash, [string]$temporaryDir) {
 $zip = GetSevenZip
 # 7-Zip inspects the ISO filesystem without relying on mounted CD-ROM devices.
 $listing = & $zip l -slt $isoFile
 if ($LASTEXITCODE -ne 0) { throw '7-Zip no pudo leer la ISO resultante.' }
 $entries = @($listing | Where-Object { $_ -match '^Path = ' } |
  ForEach-Object { $_.Substring(7).Replace('/','\').ToLowerInvariant() })
 foreach ($name in @('setup.exe','sources\boot.wim','mjon\mjon-windows-tools.exe')) {
  if ($entries -notcontains $name) { throw "Falta $name en la ISO de salida." }
 }
 $verifyFolder = Join-Path $temporaryDir 'verified-file'
 New-Item -ItemType Directory -Force -Path $verifyFolder | Out-Null
 & $zip e -y "-o$verifyFolder" $isoFile 'MJON\MJON-Windows-Tools.exe' | Out-Null
 if ($LASTEXITCODE -ne 0) { throw '7-Zip no pudo extraer MJON de la ISO final.' }
 $confirmed = Join-Path $verifyFolder 'MJON-Windows-Tools.exe'
 RequireFile $confirmed
 $hash = (Get-FileHash -LiteralPath $confirmed -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($hash -ne $expectedHash) { throw 'El hash MJON extraído de la nueva ISO no coincide.' }
}
function VerifyWindowsSource([string]$root) {
 foreach ($part in @('setup.exe','sources\boot.wim','boot\etfsboot.com','efi\microsoft\boot\efisys.bin','efi\boot\bootx64.efi')) {
  RequireFile (Join-Path $root $part)
 }
 if (-not (@('install.wim','install.esd','install.swm') | Where-Object {
  Test-Path -LiteralPath (Join-Path $root "sources\$_")
 } | Select-Object -First 1)) { throw 'Falta imagen install.wim|esd|swm.' }
 $sig = Get-AuthenticodeSignature -LiteralPath (Join-Path $root 'setup.exe')
 if ($sig.Status -ne 'Valid' -or -not $sig.SignerCertificate -or
     $sig.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
  throw 'No se pudo verificar la firma de Microsoft en setup.exe.'
 }
}
if ($ExpectedWindowsSha256 -notmatch '^[0-9a-fA-F]{64}$') { throw 'SHA256 de Windows requerido (64 caracteres).' }
RequireFile $WindowsIso
if ([IO.Path]::GetExtension($WindowsIso).ToLowerInvariant() -ne '.iso') { throw 'Se requiere un archivo ISO.' }
if (-not (Test-Path -LiteralPath $PayloadDirectory -PathType Container)) { throw 'Carpeta MJON inexistente.' }
$extracted = $null
if ($ExtractedSourceDirectory) {
 if (-not (Test-Path -LiteralPath $ExtractedSourceDirectory -PathType Container)) {
  throw 'No existe la carpeta extraída de Windows.'
 }
 $extracted = (Resolve-Path -LiteralPath $ExtractedSourceDirectory).Path
 # Prevent using an empty or incorrect folder as an installation source.
 VerifyWindowsSource $extracted
}
$src = (Resolve-Path -LiteralPath $WindowsIso).Path
$package = (Resolve-Path -LiteralPath $PayloadDirectory).Path
$dest = [IO.Path]::GetFullPath($OutputIso)
if ($src -eq $dest) { throw 'No sobrescribir la ISO original.' }
$destDir = Split-Path -Parent $dest
if (-not (Test-Path -LiteralPath $destDir -PathType Container)) { throw 'La carpeta de salida debe existir.' }
$exe = Join-Path $package 'MJON-Windows-Tools.exe'
$manifest = Join-Path $package 'SHA256SUMS.txt'
RequireFile $exe
RequireFile $manifest
$exeHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if (@(Get-Content -LiteralPath $manifest | Where-Object {
 $_.Trim().ToLowerInvariant() -eq "$exeHash  mjon-windows-tools.exe"
}).Count -eq 0) { throw 'No coincide el SHA256 de herramientas MJON.' }
$srcBytes = (Get-Item -LiteralPath $src).Length
$needed = [int64](3 * $srcBytes + 2 * (Get-Item -LiteralPath $exe).Length + 5GB)
$drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($dest))
if (-not $drive.IsReady -or $drive.AvailableFreeSpace -lt $needed) { throw "Disco insuficiente: se requieren $([math]::Ceiling($needed/1GB)) GiB libres." }
if ((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedWindowsSha256.ToLowerInvariant()) { throw 'SHA256 de ISO original incorrecto.' }
$oscdimg = GetOscdimg
$wasMounted = $false
$finalMounted = $false
$stageRoot = Join-Path $destDir ('mjon-staging-' + [guid]::NewGuid().ToString('N'))
try {
 if ($extracted) {
  # An official ISO + its verified hash is still required; avoid X-Lite DVD mounting.
  $isoRoot = $extracted
 } else {
  $current = Get-DiskImage -ImagePath $src -ErrorAction SilentlyContinue
  if ($current -and $current.Attached) { throw 'Desmontá primero la ISO original.' }
  Mount-DiskImage -ImagePath $src -ErrorAction Stop | Out-Null
  $wasMounted = $true
  $isoRoot = RootOfIso $src
 }
 VerifyWindowsSource $isoRoot
 if ($PreflightOnly) { Write-Host '[MJON] Verificación válida; sin escrituras.'; return }
 $staging = Join-Path $stageRoot 'windows-media'
 New-Item -ItemType Directory -Force -Path $staging | Out-Null
 & robocopy.exe $isoRoot $staging /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /NFL /NDL /NJH /NJS
 if ($LASTEXITCODE -ge 8) { throw "Error robocopy $LASTEXITCODE" }
 $mjon = Join-Path $staging 'MJON'
 New-Item -ItemType Directory -Force -Path $mjon | Out-Null
 Copy-Item -LiteralPath $exe -Destination $mjon
 Copy-Item -LiteralPath $manifest -Destination $mjon
 @'
MJON AI OS Windows Integration Preview (no es el producto final).
El medio de instalacion conserva Windows original y sus requisitos de seguridad.
No incluye el escritorio grafico MJON terminado ni licencia de Windows.
Herramientas opcionales: usar PowerShell despues de instalar Windows:
.\MJON-Windows-Tools.exe --doctor
No ejecuta herramientas automaticamente ni modifica la instalacion.
No redistribuir imagenes Windows sin los derechos correspondientes.
'@ | Set-Content -LiteralPath (Join-Path $mjon 'LEEME-MJON.txt') -Encoding UTF8
 # Microsoft recommends ordering the boot-critical files for media > 4.5 GB.
 # Use relative Windows paths, encoded as ASCII, one file per line.
 $bootOrder = Join-Path $stageRoot 'boot-order.txt'
 $priority = @(
  'boot\bcd', 'boot\boot.sdi', 'boot\bootfix.bin',
  'boot\etfsboot.com', 'boot\memtest.efi',
  'efi\microsoft\boot\bcd', 'efi\boot\bootx64.efi',
  'efi\microsoft\boot\efisys.bin', 'sources\boot.wim'
 )
 $present = @($priority | Where-Object {
  Test-Path -LiteralPath (Join-Path $staging $_) -PathType Leaf
 })
 [System.IO.File]::WriteAllLines($bootOrder, [string[]]$present, [System.Text.Encoding]::ASCII)
 $bios = Join-Path $staging 'boot\etfsboot.com'
 $uefi = Join-Path $staging 'efi\microsoft\boot\efisys.bin'
 $boot = "-bootdata:2#p0,e,b$bios#pEF,e,b$uefi"
 & $oscdimg -m -o -u2 -udfver102 -lMJON_WIN11_X64 $boot "-yo$bootOrder" $staging $dest
 if ($LASTEXITCODE -ne 0) { throw "oscdimg falló con $LASTEXITCODE" }
 RequireFile $dest
 if ($extracted) {
  # X-Lite installations may not expose mounted ISO drives; inspect with 7-Zip.
  VerifyOutputWith7Zip $dest $exeHash $stageRoot
 } else {
  Mount-DiskImage -ImagePath $dest -ErrorAction Stop | Out-Null
  $finalMounted = $true
  $finalRoot = RootOfIso $dest
  RequireFile (Join-Path $finalRoot 'setup.exe')
  RequireFile (Join-Path $finalRoot 'sources\boot.wim')
  $inside = Join-Path $finalRoot 'MJON\MJON-Windows-Tools.exe'
  RequireFile $inside
  if ((Get-FileHash -LiteralPath $inside -Algorithm SHA256).Hash.ToLowerInvariant() -ne $exeHash) { throw 'Hash de ejecutable dentro de ISO incorrecto.' }
 }
 Write-Host "[MJON] ISO de integración creada: $dest"
 Write-Host "[MJON] SHA256: $((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash)"
 Write-Host '[MJON] Arranque UEFI/instalación real y escritorio MJON siguen pendientes.'
} finally {
 if ($finalMounted) { Dismount-DiskImage -ImagePath $dest -ErrorAction SilentlyContinue | Out-Null }
 if ($wasMounted) { Dismount-DiskImage -ImagePath $src -ErrorAction SilentlyContinue | Out-Null }
 if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
