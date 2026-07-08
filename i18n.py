"""
Lightweight i18n module for Rin-TOTP.

Provides a Translator singleton that:
- Loads JSON-based language files from the translations directory
- Exposes translated strings via a QObject (`tr(key)`) callable from QML
- Emits a `languageChanged` signal so QML can re-render
- Supports "follow system" language detection
- Persists language preference

Supported languages (in `translations/` folder):
- zh_CN.json (Simplified Chinese, default)
- en_US.json (English)
"""

import json
import os
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtCore import QObject, Signal, Slot, Property, QLocale


TRANSLATIONS_DIR = Path(__file__).parent / "translations"
CONFIG_FILE = Path(__file__).parent / ".rintotp_lang"

DEFAULT_LANG = "zh_CN"

DEFAULT_STRINGS = {
    "app.title": "Rin-TOTP",
    "nav.codes": "验证码",
    "nav.settings": "设置",
    "nav.about": "关于",
    "header.codes": "验证码",
    "header.add": "+ 添加",
    "empty.title": "暂无账号",
    "empty.subtitle": "点击右上角「+ 添加」按钮添加第一个账号",
    "button.copy": "复制",
    "button.copied": "已复制!",
    "button.unlock": "解锁",
    "button.add": "+ 添加",
    "button.cancel": "取消",
    "menu.edit": "编辑",
    "menu.delete": "删除",
    "menu.detach": "分离到桌面",
    "menu.reattach": "收回卡片",
    "dialog.password.title.new": "设置主密码",
    "dialog.password.title.existing": "输入主密码",
    "dialog.password.desc.new": "请设置一个主密码来保护您的密钥",
    "dialog.password.desc.existing": "请输入主密码以解锁",
    "dialog.password.placeholder": "主密码",
    "dialog.password.confirm": "确认主密码",
    "dialog.password.mismatch": "两次输入的密码不一致",
    "dialog.password.wrong": "密码错误",
    "dialog.password.too_short": "密码长度不能少于 4 位",
    "dialog.addedit.title.new": "添加账号",
    "dialog.addedit.title.edit": "编辑账号",
    "dialog.addedit.name": "账号名",
    "dialog.addedit.issuer": "发行方",
    "dialog.addedit.secret": "密钥",
    "dialog.addedit.otpauth": "或粘贴 otpauth:// 链接",
    "dialog.addedit.digits": "位数",
    "dialog.addedit.period": "周期 (秒)",
    "dialog.addedit.algorithm": "算法",
    "dialog.addedit.name.placeholder": "例如: user@example.com",
    "dialog.addedit.issuer.placeholder": "例如: Google, GitHub",
    "dialog.addedit.secret.placeholder": "Base32 编码的密钥",
    "dialog.addedit.otpauth.placeholder": "otpauth://totp/...",
    "dialog.delete.title": "确认删除",
    "dialog.delete.message": "确定要删除此账号吗？此操作无法撤销。",
    "settings.title": "设置",
    "settings.appearance": "外观",
    "settings.theme": "主题",
    "settings.theme.system": "跟随系统",
    "settings.theme.light": "浅色",
    "settings.theme.dark": "深色",
    "settings.security": "安全",
    "settings.language": "语言",
    "settings.language.auto": "跟随系统",
    "settings.behavior": "行为",
    "settings.close_behavior": "关闭按钮行为",
    "settings.close_ask": "询问 (关闭/隐藏到托盘)",
    "settings.close_minimize": "总是最小化到托盘",
    "settings.close_quit": "总是退出",
    "settings.data": "数据",
    "settings.change_password": "修改主密码",
    "settings.export": "导出数据",
    "settings.import": "导入数据",
    "lock.title": "已锁定",
    "lock.subtitle": "请输入主密码以继续使用",
    "notif.copied": "已复制到剪贴板",
    "notif.card_off": "已收回桌面卡片",
    "notif.card_on": "已分离到桌面",
    "notif.saved": "已保存",
    "notif.deleted": "已删除",
    "common.ok": "确定",
    "common.cancel": "取消",
    "common.close": "关闭",
    "common.confirm": "确认",
    "dialog.close.title": "关闭应用",
    "dialog.close.question": "您希望如何关闭应用？",
    "dialog.close.desc": "隐藏到托盘：应用将继续运行，可从系统托盘恢复\n完全退出：应用将完全关闭，所有桌面卡片也会关闭",
    "dialog.close.hide_to_tray": "隐藏到托盘",
    "dialog.close.quit": "完全退出",
    "dialog.close.cancel": "取消",
    "settings.time_sync": "时间校准",
    "settings.time_offset": "时间偏移",
    "settings.time_offset.desc": "当系统时间不准确时，可手动调整时间偏移量或通过NTP自动校时",
    "settings.sync_ntp": "NTP 校时",
    "settings.reset_time": "重置",
    "settings.ntp_server": "NTP 服务器",
    "settings.ntp_server.placeholder": "输入服务器地址",
    "settings.syncing": "同步中...",
    "settings.time_offset.normal": "时间正常",
    "settings.time_offset.ahead": "系统时间快 {offset} 秒",
    "settings.time_offset.behind": "系统时间慢 {offset} 秒",
}


def _detect_system_language() -> str:
    """Detect the system UI language and return the best-matching lang code.

    Tries (in order):
    1. Exact match against ``uiLanguages()`` (preferred user UI locales).
    2. Exact match against ``QLocale.system().name()``.
    3. Base language fallback to one of the supported codes.
    4. Environment variables ``LC_ALL`` / ``LC_MESSAGES`` / ``LANG`` (useful
       on Linux/macOS where QLocale may report "C" or empty).
    """
    candidates: list[str] = []

    # 1) QLocale.system().uiLanguages() — preferred order list of locale codes.
    try:
        for loc in QLocale.system().uiLanguages():
            candidates.append(loc)
    except Exception:
        pass

    # 2) QLocale.system().name() (single best match).
    try:
        candidates.append(QLocale.system().name())
    except Exception:
        pass

    # 3) Environment variables.
    for env_var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(env_var)
        if val:
            # values may look like "zh_CN.UTF-8" or "en_US.utf8"
            cleaned = val.split(".")[0].strip()
            if cleaned:
                candidates.append(cleaned)

    # Resolve each candidate to a supported language code.
    for cand in candidates:
        if not cand:
            continue
        # Normalize separators — QLocale returns "zh_CN" but env may use "." or "-".
        normalized = cand.replace("-", "_")
        if (TRANSLATIONS_DIR / f"{normalized}.json").exists():
            return normalized
        base = normalized.split("_")[0] if "_" in normalized else normalized
        if base.startswith("zh"):
            return "zh_CN"
        if base.startswith("en"):
            return "en_US"

    return DEFAULT_LANG


def _load_saved_language() -> str:
    """Load saved language preference. Returns empty string if not set."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def _save_language(lang_code: str) -> None:
    """Save language preference to a simple text file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(lang_code)
    except Exception:
        pass


class Translator(QObject):
    """Singleton translator that loads language files and exposes tr() to QML."""

    languageChanged = Signal()

    _instance = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_lang = DEFAULT_LANG
        self._is_auto = False
        self._strings = dict(DEFAULT_STRINGS)
        self._revision = 0  # bumped on every change; QML binds to this

        # Load saved preference (or auto-detect)
        saved = _load_saved_language()
        if saved == "auto" or saved == "":
            self._is_auto = True
            self._current_lang = _detect_system_language()
        else:
            self._is_auto = False
            self._current_lang = saved

        self._load_language(self._current_lang)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = Translator()
        return cls._instance

    def _load_language(self, lang_code: str) -> None:
        """Load strings from a JSON file. Falls back to defaults on failure."""
        self._strings = dict(DEFAULT_STRINGS)

        path = TRANSLATIONS_DIR / f"{lang_code}.json"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._strings.update(data)
        except Exception as e:
            print(f"[i18n] Failed to load {path}: {e}")

    @Slot(str, result=str)
    def tr(self, key: str) -> str:
        """Translate a key. Returns the key itself when missing."""
        return self._strings.get(key, key)

    @Slot(result=str)
    def currentLanguage(self) -> str:
        return self._current_lang

    @Slot(result=bool)
    def isAuto(self) -> bool:
        return self._is_auto

    def _get_language(self):
        return self._current_lang

    language = Property(str, _get_language, notify=languageChanged)

    def _get_revision(self):
        return self._revision

    # QML should bind to ``revision`` to refresh derived text whenever the
    # active language or its underlying strings change.
    revision = Property(int, _get_revision, notify=languageChanged)

    @Slot(str)
    def setLanguage(self, lang_code: str) -> None:
        """Set language by code. Use 'auto' to follow system."""
        print(f"[i18n] setLanguage called with: '{lang_code}', current: '{self._current_lang}', isAuto: {self._is_auto}")
        if lang_code == "auto":
            detected = _detect_system_language()
            print(f"[i18n] Auto-detected language: '{detected}'")
            if not self._is_auto or detected != self._current_lang:
                self._is_auto = True
                self._current_lang = detected
                self._load_language(detected)
                _save_language("auto")
                self._revision += 1
                print(f"[i18n] Emitting languageChanged, new lang: '{self._current_lang}', rev: {self._revision}")
                self.languageChanged.emit()
            return

        if lang_code == self._current_lang and not self._is_auto:
            print(f"[i18n] Language already set to '{lang_code}', skipping")
            return
        self._is_auto = False
        self._current_lang = lang_code
        self._load_language(lang_code)
        _save_language(lang_code)
        self._revision += 1
        print(f"[i18n] Emitting languageChanged, new lang: '{self._current_lang}', rev: {self._revision}")
        self.languageChanged.emit()

    @Slot(result="QVariantList")
    def availableLanguages(self):
        """Return list of {code, name} objects for UI language selector."""
        return [
            {"code": "auto", "name": "跟随系统"},
            {"code": "zh_CN", "name": "简体中文"},
            {"code": "en_US", "name": "English"},
        ]


# Convenience function for Python-side use
def tr(key: str) -> str:
    return Translator.instance().tr(key)
