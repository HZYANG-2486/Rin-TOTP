import sys
import os
import uuid
import time
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout, QMessageBox, QMenu,
    QToolBar, QStatusBar, QProgressBar, QComboBox, QSpinBox,
    QFileDialog, QInputDialog, QSystemTrayIcon, QStyle, QFrame
)
from PySide6.QtCore import Qt, QTimer, QSize, QPoint, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont, QClipboard

from totp import TOTPAccount, TOTPGenerator
from storage import SecureStorage


APP_NAME = "Rin-TOTP"
DATA_DIR = os.path.join(str(Path.home()), ".rintotp")


class PasswordDialog(QDialog):
    def __init__(self, storage: SecureStorage, is_new: bool = False, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.is_new = is_new
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(380, is_new and 220 or 180)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 20)
        layout.setSpacing(12)
        
        title = QLabel("设置主密码" if is_new else "输入主密码")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        if is_new:
            desc = QLabel("请设置一个主密码来保护您的密钥")
            desc.setAlignment(Qt.AlignCenter)
            desc.setStyleSheet("color: #888; font-size: 11px;")
            layout.addWidget(desc)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("主密码")
        form_layout.addRow("密码:", self.password_edit)
        
        if is_new:
            self.confirm_edit = QLineEdit()
            self.confirm_edit.setEchoMode(QLineEdit.Password)
            self.confirm_edit.setPlaceholderText("再次输入")
            form_layout.addRow("确认:", self.confirm_edit)
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.password_edit.setFocus()

    def _on_accept(self):
        pwd = self.password_edit.text()
        if not pwd:
            QMessageBox.warning(self, "警告", "密码不能为空")
            return
        
        if self.is_new:
            confirm = self.confirm_edit.text()
            if pwd != confirm:
                QMessageBox.warning(self, "警告", "两次输入的密码不一致")
                return
            self.storage.set_password(pwd)
            self.accept()
        else:
            if self.storage.verify_password(pwd):
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "密码不正确")
                self.password_edit.selectAll()
                self.password_edit.setFocus()


class AddEditDialog(QDialog):
    def __init__(self, account: TOTPAccount = None, parent=None):
        super().__init__(parent)
        self.account = account
        self.setWindowTitle("编辑账号" if account else "添加账号")
        self.setFixedSize(420, 320)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(10)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: user@example.com")
        form_layout.addRow("账号名:", self.name_edit)
        
        self.issuer_edit = QLineEdit()
        self.issuer_edit.setPlaceholderText("例如: Google, GitHub")
        form_layout.addRow("发行方:", self.issuer_edit)
        
        self.secret_edit = QLineEdit()
        self.secret_edit.setPlaceholderText("Base32 密钥")
        form_layout.addRow("密钥:", self.secret_edit)
        
        algo_layout = QHBoxLayout()
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["SHA1", "SHA256", "SHA512"])
        algo_layout.addWidget(self.algo_combo)
        algo_layout.addStretch()
        form_layout.addRow("算法:", algo_layout)
        
        digits_layout = QHBoxLayout()
        self.digits_spin = QSpinBox()
        self.digits_spin.setRange(4, 8)
        self.digits_spin.setValue(6)
        digits_layout.addWidget(self.digits_spin)
        digits_layout.addStretch()
        form_layout.addRow("位数:", digits_layout)
        
        period_layout = QHBoxLayout()
        self.period_spin = QSpinBox()
        self.period_spin.setRange(15, 120)
        self.period_spin.setValue(30)
        self.period_spin.setSuffix(" 秒")
        period_layout.addWidget(self.period_spin)
        period_layout.addStretch()
        form_layout.addRow("周期:", period_layout)
        
        layout.addLayout(form_layout)
        
        layout.addStretch()
        
        gen_btn = QPushButton("生成随机密钥")
        gen_btn.clicked.connect(self._generate_secret)
        layout.addWidget(gen_btn)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        if account:
            self.name_edit.setText(account.name)
            self.issuer_edit.setText(account.issuer)
            self.secret_edit.setText(account.secret)
            self.algo_combo.setCurrentText(account.algorithm)
            self.digits_spin.setValue(account.digits)
            self.period_spin.setValue(account.period)

    def _generate_secret(self):
        secret = TOTPGenerator.generate_secret(32)
        self.secret_edit.setText(secret)

    def _on_accept(self):
        name = self.name_edit.text().strip()
        secret = self.secret_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "警告", "请输入账号名")
            return
        if not secret:
            QMessageBox.warning(self, "警告", "请输入密钥")
            return
        if not TOTPGenerator.validate_secret(secret):
            QMessageBox.warning(self, "警告", "密钥格式不正确（必须是Base32格式）")
            return
        
        self.accept()

    def get_account_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "issuer": self.issuer_edit.text().strip(),
            "secret": self.secret_edit.text().strip().upper(),
            "algorithm": self.algo_combo.currentText(),
            "digits": self.digits_spin.value(),
            "period": self.period_spin.value(),
        }


class TOTPItemWidget(QWidget):
    copy_clicked = Signal(str)
    edit_clicked = Signal(str)
    delete_clicked = Signal(str)

    def __init__(self, account: TOTPAccount, parent=None):
        super().__init__(parent)
        self.account = account
        self.setFixedHeight(90)
        self._code = ""
        self._time_left = 30
        
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)
        
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)
        
        self.issuer_label = QLabel(self.account.issuer or "Unknown")
        issuer_font = QFont()
        issuer_font.setBold(True)
        issuer_font.setPointSize(11)
        self.issuer_label.setFont(issuer_font)
        self.issuer_label.setStyleSheet("color: #333;")
        left_layout.addWidget(self.issuer_label)
        
        self.name_label = QLabel(self.account.name)
        self.name_label.setStyleSheet("color: #666; font-size: 11px;")
        left_layout.addWidget(self.name_label)
        
        self.code_label = QLabel("------")
        code_font = QFont("Monospace")
        code_font.setPointSize(20)
        code_font.setBold(True)
        self.code_label.setFont(code_font)
        self.code_label.setStyleSheet("color: #1a73e8; letter-spacing: 2px;")
        left_layout.addWidget(self.code_label)
        
        layout.addLayout(left_layout, 1)
        
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(100, 6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background-color: #1a73e8;
            }
        """)
        right_layout.addWidget(self.progress_bar)
        
        self.time_label = QLabel("30s")
        self.time_label.setAlignment(Qt.AlignRight)
        self.time_label.setStyleSheet("color: #888; font-size: 11px;")
        right_layout.addWidget(self.time_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setFixedSize(55, 24)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        self.copy_btn.clicked.connect(self._on_copy)
        btn_layout.addWidget(self.copy_btn)
        
        self.menu_btn = QPushButton("⋯")
        self.menu_btn.setFixedSize(24, 24)
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.menu_btn.clicked.connect(self._show_menu)
        btn_layout.addWidget(self.menu_btn)
        
        right_layout.addLayout(btn_layout)
        layout.addLayout(right_layout)

    def update_code(self):
        self._code = TOTPGenerator.generate(self.account)
        self._time_left = TOTPGenerator.time_remaining(self.account.period)
        progress = TOTPGenerator.progress(self.account.period)
        
        display_code = TOTPGenerator.format_code(self._code)
        self.code_label.setText(display_code)
        self.time_label.setText(f"{self._time_left}s")
        self.progress_bar.setValue(int((1 - progress) * 100))
        
        if self._time_left <= 5:
            self.code_label.setStyleSheet("color: #d93025; letter-spacing: 2px;")
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 3px;
                    background-color: #e0e0e0;
                }
                QProgressBar::chunk {
                    border-radius: 3px;
                    background-color: #d93025;
                }
            """)
        else:
            self.code_label.setStyleSheet("color: #1a73e8; letter-spacing: 2px;")
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 3px;
                    background-color: #e0e0e0;
                }
                QProgressBar::chunk {
                    border-radius: 3px;
                    background-color: #1a73e8;
                }
            """)

    def _on_copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._code)
        self.copy_btn.setText("已复制!")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        QTimer.singleShot(1500, self._reset_copy_btn)
        self.copy_clicked.emit(self.account.id)

    def _reset_copy_btn(self):
        self.copy_btn.setText("复制")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)

    def _show_menu(self):
        menu = QMenu(self)
        
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self.edit_clicked.emit(self.account.id))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_clicked.emit(self.account.id))
        menu.addAction(delete_action)
        
        pos = self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height()))
        menu.exec(pos)


class MainWindow(QMainWindow):
    def __init__(self, storage: SecureStorage):
        super().__init__()
        self.storage = storage
        self.accounts: list[TOTPAccount] = []
        self.item_widgets: dict[str, TOTPItemWidget] = {}
        
        self._init_ui()
        self._load_accounts()
        self._start_timer()

    def _init_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(480, 500)
        self.resize(480, 600)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #fafafa;
            }
            QListWidget {
                background-color: #fafafa;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: white;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #f0f4ff;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        
        title_label = QLabel("🔐  身份验证器")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("+ 添加")
        add_btn.setFixedSize(75, 30)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        add_btn.clicked.connect(self._add_account)
        header_layout.addWidget(add_btn)
        
        main_layout.addWidget(header)
        
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(0)
        main_layout.addWidget(self.list_widget)
        
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: white; border-top: 1px solid #e0e0e0;")
        self.setStatusBar(self.status_bar)
        
        self._create_actions()
        self._create_tray()

    def _create_actions(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件")
        
        import_action = QAction("导入...", self)
        import_action.triggered.connect(self._import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction("导出...", self)
        export_action.triggered.connect(self._export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        lock_action = QAction("锁定", self)
        lock_action.triggered.connect(self._lock_app)
        file_menu.addAction(lock_action)
        
        change_pwd_action = QAction("修改主密码...", self)
        change_pwd_action.triggered.connect(self._change_password)
        file_menu.addAction(change_pwd_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        
        tray_menu = QMenu()
        
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        lock_action = QAction("锁定", self)
        lock_action.triggered.connect(self._lock_app)
        tray_menu.addAction(lock_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def _load_accounts(self):
        self.accounts = self.storage.load_accounts()
        self._refresh_list()
        self.status_bar.showMessage(f"共 {len(self.accounts)} 个账号")

    def _refresh_list(self):
        self.list_widget.clear()
        self.item_widgets.clear()
        
        for account in self.accounts:
            self._add_list_item(account)

    def _add_list_item(self, account: TOTPAccount):
        item = QListWidgetItem(self.list_widget)
        item.setSizeHint(QSize(0, 90))
        
        widget = TOTPItemWidget(account)
        widget.copy_clicked.connect(self._on_copy)
        widget.edit_clicked.connect(self._edit_account)
        widget.delete_clicked.connect(self._delete_account)
        widget.update_code()
        
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        self.item_widgets[account.id] = widget

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_codes)
        self.timer.start(500)

    def _update_codes(self):
        for widget in self.item_widgets.values():
            widget.update_code()

    def _add_account(self):
        dialog = AddEditDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_account_data()
            new_id = str(uuid.uuid4())
            account = TOTPAccount(
                id=new_id,
                name=data["name"],
                issuer=data["issuer"],
                secret=data["secret"],
                digits=data["digits"],
                period=data["period"],
                algorithm=data["algorithm"],
            )
            self.accounts.append(account)
            self.storage.save_accounts(self.accounts)
            self._add_list_item(account)
            self.status_bar.showMessage(f"共 {len(self.accounts)} 个账号")

    def _edit_account(self, account_id: str):
        account = next((a for a in self.accounts if a.id == account_id), None)
        if not account:
            return
        
        dialog = AddEditDialog(account, parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_account_data()
            account.name = data["name"]
            account.issuer = data["issuer"]
            account.secret = data["secret"]
            account.digits = data["digits"]
            account.period = data["period"]
            account.algorithm = data["algorithm"]
            
            self.storage.save_accounts(self.accounts)
            
            if account_id in self.item_widgets:
                widget = self.item_widgets[account_id]
                widget.account = account
                widget.issuer_label.setText(account.issuer or "Unknown")
                widget.name_label.setText(account.name)
                widget.update_code()

    def _delete_account(self, account_id: str):
        account = next((a for a in self.accounts if a.id == account_id), None)
        if not account:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除账号 \"{account.label}\" 吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.accounts = [a for a in self.accounts if a.id != account_id]
            self.storage.save_accounts(self.accounts)
            self._refresh_list()
            self.status_bar.showMessage(f"共 {len(self.accounts)} 个账号")

    def _on_copy(self, account_id: str):
        pass

    def _import_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入数据", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = f.read()
            
            if self.storage.import_data(data):
                self._load_accounts()
                QMessageBox.information(self, "成功", "导入成功！")
            else:
                QMessageBox.warning(self, "错误", "导入失败，请检查文件格式")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败: {str(e)}")

    def _export_data(self):
        pwd, ok = QInputDialog.getText(
            self, "验证密码", "请输入主密码以导出:",
            QLineEdit.Password
        )
        if not ok:
            return
        
        data = self.storage.export_data(pwd)
        if data is None:
            QMessageBox.warning(self, "错误", "密码不正确")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "totp_backup.json", "JSON Files (*.json)"
        )
        if not file_path:
            return
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(data)
            QMessageBox.information(self, "成功", "导出成功！\n请妥善保管备份文件。")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")

    def _change_password(self):
        old_pwd, ok = QInputDialog.getText(
            self, "当前密码", "请输入当前主密码:",
            QLineEdit.Password
        )
        if not ok:
            return
        
        dialog = PasswordDialog(self.storage, is_new=True, parent=self)
        dialog.setWindowTitle("设置新密码")
        dialog.password_edit.setPlaceholderText("新密码")
        dialog.confirm_edit.setPlaceholderText("确认新密码")
        
        if dialog.exec() == QDialog.Accepted:
            new_pwd = dialog.password_edit.text()
            if self.storage.change_password(old_pwd, new_pwd):
                QMessageBox.information(self, "成功", "密码修改成功！")
            else:
                QMessageBox.warning(self, "错误", "原密码不正确")

    def _lock_app(self):
        self.hide()
        self.storage.lock()
        
        dialog = PasswordDialog(self.storage, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_accounts()
            self.show()
        else:
            QApplication.quit()

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            f"<h3>{APP_NAME}</h3>"
            "<p>一个 TOTP 身份验证器</p>"
            "<p>基于时间的一次性密码 (TOTP) 应用</p>"
            "<p><b>功能特性:</b></p>"
            "<ul>"
            "<li>🔒 AES 加密存储密钥</li>"
            "<li>⏱️ 实时验证码更新</li>"
            "<li>📋 一键复制验证码</li>"
            "<li>💾 导入/导出备份</li>"
            "<li>🔔 系统托盘支持</li>"
            "</ul>"
        )

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            self.tray_icon.showMessage(
                APP_NAME,
                "程序已最小化到系统托盘",
                QSystemTrayIcon.Information,
                2000
            )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    
    storage = SecureStorage(DATA_DIR)
    
    if storage.has_password():
        dialog = PasswordDialog(storage)
        if dialog.exec() != QDialog.Accepted:
            return
    else:
        dialog = PasswordDialog(storage, is_new=True)
        if dialog.exec() != QDialog.Accepted:
            return
    
    window = MainWindow(storage)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
