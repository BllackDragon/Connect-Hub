# Connect Hub — паспорт проекта

## Что это

Десктопное приложение для Windows — быстрое подключение к VPN
и открытие файлов удалённого доступа (VNC, RDP, .bat-ярлыки)
из сетевых папок.

## Стек

- Python 3.12.7 (venv в D:\Connect Launcher\venv\)
- PyQt6 6.11 (GUI)
- PyInstaller 6.22 (упаковка в .exe, режим onedir)
- Inno Setup 6 (установщик)

## Структура файлов

D:\Connect Launcher\
- launcher.py                 исходник приложения
- launcher_config.json        конфиг (пути, таймауты) рядом с exe
- vnc_cache.json              кэш сканирования VNC-папки
- icon.ico                    многомасштабная иконка
- venv\                       виртуальное окружение (для сборки)
- Connect Hub\                ГОТОВАЯ СБОРКА (onedir)
    - Connect Hub.exe
    - _internal\              Qt, Python DLL, все библиотеки
- installer.iss               скрипт Inno Setup
- PASSPORT.md, SYNTAX.md      документация

## Архитектура приложения

### Класс VpnSession

Описывает одну активную VPN-сессию. Поля:
- id, bat_path, name
- proc — объект subprocess.Popen (запускает powershell.exe runner)
- log_file — путь к лог-файлу в %TEMP%\vpn-launcher-TIMESTAMP.log
- log_pos — позиция чтения в лог-файле
- ready, soft_up — флаги готовности
- status — starting / up / error / stopped
- page, log_edit, status_label, stop_btn — ссылки на UI

### Класс Launcher(QMainWindow)

Главное окно. Ключевые методы:
- _build_ui() — верстка (шапка с кнопками, сплиттер VPN/VNC, вкладки сессий)
- _scan_vpn() / _scan_vnc() — сканирование папок в фоне через threading
- _build_tree() — построение дерева VNC (ленивое, по клику раскрытия)
- _start_session(bat_path) — запуск VPN-сессии
- _launch(s) — старт VPN через промежуточный .ps1 и лог-файл
- _poll_sessions() — таймер 400 мс читает лог-файл, определяет статус
- _stop_session(s) — taskkill /F /T по дереву процессов
- _update_tap_counter() — пересчитывает свободные TAP через Get-NetAdapter
- _open_settings(), _open_tap_manager(), _restart_taps() — диалоги
- _init_tray(), _init_single_instance_server() — трей и single instance

### Класс SettingsDialog(QDialog)

Окно настроек. Поля: vpn_dir, vnc_root, vpn_timeout,
vpn_soft_up_after, show_all_files, vnc_exclude_patterns.

### Класс TapManagerDialog(QDialog)

Управление TAP-адаптерами. Использует:
- C:\Program Files\TAP-Windows\bin\tapinstall.exe — install / remove
- pnputil /remove-device INSTANCE_ID — удаление конкретного
- Get-NetAdapter — для показа списка
- UAC-повышение через ShellExecuteW с runas

## Как работает запуск VPN

1. Пользователь кликает по профилю.
2. _start_session создаёт VpnSession, добавляет вкладку.
3. _launch:
   - создаёт временный .ps1 в %TEMP%\vpn-launcher-STAMP.ps1,
     который делает: cmd /c "pushd DIR && call BAT" *>&1 | Out-File LOG
   - запускает powershell.exe -File RUNNER через subprocess.Popen
     с флагом CREATE_NO_WINDOW.
4. _poll_sessions каждые 400 мс читает новые строки из log-файла,
   пишет в UI, ждёт маркер Initialization Sequence Completed.
5. Если маркера нет через vpn_soft_up_after секунд, но процесс жив —
   статус переводится в ONLINE (soft-up).

Почему через .ps1, а не напрямую cmd.exe: у cmd.exe на Windows проблемы
с UNC-путями в cwd (нельзя перейти в \\server\share\...). Команда pushd
создаёт временный сетевой диск и позволяет ..\bin\openvpn работать.

## Конфиг launcher_config.json

vpn_dir              — папка с .bat-профилями (X:\openvpn\start)
vnc_root             — корень файлов подключений (M:\...\VNC)
vpn_timeout          — общий таймаут ожидания (60)
vpn_soft_up_after    — soft-up через N секунд (15)
vnc_extensions       — типы боевых файлов (.vnc, .lnk, .rdp, .bat)
vnc_exclude_patterns — подстроки папок-исключений (неактивн, устаревш)
extra_vnc_roots      — дополнительные корни
show_all_files       — показывать ли все файлы (true)

Если файл отсутствует — создаётся с дефолтами. Ищется в HERE
(Path(sys.executable).parent для .exe, Path(__file__).parent для .py).

## Известные подводные камни

1. re.subn ест бэкслэши. В строках-заменах обратный слэш интерпретируется.
   Всегда использовать lambda m: replacement вместо строки.
2. PowerShell 5.1 читает .ps1 как cp1251 без BOM. Все русские .ps1
   сохранять как UTF-8 С BOM.
3. Get-Content -Encoding cp866 не работает в PS 5.1.
   Использовать -Encoding Oem или читать байты в Python.
4. QHeaderView, QPixmap, QPainter нужно явно импортировать из PyQt6.
5. PyInstaller onedir даёт быстрый старт (~0.3 с),
   onefile — медленный (3-5 с распаковки).
6. Иконка в панели задач Windows работает только если задан
   AppUserModelID через SetCurrentProcessExplicitAppUserModelID.
7. Права на запись: не ставить в Program Files. Использовать
   %LOCALAPPDATA%\Programs\.
8. UAC-операции (TAP) запускаются через ShellExecuteW с runas,
   результат читается из лог-файла %TEMP%\connecthub-elev-STAMP.log.

## Ключи для повторной сборки

Проверка синтаксиса:
  & 'D:\Connect Launcher\venv\Scripts\python.exe' -m py_compile 'D:\Connect Launcher\launcher.py'

Сборка exe — см. SYNTAX.md

## Что нужно на новой машине

- Windows 10/11 (x64)
- TAP-Windows драйвер: C:\Program Files\TAP-Windows\
- VNC-клиент (TightVNC/RealVNC) для открытия .vnc
- Доступ к сетевым папкам (X:, M: или UNC)