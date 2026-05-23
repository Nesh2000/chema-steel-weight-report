import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from database import DatabaseManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Steel Weight Calculator")
    app.setOrganizationName("SteelSoft")

    db_manager = DatabaseManager()
    window = MainWindow(db_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
