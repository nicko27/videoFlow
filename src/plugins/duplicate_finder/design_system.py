"""
Unified design system for the duplicate finder plugin.

This module centralizes all design constants (colors, spacing, fonts, etc.)
to ensure visual consistency across the entire plugin.
"""

from typing import Dict, Optional


class Colors:
    """Color palette for the duplicate finder plugin."""

    # Primary colors
    PRIMARY = "#007BFF"
    PRIMARY_DARK = "#0056B3"
    PRIMARY_DARKER = "#004085"
    PRIMARY_LIGHT = "#CCE5FF"
    PRIMARY_LIGHTER = "#E7F3FF"

    # Secondary colors
    SECONDARY = "#6C757D"
    SECONDARY_DARK = "#545B62"
    SECONDARY_DARKER = "#454D55"
    SECONDARY_LIGHT = "#ADB5BD"

    # Success colors
    SUCCESS = "#28A745"
    SUCCESS_DARK = "#218838"
    SUCCESS_DARKER = "#1E7E34"
    SUCCESS_LIGHT = "#D4EDDA"
    SUCCESS_LIGHTER = "#E8F5E8"

    # Danger/Error colors
    DANGER = "#DC3545"
    DANGER_DARK = "#C82333"
    DANGER_DARKER = "#A71E2A"
    DANGER_LIGHT = "#F8D7DA"
    DANGER_LIGHTER = "#FFEBEE"

    # Warning colors
    WARNING = "#FFC107"
    WARNING_DARK = "#E0A800"
    WARNING_LIGHT = "#FFF3CD"
    WARNING_LIGHTER = "#FFF8E1"

    # Info colors
    INFO = "#17A2B8"
    INFO_DARK = "#117A8B"
    INFO_LIGHT = "#D1ECF1"
    INFO_LIGHTER = "#E0F7FA"

    # Orange colors (for video B)
    ORANGE = "#FF9800"
    ORANGE_DARK = "#F57C00"
    ORANGE_DARKER = "#EF6C00"
    ORANGE_LIGHT = "#FFE0B2"
    ORANGE_LIGHTER = "#FFF3E0"

    # Green colors (for video A)
    GREEN = "#4CAF50"
    GREEN_DARK = "#388E3C"
    GREEN_LIGHT = "#C8E6C9"
    GREEN_LIGHTER = "#E8F5E9"

    # Neutral colors
    BLACK = "#000000"
    WHITE = "#FFFFFF"
    GRAY_50 = "#F8F9FA"
    GRAY_100 = "#F5F5F5"
    GRAY_200 = "#EEEEEE"
    GRAY_300 = "#E0E0E0"
    GRAY_400 = "#CCCCCC"
    GRAY_500 = "#AAAAAA"
    GRAY_600 = "#757575"
    GRAY_700 = "#616161"
    GRAY_800 = "#424242"
    GRAY_900 = "#212121"

    # Border colors
    BORDER_LIGHT = "#DDDDDD"
    BORDER_DEFAULT = "#CCCCCC"
    BORDER_DARK = "#AAAAAA"

    # Background colors
    BG_PRIMARY = "#FFFFFF"
    BG_SECONDARY = "#F8F9FA"
    BG_TERTIARY = "#F0F0F0"
    BG_DARK = "#ECF0F1"


class Spacing:
    """Spacing constants for margins, padding, and gaps."""

    # Margins and padding
    XXS = 2
    XS = 5
    SM = 8
    MD = 10
    LG = 12
    XL = 15
    XXL = 20
    XXXL = 30

    # Border radius
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 10
    RADIUS_XL = 15

    # Standard component heights
    BUTTON_HEIGHT = 35
    BUTTON_HEIGHT_LG = 60
    INPUT_HEIGHT = 30
    PROGRESS_BAR_HEIGHT = 30
    STATUS_BAR_HEIGHT = 50
    FILE_ITEM_HEIGHT = 70


class Typography:
    """Typography constants for fonts and text sizes."""

    # Font family
    FONT_FAMILY = "Arial"

    # Font sizes (in pixels)
    FONT_XXS = 9
    FONT_XS = 10
    FONT_SM = 11
    FONT_MD = 12
    FONT_LG = 14
    FONT_XL = 16
    FONT_XXL = 20
    FONT_XXXL = 24

    # Font weights
    WEIGHT_NORMAL = "normal"
    WEIGHT_BOLD = "bold"
    WEIGHT_LIGHT = "light"


class Styles:
    """Pre-built style strings for common components."""

    @staticmethod
    def button(
        bg_color: str = Colors.PRIMARY,
        hover_color: str = Colors.PRIMARY_DARK,
        pressed_color: str = Colors.PRIMARY_DARKER,
        text_color: str = Colors.WHITE,
        height: int = Spacing.BUTTON_HEIGHT,
        radius: int = Spacing.RADIUS_MD,
        font_size: int = Typography.FONT_MD,
        bold: bool = True
    ) -> str:
        """Generate button stylesheet.

        Args:
            bg_color: Background color
            hover_color: Hover state color
            pressed_color: Pressed state color
            text_color: Text color
            height: Button height
            radius: Border radius
            font_size: Font size
            bold: Whether text should be bold

        Returns:
            CSS stylesheet string
        """
        font_weight = Typography.WEIGHT_BOLD if bold else Typography.WEIGHT_NORMAL

        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                font-size: {font_size}px;
                font-weight: {font_weight};
                min-height: {height}px;
                padding: {Spacing.MD}px {Spacing.XXL}px;
                border-radius: {radius}px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:disabled {{
                background-color: {Colors.GRAY_300};
                color: {Colors.GRAY_600};
            }}
        """

    @staticmethod
    def action_button(
        bg_color: str,
        hover_color: str,
        pressed_color: str
    ) -> str:
        """Generate large action button stylesheet.

        Args:
            bg_color: Background color
            hover_color: Hover state color
            pressed_color: Pressed state color

        Returns:
            CSS stylesheet string
        """
        return f"""
            QPushButton {{
                background-color: {bg_color} !important;
                color: white !important;
                font-size: {Typography.FONT_LG}px;
                font-weight: bold;
                padding: {Spacing.XL}px {Spacing.XXL}px;
                border-radius: {Spacing.RADIUS_LG}px;
                border: none;
                min-height: {Spacing.BUTTON_HEIGHT_LG}px;
                min-width: 160px;
            }}
            QPushButton:hover {{
                background-color: {hover_color} !important;
            }}
            QPushButton:pressed {{
                background-color: {pressed_color} !important;
            }}
        """

    @staticmethod
    def frame(
        bg_color: str = Colors.BG_PRIMARY,
        border_color: str = Colors.BORDER_LIGHT,
        border_width: int = 1,
        radius: int = Spacing.RADIUS_MD,
        padding: int = Spacing.MD
    ) -> str:
        """Generate frame stylesheet.

        Args:
            bg_color: Background color
            border_color: Border color
            border_width: Border width in pixels
            radius: Border radius
            padding: Internal padding

        Returns:
            CSS stylesheet string
        """
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: {border_width}px solid {border_color};
                border-radius: {radius}px;
                padding: {padding}px;
            }}
        """

    @staticmethod
    def video_frame(color: str) -> str:
        """Generate video comparison frame stylesheet.

        Args:
            color: Accent color for the frame

        Returns:
            CSS stylesheet string
        """
        return f"""
            QFrame {{
                background-color: {Colors.WHITE};
                border: 3px solid {color};
                border-radius: {Spacing.RADIUS_XL}px;
            }}
        """

    @staticmethod
    def progress_bar() -> str:
        """Generate progress bar stylesheet.

        Returns:
            CSS stylesheet string
        """
        return f"""
            QProgressBar {{
                border: 2px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_XL}px;
                text-align: center;
                font-weight: bold;
                font-size: {Typography.FONT_MD}px;
                color: {Colors.BLACK};
                background-color: {Colors.GRAY_100};
                min-height: {Spacing.PROGRESS_BAR_HEIGHT}px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.SUCCESS}, stop:1 {Colors.SUCCESS_DARK});
                border-radius: {Spacing.RADIUS_MD}px;
                margin: 2px;
            }}
        """

    @staticmethod
    def slider() -> str:
        """Generate slider stylesheet.

        Returns:
            CSS stylesheet string
        """
        return f"""
            QSlider::groove:horizontal {{
                border: 1px solid {Colors.BORDER_DEFAULT};
                height: 8px;
                background: {Colors.GRAY_100};
                border-radius: {Spacing.RADIUS_SM}px;
            }}
            QSlider::handle:horizontal {{
                background: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY_DARK};
                width: 20px;
                margin: -6px 0;
                border-radius: {Spacing.RADIUS_LG}px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {Colors.PRIMARY_DARK};
            }}
        """

    @staticmethod
    def label(
        color: str = Colors.BLACK,
        font_size: int = Typography.FONT_MD,
        bold: bool = False,
        bg_color: Optional[str] = None
    ) -> str:
        """Generate label stylesheet.

        Args:
            color: Text color
            font_size: Font size
            bold: Whether text should be bold
            bg_color: Background color (optional)

        Returns:
            CSS stylesheet string
        """
        font_weight = Typography.WEIGHT_BOLD if bold else Typography.WEIGHT_NORMAL
        bg_style = f"background-color: {bg_color};" if bg_color else ""

        return f"""
            QLabel {{
                color: {color};
                font-size: {font_size}px;
                font-weight: {font_weight};
                {bg_style}
            }}
        """

    @staticmethod
    def file_item() -> str:
        """Generate file list item stylesheet.

        Returns:
            CSS stylesheet string
        """
        return f"""
            QFrame {{
                background-color: {Colors.GRAY_50};
                border: 1px solid {Colors.BORDER_LIGHT};
                margin: {Spacing.XXS}px;
                border-radius: {Spacing.RADIUS_SM}px;
            }}
            QFrame:hover {{
                background-color: {Colors.GRAY_200};
            }}
        """

    @staticmethod
    def status_badge(
        bg_color: str,
        border_color: str
    ) -> str:
        """Generate status badge stylesheet.

        Args:
            bg_color: Background color
            border_color: Border color

        Returns:
            CSS stylesheet string
        """
        return f"""
            color: {Colors.BLACK};
            background-color: {bg_color};
            border: 1px solid {border_color};
            padding: {Spacing.XXS}px;
            border-radius: {Spacing.XXS}px;
        """


class StatusColors:
    """Color mappings for different status types."""

    SUCCESS = {
        'bg': Colors.SUCCESS_LIGHT,
        'border': Colors.SUCCESS,
        'text': Colors.SUCCESS_DARKER
    }

    ERROR = {
        'bg': Colors.DANGER_LIGHT,
        'border': Colors.DANGER,
        'text': Colors.DANGER_DARKER
    }

    PROCESSING = {
        'bg': Colors.PRIMARY_LIGHT,
        'border': Colors.PRIMARY,
        'text': Colors.PRIMARY_DARKER
    }

    WARNING = {
        'bg': Colors.WARNING_LIGHT,
        'border': Colors.WARNING,
        'text': Colors.WARNING_DARK
    }

    INFO = {
        'bg': Colors.INFO_LIGHT,
        'border': Colors.INFO,
        'text': Colors.INFO_DARK
    }

    CACHED = {
        'bg': Colors.INFO_LIGHTER,
        'border': Colors.INFO,
        'text': Colors.BLACK
    }

    DELETED = {
        'bg': Colors.GRAY_300,
        'border': Colors.GRAY_500,
        'text': Colors.BLACK
    }


# Export convenience functions
def get_status_colors(status_type: str) -> Dict[str, str]:
    """Get colors for a status type.

    Args:
        status_type: One of 'success', 'error', 'processing', 'warning', 'info', 'cached', 'deleted'

    Returns:
        Dictionary with 'bg', 'border', and 'text' keys
    """
    status_map = {
        'success': StatusColors.SUCCESS,
        'error': StatusColors.ERROR,
        'processing': StatusColors.PROCESSING,
        'warning': StatusColors.WARNING,
        'info': StatusColors.INFO,
        'cached': StatusColors.CACHED,
        'deleted': StatusColors.DELETED
    }

    return status_map.get(status_type.lower(), StatusColors.INFO)
