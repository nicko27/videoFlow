"""User interface components for VideoFlow.

This package contains all PyQt6-based user interface components for the VideoFlow
application, including the main window, plugin buttons, and UI widgets.

Components:
    - main_window: Main application window with plugin grid layout
    - Custom widgets for plugin interaction and visualization

The UI follows a modern, card-based design with color-coded plugin buttons
and intuitive navigation. Each plugin is represented as a colored card with
an icon, name, and description.

Design principles:
    - Clean, modern interface with rounded corners
    - Color-coded plugins for easy identification
    - Responsive layout that adapts to window size
    - Consistent styling across all components
    - Accessibility-focused design

Example:
    Creating and displaying the main window::

        from PyQt6.QtWidgets import QApplication
        from src.ui.main_window import MainWindow

        app = QApplication([])
        window = MainWindow()
        window.show()
        app.exec()
"""
