"""
Widget Registry - Centralized widget registration and access.

Provides a unified interface for managing UI widgets throughout the application,
eliminating scattered getattr() calls and providing validation.
"""
from typing import Dict, Optional, Set, List, Any
from PyQt6.QtWidgets import QWidget, QTabWidget

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.WidgetRegistry')


class WidgetRegistry:
    """
    Centralized registry for UI widgets.

    Manages widget registration from tabs and provides validated access,
    replacing scattered getattr() calls with a clean API.

    Usage:
        registry = WidgetRegistry()
        registry.register_from_tab(tab_widget, "analysis")
        threshold_spin = registry.get("threshold_spin")
    """

    def __init__(self):
        """Initialize empty widget registry."""
        self._widgets: Dict[str, QWidget] = {}
        self._groups: Dict[str, Set[str]] = {}
        self._required_widgets: Set[str] = set()

    def register(self, name: str, widget: QWidget, group: Optional[str] = None):
        """
        Register a single widget.

        Args:
            name: Widget identifier (should match objectName)
            widget: The widget instance
            group: Optional group name (e.g., "hashing", "comparison")
        """
        if name in self._widgets:
            logger.warning(f"Widget '{name}' already registered, replacing")

        self._widgets[name] = widget

        # Add to group if specified
        if group:
            if group not in self._groups:
                self._groups[group] = set()
            self._groups[group].add(name)

        logger.debug(f"Registered widget: {name}" + (f" (group: {group})" if group else ""))

    def register_from_tab(self, tab_widget: QWidget, group: Optional[str] = None):
        """
        Register all widgets from a tab using findChildren().

        Args:
            tab_widget: The tab widget to scan
            group: Optional group name for all widgets in this tab
        """
        # Find all widgets with objectName set
        all_widgets = tab_widget.findChildren(QWidget)
        registered_count = 0

        for widget in all_widgets:
            name = widget.objectName()
            if name:  # Only register widgets with objectName
                self.register(name, widget, group)
                registered_count += 1

        logger.info(f"Registered {registered_count} widgets from tab" +
                   (f" (group: {group})" if group else ""))

    def register_from_tabs(self, tabs: QTabWidget, group_prefix: Optional[str] = None):
        """
        Register widgets from all tabs in a QTabWidget.

        Args:
            tabs: QTabWidget containing multiple tabs
            group_prefix: Optional prefix for group names (e.g., "main_")
        """
        for i in range(tabs.count()):
            tab = tabs.widget(i)
            tab_name = tab.objectName() if tab.objectName() else f"tab_{i}"

            # Use tab_name as group, with optional prefix
            group = f"{group_prefix}{tab_name}" if group_prefix else tab_name

            self.register_from_tab(tab, group)

        logger.info(f"Registered widgets from {tabs.count()} tabs")

    def get(self, name: str, default: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        Get a widget by name.

        Args:
            name: Widget identifier
            default: Default value if widget not found

        Returns:
            Widget instance or default
        """
        widget = self._widgets.get(name, default)

        if widget is None and default is None:
            logger.warning(f"Widget '{name}' not found in registry")

        return widget

    def get_required(self, name: str) -> QWidget:
        """
        Get a required widget by name.

        Args:
            name: Widget identifier

        Returns:
            Widget instance

        Raises:
            KeyError: If widget not found
        """
        if name not in self._widgets:
            raise KeyError(f"Required widget '{name}' not found in registry")

        return self._widgets[name]

    def get_group(self, group: str) -> Dict[str, QWidget]:
        """
        Get all widgets in a group.

        Args:
            group: Group name

        Returns:
            Dictionary of widget_name -> widget for the group
        """
        if group not in self._groups:
            logger.warning(f"Group '{group}' not found in registry")
            return {}

        return {
            name: self._widgets[name]
            for name in self._groups[group]
            if name in self._widgets
        }

    def get_all(self) -> Dict[str, QWidget]:
        """
        Get all registered widgets.

        Returns:
            Dictionary of widget_name -> widget
        """
        return self._widgets.copy()

    def has(self, name: str) -> bool:
        """
        Check if a widget is registered.

        Args:
            name: Widget identifier

        Returns:
            True if widget is registered
        """
        return name in self._widgets

    def unregister(self, name: str):
        """
        Unregister a widget.

        Args:
            name: Widget identifier
        """
        if name in self._widgets:
            del self._widgets[name]

            # Remove from all groups
            for group in self._groups.values():
                group.discard(name)

            logger.debug(f"Unregistered widget: {name}")

    def clear(self):
        """Clear all registered widgets."""
        self._widgets.clear()
        self._groups.clear()
        self._required_widgets.clear()
        logger.debug("Cleared widget registry")

    def set_required(self, *names: str):
        """
        Mark widgets as required for validation.

        Args:
            *names: Widget identifiers to mark as required
        """
        self._required_widgets.update(names)
        logger.debug(f"Marked {len(names)} widgets as required")

    def validate(self) -> bool:
        """
        Validate that all required widgets are registered.

        Returns:
            True if all required widgets are present
        """
        missing = self.get_missing()

        if missing:
            logger.error(f"Validation failed: {len(missing)} required widgets missing: {missing}")
            return False

        logger.debug("Validation passed: all required widgets registered")
        return True

    def get_missing(self) -> List[str]:
        """
        Get list of missing required widgets.

        Returns:
            List of widget identifiers that are required but not registered
        """
        return [
            name for name in self._required_widgets
            if name not in self._widgets
        ]

    def get_widget_value(self, name: str, default: Any = None) -> Any:
        """
        Get the current value from a widget.

        Supports common widget types: spinbox, checkbox, lineedit, combobox, etc.

        Args:
            name: Widget identifier
            default: Default value if widget not found or has no value

        Returns:
            Widget value or default
        """
        widget = self.get(name)

        if widget is None:
            return default

        # Try common value accessors
        if hasattr(widget, 'value'):
            return widget.value()
        elif hasattr(widget, 'isChecked'):
            return widget.isChecked()
        elif hasattr(widget, 'text'):
            return widget.text()
        elif hasattr(widget, 'currentText'):
            return widget.currentText()
        elif hasattr(widget, 'currentIndex'):
            return widget.currentIndex()

        logger.warning(f"Widget '{name}' has no known value accessor")
        return default

    def set_widget_value(self, name: str, value: Any) -> bool:
        """
        Set the value of a widget.

        Supports common widget types: spinbox, checkbox, lineedit, combobox, etc.

        Args:
            name: Widget identifier
            value: Value to set

        Returns:
            True if value was set successfully
        """
        widget = self.get(name)

        if widget is None:
            return False

        # Try common value setters
        try:
            if hasattr(widget, 'setValue'):
                widget.setValue(value)
                return True
            elif hasattr(widget, 'setChecked'):
                widget.setChecked(bool(value))
                return True
            elif hasattr(widget, 'setText'):
                widget.setText(str(value))
                return True
            elif hasattr(widget, 'setCurrentText'):
                widget.setCurrentText(str(value))
                return True
            elif hasattr(widget, 'setCurrentIndex'):
                widget.setCurrentIndex(int(value))
                return True
        except Exception as e:
            logger.error(f"Failed to set value for widget '{name}': {e}")
            return False

        logger.warning(f"Widget '{name}' has no known value setter")
        return False

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'total_widgets': len(self._widgets),
            'total_groups': len(self._groups),
            'required_widgets': len(self._required_widgets),
            'missing_required': len(self.get_missing())
        }

    def __len__(self) -> int:
        """Return number of registered widgets."""
        return len(self._widgets)

    def __contains__(self, name: str) -> bool:
        """Check if widget is registered using 'in' operator."""
        return name in self._widgets

    def __repr__(self) -> str:
        """String representation of registry."""
        stats = self.get_stats()
        return (f"WidgetRegistry(widgets={stats['total_widgets']}, "
                f"groups={stats['total_groups']}, "
                f"required={stats['required_widgets']})")


# Global instance for convenience
_global_widget_registry: Optional[WidgetRegistry] = None


def get_widget_registry() -> WidgetRegistry:
    """
    Get the global widget registry instance.

    Returns:
        Global WidgetRegistry instance
    """
    global _global_widget_registry

    if _global_widget_registry is None:
        _global_widget_registry = WidgetRegistry()
        logger.info("Created global WidgetRegistry instance")

    return _global_widget_registry


def reset_widget_registry():
    """Reset the global widget registry (mainly for testing)."""
    global _global_widget_registry
    _global_widget_registry = None
