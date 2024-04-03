import os
import sys

from PySide6.QtCore import QSize, QCoreApplication, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyleFactory, QMenu, QSystemTrayIcon

import autohelper
from autohelper.gui.Communicate import communicate
from autohelper.gui.MainWindow import MainWindow
from autohelper.gui.i18n.path import i18n_path
from autohelper.gui.icon.icon import icon_path
from autohelper.gui.loading.LoadingWindow import LoadingWindow
from autohelper.gui.overlay.OverlayWindow import OverlayWindow
from autohelper.logging.Logger import get_logger

logger = get_logger(__name__)


class App:
    def __init__(self, icon=None, overlay=False, title="AutoUI", tasks=None,
                 exit_event=None):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setStyle(QStyleFactory.create("Fusion"))
        self.tasks = tasks
        self.title = title
        self.overlay = overlay
        self.loading_window = None
        self.overlay_window = None
        self.main_window = None
        self.exit_event = exit_event
        self.icon = QIcon(icon or icon_path)
        self.tray = QSystemTrayIcon(self.icon)

        locale = QLocale.system().name()
        translator = QTranslator(self.app)
        full_path = os.path.join(i18n_path, f"{QLocale().name()}")
        if translator.load(QLocale().name(), i18n_path):
            translator.setParent(self.app)
            self.app.installTranslator(translator)
            QCoreApplication.installTranslator(translator)
            logger.debug(f"translator install success {QCoreApplication.translate('MainWindow', 'Debug')}")
        else:
            logger.debug(f"No translation available for {locale}, falling back to English/default. {full_path}")

        # Create a context menu for the tray
        menu = QMenu()
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.quit)

        # Set the context menu and show the tray icon
        self.tray.setContextMenu(menu)
        self.tray.show()

        communicate.init.connect(self.on_init)

    def show_notification(self, title, message):
        self.tray.showMessage("Title", "Message")

    def show_loading(self):
        self.loading_window = LoadingWindow(self, self.exit_event)
        size = self.size_relative_to_screen(width=0.4, height=0.4)
        self.loading_window.resize(size)
        self.loading_window.setMinimumSize(size)
        self.center_window(self.loading_window)
        self.loading_window.show()

    def center_window(self, window):
        screen = self.app.primaryScreen()
        size = screen.size()
        # Calculate half the screen size
        half_screen_width = size.width() / 2
        half_screen_height = size.height() / 2

        window.move(half_screen_width / 2, half_screen_height / 2)

    def on_init(self, done, message):
        if done:
            self.loading_window.loading_done()
        else:
            self.loading_window.update_progress(message)

    def show_main_window(self):
        self.loading_window.close()
        self.main_window = MainWindow(self.tasks, self.overlay, exit_event=self.exit_event)
        self.main_window.setWindowTitle(self.title)  # Set the window title here
        self.main_window.setWindowIcon(self.icon)
        if self.overlay and autohelper.gui.device_manager.hwnd is not None:
            self.overlay_window = OverlayWindow(autohelper.gui.device_manager.hwnd)

        size = self.size_relative_to_screen(width=0.5, height=0.5)
        self.main_window.resize(size)
        self.main_window.setMinimumSize(size)

        # Optional: Move the window to the center of the screen

        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def size_relative_to_screen(self, width, height):
        screen = self.app.primaryScreen()
        size = screen.size()
        # Calculate half the screen size
        half_screen_width = size.width() * width
        half_screen_height = size.height() * height
        # Resize the window to half the screen size
        size = QSize(half_screen_width, half_screen_height)
        return size

    def exec(self):
        sys.exit(self.app.exec())

    def quit(self):
        self.exit_event.set()
        self.app.quit()
