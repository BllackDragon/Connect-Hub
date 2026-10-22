#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VPN + VNC Launcher — Python + PyQt6, тёмная тема."""
import ctypes
import re
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import threading
from PyQt6.QtCore import Qt, QTimer, QSize, QFileInfo, QEvent
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLineEdit, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QTabWidget, QPushButton, QLabel, QPlainTextEdit,
    QMessageBox, QFrame, QFileIconProvider, QMenu,
    QDialog, QCheckBox, QSpinBox, QFileDialog, QSystemTrayIcon,
    QDialog, QProgressBar,
)

if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
else:
    HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "launcher_config.json"
CACHE_PATH = HERE / "vnc_cache.json"
SINGLE_INSTANCE_KEY = "ConnectHub_SingleInstance_v1"

DEFAULT_CONFIG = {
    "vpn_dir": r"X:\openvpn\start",
    "vnc_root": r"M:\Обмен HRC СО\VNC",
    "vpn_timeout": 60,
    "vpn_soft_up_after": 15,
    "vnc_extensions": [".vnc", ".lnk", ".rdp", ".bat"],
    "vnc_exclude_patterns": ["неактивн", "устаревш"],
    "show_all_files": True,
    "extra_vnc_roots": [],
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


def set_dark_titlebar(window):
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        val = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        abgr = ctypes.c_uint(0xFF17110D)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 34, ctypes.byref(abgr), ctypes.sizeof(abgr))
    except Exception:
        pass


QSS = """
* { font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow, QWidget#central { background-color: #0d1117; color: #c9d1d9; }
QFrame#card { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; }
QLabel#cardTitle { color: #8b949e; font-size: 9pt; font-weight: 600; letter-spacing: 1px; }
QLabel#cardBadge { background-color: #21262d; color: #8b949e; padding: 2px 8px; border-radius: 9px; font-size: 9pt; }
QLabel#brand { color: #c9d1d9; font-size: 13pt; font-weight: 600; }
QLineEdit { background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 7px 11px; color: #c9d1d9; selection-background-color: #1f6feb; selection-color: #ffffff; }
QLineEdit:focus { border: 1px solid #58a6ff; }
QLineEdit:hover { border: 1px solid #484f58; }
QPushButton { background-color: transparent; border: 1px solid #30363d; border-radius: 6px; padding: 7px 14px; color: #c9d1d9; font-weight: 600; }
QPushButton:hover { background-color: #21262d; border-color: #484f58; }
QPushButton:pressed { background-color: #30363d; }
QPushButton#primary { background-color: #1f6feb; border: none; color: white; }
QPushButton#primary:hover { background-color: #388bfd; }
QPushButton#danger { background-color: #da3633; border: none; color: white; }
QPushButton#danger:hover { background-color: #f85149; }
QPushButton#dangerOutline { background-color: transparent; border: 1px solid #f85149; color: #f85149; }
QPushButton#dangerOutline:hover { background-color: #2d1214; }
QPushButton:pressed { background-color: #30363d; }
QPushButton#primary:pressed { background-color: #1158c7; }
QPushButton#danger:pressed { background-color: #a52a2a; }
QPushButton#dangerOutline:pressed { background-color: #442020; }
QPushButton:disabled { color: #484f58; border-color: #21262d; }
QPushButton#primary:disabled { background-color: #21262d; color: #484f58; border: none; }
QPushButton#danger:disabled { background-color: #21262d; color: #484f58; border: none; }
QListWidget { background-color: transparent; border: none; outline: none; padding: 4px; }
QListWidget::item { padding: 8px 10px; border-radius: 6px; margin: 1px 0; color: #c9d1d9; }
QListWidget::item:hover { background-color: #21262d; }
QListWidget::item:selected { background-color: #1f6feb; color: white; }
QTreeWidget { background-color: transparent; border: none; outline: none; padding: 4px; color: #c9d1d9; }
QTreeWidget::item { padding: 3px 2px; border-radius: 4px; }
QTreeWidget::item:hover { background-color: #21262d; }
QTreeWidget::item:selected { background-color: #1f6feb; color: white; }
QTabWidget::pane { border: none; background-color: #010409; border-radius: 6px; }
QTabBar::tab { background-color: #21262d; color: #8b949e; padding: 6px 10px 6px 12px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; min-width: 130px; font-weight: 600; }
QTabBar::tab:selected { background-color: #161b22; color: #c9d1d9; }
QTabBar::tab:hover { background-color: #30363d; }
QPlainTextEdit { background-color: #010409; border: none; color: #c9d1d9; font-family: 'Consolas', monospace; font-size: 10pt; selection-background-color: #1f6feb; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #30363d; min-height: 30px; border-radius: 5px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #484f58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #30363d; min-width: 30px; border-radius: 5px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background: #484f58; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QStatusBar { background-color: #161b22; border-top: 1px solid #30363d; color: #8b949e; }
QStatusBar::item { border: none; }
QMenu { background-color: #161b22; border: 1px solid #30363d; color: #c9d1d9; padding: 4px; }
QMenu::item { padding: 6px 20px; border-radius: 4px; }
QMenu::item:selected { background-color: #1f6feb; color: white; }
"""


def _proc_modifier(args):
    """Скрыть консольное окно у cmd.exe, запущенного через QProcess."""
    try:
        args.flags |= 0x08000000  # CREATE_NO_WINDOW
    except Exception:
        pass
    return args



# === Search normalization ===
_RU_TO_EN = {
    "й":"q","ц":"w","у":"e","к":"r","е":"t","н":"y","г":"u","ш":"i","щ":"o","з":"p",
    "ф":"a","ы":"s","в":"d","а":"f","п":"g","р":"h","о":"j","л":"k","д":"l",
    "я":"z","ч":"x","с":"c","м":"v","и":"b","т":"n","ь":"m",
}
_EN_TO_RU = {v: k for k, v in _RU_TO_EN.items()}
_TRANS = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z",
    "и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r",
    "с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"ts","ч":"ch","ш":"sh",
    "щ":"shch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
}

def _alnum(s):
    return "".join(c for c in s if c.isalnum())

def _translit(s):
    return "".join(_TRANS.get(c, c) for c in s.lower())

def _kbd_ru_to_en(s):
    return "".join(_RU_TO_EN.get(c, c) for c in s)

def _kbd_en_to_ru(s):
    return "".join(_EN_TO_RU.get(c, c) for c in s)

def _variants(s):
    s = s.strip().lower()
    out = set()
    out.add(_alnum(s))
    out.add(_alnum(_translit(s)))
    s_vis = s.replace("с", "c").replace("у", "y").replace("х", "x")
    out.add(_alnum(_translit(s_vis)))
    k1 = _kbd_ru_to_en(s)
    out.add(_alnum(k1))
    out.add(_alnum(_translit(k1)))
    k2 = _kbd_en_to_ru(s)
    out.add(_alnum(k2))
    out.add(_alnum(_translit(k2)))
    return {v for v in out if v}

def _matches(query, target):
    if not query:
        return True
    for q in _variants(query):
        for t in _variants(target):
            if q and q in t:
                return True
    return False

def _count_taps():
    """Возвращает (total, busy). Busy = адаптер в состоянии Up."""
    try:
        ps = ("Get-NetAdapter -ErrorAction SilentlyContinue | "
              "Where-Object { $_.InterfaceDescription -match 'TAP' } | "
              "ForEach-Object { $_.Status }")
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=8,
            creationflags=0x08000000,
        )
        statuses = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        total = len(statuses)
        busy = sum(1 for st in statuses if st.lower() == "up")
        return total, busy
    except Exception:
        return 0, 0


def _find_tapctl():
    """Возвращает путь к tapctl.exe или None."""
    candidates = [
        r"C:\Program Files\OpenVPN\bin\tapctl.exe",
        r"C:\Program Files (x86)\OpenVPN\bin\tapctl.exe",
        r"C:\Program Files\TAP-Windows\bin\tapctl.exe",
        r"C:\Program Files (x86)\TAP-Windows\bin\tapctl.exe",
        r"C:\Program Files\OpenVPN Connect\tapctl.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


class VpnSession:
    def __init__(self, sid, bat_path, name):
        self.id = sid
        self.bat_path = bat_path
        self.name = name
        self.proc = None
        self.ready = False
        self.soft_up = False
        self.start_time = None
        self.status = "starting"
        self.log_file = None
        self.log_pos = 0
        self.runner_file = None
        self.log_file = None
        self.log_pos = 0
        self.runner_file = None
        self.page = None
        self.log_edit = None
        self.status_label = None
        self.stop_btn = None



class SettingsDialog(QDialog):
    """Окно настроек путей и параметров."""
    def __init__(self, parent, cfg, cfg_path):
        super().__init__(parent)
        self.cfg = dict(cfg)
        self.cfg_path = cfg_path
        self.result_cfg = None

        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.setMinimumWidth(780)
        self.setStyleSheet("""
            QDialog { background-color:#161b22; }
            QLabel { color:#c9d1d9; background:transparent; }
            QLabel#hint { color:#6e7681; font-size:9pt; }
            QLabel#section { color:#58a6ff; font-size:11pt; font-weight:600; }
            QLineEdit {
                background-color:#0d1117; border:1px solid #30363d;
                border-radius:6px; padding:8px 11px; color:#c9d1d9;
                selection-background-color:#1f6feb;
            }
            QLineEdit:focus { border:1px solid #58a6ff; }
            QCheckBox { color:#c9d1d9; }
            QSpinBox {
                background-color:#0d1117; border:1px solid #30363d;
                border-radius:6px; padding:6px; color:#c9d1d9;
            }
            QPushButton {
                background:transparent; border:1px solid #30363d;
                border-radius:6px; padding:8px 16px; color:#c9d1d9;
                font-weight:600;
            }
            QPushButton:hover { background-color:#21262d; border-color:#484f58; }
            QPushButton#ok {
                background-color:#238636; border:none; color:white;
            }
            QPushButton#ok:hover { background-color:#2ea043; }
            QPushButton#test {
                background:transparent; border:1px solid #30363d; color:#8b949e;
                padding:6px 12px; font-size:9pt;
            }
            QPushButton#test:hover { color:#c9d1d9; }
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(14)

        t = QLabel("Настройки путей")
        t.setStyleSheet("color:#c9d1d9; font-size:15pt; font-weight:600;")
        v.addWidget(t)

        # --- VPN path ---
        v.addWidget(self._section("1. Папка VPN-профилей (.bat)"))
        v.addWidget(self._hint(
            r"Папка, где лежат .bat файлы для подключения к VPN. "
            r"Лаунчер при клике по профилю запускает соответствующий .bat. "
            r"Путь можно указывать как локальный (X:\openvpn\start), так и сетевой "
            r"(\\srv-file1.ssa.ru\home$\User\openvpn\start)."
        ))
        row1 = QHBoxLayout()
        self.txt_vpn = QLineEdit(str(self.cfg.get("vpn_dir", "")))
        self.txt_vpn.setPlaceholderText(r"Пример: X:\openvpn\start")
        row1.addWidget(self.txt_vpn, 1)
        b1 = QPushButton("...")
        b1.setFixedWidth(44)
        b1.clicked.connect(lambda: self._browse(self.txt_vpn))
        row1.addWidget(b1)
        v.addLayout(row1)
        v.addLayout(self._test_row(self.txt_vpn, "Папка с .bat"))

        # --- VNC path ---
        v.addWidget(self._section("2. Корневая папка подключений"))
        v.addWidget(self._hint(
            r"Главная папка, где хранится информация о клиентах — файлы .vnc, .rdp, .lnk, "
            r"а также текстовые и другие сопутствующие файлы. Все подпапки будут видны "
            r"в дереве справа. Пример: M:\Обмен HRC СО\VNC"
        ))
        row2 = QHBoxLayout()
        self.txt_vnc = QLineEdit(str(self.cfg.get("vnc_root", "")))
        self.txt_vnc.setPlaceholderText(r"Пример: M:\Обмен HRC СО\VNC")
        row2.addWidget(self.txt_vnc, 1)
        b2 = QPushButton("...")
        b2.setFixedWidth(44)
        b2.clicked.connect(lambda: self._browse(self.txt_vnc))
        row2.addWidget(b2)
        v.addLayout(row2)
        v.addLayout(self._test_row(self.txt_vnc, "Папка с файлами"))

        # --- Timeouts ---
        v.addWidget(self._section("3. Параметры подключения"))
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Таймаут ожидания VPN, сек:"))
        self.sp_timeout = QSpinBox()
        self.sp_timeout.setRange(5, 300)
        self.sp_timeout.setValue(int(self.cfg.get("vpn_timeout", 60)))
        row3.addWidget(self.sp_timeout)
        row3.addSpacing(24)
        row3.addWidget(QLabel("Считать онлайн через, сек:"))
        self.sp_soft = QSpinBox()
        self.sp_soft.setRange(3, 120)
        self.sp_soft.setValue(int(self.cfg.get("vpn_soft_up_after", 15)))
        row3.addWidget(self.sp_soft)
        row3.addStretch(1)
        v.addLayout(row3)
        v.addWidget(self._hint(
            "«Таймаут» — сколько секунд ждать маркер завершения соединения, "
            "иначе статус станет ERROR. «Считать онлайн через» — сколько секунд "
            "ждать живого процесса, чтобы показать статус ONLINE."
        ))

        # --- Files ---
        self.chk_all = QCheckBox("Показывать в дереве все файлы (не только .vnc / .rdp / .lnk / .bat)")
        self.chk_all.setChecked(bool(self.cfg.get("show_all_files", True)))
        v.addWidget(self.chk_all)

        v.addWidget(QLabel("4. Исключённые папки (подстроки через запятую):"))
        self.txt_ex = QLineEdit(", ".join(self.cfg.get("vnc_exclude_patterns", [])))
        v.addWidget(self.txt_ex)
        v.addWidget(self._hint(
            r"Папки, имя которых содержит любую из этих подстрок (регистр не важен), "
            r"не будут отображаться в дереве. Пример: неактивн, устаревш, архив"
        ))

        v.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        b_cancel = QPushButton("Отмена")
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        b_save = QPushButton("Сохранить и пересканировать")
        b_save.setObjectName("ok")
        b_save.clicked.connect(self._save)
        btns.addWidget(b_save)
        v.addLayout(btns)

    def _section(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _hint(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("hint")
        lbl.setWordWrap(True)
        return lbl

    def _browse(self, line_edit):
        start = line_edit.text().strip() or "C:" + chr(92)
        chosen = QFileDialog.getExistingDirectory(self, "Выберите папку", start)
        if chosen:
            line_edit.setText(chosen)

    def _test_row(self, line_edit, label):
        h = QHBoxLayout()
        b = QPushButton("Проверить")
        b.setObjectName("test")
        b.setFixedWidth(110)
        res = QLabel("")
        res.setObjectName("hint")
        def do_test():
            p = line_edit.text().strip()
            if not p:
                res.setText("Пусто")
                res.setStyleSheet("color:#d29922;")
                return
            path = Path(p)
            if path.is_dir():
                try:
                    n = sum(1 for _ in path.iterdir())
                    res.setText("OK · объектов: " + str(n))
                    res.setStyleSheet("color:#3fb950;")
                except Exception as e:
                    res.setText("Есть, но нет доступа: " + str(e))
                    res.setStyleSheet("color:#d29922;")
            else:
                res.setText("Папка не найдена")
                res.setStyleSheet("color:#f85149;")
        b.clicked.connect(do_test)
        h.addWidget(b)
        h.addWidget(QLabel(label + ":"))
        h.addWidget(res, 1)
        return h

    def _save(self):
        self.cfg["vpn_dir"] = self.txt_vpn.text().strip()
        self.cfg["vnc_root"] = self.txt_vnc.text().strip()
        self.cfg["vpn_timeout"] = int(self.sp_timeout.value())
        self.cfg["vpn_soft_up_after"] = int(self.sp_soft.value())
        self.cfg["show_all_files"] = bool(self.chk_all.isChecked())
        parts = [p.strip() for p in self.txt_ex.text().split(",") if p.strip()]
        self.cfg["vnc_exclude_patterns"] = parts
        try:
            self.cfg_path.write_text(
                json.dumps(self.cfg, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self.result_cfg = self.cfg
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить: " + str(e))



class TapManagerDialog(QDialog):
    """Окно управления TAP-адаптерами — таблица + мигание нового."""

    TAPINSTALL = r"C:\Program Files\TAP-Windows\bin\tapinstall.exe"
    TAPINF     = r"C:\Program Files\TAP-Windows\driver\OemVista.inf"

    def __init__(self, parent, launcher):
        super().__init__(parent)
        self.launcher = launcher
        self._busy = False
        self._busy_label = ""
        self._dots = 0
        self._flash_timer = None
        self._flash_left = 0
        self._flash_item = None

        _ico = _find_icon()
        if _ico:
            self.setWindowIcon(QIcon(str(_ico)))
        self.setWindowTitle("TAP-адаптеры")
        self.setModal(True)
        self.setMinimumSize(720, 620)
        self.setStyleSheet("""
            QDialog { background-color:#0d1117; }
            QLabel { color:#c9d1d9; background:transparent; }
            QLabel#title { color:#e6edf3; font-size:15pt; font-weight:600; }
            QLabel#subtitle { color:#6e7681; font-size:9pt; }
            QLabel#stats { color:#8b949e; font-size:9pt; }
            QLabel#statsB { color:#e6edf3; font-size:9pt; font-weight:600; }
            QLabel#busy { color:#d29922; font-size:10pt; font-weight:600; }
            QLabel#hint { color:#6e7681; font-size:9pt; }
            QFrame#card {
                background-color:#161b22;
                border:1px solid #21262d;
                border-radius:10px;
            }
            QTreeWidget {
                background:transparent;
                border:none;
                color:#c9d1d9;
                outline:none;
                font-size:10pt;
            }
            QTreeWidget::item {
                padding:11px 6px;
                border-radius:6px;
            }
            QTreeWidget::item:hover { background-color:#1c2128; }
            QTreeWidget::item:selected {
                background-color:#1f6feb;
                color:white;
            }
            QHeaderView::section {
                background-color:transparent;
                color:#6e7681;
                border:none;
                border-bottom:1px solid #21262d;
                padding:8px 6px;
                font-size:8.5pt;
                font-weight:600;
            }
            QPushButton {
                background:transparent;
                border:1px solid #30363d;
                border-radius:7px;
                padding:10px 18px;
                color:#c9d1d9;
                font-weight:600;
                min-height:20px;
            }
            QPushButton:hover { background-color:#21262d; border-color:#484f58; }
            QPushButton:pressed { background-color:#30363d; }
            QPushButton:disabled { color:#484f58; border-color:#21262d; }
            QPushButton#add {
                background-color:#238636; border:none; color:white;
            }
            QPushButton#add:hover { background-color:#2ea043; }
            QPushButton#add:pressed { background-color:#196c2e; }
            QPushButton#add:disabled { background-color:#21262d; color:#484f58; }
            QPushButton#del {
                background:transparent; border:1px solid #f85149; color:#f85149;
            }
            QPushButton#del:hover { background-color:#2d1214; }
            QPushButton#del:pressed { background-color:#442020; }
            QPushButton#del:disabled { color:#484f58; border-color:#21262d; }
            QPushButton#all {
                background:transparent; border:1px solid #8b4449; color:#f85149;
                font-size:9pt; padding:7px 14px;
            }
            QPushButton#all:hover { background-color:#2d1214; }
            QPushButton#all:disabled { color:#484f58; border-color:#21262d; }
            QPushButton#close {
                background-color:#1f6feb; border:none; color:white;
            }
            QPushButton#close:hover { background-color:#388bfd; }
            QPushButton#close:pressed { background-color:#1158c7; }
            QPushButton#close:disabled { background-color:#21262d; color:#484f58; }
            QProgressBar {
                background-color:#161b22; border:none; border-radius:2px;
                height:3px;
            }
            QProgressBar::chunk { background-color:#58a6ff; border-radius:2px; }
            QScrollBar:vertical {
                background:transparent; width:10px; margin:2px;
            }
            QScrollBar::handle:vertical {
                background:#30363d; min-height:30px; border-radius:5px;
            }
            QScrollBar::handle:vertical:hover { background:#484f58; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 20)
        v.setSpacing(14)

        # ============ Header ============
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        ico_lbl = QLabel()
        if _ico:
            ico_lbl.setPixmap(QIcon(str(_ico)).pixmap(36, 36))
        hdr.addWidget(ico_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t = QLabel("TAP-адаптеры")
        t.setObjectName("title")
        title_col.addWidget(t)
        st = QLabel("Управление виртуальными сетевыми интерфейсами для VPN")
        st.setObjectName("subtitle")
        title_col.addWidget(st)
        hdr.addLayout(title_col, 1)
        v.addLayout(hdr)

        # ============ Stats ============
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)
        stats_row.addWidget(QLabel("Всего:"))
        self.lbl_total = QLabel("0")
        self.lbl_total.setObjectName("statsB")
        stats_row.addWidget(self.lbl_total)

        stats_row.addWidget(QLabel("·"))
        stats_row.addWidget(QLabel("Активных:"))
        self.lbl_active = QLabel("0")
        self.lbl_active.setObjectName("statsB")
        stats_row.addWidget(self.lbl_active)

        stats_row.addWidget(QLabel("·"))
        stats_row.addWidget(QLabel("Свободно:"))
        self.lbl_free = QLabel("0")
        self.lbl_free.setObjectName("statsB")
        stats_row.addWidget(self.lbl_free)

        stats_row.addStretch(1)
        v.addLayout(stats_row)

        # ============ Table Card ============
        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(8, 6, 8, 8)
        cv.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["", "АДАПТЕР", "СТАТУС", "INSTANCE ID"])
        # Заголовок требует 4 колонки — а нам надо 3. Уберём лишний столбец
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["АДАПТЕР", "СТАТУС", "INSTANCE ID"])
        self.tree.setRootIsDecorated(False)
        self.tree.setItemsExpandable(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setMinimumHeight(240)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 140)
        self.tree.setColumnWidth(2, 170)
        cv.addWidget(self.tree)
        v.addWidget(card, 1)

        # ============ Hint ============
        hint = QLabel(
            "Один активный VPN занимает один TAP-адаптер. "
            "Если не хватает — добавь новые кнопкой ниже."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        v.addWidget(hint)

        # ============ Progress ============
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setVisible(False)
        v.addWidget(self.progress)

        self.busy_lbl = QLabel("")
        self.busy_lbl.setObjectName("busy")
        self.busy_lbl.setVisible(False)
        v.addWidget(self.busy_lbl)

        # ============ Buttons row 1 ============
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.btn_add = QPushButton("+  Добавить TAP")
        self.btn_add.setObjectName("add")
        self.btn_add.clicked.connect(self._do_add)
        row1.addWidget(self.btn_add)

        self.btn_del = QPushButton("−  Удалить выбранный")
        self.btn_del.setObjectName("del")
        self.btn_del.clicked.connect(self._do_remove)
        row1.addWidget(self.btn_del)

        self.btn_ref = QPushButton("Обновить")
        self.btn_ref.clicked.connect(self._refresh)
        row1.addWidget(self.btn_ref)
        row1.addStretch(1)
        v.addLayout(row1)

        # ============ Buttons row 2 ============
        row2 = QHBoxLayout()
        self.btn_all = QPushButton("Удалить ВСЕ TAP")
        self.btn_all.setObjectName("all")
        self.btn_all.clicked.connect(self._do_remove_all)
        row2.addWidget(self.btn_all)
        row2.addStretch(1)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.setObjectName("close")
        self.btn_close.clicked.connect(self.accept)
        row2.addWidget(self.btn_close)
        v.addLayout(row2)

        # ============ Timers ============
        self._poll_timer = None
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(400)
        self._dot_timer.timeout.connect(self._animate_dots)
        self._dot_timer.start()

        self._refresh()

    # ============ Busy ============
    def _animate_dots(self):
        if not self._busy:
            return
        self._dots = (self._dots + 1) % 4
        self.busy_lbl.setText(self._busy_label + "." * (self._dots + 1))

    def _set_busy(self, busy, label=""):
        self._busy = busy
        self._busy_label = label
        for b in (self.btn_add, self.btn_del, self.btn_ref, self.btn_all, self.btn_close):
            b.setEnabled(not busy)
        self.tree.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.busy_lbl.setVisible(busy)
        if busy:
            self._dots = 0
            self.busy_lbl.setText(label + ".")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            self.busy_lbl.setText("")
            QApplication.restoreOverrideCursor()

    # ============ Status dots ============
    def _status_dot(self, color_hex):
        pix = QPixmap(10, 10)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(color_hex))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, 8, 8)
        p.end()
        return QIcon(pix)

    # ============ Refresh ============
    def _refresh(self):
        if self._busy:
            return
        self.tree.clear()

        ps = (
            "Get-NetAdapter -ErrorAction SilentlyContinue | "
            "Where-Object { $_.InterfaceDescription -match 'TAP' } | "
            "ForEach-Object { "
            "$_.Name + '|' + $_.Status + '|' + $_.PnPDeviceID }"
        )
        try:
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=10,
                creationflags=0x08000000)
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
            if not lines:
                it = QTreeWidgetItem(["(TAP-адаптеры не найдены)", "", ""])
                it.setForeground(0, QColor("#6e7681"))
                self.tree.addTopLevelItem(it)
                self._update_stats()
                return

            for line in lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 3:
                    continue
                name, status, inst = parts[0], parts[1], parts[2]

                if status.lower() == "up":
                    dot_color = "#3fb950"
                    status_text = "Подключён"
                    name_color = QColor("#c9d1d9")
                elif status.lower() == "disabled":
                    dot_color = "#d29922"
                    status_text = "Отключён"
                    name_color = QColor("#8b949e")
                else:
                    dot_color = "#6e7681"
                    status_text = "Свободен"
                    name_color = QColor("#8b949e")

                it = QTreeWidgetItem([name, status_text, inst])
                it.setIcon(0, self._status_dot(dot_color))
                it.setForeground(0, name_color)
                it.setForeground(1, QColor(dot_color))
                it.setForeground(2, QColor("#6e7681"))
                it.setData(0, Qt.ItemDataRole.UserRole, {
                    "name": name, "status": status, "instance": inst,
                })
                # Tooltip
                it.setToolTip(0, f"{name}\nСтатус: {status}")
                it.setToolTip(2, inst)
                self.tree.addTopLevelItem(it)

            self._update_stats()
        except Exception as e:
            it = QTreeWidgetItem([f"Ошибка: {e}", "", ""])
            it.setForeground(0, QColor("#f85149"))
            self.tree.addTopLevelItem(it)

    def _update_stats(self):
        total = self.tree.topLevelItemCount()
        active = 0
        for i in range(total):
            d = self.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
            if d and d.get("status", "").lower() == "up":
                active += 1
        self.lbl_total.setText(str(total))
        self.lbl_active.setText(str(active))
        self.lbl_free.setText(str(max(0, total - active)))

    def _get_instances(self):
        result = set()
        for i in range(self.tree.topLevelItemCount()):
            d = self.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
            if d and d.get("instance"):
                result.add(d["instance"])
        return result

    # ============ Flash new item ============
    def _flash_new(self, new_instances):
        if not new_instances:
            return
        target = None
        for i in range(self.tree.topLevelItemCount()):
            d = self.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
            if d and d.get("instance") in new_instances:
                target = self.tree.topLevelItem(i)
                break
        if target is None:
            return
        try:
            self.tree.setCurrentItem(target)
            self.tree.scrollToItem(target)
        except Exception:
            pass
        self._flash_item = target
        self._flash_left = 8
        if self._flash_timer:
            self._flash_timer.stop()
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(200)
        self._flash_timer.timeout.connect(self._flash_tick)
        self._flash_timer.start()

    def _flash_tick(self):
        from PyQt6.QtGui import QBrush, QFont
        if self._flash_left <= 0:
            self._flash_timer.stop()
            if self._flash_item:
                try:
                    for col in range(3):
                        self._flash_item.setBackground(col, QBrush(QColor(0, 0, 0, 0)))
                    f = self._flash_item.font(0)
                    f.setBold(False)
                    for col in range(3):
                        self._flash_item.setFont(col, f)
                except Exception:
                    pass
            self._flash_item = None
            return
        if self._flash_left % 2 == 0:
            bg = QColor("#166534")
        else:
            bg = QColor("#0d3b23")
        if self._flash_item:
            try:
                for col in range(3):
                    self._flash_item.setBackground(col, QBrush(bg))
                f = self._flash_item.font(0)
                f.setBold(True)
                for col in range(3):
                    self._flash_item.setFont(col, f)
            except Exception:
                pass
        self._flash_left -= 1

    # ============ Operations ============
    def _run_busy(self, script_body, label, before_instances=None):
        started, log = self.launcher._run_elevated_script(script_body, label)
        if not started:
            QMessageBox.warning(self, "TAP", "UAC отклонён или ошибка запуска.")
            return

        self._set_busy(True, label)
        tries = [0]

        def tick():
            tries[0] += 1
            if tries[0] > 120:
                self._poll_timer.stop()
                self._set_busy(False)
                QMessageBox.warning(self, "TAP", "Превышено время ожидания.")
                return
            if not log or not log.exists():
                return
            try:
                txt = log.read_text(encoding="utf-8-sig", errors="replace")
            except Exception:
                return
            if "DONE" in txt:
                self._poll_timer.stop()
                self._set_busy(False)
                # Пауза перед refresh, чтобы Windows увидел изменения
                def after_refresh():
                    self._refresh()
                    if before_instances is not None:
                        after = self._get_instances()
                        new = after - before_instances
                        if new:
                            QTimer.singleShot(150, lambda: self._flash_new(new))
                    QTimer.singleShot(1200, self.launcher._update_tap_counter)
                QTimer.singleShot(900, after_refresh)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(400)
        self._poll_timer.timeout.connect(tick)
        self._poll_timer.start()

    def _do_add(self):
        before = self._get_instances()
        tap_esc = self.TAPINSTALL.replace("'", "''")
        inf_esc = self.TAPINF.replace("'", "''")
        lines = [
            "$tapinstall = '" + tap_esc + "'",
            "$inf = '" + inf_esc + "'",
            "if (-not (Test-Path $tapinstall)) {",
            "    'ERROR: tapinstall.exe не найден' | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "    exit 1",
            "}",
            "if (-not (Test-Path $inf)) {",
            "    'ERROR: OemVista.inf не найден' | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "    exit 1",
            "}",
            "('Установка TAP: ' + $inf) | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "(& $tapinstall install $inf tap0901 2>&1 | Out-String) | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "'Новый TAP-адаптер создан.' | Out-File -Append -LiteralPath $log -Encoding UTF8",
        ]
        self._run_busy("\n".join(lines), "Создаю TAP-адаптер", before_instances=before)

    def _do_remove(self):
        item = self.tree.currentItem()
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        name = data["name"]
        inst = data["instance"]
        status = data.get("status", "").lower()

        if status == "up":
            r = QMessageBox.question(
                self, "Удаление активного TAP",
                'Адаптер "' + name + '" сейчас занят активным VPN.\n\n'
                'Удалить его? Сессия может прерваться.')
            if r != QMessageBox.StandardButton.Yes:
                return

        inst_esc = inst.replace("'", "''")
        lines = [
            "$inst = '" + inst_esc + "'",
            "('Удаляю: ' + $inst) | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "$out = & pnputil /remove-device $inst 2>&1 | Out-String",
            "$out | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "if ($LASTEXITCODE -eq 0 -or $out -match 'успешно|successfully') {",
            "    ('OK удалён: ' + $inst) | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "} else {",
            "    ('ERROR: не удалось удалить ' + $inst) | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "}",
        ]
        self._run_busy("\n".join(lines), "Удаляю TAP-адаптер")

    def _do_remove_all(self):
        r = QMessageBox.question(
            self, "Удаление всех TAP",
            "Удалить ВСЕ TAP-адаптеры?\n\nАктивные VPN будут отключены.")
        if r != QMessageBox.StandardButton.Yes:
            return
        tap_esc = self.TAPINSTALL.replace("'", "''")
        lines = [
            "$tapinstall = '" + tap_esc + "'",
            "if (Test-Path $tapinstall) {",
            "    ('Удаление всех TAP...') | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "    (& $tapinstall remove tap0901 2>&1 | Out-String) | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "} else {",
            "    'ERROR: tapinstall.exe не найден' | Out-File -Append -LiteralPath $log -Encoding UTF8",
            "}",
            "'Все TAP-адаптеры удалены.' | Out-File -Append -LiteralPath $log -Encoding UTF8",
        ]
        self._run_busy("\n".join(lines), "Удаляю все TAP-адаптеры")

class Launcher(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.sessions = {}
        self.next_session_id = 1
        self.active_session_id = None
        self.vpn_list = []
        self.all_files = []
        self.exts = {e.lower() for e in cfg["vnc_extensions"]}
        self.show_all_files = bool(cfg.get("show_all_files", True))
        self.excludes = [p.lower() for p in cfg["vnc_exclude_patterns"]]
        self.icon_provider = QFileIconProvider()
        self.poll_timer = None

        self.setWindowTitle("Connect Hub")
        scr = QApplication.primaryScreen()
        geo = scr.availableGeometry() if scr else None
        if geo:
            w = min(1400, int(geo.width() * 0.9))
            h = min(880, int(geo.height() * 0.88))
        else:
            w, h = 1200, 760
        self.resize(w, h)
        self.setMinimumSize(900, 600)

        self._name_cache = {}
        root_path = Path(cfg['vnc_root'])
        self._icon_folder = self.icon_provider.icon(QFileInfo(str(root_path)))
        self._icon_vnc = self.icon_provider.icon(QFileInfo(str(root_path / 'dummy.vnc')))
        self._icon_file = self.icon_provider.icon(QFileInfo(str(root_path / 'dummy.txt')))
        self._dirs = set()
        self._files_by_dir = {}
        self._tap_timer = None
        self._really_quit = False
        self._tray_hint_shown = False
        self._tray = None
        self._local_server = None
        self._tap_total = 0
        self._tap_busy = 0
        self._tap_log = None
        self._tap_tries = 0
        self._tree_debounce = QTimer(self)
        self._tree_debounce.setSingleShot(True)
        self._tree_debounce.setInterval(300)
        self._tree_debounce.timeout.connect(self._build_tree)

        self._build_ui()
        QTimer.singleShot(0, self._initial_scan)

    def _is_alive(self, s):
        return s.proc is not None and s.proc.poll() is None

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_body(), 1)
        root.addWidget(self._make_sessions())

        sb = self.statusBar()
        self.status_left = QLabel("Готов.")
        self.status_right = QLabel("")
        self.status_left.setStyleSheet("color:#8b949e; font-size:9pt; padding-left:14px;")
        self.status_right.setStyleSheet("color:#8b949e; font-size:9pt; padding-right:14px;")
        sb.addWidget(self.status_left, 1)
        sb.addPermanentWidget(self.status_right)

        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(
            lambda: self.status_right.setText(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self._clock.start()
        self._init_tray()
        self._init_single_instance_server()

    def _make_header(self):
        bar = QFrame()
        bar.setStyleSheet("QFrame { background-color:#161b22; border-bottom:1px solid #30363d; }")
        bar.setFixedHeight(62)
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(10)

        brand = QLabel("Connect Hub")
        brand.setObjectName("brand")
        h.addWidget(brand)
        h.addSpacing(30)

        self.pill_vpn = self._make_pill("#58a6ff", "#0c2d48", "0 профилей")
        self.pill_active = self._make_pill("#d29922", "#3d2a05", "0 активных")
        self.pill_files = self._make_pill("#3fb950", "#0d2f1b", "0 файлов")
        h.addWidget(self.pill_vpn[0])
        h.addWidget(self.pill_active[0])
        h.addWidget(self.pill_files[0])
        h.addStretch(1)

        self.btn_tapmgr = QPushButton("TAP-АДАПТЕРЫ")
        self.btn_tapmgr.clicked.connect(self._open_tap_manager)
        h.addWidget(self.btn_tapmgr)

        self.btn_settings = QPushButton("НАСТРОЙКИ")
        self.btn_settings.clicked.connect(self._open_settings)
        h.addWidget(self.btn_settings)

        self.btn_tap_restart = QPushButton("ПЕРЕЗАПУСТИТЬ TAP")
        self.btn_tap_restart.clicked.connect(self._restart_taps)
        h.addWidget(self.btn_tap_restart)

        self.btn_refresh = QPushButton("ОБНОВИТЬ")
        b1 = self.btn_refresh
        b1.clicked.connect(self._initial_scan)
        h.addWidget(b1)
        b2 = QPushButton("ОТКЛЮЧИТЬ ВСЁ")
        b2.setObjectName("danger")
        b2.clicked.connect(self._disconnect_all)
        h.addWidget(b2)
        return bar

    def _make_pill(self, dot_color, bg_color, text):
        pill = QFrame()
        pill.setStyleSheet(f"QFrame {{ background-color:{bg_color}; border-radius:12px; }}")
        pill.setFixedHeight(28)
        h = QHBoxLayout(pill)
        h.setContentsMargins(10, 0, 12, 0)
        h.setSpacing(7)
        dot = QLabel("\u25CF")
        dot.setStyleSheet(f"color:{dot_color}; font-size:11pt; background:transparent;")
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#c9d1d9; font-size:9pt; background:transparent;")
        h.addWidget(dot)
        h.addWidget(lbl)
        return pill, dot, lbl

    def _make_body(self):
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setStyleSheet("QSplitter::handle { background:transparent; }")
        split.setContentsMargins(16, 14, 16, 8)
        split.setHandleWidth(14)

        left = self._make_card("VPN ПРОФИЛИ")
        self.badge_vpn = left["badge"]
        lv = left["layout"]
        self.vpn_search = QLineEdit()
        self.vpn_search.setPlaceholderText("Поиск по имени...")
        self.vpn_search.textChanged.connect(self._render_vpn)
        lv.addWidget(self.vpn_search)
        self.vpn_list_widget = QListWidget()
        self.vpn_list_widget.setIconSize(QSize(18, 18))
        self.vpn_list_widget.itemDoubleClicked.connect(self._on_vpn_activated)
        self.vpn_list_widget.itemActivated.connect(self._on_vpn_activated)
        self.vpn_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.vpn_list_widget.customContextMenuRequested.connect(self._on_vpn_ctx)
        lv.addWidget(self.vpn_list_widget, 1)

        right = self._make_card("ФАЙЛЫ ПОДКЛЮЧЕНИЯ")
        self.badge_files = right["badge"]
        rv = right["layout"]
        self.files_search = QLineEdit()
        self.files_search.setPlaceholderText("Поиск по имени или пути...")
        self.files_search.textChanged.connect(self._schedule_tree)
        rv.addWidget(self.files_search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(False)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Файл", "Папка"])
        self.tree.setColumnWidth(0, 340)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.itemDoubleClicked.connect(self._on_tree_activated)
        self.tree.itemExpanded.connect(self._on_tree_expand)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_ctx)
        rv.addWidget(self.tree, 1)

        row = QHBoxLayout()
        row.setSpacing(8)
        b_open = QPushButton("ОТКРЫТЬ")
        b_open.setObjectName("primary")
        b_open.clicked.connect(self._open_selected)
        row.addWidget(b_open)
        b_show = QPushButton("ПОКАЗАТЬ В ПАПКЕ")
        b_show.clicked.connect(self._show_in_folder)
        row.addWidget(b_show)
        row.addStretch(1)
        rv.addLayout(row)

        split.addWidget(left["card"])
        split.addWidget(right["card"])
        split.setSizes([400, 900])
        return split

    def _make_card(self, title):
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(10)
        h = QHBoxLayout()
        h.setSpacing(8)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        h.addWidget(t)
        badge = QLabel("0")
        badge.setObjectName("cardBadge")
        h.addWidget(badge)
        h.addStretch(1)
        v.addLayout(h)
        return {"card": card, "layout": v, "badge": badge}

    def _make_sessions(self):
        card = QFrame()
        card.setObjectName("card")
        card.setFixedHeight(200)
        card.setStyleSheet(
            "QFrame#card { background-color:#161b22; border:1px solid #30363d;"
            " border-radius:10px; margin: 0 16px 8px 16px; }")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(8)
        h = QHBoxLayout()
        h.setSpacing(8)
        t = QLabel("АКТИВНЫЕ СЕССИИ")
        t.setObjectName("cardTitle")
        h.addWidget(t)
        self.badge_sessions = QLabel("0")
        self.badge_sessions.setObjectName("cardBadge")
        h.addWidget(self.badge_sessions)
        h.addStretch(1)
        v.addLayout(h)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_session)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        v.addWidget(self.tabs, 1)
        return card




    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.status_left.setText("Системный трей недоступен")
            return
        self._tray = QSystemTrayIcon(self)
        ico = _find_icon()
        if ico:
            self._tray.setIcon(QIcon(str(ico)))
        else:
            self._tray.setIcon(self.windowIcon())
        self._tray.setToolTip("Connect Hub")

        m = QMenu()
        a_show = m.addAction("Развернуть")
        a_show.triggered.connect(self._show_from_tray)
        m.addSeparator()
        a_quit = m.addAction("Выход")
        a_quit.triggered.connect(self._quit_from_tray)
        self._tray.setContextMenu(m)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger or \
           reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_from_tray(self):
        self._really_quit = True
        self.close()

    def _check_other_instance(self, sock):
        try:
            data = bytes(sock.readAll()).decode("utf-8", errors="replace")
            if "SHOW" in data:
                self._show_from_tray()
        except Exception:
            pass
        try:
            sock.disconnectFromServer()
        except Exception:
            pass

    def _init_single_instance_server(self):
        self._local_server = QLocalServer(self)
        try:
            QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        except Exception:
            pass
        if not self._local_server.listen(SINGLE_INSTANCE_KEY):
            self.status_left.setText("Не удалось занять single-instance слот")
            return
        def on_new_conn():
            while self._local_server.hasPendingConnections():
                c = self._local_server.nextPendingConnection()
                c.readyRead.connect(lambda cc=c: self._check_other_instance(cc))
        self._local_server.newConnection.connect(on_new_conn)

    def _update_tap_counter(self):
        try:
            total, busy = _count_taps()
            self._tap_total = total
            self._tap_busy = busy
            print(f"[TAP] total={total}, busy={busy}")
            try:
                with open(HERE / "tap_debug.log", "a", encoding="utf-8") as f:
                    from datetime import datetime as _dt
                    f.write(f"[{_dt.now().isoformat()}] total={total} busy={busy}\n")
            except Exception:
                pass
        except Exception as e:
            print("[TAP] error:", e)
            self._tap_total = 0
            self._tap_busy = 0
        # обновляем статус-бар
        try:
            self._update_counters()
        except Exception:
            pass

    def _has_free_tap(self):
        self._update_tap_counter()
        if self._tap_total == 0:
            return False, "TAP-адаптеры не найдены"
        if self._tap_busy >= self._tap_total:
            return False, f"Все {self._tap_total} TAP-адаптеров заняты"
        return True, ""


    def _run_elevated_script(self, script_body, label="task"):
        import tempfile
        temp = Path(tempfile.gettempdir())
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        ps_file = temp / f"connecthub-elev-{stamp}.ps1"
        log_file = temp / f"connecthub-elev-{stamp}.log"

        header = (
            "$ErrorActionPreference='Continue'\n"
            "$log = '" + str(log_file).replace("'", "''") + "'\n"
            "'START' | Out-File -LiteralPath $log -Encoding UTF8\n"
        )
        footer = "\n'DONE' | Out-File -LiteralPath $log -Append -Encoding UTF8\n"
        ps_file.write_text(header + script_body + footer, encoding="utf-8-sig")

        params = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + str(ps_file) + '"'
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe", params, None, 0)
            return rc > 32, log_file
        except Exception:
            return False, None

    def _open_tap_manager(self):
        try:
            self.btn_tapmgr.setEnabled(False)
            self.btn_tapmgr.setText("ОТКРЫВАЮ...")
            QApplication.processEvents()
        except Exception:
            pass
        try:
            dlg = TapManagerDialog(self, self)
            dlg.exec()
            self._update_tap_counter()
        finally:
            try:
                self.btn_tapmgr.setEnabled(True)
                self.btn_tapmgr.setText("TAP-АДАПТЕРЫ")
            except Exception:
                pass

    def _open_settings(self):
        try:
            self.btn_settings.setEnabled(False)
            self.btn_settings.setText("ЗАГРУЗКА...")
            QApplication.processEvents()
        except Exception:
            pass
        try:
            dlg = SettingsDialog(self, self.cfg, CONFIG_PATH)
        except Exception:
            try:
                self.btn_settings.setEnabled(True)
                self.btn_settings.setText("НАСТРОЙКИ")
            except Exception:
                pass
            raise
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_cfg:
            self.cfg = dlg.result_cfg
            self.exts = {e.lower() for e in self.cfg["vnc_extensions"]}
            self.excludes = [p.lower() for p in self.cfg["vnc_exclude_patterns"]]
            self.show_all_files = bool(self.cfg.get("show_all_files", True))
            self._name_cache.clear()
            try:
                if CACHE_PATH.exists():
                    CACHE_PATH.unlink()
            except Exception:
                pass
            self.status_left.setText("Настройки сохранены. Пересканирую...")
            try:
                self.btn_settings.setEnabled(True)
                self.btn_settings.setText("НАСТРОЙКИ")
            except Exception:
                pass
            self._initial_scan()
            return
        try:
            self.btn_settings.setEnabled(True)
            self.btn_settings.setText("НАСТРОЙКИ")
        except Exception:
            pass

    def _restart_taps(self):
        try:
            self.btn_tap_restart.setEnabled(False)
            self.btn_tap_restart.setText("ЗАПУСКАЮ...")
            QApplication.processEvents()
        except Exception:
            pass
        try:
            self._restart_taps_impl()
        finally:
            try:
                self.btn_tap_restart.setEnabled(True)
                self.btn_tap_restart.setText("ПЕРЕЗАПУСТИТЬ TAP")
            except Exception:
                pass

    def _restart_taps_impl(self):
        import tempfile
        temp = Path(tempfile.gettempdir())
        script = temp / "restart_taps.ps1"
        log = temp / "restart_taps.log"
        try:
            if log.exists():
                log.unlink()
        except Exception:
            pass

        ps_lines = [
            "$ErrorActionPreference = 'Continue'",
            "$log = '" + str(log).replace("'", "''") + "'",
            "'Инициализация...' | Out-File -LiteralPath $log -Encoding UTF8",
            "$adapters = Get-NetAdapter | Where-Object {",
            "    $_.InterfaceDescription -match 'TAP' -or",
            "    $_.Name -match 'TAP' -or",
            "    $_.InterfaceDescription -match 'OpenVPN'",
            "}",
            "if (-not $adapters) {",
            "    'TAP-адаптеры не найдены.' | Out-File -LiteralPath $log -Append -Encoding UTF8",
            "} else {",
            "    foreach ($a in $adapters) {",
            "        ('Отключаю: ' + $a.Name + '  [' + $a.InterfaceDescription + ']') | Out-File -LiteralPath $log -Append -Encoding UTF8",
            "        try { Disable-NetAdapter -Name $a.Name -Confirm:$false -ErrorAction Stop }",
            "        catch { ('  ошибка: ' + $_) | Out-File -LiteralPath $log -Append -Encoding UTF8 }",
            "    }",
            "    Start-Sleep -Seconds 2",
            "    foreach ($a in $adapters) {",
            "        ('Включаю: ' + $a.Name) | Out-File -LiteralPath $log -Append -Encoding UTF8",
            "        try { Enable-NetAdapter -Name $a.Name -Confirm:$false -ErrorAction Stop }",
            "        catch { ('  ошибка: ' + $_) | Out-File -LiteralPath $log -Append -Encoding UTF8 }",
            "    }",
            "}",
            "'DONE' | Out-File -LiteralPath $log -Append -Encoding UTF8",
        ]
        script.write_text("\n".join(ps_lines), encoding="utf-8-sig")

        # ============ Диалог с прогрессом ============
        dlg = QDialog(self)
        dlg.setWindowTitle("Перезапуск TAP")
        dlg.setModal(True)
        dlg.setFixedSize(500, 170)
        dlg.setStyleSheet("QDialog { background-color:#161b22; }")

        v = QVBoxLayout(dlg)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)

        title_lbl = QLabel("Перезапуск TAP-адаптеров")
        title_lbl.setStyleSheet("color:#c9d1d9; font-size:13pt; font-weight:600; background:transparent;")
        v.addWidget(title_lbl)

        step_lbl = QLabel("Ожидание подтверждения UAC...")
        step_lbl.setStyleSheet("color:#8b949e; font-size:10pt; background:transparent;")
        step_lbl.setWordWrap(True)
        v.addWidget(step_lbl)

        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        bar.setStyleSheet(
            "QProgressBar { border:none; background:#0d1117; border-radius:3px; }"
            "QProgressBar::chunk { background:#58a6ff; border-radius:3px; }"
        )
        v.addWidget(bar)

        v.addStretch(1)

        dlg.show()
        QApplication.processEvents()

        # ============ Запуск elevated ============
        try:
            params = ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'
                      + str(script) + '"')
            rc = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe", params, None, 0)
            if rc <= 32:
                dlg.close()
                QMessageBox.warning(self, "Ошибка",
                    "Запрос прав администратора отклонён (код " + str(rc) + ").")
                return
        except Exception as e:
            dlg.close()
            QMessageBox.warning(self, "Ошибка", str(e))
            return

        state = {"tries": 0, "done": False, "seen_steps": 0}

        def tick():
            state["tries"] += 1
            if state["tries"] > 180:  # ~90 сек
                timer.stop()
                dlg.close()
                QMessageBox.warning(self, "TAP", "Превышено время ожидания.")
                return
            if not log.exists():
                return
            try:
                text = log.read_text(encoding="utf-8-sig", errors="replace")
            except Exception:
                return
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines:
                last = lines[-1]
                if last != "DONE":
                    step_lbl.setText(last)
            if "DONE" in text and not state["done"]:
                state["done"] = True
                timer.stop()
                title_lbl.setText("Готово")
                step_lbl.setText("TAP-адаптеры успешно перезапущены.")
                bar.setRange(0, 1)
                bar.setValue(1)
                bar.setStyleSheet(
                    "QProgressBar { border:none; background:#0d1117; border-radius:3px; }"
                    "QProgressBar::chunk { background:#3fb950; border-radius:3px; }"
                )
                QTimer.singleShot(1600, dlg.accept)
                try:
                    log.unlink()
                except Exception:
                    pass
                self.status_left.setText("TAP-адаптеры перезапущены.")
                # Обновить счётчик адаптеров через паузу (адаптеры ещё инициализируются)
                QTimer.singleShot(1500, self._update_tap_counter)

        timer = QTimer(dlg)
        timer.setInterval(500)
        timer.timeout.connect(tick)
        timer.start()
        dlg.exec()


    def _poll_tap(self):
        self._tap_tries += 1
        log = getattr(self, "_tap_log", None)
        if not log:
            self._tap_timer.stop()
            return
        if log.exists():
            try:
                text = log.read_text(encoding="utf-8-sig", errors="replace")
            except Exception:
                text = ""
            if "DONE" in text:
                self._tap_timer.stop()
                lines = [l for l in text.splitlines() if l.strip() and l.strip() != "DONE"]
                QMessageBox.information(self, "TAP перезапущены", "\n".join(lines))
                self.status_left.setText("TAP-адаптеры перезапущены.")
                try:
                    log.unlink()
                except Exception:
                    pass
                return
        if self._tap_tries > 60:  # ~40 секунд
            self._tap_timer.stop()
            self.status_left.setText("Таймаут перезапуска TAP.")
            QMessageBox.warning(self, "TAP", "Превышено время ожидания.\n"
                "Проверь, разрешил ли ты UAC и запущены ли службы сети.")


    def _initial_scan(self):
        if getattr(self, "_scan_running", False):
            return
        self._scan_running = True
        self.status_left.setText("Загрузка кэша...")
        QApplication.processEvents()
        if not self._load_cache():
            self.status_left.setText("Сканирую (первый запуск, ~10 сек)...")
            QApplication.processEvents()
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        try:
            self._scan_vpn()
            QTimer.singleShot(0, self._render_vpn)
            QTimer.singleShot(0, lambda: self.status_left.setText("Сканирую файлы подключений..."))
            self._scan_vnc()
            self._save_cache()
            QTimer.singleShot(0, self._update_tap_counter)
            QTimer.singleShot(0, self._build_tree)
            QTimer.singleShot(0, self._update_counters)
            QTimer.singleShot(0, lambda: self.status_left.setText("Готов."))
            QTimer.singleShot(0, lambda: (self.btn_refresh.setEnabled(True), self.btn_refresh.setText("ОБНОВИТЬ")))
        except Exception:
            import traceback
            tb = traceback.format_exc()
            QTimer.singleShot(0, lambda t=tb: self._log_error(t))
        finally:
            self._scan_running = False

    def _log_error(self, tb):
        try:
            p = HERE / "errors.log"
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n")
                f.write("[" + datetime.now().isoformat() + "]\n")
                f.write(tb)
                f.write("\n")
        except Exception:
            pass

    def _scan_vpn(self):
        self.vpn_list = []
        d = Path(self.cfg["vpn_dir"])
        if not d.exists():
            return
        try:
            self.vpn_list = sorted(
                (p for p in d.glob("*.bat") if p.is_file()),
                key=lambda p: p.stem.lower())
        except Exception:
            pass

    def _iter_files_fast(self, root):
        stack = [str(root)]
        while stack:
            cur = stack.pop()
            try:
                for entry in os.scandir(cur):
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            yield Path(entry.path)
                    except OSError:
                        pass
            except OSError:
                pass

    def _scan_vnc(self):
        self.all_files = []
        self._name_cache.clear()
        roots = [Path(self.cfg["vnc_root"])] + [Path(p) for p in self.cfg["extra_vnc_roots"]]
        for root in roots:
            if not root.exists():
                continue
            try:
                for p in self._iter_files_fast(root):
                    if not self.show_all_files and p.suffix.lower() not in self.exts:
                        continue
                    try:
                        rel = p.relative_to(root)
                    except ValueError:
                        continue
                    parts = rel.parts[:-1]
                    if any(any(pat in part.lower() for pat in self.excludes)
                           for part in parts):
                        continue
                    self.all_files.append(p)
            except Exception:
                continue
        self.all_files.sort(key=lambda p: str(p).lower())

    def _load_cache(self):
        try:
            if CACHE_PATH.exists():
                data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                files = [Path(p) for p in data.get("files", [])]
                if files:
                    self.all_files = files
                    self._build_tree()
                    self._update_counters()
                    return True
        except Exception:
            pass
        return False

    def _save_cache(self):
        try:
            data = {"files": [str(p) for p in self.all_files]}
            CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


    def _render_vpn(self):
        self.vpn_list_widget.clear()
        q = self.vpn_search.text().strip()
        dummy = Path(self.cfg["vpn_dir"]) / "dummy.bat"
        icon_bat = self.icon_provider.icon(QFileInfo(str(dummy)))
        for p in self.vpn_list:
            if q and not _matches(q, p.stem):
                continue
            it = QListWidgetItem(icon_bat, p.stem)
            it.setData(Qt.ItemDataRole.UserRole, str(p))
            self.vpn_list_widget.addItem(it)

    def _schedule_tree(self):
        self._tree_debounce.start()

    def _build_tree(self):
        self.tree.clear()
        root_path = Path(self.cfg["vnc_root"])
        q = self.files_search.text().strip().lower()

        # ============ Активный поиск — плоский список, как раньше ============
        if q:
            q_vars = _variants(q)
            LIMIT = 500
            matched = []
            for f in self.all_files:
                key = str(f)
                cached = self._name_cache.get(key)
                if cached is None:
                    cached = _variants(f.name) | _variants(key)
                    self._name_cache[key] = cached
                hit = False
                for qv in q_vars:
                    if not qv:
                        continue
                    for cv in cached:
                        if qv in cv:
                            hit = True
                            break
                    if hit:
                        break
                if hit:
                    matched.append(f)
                    if len(matched) >= LIMIT:
                        break

            root = QTreeWidgetItem([f"Результаты: {len(matched)}", ""])
            root.setIcon(0, self._icon_folder)
            root.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(root)
            for f in matched:
                try:
                    rel = f.relative_to(root_path)
                    folder = str(rel.parent) if str(rel.parent) != "." else ""
                except ValueError:
                    folder = ""
                it = QTreeWidgetItem([f.name, folder])
                is_vnc = f.suffix.lower() in self.exts
                it.setIcon(0, self._icon_vnc if is_vnc else self._icon_file)
                it.setForeground(0, QColor("#58a6ff") if is_vnc else QColor("#8b949e"))
                it.setForeground(1, QColor("#6e7681"))
                it.setData(0, Qt.ItemDataRole.UserRole, ("FILE", str(f), str(f)))
                it.setToolTip(0, str(f))
                root.addChild(it)
            root.setExpanded(True)
            return

        # ============ Пустой поиск — ленивое дерево ============
        # Индексируем только верхний уровень; вложенное подгружается по клику
        self._dirs.clear()
        self._files_by_dir.clear()
        for f in self.all_files:
            try:
                rel = f.relative_to(root_path)
            except ValueError:
                continue
            parts = rel.parts
            for i in range(1, len(parts)):
                self._dirs.add("/".join(parts[:i]))
            parent_key = "/".join(parts[:-1])
            self._files_by_dir.setdefault(parent_key, []).append(
                (f.name, str(f), f.suffix.lower())
            )

        root_item = QTreeWidgetItem([str(root_path), ""])
        root_item.setIcon(0, self._icon_folder)
        root_item.setData(0, Qt.ItemDataRole.UserRole, ("DIR", "", str(root_path)))
        self.tree.addTopLevelItem(root_item)

        self._fill_item(root_item, "")

        root_item.setExpanded(True)

    def _fill_item(self, node, dir_key):
        node.takeChildren()
        # Файлы текущей папки
        for name, full_path, ext in self._files_by_dir.get(dir_key, []):
            child = QTreeWidgetItem([name, ""])
            is_vnc = ext in self.exts
            child.setIcon(0, self._icon_vnc if is_vnc else self._icon_file)
            child.setForeground(0, QColor("#58a6ff") if is_vnc else QColor("#6e7681"))
            child.setData(0, Qt.ItemDataRole.UserRole, ("FILE", full_path, full_path))
            child.setToolTip(0, full_path)
            node.addChild(child)
        # Подпапки
        prefix = dir_key + "/" if dir_key else ""
        for d in self._dirs:
            if not d.startswith(prefix):
                continue
            rest = d[len(prefix):]
            if "/" in rest:
                continue
            sub = QTreeWidgetItem([rest, ""])
            sub.setIcon(0, self._icon_folder)
            sub.setData(0, Qt.ItemDataRole.UserRole, ("DIR", d, str(Path(self.cfg["vnc_root"]) / d)))
            # placeholder, чтобы стрелка раскрытия отрисовалась
            sub.addChild(QTreeWidgetItem(["..."]))
            node.addChild(sub)

    def _on_tree_expand(self, item):
        tag = item.data(0, Qt.ItemDataRole.UserRole)
        if not tag or tag[0] != "DIR":
            return
        # уже заполнено?
        if item.childCount() == 1 and item.child(0).text(0) == "...":
            item.takeChildren()
            self._fill_item(item, tag[1])


    def _update_counters(self):
        active = sum(1 for s in self.sessions.values()
                     if self._is_alive(s))
        self.pill_vpn[2].setText(f"{len(self.vpn_list)} профилей")
        self.pill_active[2].setText(f"{active} активных")
        self.pill_files[2].setText(f"{len(self.all_files)} файлов")
        self.badge_vpn.setText(str(len(self.vpn_list)))
        vnc_cnt = sum(1 for f in self.all_files if f.suffix.lower() in self.exts)
        self.badge_files.setText(f"{vnc_cnt} / {len(self.all_files)}")
        self.badge_sessions.setText(str(active))
        vnc_total = sum(1 for f in self.all_files if f.suffix.lower() in self.exts)
        tap_info = ""
        if self._tap_total > 0:
            tap_free = self._tap_total - self._tap_busy
            tap_info = f"   ·   TAP свободно: {tap_free}/{self._tap_total}"
        self.status_left.setText(
            f"Профилей: {len(self.vpn_list)}   ·   "
            f"Подключений: {vnc_total}   ·   "
            f"Всего файлов: {len(self.all_files)}   ·   "
            f"Активных сессий: {active}" + tap_info)

    def _start_session(self, bat_path):
        for s in self.sessions.values():
            if s.bat_path == bat_path and s.proc and \
                    self._is_alive(s):
                self.tabs.setCurrentIndex(self.tabs.indexOf(s.page))
                return
        sid = self.next_session_id
        self.next_session_id += 1
        s = VpnSession(sid, bat_path, Path(bat_path).stem)
        self.sessions[sid] = s
        self._create_session_page(s)
        self._launch(s)

    def _create_session_page(self, s):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(10)
        nl = QLabel(s.name)
        nl.setStyleSheet("color:#79c0ff; font-size:12pt; font-weight:600;")
        head.addWidget(nl)
        sl = QLabel("\u25CF CONNECTING...")
        sl.setStyleSheet("color:#d29922; font-size:10pt; font-weight:600;")
        head.addWidget(sl)
        head.addStretch(1)
        sb = QPushButton("ОСТАНОВИТЬ")
        sb.setObjectName("dangerOutline")
        sb.clicked.connect(lambda _, ss=s: self._stop_session(ss))
        head.addWidget(sb)
        v.addLayout(head)

        log = QPlainTextEdit()
        log.setReadOnly(True)
        log.setMaximumBlockCount(20000)
        v.addWidget(log, 1)

        s.page = page
        s.log_edit = log
        s.status_label = sl
        s.stop_btn = sb
        idx = self.tabs.addTab(page, f"\u23F3 {s.name}")
        self.tabs.setCurrentIndex(idx)

    def _launch(self, s):
        bat = Path(s.bat_path)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        temp = os.environ.get("TEMP", "C:\\")
        log_file = Path(temp) / f"vpn-launcher-{stamp}.log"
        runner_file = Path(temp) / f"vpn-launcher-{stamp}.ps1"

        d = str(bat.parent).replace("'", "''")
        f = bat.name.replace("'", "''")
        l = str(log_file).replace("'", "''")

        body = (
            "$ErrorActionPreference = 'Continue'\n"
            "$dir  = '" + d + "'\n"
            "$file = '" + f + "'\n"
            "$log  = '" + l + "'\n"
            "cmd.exe /c \"pushd `\"$dir`\" && call `\"$file`\"\" *>&1 | Out-File -LiteralPath $log -Encoding UTF8\n"
        )
        runner_file.write_text(body, encoding="utf-8")

        self._log(s, f"[VPN] LAUNCH :: {s.bat_path}")
        try:
            p = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-WindowStyle", "Hidden", "-File", str(runner_file)],
                cwd=temp,
                creationflags=0x08000000,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except Exception as e:
            self._log(s, f"[!!] LAUNCH ERROR: {e}")
            self._set_status(s, "error")
            return

        s.proc = p
        s.start_time = time.time()
        s.ready = False
        s.soft_up = False
        s.log_file = log_file
        s.log_pos = 0
        s.runner_file = runner_file

        if self.poll_timer is None:
            self.poll_timer = QTimer(self)
            self.poll_timer.setInterval(400)
            self.poll_timer.timeout.connect(self._poll_sessions)
        if not self.poll_timer.isActive():
            self.poll_timer.start()
        self._update_counters()
        # TAP занялся — обновим счётчик
        QTimer.singleShot(2000, self._update_tap_counter)

    def _poll_sessions(self):
        any_starting = False
        for s in list(self.sessions.values()):
            if not s.proc:
                continue

            # --- читаем новые строки из лог-файла ---
            if s.log_file and s.log_file.exists():
                try:
                    content = s.log_file.read_text(encoding="utf-8-sig", errors="replace")
                    if len(content) > s.log_pos:
                        new_text = content[s.log_pos:]
                        s.log_pos = len(content)
                        for line in new_text.splitlines():
                            if line.strip():
                                self._log(s, line.rstrip())
                        if "Initialization Sequence Completed" in new_text:
                            s.ready = True
                except Exception:
                    pass

            ret = s.proc.poll()

            if ret is not None:
                if s.status == "stopped":
                    continue
                # дочитываем остаток
                if s.log_file and s.log_file.exists():
                    try:
                        content = s.log_file.read_text(encoding="utf-8-sig", errors="replace")
                        if len(content) > s.log_pos:
                            for line in content[s.log_pos:].splitlines():
                                if line.strip():
                                    self._log(s, line.rstrip())
                            s.log_pos = len(content)
                    except Exception:
                        pass
                if s.ready:
                    s.status = "stopped"
                    self._set_status(s, "stopped")
                    self._log(s, "[--] VPN DISCONNECTED")
                else:
                    s.status = "error"
                    self._set_status(s, "error")
                    self._log(s, f"[!!] EXIT CODE {ret}")
                # чистим временные файлы
                for ff in (s.log_file, s.runner_file):
                    try:
                        if ff and ff.exists():
                            ff.unlink()
                    except Exception:
                        pass
                s.proc = None
                self._update_counters()
                continue

            if s.status == "starting" and not s.ready:
                any_starting = True
                elapsed = time.time() - s.start_time if s.start_time else 0
                if not s.soft_up and elapsed >= self.cfg["vpn_soft_up_after"]:
                    s.soft_up = True
                    s.status = "up"
                    self._set_status(s, "up")
                    self._log(s, "[++] VPN ONLINE (по таймауту, маркер не найден)")
                    self._update_counters()
                elif elapsed > self.cfg["vpn_timeout"]:
                    s.status = "error"
                    self._set_status(s, "error")
                    self._log(s, f"[!!] TIMEOUT {self.cfg['vpn_timeout']}s")
            elif s.ready and s.status == "starting":
                s.status = "up"
                self._set_status(s, "up")
                self._log(s, "[++] VPN ONLINE")
                self._update_counters()
        if not any_starting and self.poll_timer:
            self.poll_timer.stop()


    def _set_status(self, s, state):
        styles = {
            "up":       ("\u25CF ONLINE",        "#3fb950", "\U0001F7E2"),
            "error":    ("\u25CF ERROR",         "#f85149", "\U0001F534"),
            "stopped":  ("\u25CF OFFLINE",       "#6e7681", "\u26AA"),
            "starting": ("\u25CF CONNECTING...", "#d29922", "\u23F3"),
        }
        text, color, glyph = styles.get(state, styles["starting"])
        if s.status_label:
            s.status_label.setText(text)
            s.status_label.setStyleSheet(
                f"color:{color}; font-size:10pt; font-weight:600;")
        idx = self.tabs.indexOf(s.page)
        if idx >= 0:
            self.tabs.setTabText(idx, f"{glyph} {s.name}")

    def _log(self, s, msg):
        if not s.log_edit:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        s.log_edit.appendPlainText(f"{ts}  {msg}")

    def _stop_session(self, s):
        if s.proc and s.proc.poll() is None:
            self._log(s, "[VPN] STOPPING...")
            pid = s.proc.pid
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    creationflags=0x08000000, capture_output=True)
            except Exception:
                pass
            try:
                s.proc.wait(timeout=3)
            except Exception:
                pass
        s.status = "stopped"
        self._set_status(s, "stopped")
        self._log(s, "[--] SESSION TERMINATED")
        for ff in (getattr(s, "log_file", None), getattr(s, "runner_file", None)):
            try:
                if ff and ff.exists():
                    ff.unlink()
            except Exception:
                pass
        for ff in (getattr(s, "log_file", None), getattr(s, "runner_file", None)):
            try:
                if ff and ff.exists():
                    ff.unlink()
            except Exception:
                pass
        if s.stop_btn:
            s.stop_btn.setEnabled(False)
            s.stop_btn.setText("ОСТАНОВЛЕН")
        self._update_counters()
        # TAP освободился — обновим счётчик
        QTimer.singleShot(1200, self._update_tap_counter)


    def _close_session(self, index):
        s = None
        for ss in self.sessions.values():
            if self.tabs.indexOf(ss.page) == index:
                s = ss
                break
        if not s:
            return
        alive = self._is_alive(s)
        if alive:
            r = QMessageBox.question(
                self, "Закрытие сессии",
                f'Сессия "{s.name}" активна. Остановить и закрыть?')
            if r != QMessageBox.StandardButton.Yes:
                return
        self._stop_session(s)
        self.tabs.removeTab(index)
        if s.page:
            s.page.deleteLater()
        self.sessions.pop(s.id, None)
        self._update_counters()

    def _disconnect_all(self):
        alive = [s for s in self.sessions.values()
                 if self._is_alive(s)]
        if not alive:
            return
        r = QMessageBox.question(
            self, "Подтверждение",
            f"Остановить все активные VPN ({len(alive)})?")
        if r != QMessageBox.StandardButton.Yes:
            return
        for s in alive:
            self._stop_session(s)
        self._update_counters()

    def _on_tab_changed(self, index):
        for s in self.sessions.values():
            if self.tabs.indexOf(s.page) == index:
                self.active_session_id = s.id
                return

    def _on_vpn_activated(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._start_session(path)

    def _on_vpn_ctx(self, pos):
        item = self.vpn_list_widget.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        a_run = menu.addAction("Запустить VPN")
        a_show = menu.addAction("Показать в папке")
        act = menu.exec(self.vpn_list_widget.mapToGlobal(pos))
        if act == a_run:
            self._start_session(path)
        elif act == a_show:
            subprocess.Popen(["explorer", "/select,", path])

    def _on_tree_activated(self, item, _col):
        tag = item.data(0, Qt.ItemDataRole.UserRole)
        if not tag:
            return
        kind, val, full = tag
        if kind == "FILE":
            self._open_path(full)
        elif kind == "DIR":
            item.setExpanded(not item.isExpanded())

    def _on_tree_ctx(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        tag = item.data(0, Qt.ItemDataRole.UserRole)
        if not tag:
            return
        kind, val, full = tag
        menu = QMenu(self)
        a_open = menu.addAction("Открыть")
        a_show = menu.addAction("Показать в папке")
        act = menu.exec(self.tree.mapToGlobal(pos))
        if act == a_open and kind == "FILE":
            self._open_path(full)
        elif act == a_show:
            if kind == "FILE":
                subprocess.Popen(["explorer", "/select,", full])
            else:
                subprocess.Popen(["explorer", full])

    def _open_selected(self):
        item = self.tree.currentItem()
        if not item:
            return
        tag = item.data(0, Qt.ItemDataRole.UserRole)
        if not tag:
            return
        kind, val, full = tag
        if kind == "FILE":
            self._open_path(full)

    def _show_in_folder(self):
        item = self.tree.currentItem()
        if item:
            tag = item.data(0, Qt.ItemDataRole.UserRole)
            if tag:
                kind, val, full = tag
                if kind == "FILE":
                    subprocess.Popen(["explorer", "/select,", full])
                    return
                else:
                    subprocess.Popen(["explorer", full])
                    return
        subprocess.Popen(["explorer", self.cfg["vnc_root"]])

    def _open_path(self, path):
        try:
            p = Path(path)
            if p.suffix.lower() == ".bat":
                subprocess.Popen(
                    ["cmd.exe", "/c", f'pushd "{p.parent}" && call "{p.name}"'],
                    cwd=os.environ.get("TEMP", "C:\\"),
                    creationflags=0x08000000)
            else:
                os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть:\n{path}\n\n{e}")


    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                QTimer.singleShot(0, self.hide)
                event.ignore()
                return
        super().changeEvent(event)

    def closeEvent(self, event):
        # Если не через меню трея — просто сворачиваем в трей
        if not getattr(self, "_really_quit", False):
            if self._tray is not None:
                self.hide()
                event.ignore()
                if not self._tray_hint_shown:
                    self._tray_hint_shown = True
                    try:
                        self._tray.showMessage(
                            "Connect Hub",
                            "Программа свёрнута в трей. Для выхода — меню трея → Выход.",
                            QSystemTrayIcon.MessageIcon.Information,
                            3500)
                    except Exception:
                        pass
                return

        # Реальный выход
        alive = [s for s in self.sessions.values() if self._is_alive(s)]
        if alive:
            r = QMessageBox.question(
                self, "Выход",
                f"Активных VPN: {len(alive)}. Остановить перед выходом?")
            if r == QMessageBox.StandardButton.Yes:
                for s in alive:
                    self._stop_session(s)
        try:
            if self._local_server:
                self._local_server.close()
                QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        except Exception:
            pass
        try:
            if self._tray:
                self._tray.hide()
        except Exception:
            pass
        event.accept()


def _install_excepthook():
    import traceback
    log = HERE / "errors.log"
    def hook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write("\n[" + datetime.now().isoformat() + "]\n" + tb + "\n")
        except Exception:
            pass
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.critical(None, "Ошибка",
                    exc_type.__name__ + ": " + str(exc_value) +
                    "\n\nПодробности: " + str(log))
        except Exception:
            pass
    sys.excepthook = hook


def _find_icon():
    """Ищет icon.ico в нескольких местах: рядом с exe, _internal, _MEIPASS, рядом со скриптом."""
    candidates = []
    # 1. Рядом с exe
    candidates.append(HERE / "icon.ico")
    # 2. В _internal рядом с exe (onedir PyInstaller)
    candidates.append(HERE / "_internal" / "icon.ico")
    # 3. В _MEIPASS (onefile или как --add-data)
    try:
        import sys as _s
        meipass = getattr(_s, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "icon.ico")
    except Exception:
        pass
    # 4. Рядом с launcher.py (dev-режим)
    try:
        candidates.append(Path(__file__).resolve().parent / "icon.ico")
    except Exception:
        pass
    # 5. CWD
    candidates.append(Path.cwd() / "icon.ico")

    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return None


def _set_appid():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "ConnectHub.App.v1")
    except Exception:
        pass


def main():
    _install_excepthook()
    try:
        _set_appid()
    except Exception:
        pass
    cfg = load_config()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    _icon = _find_icon()
    if _icon:
        app.setWindowIcon(QIcon(str(_icon)))

    # === Single instance: если другой экземпляр уже работает — показать его ===
    sock = QLocalSocket()
    sock.connectToServer(SINGLE_INSTANCE_KEY)
    if sock.waitForConnected(400):
        try:
            sock.write(b"SHOW\n")
            sock.flush()
            sock.waitForBytesWritten(400)
        except Exception:
            pass
        try:
            sock.disconnectFromServer()
        except Exception:
            pass
        return 0

    win = Launcher(cfg)
    if _icon:
        win.setWindowIcon(QIcon(str(_icon)))
    win.show()
    set_dark_titlebar(win)
    QTimer.singleShot(50, lambda: set_dark_titlebar(win))
    QTimer.singleShot(400, lambda: set_dark_titlebar(win))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()