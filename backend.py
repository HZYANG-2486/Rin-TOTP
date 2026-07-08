"""
Backend bridge between Python TOTP/storage logic and QML frontend.
Exposes TOTPModel (QAbstractListModel), Backend (QObject), and CardManager.
"""

import os
import uuid
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore
from PySide6.QtCore import (
    Qt, QObject, QTimer, Signal, Slot, QModelIndex,
    QAbstractListModel, QUrl, QPersistentModelIndex, Property
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent

from totp import TOTPAccount, TOTPGenerator
from storage import SecureStorage
from i18n import Translator


APP_NAME = "Rin-TOTP"
DATA_DIR = os.path.join(str(Path.home()), ".rintotp")
QML_DIR = Path(__file__).parent / "qml"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


class TOTPModel(QAbstractListModel):
    """QAbstractListModel exposing TOTP accounts with computed code/progress roles."""

    countChanged = Signal()

    IdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    IssuerRole = Qt.UserRole + 3
    LabelRole = Qt.UserRole + 4
    CodeRole = Qt.UserRole + 5       # formatted display code
    RawCodeRole = Qt.UserRole + 6    # raw code for clipboard
    TimeRemainingRole = Qt.UserRole + 7
    ProgressRole = Qt.UserRole + 8
    CardModeRole = Qt.UserRole + 9
    DigitsRole = Qt.UserRole + 10
    PeriodRole = Qt.UserRole + 11
    AlgorithmRole = Qt.UserRole + 12

    _ROLE_NAMES = {
        IdRole: b"accountId",
        NameRole: b"name",
        IssuerRole: b"issuer",
        LabelRole: b"label",
        CodeRole: b"code",
        RawCodeRole: b"rawCode",
        TimeRemainingRole: b"timeRemaining",
        ProgressRole: b"progress",
        CardModeRole: b"cardMode",
        DigitsRole: b"digits",
        PeriodRole: b"period",
        AlgorithmRole: b"algorithm",
    }

    # Roles that change every tick (time-sensitive)
    _TICK_ROLES = [CodeRole, RawCodeRole, TimeRemainingRole, ProgressRole]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accounts: List[TOTPAccount] = []
        self._time_offset: int = 0

    def set_time_offset(self, offset: int):
        self._time_offset = int(offset)
        if self._accounts:
            top = self.index(0)
            bottom = self.index(len(self._accounts) - 1)
            self.dataChanged.emit(top, bottom, self._TICK_ROLES)

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._accounts)

    def _get_count(self):
        return len(self._accounts)

    count = Property(int, _get_count, notify=countChanged)

    def roleNames(self):
        return self._ROLE_NAMES

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._accounts):
            return None
        acc = self._accounts[index.row()]
        if role == self.IdRole:
            return acc.id
        elif role == self.NameRole:
            return acc.name
        elif role == self.IssuerRole:
            return acc.issuer if acc.issuer else "Unknown"
        elif role == self.LabelRole:
            return acc.label
        elif role == self.CodeRole:
            import time
            t = time.time() + self._time_offset
            return TOTPGenerator.format_code(TOTPGenerator.generate(acc, at_time=t))
        elif role == self.RawCodeRole:
            import time
            t = time.time() + self._time_offset
            return TOTPGenerator.generate(acc, at_time=t)
        elif role == self.TimeRemainingRole:
            import time
            t = time.time() + self._time_offset
            return TOTPGenerator.time_remaining(acc.period, at_time=t)
        elif role == self.ProgressRole:
            import time
            t = time.time() + self._time_offset
            return TOTPGenerator.progress(acc.period, at_time=t)
        elif role == self.CardModeRole:
            return acc.card_mode
        elif role == self.DigitsRole:
            return acc.digits
        elif role == self.PeriodRole:
            return acc.period
        elif role == self.AlgorithmRole:
            return acc.algorithm
        return None

    def set_accounts(self, accounts: List[TOTPAccount]):
        self.beginResetModel()
        self._accounts = list(accounts)
        self.endResetModel()
        self.countChanged.emit()

    def get_account(self, account_id: str) -> Optional[TOTPAccount]:
        for acc in self._accounts:
            if acc.id == account_id:
                return acc
        return None

    def tick(self):
        """Emit dataChanged for time-sensitive roles on all rows."""
        if not self._accounts:
            return
        top = self.index(0)
        bottom = self.index(len(self._accounts) - 1)
        self.dataChanged.emit(top, bottom, self._TICK_ROLES)

    def update_row(self, row: int):
        if 0 <= row < len(self._accounts):
            idx = self.index(row)
            self.dataChanged.emit(idx, idx, self._ROLE_NAMES.keys())


class CardManager(QObject):
    """Manages frameless always-on-top desktop card windows for card-mode accounts."""

    cardsChanged = Signal()

    def __init__(self, engine, backend, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._backend = backend
        self._cards = {}          # account_id -> QQuickWindow
        self._component = None
        self._positions = {}      # account_id -> (x, y) remembered positions

    def _get_component(self) -> QQmlComponent:
        if self._component is None:
            url = QUrl.fromLocalFile(str(QML_DIR / "CardWindow.qml"))
            self._component = QQmlComponent(self._engine, url)
            if self._component.isError():
                for err in self._component.errors():
                    print(f"CardWindow QML error: {err.toString()}")
        return self._component

    def sync_cards(self):
        """Show/hide cards to match card_mode flags."""
        accounts = self._backend.get_accounts()
        for acc in accounts:
            if acc.card_mode and acc.id not in self._cards:
                self._show_card(acc)
            elif not acc.card_mode and acc.id in self._cards:
                self._hide_card(acc.id)
        # Close cards for deleted accounts
        active_ids = {a.id for a in accounts}
        for cid in list(self._cards.keys()):
            if cid not in active_ids:
                self._hide_card(cid)

    def _show_card(self, account: TOTPAccount):
        comp = self._get_component()
        if comp is None or comp.isError():
            return

        initial = {
            "accountId": account.id,
            "issuerText": account.issuer or "Unknown",
            "nameText": account.name,
            "period": account.period,
        }
        pos = self._positions.get(account.id)
        if pos:
            initial["cardX"] = pos[0]
            initial["cardY"] = pos[1]

        window = comp.createWithInitialProperties(initial)
        if window is None:
            return

        window.setProperty("backend", self._backend)
        # provide initial code data
        self._update_card(window, account)
        window.show()
        self._cards[account.id] = window
        self.cardsChanged.emit()

    def _hide_card(self, account_id: str):
        window = self._cards.pop(account_id, None)
        if window:
            pos = (window.property("x"), window.property("y"))
            self._positions[account_id] = pos
            window.close()
            window.deleteLater()
            self.cardsChanged.emit()

    def _update_card(self, window, account: TOTPAccount):
        import time
        t = time.time() + self._backend.timeOffset
        code = TOTPGenerator.generate(account, at_time=t)
        time_left = TOTPGenerator.time_remaining(account.period, at_time=t)
        progress = TOTPGenerator.progress(account.period, at_time=t)
        window.setProperty("codeText", TOTPGenerator.format_code(code))
        window.setProperty("rawCode", code)
        window.setProperty("timeRemaining", time_left)
        window.setProperty("progressValue", progress)

    def update_all(self):
        """Refresh code/time on all open card windows."""
        for account_id, window in self._cards.items():
            acc = self._backend.get_account_by_id(account_id)
            if acc:
                self._update_card(window, acc)

    def close_all(self):
        for account_id in list(self._cards.keys()):
            self._hide_card(account_id)

    @Slot(str)
    def hideCard(self, account_id: str):
        """Called from QML when user closes a card window."""
        self._hide_card(account_id)
        # Also turn off card_mode in backend
        self._backend.set_card_mode(account_id, False)


class Backend(QObject):
    """Main backend exposed to QML as a context property."""

    # Signals
    authenticated = Signal()
    accountsChanged = Signal()
    notification = Signal(str, str)  # (title, message)
    requestAddDialog = Signal(str)   # account_id or "" for new
    requestEditDialog = Signal(str)  # account_id
    requestPasswordDialog = Signal(bool)  # is_new
    requestExport = Signal(str)      # data to save
    requestImport = Signal()
    cardModeChanged = Signal(str)    # account_id whose card mode changed
    showTrayMessage = Signal(str, str)  # (title, message) for system tray
    autoLockChanged = Signal(bool)   # auto-lock setting changed
    askOnCloseChanged = Signal(bool) # ask-on-close setting changed
    timeOffsetChanged = Signal(int)  # time offset setting changed (seconds)
    syncingTime = Signal(bool)       # time sync in progress

    def __init__(self, data_dir=DATA_DIR, parent=None):
        super().__init__(parent)
        self._data_dir = data_dir
        self._config_file = os.path.join(data_dir, "config.json")
        self._storage = SecureStorage(data_dir)
        self._model = TOTPModel(self)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._card_manager: Optional[CardManager] = None
        self._config = self._load_config()
        self._model.set_time_offset(self._config.get("time_offset", 0))

    def _load_config(self):
        """Load application configuration from JSON file."""
        default_config = {
            "auto_lock": False,
            "ask_on_close": True,
            "time_offset": 0,
            "ntp_server": "pool.ntp.org",
        }
        if not os.path.exists(self._config_file):
            self._save_config(default_config)
            return default_config
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                import json
                config = json.load(f)
                return {**default_config, **config}
        except Exception:
            return default_config

    def _save_config(self, config=None):
        """Save application configuration to JSON file."""
        if config is None:
            config = self._config
        try:
            import json
            os.makedirs(self._data_dir, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    # --- Properties for QML ---

    @Slot(result="QVariant")
    def model(self):
        return self._model

    @Slot(result="QVariant")
    def translator(self):
        return Translator.instance()

    # --- Configuration ---

    def _get_auto_lock(self):
        return self._config.get("auto_lock", False)

    def _set_auto_lock(self, enabled: bool):
        if self._config.get("auto_lock", False) != enabled:
            self._config["auto_lock"] = enabled
            self._save_config()
            self.autoLockChanged.emit(enabled)

    autoLock = Property(bool, _get_auto_lock, _set_auto_lock, notify=autoLockChanged)

    def _get_ask_on_close(self):
        return self._config.get("ask_on_close", True)

    def _set_ask_on_close(self, enabled: bool):
        if self._config.get("ask_on_close", True) != enabled:
            self._config["ask_on_close"] = enabled
            self._save_config()
            self.askOnCloseChanged.emit(enabled)

    askOnClose = Property(bool, _get_ask_on_close, _set_ask_on_close, notify=askOnCloseChanged)

    def _get_time_offset(self):
        return self._config.get("time_offset", 0)

    def _set_time_offset(self, offset: int):
        if self._config.get("time_offset", 0) != offset:
            self._config["time_offset"] = int(offset)
            self._save_config()
            self.timeOffsetChanged.emit(int(offset))
            self._model.set_time_offset(int(offset))
            if self._card_manager:
                self._card_manager.update_all()

    timeOffset = Property(int, _get_time_offset, _set_time_offset, notify=timeOffsetChanged)

    ntpServerChanged = Signal(str)

    def _get_ntp_server(self):
        return self._config.get("ntp_server", "pool.ntp.org")

    def _set_ntp_server(self, server: str):
        if server and self._config.get("ntp_server", "pool.ntp.org") != server:
            self._config["ntp_server"] = server.strip()
            self._save_config()
            self.ntpServerChanged.emit(server.strip())

    ntpServer = Property(str, _get_ntp_server, _set_ntp_server, notify=ntpServerChanged)

    @Slot(result="QVariantList")
    def ntpServers(self):
        """Return list of common NTP servers for UI selector."""
        return [
            {"name": "pool.ntp.org", "display": "NTP Pool (全球)"},
            {"name": "time.windows.com", "display": "Windows Time"},
            {"name": "time.apple.com", "display": "Apple Time"},
            {"name": "ntp.aliyun.com", "display": "阿里云 NTP"},
            {"name": "ntp.tencent.com", "display": "腾讯云 NTP"},
            {"name": "cn.pool.ntp.org", "display": "中国 NTP Pool"},
            {"name": "asia.pool.ntp.org", "display": "亚洲 NTP Pool"},
            {"name": "custom", "display": "自定义..."},
        ]

    @Slot(result=float)
    def currentTime(self):
        """Return current time adjusted by offset."""
        import time
        return time.time() + self._config.get("time_offset", 0)

    @Slot()
    def syncTimeNtp(self):
        """Sync time with NTP server in a background thread."""
        import threading
        self.syncingTime.emit(True)

        def do_sync():
            import time
            import socket
            import struct

            try:
                ntp_server = self._config.get("ntp_server", "pool.ntp.org")
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client.settimeout(5)

                data = b'\x1b' + 47 * b'\0'
                client.sendto(data, (ntp_server, 123))
                data, _ = client.recvfrom(1024)
                client.close()

                if data:
                    t = struct.unpack('!12I', data)[10]
                    t -= 2208988800
                    local_time = time.time()
                    offset = int(t - local_time)
                    self._set_time_offset(offset)
                    self.notification.emit("成功", f"已与 {ntp_server} 同步，时间偏移: {offset} 秒")
            except Exception as e:
                self.notification.emit("错误", f"校时失败: {str(e)}")
            finally:
                self.syncingTime.emit(False)

        threading.Thread(target=do_sync, daemon=True).start()

    # --- Authentication ---

    @Slot(result=bool)
    def hasPassword(self):
        return self._storage.has_password()

    @Slot(str, str, result=bool)
    def setupPassword(self, password, confirm):
        if not password or password != confirm:
            return False
        self._storage.set_password(password)
        self.lockedChanged.emit(False)
        self.authenticated.emit()
        return True

    @Slot(str, result=bool)
    def verifyPassword(self, password):
        if self._storage.verify_password(password):
            self._load_and_notify()
            self.lockedChanged.emit(False)
            self.authenticated.emit()
            return True
        return False

    lockedChanged = Signal(bool)

    def _get_is_locked(self):
        return self._storage.is_locked()

    isLocked = Property(bool, _get_is_locked, notify=lockedChanged)

    @Slot()
    def lock(self):
        self._storage.lock()
        self._model.set_accounts([])
        if self._card_manager:
            self._card_manager.close_all()
        self.lockedChanged.emit(True)
        self.requestPasswordDialog.emit(False)

    @Slot()
    def minimizeToTray(self):
        """Called from QML when the main window is hidden to tray."""
        self.showTrayMessage.emit("Rin-TOTP", "应用已最小化到系统托盘，点击图标恢复")

    @Slot(str)
    def hideCard(self, account_id: str):
        """Delegate from a desktop card's close button to the card manager."""
        if self._card_manager:
            self._card_manager.hideCard(account_id)

    # --- Account CRUD ---

    def _load_and_notify(self):
        accounts = self._storage.load_accounts()
        self._model.set_accounts(accounts)
        self.accountsChanged.emit()
        if self._card_manager:
            self._card_manager.sync_cards()

    @Slot(result=int)
    def accountCount(self):
        return len(self._model._accounts)

    def get_accounts(self) -> List[TOTPAccount]:
        return list(self._model._accounts)

    def get_account_by_id(self, account_id: str) -> Optional[TOTPAccount]:
        return self._model.get_account(account_id)

    @Slot(str, result="QVariant")
    def getAccount(self, account_id):
        acc = self._model.get_account(account_id)
        if not acc:
            return {}
        return {
            "id": acc.id,
            "name": acc.name,
            "issuer": acc.issuer,
            "secret": acc.secret,
            "digits": acc.digits,
            "period": acc.period,
            "algorithm": acc.algorithm,
            "card_mode": acc.card_mode,
        }

    @Slot("QVariant", result=bool)
    def addAccount(self, data):
        try:
            # Convert QJSValue to Python dict
            from PySide6.QtQml import QJSValue
            if isinstance(data, QJSValue):
                data = data.toVariant()
            
            name = data.get("name", "").strip()
            secret = data.get("secret", "").strip().upper()
            if not name or not secret:
                self.notification.emit("警告", "账号名和密钥不能为空")
                return False
            if not TOTPGenerator.validate_secret(secret):
                self.notification.emit("警告", "密钥格式不正确（必须是Base32格式）")
                return False

            account = TOTPAccount(
                id=str(uuid.uuid4()),
                name=name,
                issuer=data.get("issuer", "").strip(),
                secret=secret,
                digits=int(data.get("digits", 6)),
                period=int(data.get("period", 30)),
                algorithm=data.get("algorithm", "SHA1"),
                card_mode=bool(data.get("card_mode", False)),
            )
            accounts = self.get_accounts()
            accounts.append(account)
            self._storage.save_accounts(accounts)
            self._load_and_notify()
            self.notification.emit("成功", f"已添加账号: {account.label}")
            return True
        except Exception as e:
            self.notification.emit("错误", f"添加失败: {e}")
            return False

    @Slot(str, "QVariant", result=bool)
    def updateAccount(self, account_id, data):
        acc = self._model.get_account(account_id)
        if not acc:
            return False
        try:
            # Convert QJSValue to Python dict
            from PySide6.QtQml import QJSValue
            if isinstance(data, QJSValue):
                data = data.toVariant()
            
            name = data.get("name", "").strip()
            secret = data.get("secret", "").strip().upper()
            if not name or not secret:
                self.notification.emit("警告", "账号名和密钥不能为空")
                return False
            if not TOTPGenerator.validate_secret(secret):
                self.notification.emit("警告", "密钥格式不正确")
                return False

            acc.name = name
            acc.issuer = data.get("issuer", "").strip()
            acc.secret = secret
            acc.digits = int(data.get("digits", 6))
            acc.period = int(data.get("period", 30))
            acc.algorithm = data.get("algorithm", "SHA1")

            self._storage.save_accounts(self.get_accounts())
            self._load_and_notify()
            self.notification.emit("成功", "账号已更新")
            return True
        except Exception as e:
            self.notification.emit("错误", f"更新失败: {e}")
            return False

    @Slot(str, result=bool)
    def deleteAccount(self, account_id):
        accounts = [a for a in self.get_accounts() if a.id != account_id]
        if len(accounts) == len(self.get_accounts()):
            return False
        self._storage.save_accounts(accounts)
        self._load_and_notify()
        self.notification.emit("已删除", "账号已删除")
        return True

    @Slot(str, result=bool)
    def toggleCardMode(self, account_id):
        acc = self._model.get_account(account_id)
        if not acc:
            return False
        return self.set_card_mode(account_id, not acc.card_mode)

    def set_card_mode(self, account_id: str, enabled: bool) -> bool:
        acc = self._model.get_account(account_id)
        if not acc:
            return False
        acc.card_mode = enabled
        self._storage.save_accounts(self.get_accounts())
        self._load_and_notify()
        self.cardModeChanged.emit(account_id)
        return True

    # --- Code operations ---

    @Slot(str)
    def copyCode(self, account_id):
        acc = self._model.get_account(account_id)
        if not acc:
            return
        code = TOTPGenerator.generate(acc)
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(code)
        self.notification.emit("已复制", f"{acc.label} 的验证码已复制到剪贴板")

    @Slot(str, result=str)
    def getCode(self, account_id):
        acc = self._model.get_account(account_id)
        if not acc:
            return ""
        return TOTPGenerator.generate(acc)

    @Slot(result=str)
    def generateSecret(self):
        return TOTPGenerator.generate_secret(32)

    @Slot(str, result="QVariant")
    def parseOTPAuthUrl(self, url):
        """Parse an otpauth:// URL and return account info dict (or empty dict on failure)."""
        result = TOTPGenerator.parse_otpauth_url(url.strip())
        if result is None:
            return {}
        return result

    @Slot(str, result=str)
    def generateOTPAuthUrl(self, account_id):
        acc = self._model.get_account(account_id)
        if not acc:
            return ""
        return TOTPGenerator.generate_otpauth_url(acc)

    # --- Import/Export ---

    @Slot(str, result=str)
    def exportData(self, password):
        data = self._storage.export_data(password)
        if data is None:
            self.notification.emit("错误", "密码不正确")
            return ""
        return data

    @Slot(str, result=bool)
    def importData(self, json_str):
        if self._storage.import_data(json_str):
            self._load_and_notify()
            self.notification.emit("成功", "导入成功！")
            return True
        self.notification.emit("错误", "导入失败，请检查文件格式")
        return False

    @Slot(str, str, result=bool)
    def exportToFile(self, password, file_url):
        data = self._storage.export_data(password)
        if data is None:
            self.notification.emit("错误", "密码不正确")
            return False
        try:
            path = QUrl(file_url).toLocalFile()
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            self.notification.emit("成功", "导出成功！请妥善保管备份文件。")
            return True
        except Exception as e:
            self.notification.emit("错误", f"导出失败: {e}")
            return False

    @Slot(str, result=bool)
    def importFromFile(self, file_url):
        try:
            path = QUrl(file_url).toLocalFile()
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            return self.importData(data)
        except Exception as e:
            self.notification.emit("错误", f"导入失败: {e}")
            return False

    @Slot(str, str, result=bool)
    def changePassword(self, old_pwd, new_pwd):
        if self._storage.change_password(old_pwd, new_pwd):
            self.notification.emit("成功", "密码修改成功！")
            return True
        self.notification.emit("错误", "原密码不正确")
        return False

    # --- Timer ---

    def start_timer(self):
        self._timer.start(500)

    def stop_timer(self):
        self._timer.stop()

    def _on_tick(self):
        self._model.tick()
        if self._card_manager:
            self._card_manager.update_all()

    def adjusted_time(self) -> float:
        """Return current time with offset applied."""
        import time
        return time.time() + self._config.get("time_offset", 0)

    # --- Card manager ---

    def set_card_manager(self, manager: CardManager):
        self._card_manager = manager

    @property
    def card_manager(self):
        return self._card_manager
