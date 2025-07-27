[Setup]
AppName=YouTube downloader by M.Hasanov
AppVersion=1.0.0
DefaultDirName={pf}\YouTube downloader by M.Hasanov
DefaultGroupName=YouTube downloader by M.Hasanov
OutputBaseFilename=YouTube downloader by M.Hasanov 1.0.0
Compression=lzma
SolidCompression=yes
SetupIconFile=C:\Users\z004pnmt\Desktop\temp_exe\visuals\icon.ico

[Languages]
Name: "bulgarian"; MessagesFile: "compiler:Languages\Bulgarian.isl"

[Files]
Source: "C:\Users\z004pnmt\Desktop\temp_exe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\z004pnmt\Desktop\temp_exe\visuals\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcuts
Name: "{group}\YouTube downloader by M.Hasanov"; Filename: "{app}\YouTube_Mp3_Downloader_M_Hasanov.exe"; IconFilename: "{app}\icon.ico"


; Desktop shortcuts
Name: "{userdesktop}\YouTube downloader by M.Hasanov"; Filename: "{app}\YouTube_Mp3_Downloader_M_Hasanov.exe"; IconFilename: "{app}\icon.ico"

