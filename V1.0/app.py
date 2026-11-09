from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QMenu,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import config
from telegram import TelegramClient, TelegramError
from timer import PomodoroTimer, Session
from pathlib import Path


class TaskSignals(QObject):
    success = Signal(object)
    failure = Signal(str)


class TelegramTask(QRunnable):
    def __init__(self, operation, *args) -> None:
        super().__init__()
        self.operation = operation
        self.args = args
        self.signals = TaskSignals()

    def run(self) -> None:
        try:
            self.signals.success.emit(self.operation(*self.args))
        except TelegramError as error:
            self.signals.failure.emit(str(error))


class SettingsDialog(QDialog):
    def __init__(self, token: str, chat_id: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PomodoroXP Settings")
        self.token_edit = QLineEdit(token)
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.chat_id_edit = QLineEdit(chat_id)

        form = QFormLayout()
        form.addRow("Telegram bot token:", self.token_edit)
        form.addRow("Telegram chat ID:", self.chat_id_edit)

        find_button = QPushButton("Find chat IDs")
        find_button.clicked.connect(self.find_chats)
        form.addRow("", find_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def find_chats(self) -> None:
        token = self.token_edit.text().strip()
        try:
            chats = TelegramClient(token, "").find_chats()
        except TelegramError as error:
            QMessageBox.warning(self, "Telegram error", str(error))
            return
        if not chats:
            QMessageBox.information(
                self,
                "No chats found",
                "Send a message to your bot in Telegram, then try again.",
            )
            return
        choices = "\n".join(f"{chat_id}: {name}" for chat_id, name in chats)
        selected = chats[0][0]
        QMessageBox.information(
            self,
            "Chats found",
            f"{choices}\n\nThe first chat ID ({selected}) was selected.",
        )
        self.chat_id_edit.setText(selected)


class TimerWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PomodoroXP")
        self.setFixedSize(280, 170)

        self.title_strip = QLabel("PomodoroXP")
        self.title_strip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_strip.setFixedHeight(24)
        self.title_strip.setStyleSheet(
            "font-weight: bold; background: palette(mid);"
        )

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 48px; font-weight: bold;")

        self.status_label = QLabel("Ready to work")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_button = QPushButton("Start")
        self.skip_button = QPushButton("Skip")
        self.reset_button = QPushButton("Reset")
        self.settings_button = QPushButton("Settings")

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.skip_button)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.settings_button)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.title_strip)
        layout.addWidget(self.time_label)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)
        self.setCentralWidget(central)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hide()
        event.ignore()


class PomodoroWindow(QObject):
    def __init__(self, application: QApplication) -> None:
        super().__init__()
        self.application = application
        self.thread_pool = QThreadPool.globalInstance()
        self.timer_model = PomodoroTimer(preset_index=config.load_preset_index())
        self.telegram = TelegramClient(config.load_token(), config.load_chat_id())
        self.window = TimerWindow()
        self.always_on_top = config.load_always_on_top()
        self.opacity_percent = config.load_opacity()
        self.window.title_strip.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.window.title_strip.customContextMenuRequested.connect(
            self._show_window_context_menu
        )
        self.window.start_button.clicked.connect(self._toggle)
        self.window.skip_button.clicked.connect(self._skip)
        self.window.reset_button.clicked.connect(self._reset)
        self.window.settings_button.clicked.connect(self._show_settings)
        icon = self._icon()
        self.window.setWindowIcon(icon)
        self._apply_window_preferences()
        self.tray = QSystemTrayIcon(icon, application)
        self.tray.setToolTip("PomodoroXP")
        self.tray.activated.connect(self._tray_activated)
        self._build_menu()
        self.tray.show()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

        self.clock = QTimer(self)
        self.clock.setInterval(250)
        self.clock.timeout.connect(self._tick)
        self.clock.start()
        self._refresh()

    def _icon(self) -> QIcon:
        return  QIcon(str(Path(__file__).with_name("pomodoro.ico")))

    def _build_menu(self) -> None:
        menu = self.tray.contextMenu()
        if menu:
            menu.deleteLater()

        menu = QMenu()
        show_action = menu.addAction("Show Timer")
        show_action.triggered.connect(self._show_window)
        menu.addSeparator()
        self.start_action = menu.addAction("Start")
        self.start_action.triggered.connect(self._toggle)
        self.skip_action = menu.addAction("Skip to Break")
        self.skip_action.triggered.connect(self._skip)
        reset_action = menu.addAction("Reset")
        reset_action.triggered.connect(self._reset)
        menu.addSeparator()

        self.preset_actions = []
        for index, preset in enumerate(self.timer_model.presets):
            action = menu.addAction(preset.label)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, selected=index: self._select_preset(selected)
            )
            self.preset_actions.append(action)

        menu.addSeparator()
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self._show_settings)
        test_action = menu.addAction("Send Test Telegram Message")
        test_action.triggered.connect(self._send_test)
        menu.addSeparator()
        quit_action = menu.addAction("Quit PomodoroXP")
        quit_action.triggered.connect(self.application.quit)
        self.tray.setContextMenu(menu)

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _apply_window_preferences(self) -> None:
        self.window.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint, self.always_on_top
        )
        self.window.setWindowOpacity(self.opacity_percent / 100)

    def _show_window_context_menu(self, position) -> None:
        menu = QMenu(self.window)
        top_action = menu.addAction("Always on Top")
        top_action.setCheckable(True)
        top_action.setChecked(self.always_on_top)
        top_action.triggered.connect(self._set_always_on_top)

        opacity_menu = menu.addMenu("Opacity")
        opacity_group = QActionGroup(opacity_menu)
        opacity_group.setExclusive(True)
        for percent in (20, 40, 60, 80, 100):
            action = opacity_menu.addAction(f"{percent}%")
            action.setCheckable(True)
            action.setChecked(percent == self.opacity_percent)
            opacity_group.addAction(action)
            action.triggered.connect(
                lambda checked=False, selected=percent: self._set_opacity(selected)
            )
        menu.exec(self.window.title_strip.mapToGlobal(position))

    def _set_always_on_top(self, enabled: bool) -> None:
        self.always_on_top = enabled
        config.save_always_on_top(enabled)
        self._apply_window_preferences()
        self._show_window()

    def _set_opacity(self, percent: int) -> None:
        self.opacity_percent = percent
        config.save_opacity(percent)
        self.window.setWindowOpacity(percent / 100)

    def _tick(self) -> None:
        completed = self.timer_model.tick()
        if completed is not None:
            self._notify_transition(completed)
        self._refresh()

    def _toggle(self) -> None:
        self.timer_model.toggle()
        self._refresh()

    def _skip(self) -> None:
        self.timer_model.skip()
        self._refresh()

    def _reset(self) -> None:
        self.timer_model.reset()
        self._refresh()

    def _select_preset(self, index: int) -> None:
        self.timer_model.select_preset(index)
        config.save_preset_index(index)
        self._refresh()

    def _refresh(self) -> None:
        session_icon = "🍅" if self.timer_model.session is Session.WORK else "☕"
        state = "Running" if self.timer_model.running else "Paused"
        title = f"{session_icon} {self.timer_model.display_time()} - {state}"
        self.tray.setToolTip(f"PomodoroXP: {title}")
        self.start_action.setText("Pause" if self.timer_model.running else "Start")
        self.window.start_button.setText(
            "Pause" if self.timer_model.running else "Start"
        )
        self.window.time_label.setText(self.timer_model.display_time())
        session_name = "Work" if self.timer_model.session is Session.WORK else "Break"
        state = "Running" if self.timer_model.running else "Paused"
        self.window.status_label.setText(f"{session_name} - {state}")
        self.skip_action.setText(
            "Skip to Break"
            if self.timer_model.session is Session.WORK
            else "Skip Break"
        )
        for index, action in enumerate(self.preset_actions):
            action.setChecked(index == self.timer_model.preset_index)

    def _notify_transition(self, completed: Session) -> None:
        if completed is Session.WORK:
            title = "Break time"
            body = f"Take a {self.timer_model.preset.rest_minutes}-minute break."
            message = f"☕ {title}: {body}"
        else:
            title = "Back to work"
            body = f"Focus for {self.timer_model.preset.work_minutes} minutes."
            message = f"🍅 {title}: {body}"
        self.tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information)
        self._send_telegram(message)

    def _send_test(self) -> None:
        self._send_telegram("🍅 Test from PomodoroXP: Telegram alerts are working.")

    def _send_telegram(self, message: str) -> None:
        task = TelegramTask(self.telegram.send_message, message)
        task.signals.success.connect(
            lambda _: self.tray.showMessage(
                "Telegram message sent",
                "Your Telegram chat was notified.",
                QSystemTrayIcon.MessageIcon.Information,
            )
        )
        task.signals.failure.connect(
            lambda error: self.tray.showMessage(
                "Telegram message failed",
                error,
                QSystemTrayIcon.MessageIcon.Warning,
            )
        )
        self.thread_pool.start(task)

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self.telegram.token, self.telegram.chat_id)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        config.save_token(dialog.token_edit.text())
        config.save_chat_id(dialog.chat_id_edit.text())
        self.telegram = TelegramClient(
            dialog.token_edit.text(), dialog.chat_id_edit.text()
        )
        self.tray.showMessage(
            "Settings saved",
            "Telegram configuration updated.",
            QSystemTrayIcon.MessageIcon.Information,
        )

    def close(self) -> None:
        self.clock.stop()
        self.window.hide()
        self.tray.hide()


def main() -> int:
    application = QApplication(sys.argv)
    application.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "PomodoroXP",
            "A system tray is not available on this desktop.",
        )
        return 1
    window = PomodoroWindow(application)
    application.aboutToQuit.connect(window.close)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
