"""VideoFlow source package.

This package contains the core application modules and plugin system for VideoFlow,
a PyQt6-based video processing application that provides various tools for managing,
editing, and organizing video files.

The package structure includes:
    - core: Core application components (plugin system, logging)
    - plugins: Plugin modules for video processing features
    - ui: User interface components

Example:
    Basic usage of the VideoFlow application::

        from src.ui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication

        app = QApplication([])
        window = MainWindow()
        window.show()
        app.exec()
"""
