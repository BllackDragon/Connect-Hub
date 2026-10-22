; Inno Setup — Connect Hub
#define MyAppName "Connect Hub"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Internal"
#define MyAppExeName "Connect Hub.exe"

[Setup]
AppId={{B8F2A1C4-7D3E-4F5A-9C6B-2E8D4A1F3B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_out
OutputBaseFilename=ConnectHub-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
DisableDirPage=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Всё содержимое сборки, кроме конфига и кэша
Source: "Connect Hub\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs; \
    Excludes: "launcher_config.json,vnc_cache.json,errors.log,tap_debug.log"

; Конфиг: не перезаписывать при обновлении, не удалять при удалении
Source: "Connect Hub\launcher_config.json"; DestDir: "{app}"; \
    Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist

; Кэш: не перезаписывать при обновлении
Source: "Connect Hub\vnc_cache.json"; DestDir: "{app}"; \
    Flags: onlyifdoesntexist skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Запустить {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Удаляем служебные файлы, которые могли появиться во время работы
Type: files; Name: "{app}\errors.log"
Type: files; Name: "{app}\tap_debug.log"
Type: files; Name: "{app}\vnc_cache.json"