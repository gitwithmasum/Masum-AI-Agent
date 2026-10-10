#define MyAppName "Masum AI Agent"
#define MyAppVersion "5.3.0"
#define MyAppPublisher "Masum Billah"
#define MyAppExeName "MasumAIAgent.exe"

[Setup]
AppId={{E4A9E90B-BFD7-4B53-B29F-5EB5AF88E460}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Masum AI Agent
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\installer-output
OutputBaseFilename=Masum-AI-Agent-Setup
SetupIconFile=..\build\masum-ai-agent.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "startup"; Description: "Start Cirilla automatically when I sign in to Windows"; GroupDescription: "Startup:"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Masum AI Agent"; Filename: "{app}\{#MyAppExeName}"
Name: "{userstartup}\Masum AI Agent"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup
Name: "{autodesktop}\Masum AI Agent"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start Cirilla now"; Flags: nowait postinstall skipifsilent
