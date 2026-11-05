; SAQR AI Studio — Inno Setup 6 script
; Build: iscc installer\saqr-studio.iss  (after pyinstaller installer\saqr-studio.spec)
#define MyAppName "SAQR AI Studio"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "SAQR"
#define MyAppExeName "SaqrAIStudio.exe"

[Setup]
AppId={{8C4E2F5A-7B1D-4C61-9B2A-1D3E5F7A9B0C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SAQR AI Studio
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=SAQR-AI-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; Arabic is shipped by Inno Setup 6 as a community translation; drop the file in
; installer/languages if you want it: Name: "arabic"; MessagesFile: "languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "الاختصارات:"
Name: "detector"; Description: "تنزيل كاشف الوجه YuNet (MIT، ~230 KB)"; GroupDescription: "النماذج:"

[Files]
Source: "..\dist\SaqrAIStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "postinstall.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\تشخيص العتاد"; Filename: "{app}\{#MyAppExeName}"; Parameters: "doctor"
Name: "{group}\إلغاء التثبيت"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\postinstall.ps1"" -AppDir ""{app}"" -InstallDetector {code:GetDetectorFlag}"; StatusMsg: "فحص العتاد وتجهيز النموذج..."; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Remove-NetFirewallRule -DisplayName 'SAQR Bridge' -ErrorAction SilentlyContinue"""; Flags: runhidden

[Code]
var DetectorPage: TInputOptionWizardPage;
function GetDetectorFlag(Param: String): String;
begin
  if DetectorPage.Values[0] then Result := '1' else Result := '0';
end;
procedure InitializeWizard;
begin
  DetectorPage := CreateInputOptionPage(wpSelectTasks,
    'النماذج', 'ثبّت كاشف الوجه الآن',
    'كاشف YuNet مرخّص MIT ويمكن تنزيله من OpenCV Zoo. النماذج الأخرى (inswapper) غير تجارية وتُستورد يدويًا.',
    False, False);
  DetectorPage.Add('تنزيل YuNet والتحقق من SHA-256');
  DetectorPage.Values[0] := True;
end;
