# Connect Hub — синтаксис и рабочие команды

## Проверка окружения

& 'D:\Connect Launcher\venv\Scripts\python.exe' -V
& 'D:\Connect Launcher\venv\Scripts\python.exe' -c "import PyQt6; from PyQt6.QtCore import QT_VERSION_STR; print(QT_VERSION_STR)"

## Запуск в dev-режиме

cd 'D:\Connect Launcher'
& '.\venv\Scripts\python.exe' -m py_compile launcher.py
& '.\venv\Scripts\python.exe' launcher.py

## Сборка .exe (onedir) — самая быстрая стартовая

Get-Process -Name 'Connect Hub' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 800

$root = 'D:\Connect Launcher'
$venvPy = Join-Path $root 'venv\Scripts\python.exe'
$icon   = Join-Path $root 'icon.ico'
$appDir = Join-Path $root 'Connect Hub'
$buildDir = Join-Path $root '_build'

if (Test-Path $appDir)   { Remove-Item $appDir -Recurse -Force }
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
Get-ChildItem $root -Filter '*.spec' -File | Remove-Item -Force -ErrorAction SilentlyContinue

& $venvPy -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name "Connect Hub" --icon "$icon" --add-data "$icon;." `
    --distpath "$root" --workpath "$buildDir" --specpath "$buildDir" `
    (Join-Path $root 'launcher.py')

if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
Get-ChildItem $root -Filter '*.spec' -File | Remove-Item -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $root 'launcher_config.json') (Join-Path $appDir 'launcher_config.json') -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $root 'vnc_cache.json') (Join-Path $appDir 'vnc_cache.json') -Force -ErrorAction SilentlyContinue

## Сборка установщика Inno Setup

Set-Location 'D:\Connect Launcher'
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' '.\installer.iss'
# Результат: D:\Connect Launcher\installer_out\ConnectHub-Setup-1.0.0.exe

## Ярлык на рабочем столе

$exe = 'D:\Connect Launcher\Connect Hub\Connect Hub.exe'
$lnkPath = 'D:\Connect Launcher\Connect Hub.lnk'
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath       = $exe
$lnk.WorkingDirectory = 'D:\Connect Launcher\Connect Hub'
$lnk.IconLocation     = $exe + ',0'
$lnk.Save()
Copy-Item $lnkPath ([Environment]::GetFolderPath('Desktop')) -Force

## Патч через Python (ПРАВИЛЬНЫЙ способ)

Проблема: str.replace и re.subn в Python интерпретируют backslash-n,
backslash-t, двойной backslash в строке-замене. Если в коде есть
двойной backslash в строке, оно превратится в одинарный и сломает
синтаксис.

Решение 1 — передавать замену через lambda:
  src, n = pat.subn(lambda m: new_block, src, count=1)

Решение 2 — собирать строки через chr():
  NL  = chr(10)
  Q   = chr(34)
  BSL = chr(92)
  line = "print(" + Q + "hello" + Q + ")" + NL

Решение 3 — файл-посредник:
  1) записать блок в отдельный файл через here-string PowerShell,
  2) прочитать его в Python и вставить через lambda.

## Работа с TAP

Все TAP-адаптеры:
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match 'TAP' } |
    Select-Object Name, Status, PnPDeviceID

Список TAP-устройств в системе:
Get-PnpDevice -Class Net | Where-Object { $_.FriendlyName -match 'TAP' }

Удалить один через pnputil (работает всегда):
pnputil /remove-device "ROOT\NET\0004"

Добавить новый TAP:
& 'C:\Program Files\TAP-Windows\bin\tapinstall.exe' install `
    'C:\Program Files\TAP-Windows\driver\OemVista.inf' tap0901

Удалить ВСЕ TAP:
& 'C:\Program Files\TAP-Windows\bin\tapinstall.exe' remove tap0901

## Проверка доступности шар

Test-Path 'X:\openvpn\start'
Test-Path 'M:\Обмен HRC СО\VNC'

## Логи

Последний лог TAP-операции:
Get-ChildItem "$env:TEMP\connecthub-elev-*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }

Последний лог VPN-сессии:
Get-ChildItem "$env:TEMP\vpn-launcher-*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }

Глобальный лог ошибок приложения:
Get-Content 'D:\Connect Launcher\Connect Hub\errors.log' -Tail 50 -Encoding UTF8

## Ключевые баги и их решения

### bad escape в re.subn
re.subn интерпретирует бэкслэши в строке-замене.
Лечение: lambda m: new_block.

### unterminated string literal
backslash-n внутри строкового литерала стал реальным переносом строки.
Лечение: chr(10), r-строки, или тройные кавычки.

### NameError: name QHeaderView is not defined
Забыли импорт. Проверь from PyQt6.QtWidgets import (...).
Нужны: QTreeWidget, QTreeWidgetItem, QHeaderView.
Из PyQt6.QtGui: QColor, QIcon, QPixmap, QPainter.

### Remove-PnpDevice не распознано
Модуль PnpDevice есть не везде. Использовать pnputil /remove-device INSTANCE_ID.

### Иконка не меняется в панели задач
Задать AppUserModelID до создания окна:
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ConnectHub.App.v1")

### TAP не добавляется или не удаляется
1) Проверить C:\Program Files\TAP-Windows\bin\tapinstall.exe существует.
2) Проверить, что UAC согласован (%TEMP%\connecthub-elev-*.log).
3) Для удаления — pnputil /remove-device "ROOT\NET\XXXX".

### Конфиг не сохраняется после установки в Program Files
Нет прав на запись. Устанавливать в %LOCALAPPDATA%\Programs\Connect Hub.

## Куда смотреть при проблемах

1. D:\Connect Launcher\Connect Hub\errors.log — глобальный перехватчик
2. %TEMP%\connecthub-elev-*.log — результаты UAC-операций (TAP)
3. %TEMP%\vpn-launcher-*.log — вывод конкретной VPN-сессии
4. %TEMP%\restart_taps.log — результат перезапуска TAP

## Быстрая шпаргалка для нового чата с ИИ

Проект: Connect Hub — Python 3.12 + PyQt6, GUI для VPN/VNC.
Пути: D:\Connect Launcher\launcher.py — исходник, Connect Hub\ — сборка,
venv\ — вирт. окружение, installer.iss — установщик.
Главные классы: Launcher, VpnSession, SettingsDialog, TapManagerDialog.
VPN запускается через промежуточный .ps1 + лог-файл, читается таймером.
TAP управляется через tapinstall.exe (install/remove) и pnputil (remove-device).
Конфиг: launcher_config.json рядом с exe. Кэш: vnc_cache.json.
Иконка: icon.ico (многомасштабная, из shell32.dll).
Сборка: PyInstaller --onedir --windowed.
Сборка установщика: Inno Setup 6, installer.iss.
Все подробности в PASSPORT.md и SYNTAX.md.