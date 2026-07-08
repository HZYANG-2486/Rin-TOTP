"""
RinUI-based entry point for Rin-TOTP.

Loads the Fluent Design main window (qml/Main.qml), wires up the Backend /
TOTPModel / CardManager to the QML engine, sets up a system tray icon, and
runs the application event loop.
"""

import sys

from PySide6.QtCore import Qt, QObject, QEvent, QMetaObject, Q_ARG, Slot
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from RinUI import RinUIWindow

from backend import Backend, CardManager, DATA_DIR, QML_DIR
from i18n import Translator


APP_NAME = "Rin-TOTP"


def _make_app_icon() -> QIcon:
    """Draw a simple shield/key icon at runtime so we don't ship a binary asset."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    # rounded square background
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#605ed2"))
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    # "T" glyph
    p.setPen(QColor("#ffffff"))
    f = QFont("Arial", 32, QFont.Bold)
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignCenter, "T")
    p.end()
    return QIcon(pix)


class CloseEventFilter(QObject):
    """Event filter that intercepts close events on the QML root window and
    shows a confirmation dialog before deciding what to do.

    All actual actions (hide-to-tray, quit, cancel) are performed from the
    Python side so we know they actually execute.
    """

    def __init__(self, qml_root: QQuickWindow, backend: Backend, tray: QSystemTrayIcon, app: QApplication):
        super().__init__()
        self._qml_root = qml_root
        self._backend = backend
        self._tray = tray
        self._app = app
        self._closing = False  # guard against re-entrancy
        self._force_close = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Close or obj is not self._qml_root:
            return super().eventFilter(obj, event)

        if self._force_close:
            return False

        if self._closing:
            event.ignore()
            return True

        self._closing = True
        event.ignore()

        # If askOnClose is disabled, directly hide to tray
        if not self._backend.askOnClose:
            self.action_hide_to_tray()
            return True

        # Ask QML side to show the close confirmation dialog.  When the user
        # picks an option, QML calls back to the Python methods below.
        QMetaObject.invokeMethod(self._qml_root, "showCloseDialog", Qt.QueuedConnection)
        return True

    @Slot()
    def action_hide_to_tray(self):
        """User chose 'hide to tray'."""
        self._closing = False
        self._qml_root.hide()
        # Auto-lock if enabled
        if self._backend.autoLock:
            self._backend.lock()
        self._backend.minimizeToTray()

    @Slot()
    def action_quit(self):
        """User chose 'quit app'."""
        self._closing = False
        self._force_close = True
        cm = self._backend.card_manager
        if cm:
            cm.close_all()
        self._tray.hide()
        self._app.quit()

    @Slot()
    def action_cancel(self):
        """User chose 'cancel'."""
        self._closing = False


class MainWindow(RinUIWindow):
    def __init__(self, backend: Backend):
        super().__init__()
        self._backend = backend

        # Expose backend + model to QML as context properties BEFORE loading.
        ctx = self.engine.rootContext()
        ctx.setContextProperty("Backend", backend)
        ctx.setContextProperty("totpModel", backend.model())
        # Translator is also pre-registered (must be available when Main.qml parses).
        ctx.setContextProperty("I18n", Translator.instance())

        self.load(str(QML_DIR / "Main.qml"))

        # Wire the CardManager to the (now-initialized) engine so it can build
        # card windows from CardWindow.qml via the shared component cache.
        card_manager = CardManager(self.engine, backend, parent=backend)
        backend.set_card_manager(card_manager)

        # Make sure the backend timer is running and the QML root window is
        # accessible to the tray handler below.
        backend.start_timer()
        self._qml_root = self.root_window


def main():
    # High-DPI awareness is set by RinUI's __init__ already.
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # keep running when main window hides to tray

    icon = _make_app_icon()
    app.setWindowIcon(icon)

    # --- Backend setup ---
    backend = Backend(data_dir=DATA_DIR)

    # --- Translator (i18n) ---
    translator = Translator.instance()

    # --- Main window (RinUI Fluent Design) ---
    main_window = MainWindow(backend)

    qml_root = main_window.root_window

    # --- System tray ---
    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip(APP_NAME)

    tray_menu = QMenu()
    show_action = QAction("显示主窗口", tray_menu)
    lock_action = QAction("锁定", tray_menu)
    quit_action = QAction("退出", tray_menu)
    tray_menu.addAction(show_action)
    tray_menu.addAction(lock_action)
    tray_menu.addSeparator()
    tray_menu.addAction(quit_action)
    tray.setContextMenu(tray_menu)

    def show_main_window():
        qml_root.show()
        qml_root.raise_()
        qml_root.requestActivate()

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            show_main_window()

    def on_quit():
        # Close any open desktop cards before quitting so they don't linger.
        cm = backend.card_manager
        if cm:
            cm.close_all()
        tray.hide()
        app.quit()

    show_action.triggered.connect(show_main_window)
    lock_action.triggered.connect(backend.lock)
    quit_action.triggered.connect(on_quit)
    tray.activated.connect(on_tray_activated)

    # --- Close event filter (handles close-confirm dialog from Python side) ---
    close_filter = CloseEventFilter(qml_root, backend, tray, app)
    qml_root.installEventFilter(close_filter)
    # Expose the filter to QML so buttons can call back into Python
    main_window.engine.rootContext().setContextProperty("CloseFilter", close_filter)

    # Forward tray messages from backend (e.g. on minimize-to-tray).
    def on_show_tray_message(title, message):
        if QSystemTrayIcon.supportsMessages():
            tray.showMessage(title, message, icon, 2000)

    backend.showTrayMessage.connect(on_show_tray_message)

    tray.show()

    # If the platform has no tray, fall back to keeping the window visible.
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("[warn] System tray not available; window will close normally.")
        app.setQuitOnLastWindowClosed(True)

    # Make sure the timer stops cleanly on quit.
    app.aboutToQuit.connect(backend.stop_timer)

    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
