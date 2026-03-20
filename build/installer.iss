; ============================================================
;  Shopee Affiliate Bot — Inno Setup Installer Script
;  Gera: ShopeeAffiliateBotSetup.exe
;
;  Requisito: Inno Setup 6+ instalado
;  Download: https://jrsoftware.org/isdl.php
;
;  Para compilar: clique com botão direito > Compile
; ============================================================

#define AppName      "Shopee Affiliate Bot"
#define AppVersion   "1.0.0"
#define AppPublisher "Herlison"
#define AppURL       "https://github.com/herlison14/shopee-affiliate-bot"
#define AppExeName   "ShopeeAffiliateBot.exe"
#define SourceDir    "..\dist\ShopeeAffiliateBot"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=license.rtf
OutputDir=..\dist
OutputBaseFilename=ShopeeAffiliateBotSetup
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Todos os arquivos compilados do PyInstaller
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Arquivo de exemplo de configuração
Source: "..\env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar";       Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\data"
Type: files;          Name: "{app}\.env"

[Code]
// Verifica se .env existe, se não, copia do .env.example
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFile, EnvExample: String;
begin
  if CurStep = ssPostInstall then
  begin
    EnvFile    := ExpandConstant('{app}\.env');
    EnvExample := ExpandConstant('{app}\.env.example');
    if not FileExists(EnvFile) then
      FileCopy(EnvExample, EnvFile, False);
  end;
end;
