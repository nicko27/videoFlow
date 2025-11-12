"""Pre-built text overlay templates for common use cases.

This module provides professional templates for titles, subtitles,
lower thirds, credits, and other common text overlay scenarios.
"""

from typing import Dict, List
from .text_overlay import (
    TextOverlay, TextStyle, TextPosition,
    AnimationType, TextAlignment
)


class TextTemplates:
    """Collection of pre-built text overlay templates."""

    # ========== TITLE TEMPLATES ==========

    @staticmethod
    def create_centered_title(
        text: str,
        start_frame: int = 0,
        end_frame: int = 150
    ) -> TextOverlay:
        """Create a large centered title overlay.

        Perfect for: Opening titles, chapter headings

        Args:
            text: Title text
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with centered title styling
        """
        style = TextStyle(
            font_family="Arial",
            font_size=72,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            outline_width=3,
            outline_color="#000000",
            shadow_offset=(4, 4),
            shadow_color="#000000",
            shadow_alpha=0.7,
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text,
            style=style,
            position=TextPosition.CENTER,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN_OUT,
            animation_duration=0.5,
            name="Centered Title"
        )

    @staticmethod
    def create_lower_third(
        main_text: str,
        subtitle: str,
        start_frame: int = 0,
        end_frame: int = 300
    ) -> List[TextOverlay]:
        """Create a professional lower third overlay.

        Perfect for: Speaker names, locations, captions

        Args:
            main_text: Main/primary text (name)
            subtitle: Secondary text (title/location)
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            List of two TextOverlay objects (main + subtitle)
        """
        # Main text style
        main_style = TextStyle(
            font_family="Arial",
            font_size=36,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            background_color="#0078D4",
            background_alpha=0.9,
            background_padding=15,
            alignment=TextAlignment.LEFT
        )

        # Subtitle style
        subtitle_style = TextStyle(
            font_family="Arial",
            font_size=24,
            color="#FFFFFF",
            alpha=0.9,
            bold=False,
            background_color="#005A9E",
            background_alpha=0.8,
            background_padding=12,
            alignment=TextAlignment.LEFT
        )

        main_overlay = TextOverlay(
            text=main_text,
            style=main_style,
            position=TextPosition.CUSTOM,
            custom_position=(50, 620),  # Assuming 1080p video
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.SLIDE_IN_LEFT,
            animation_duration=0.4,
            name="Lower Third - Main"
        )

        subtitle_overlay = TextOverlay(
            text=subtitle,
            style=subtitle_style,
            position=TextPosition.CUSTOM,
            custom_position=(50, 680),  # Below main text
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.SLIDE_IN_LEFT,
            animation_duration=0.5,
            name="Lower Third - Subtitle"
        )

        return [main_overlay, subtitle_overlay]

    @staticmethod
    def create_subtitle(
        text: str,
        start_frame: int = 0,
        end_frame: int = 100
    ) -> TextOverlay:
        """Create a subtitle/caption overlay.

        Perfect for: Dialogue, translations, captions

        Args:
            text: Subtitle text
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with subtitle styling
        """
        style = TextStyle(
            font_family="Arial",
            font_size=32,
            color="#FFFFFF",
            alpha=1.0,
            bold=False,
            outline_width=2,
            outline_color="#000000",
            background_color="#000000",
            background_alpha=0.7,
            background_padding=12,
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text,
            style=style,
            position=TextPosition.BOTTOM,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.2,
            name="Subtitle"
        )

    # ========== CREDITS TEMPLATES ==========

    @staticmethod
    def create_end_credits(
        credits_lines: List[str],
        start_frame: int = 0,
        duration_frames: int = 600
    ) -> TextOverlay:
        """Create scrolling end credits.

        Perfect for: Film credits, acknowledgments

        Args:
            credits_lines: List of credit lines
            start_frame: Starting frame
            duration_frames: Total duration in frames

        Returns:
            TextOverlay with credits styling
        """
        credits_text = "\n".join(credits_lines)

        style = TextStyle(
            font_family="Arial",
            font_size=28,
            color="#FFFFFF",
            alpha=1.0,
            bold=False,
            line_spacing=1.5,
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=credits_text,
            style=style,
            position=TextPosition.CENTER,
            start_frame=start_frame,
            end_frame=start_frame + duration_frames,
            animation=AnimationType.FADE_IN_OUT,
            animation_duration=1.0,
            name="End Credits"
        )

    # ========== SOCIAL MEDIA TEMPLATES ==========

    @staticmethod
    def create_youtube_intro(
        channel_name: str,
        tagline: str,
        start_frame: int = 0,
        end_frame: int = 180
    ) -> List[TextOverlay]:
        """Create YouTube-style intro overlay.

        Perfect for: Channel branding, video intros

        Args:
            channel_name: Channel name
            tagline: Channel tagline/motto
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            List of TextOverlay objects for intro
        """
        # Channel name
        channel_style = TextStyle(
            font_family="Impact",
            font_size=64,
            color="#FF0000",
            alpha=1.0,
            bold=True,
            outline_width=4,
            outline_color="#FFFFFF",
            alignment=TextAlignment.CENTER
        )

        # Tagline
        tagline_style = TextStyle(
            font_family="Arial",
            font_size=32,
            color="#FFFFFF",
            alpha=0.9,
            bold=False,
            alignment=TextAlignment.CENTER
        )

        channel_overlay = TextOverlay(
            text=channel_name,
            style=channel_style,
            position=TextPosition.CENTER,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.ZOOM_IN,
            animation_duration=0.8,
            name="YouTube Channel Name"
        )

        tagline_overlay = TextOverlay(
            text=tagline,
            style=tagline_style,
            position=TextPosition.CUSTOM,
            custom_position=(640, 600),  # Below channel name
            start_frame=start_frame + 30,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.5,
            name="YouTube Tagline"
        )

        return [channel_overlay, tagline_overlay]

    @staticmethod
    def create_instagram_caption(
        text: str,
        start_frame: int = 0,
        end_frame: int = 200
    ) -> TextOverlay:
        """Create Instagram-style caption overlay.

        Perfect for: Stories, reels, short-form content

        Args:
            text: Caption text
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with Instagram styling
        """
        style = TextStyle(
            font_family="Arial",
            font_size=40,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            outline_width=3,
            outline_color="#000000",
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text,
            style=style,
            position=TextPosition.BOTTOM,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.3,
            name="Instagram Caption"
        )

    # ========== INFORMATIONAL TEMPLATES ==========

    @staticmethod
    def create_warning_banner(
        text: str,
        start_frame: int = 0,
        end_frame: int = 150
    ) -> TextOverlay:
        """Create warning/alert banner overlay.

        Perfect for: Warnings, alerts, important notices

        Args:
            text: Warning text
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with warning styling
        """
        style = TextStyle(
            font_family="Arial",
            font_size=36,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            background_color="#FF0000",
            background_alpha=0.9,
            background_padding=20,
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text,
            style=style,
            position=TextPosition.TOP,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.3,
            name="Warning Banner"
        )

    @staticmethod
    def create_call_to_action(
        text: str,
        start_frame: int = 0,
        end_frame: int = 180
    ) -> TextOverlay:
        """Create call-to-action overlay.

        Perfect for: Subscribe reminders, website links, CTAs

        Args:
            text: CTA text
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with CTA styling
        """
        style = TextStyle(
            font_family="Arial",
            font_size=42,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            background_color="#00AA00",
            background_alpha=0.95,
            background_padding=18,
            outline_width=2,
            outline_color="#FFFFFF",
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text,
            style=style,
            position=TextPosition.BOTTOM_RIGHT,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.SLIDE_IN_BOTTOM,
            animation_duration=0.5,
            name="Call to Action"
        )

    # ========== NEW SOCIAL MEDIA TEMPLATES ==========

    @staticmethod
    def create_tiktok_caption(
        text: str,
        start_frame: int = 0,
        end_frame: int = 180
    ) -> TextOverlay:
        """Create TikTok-style caption overlay.

        Perfect for: TikTok videos, vertical short-form content

        Args:
            text: Caption text
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with TikTok styling
        """
        style = TextStyle(
            font_family="Impact",
            font_size=44,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            outline_width=4,
            outline_color="#000000",
            shadow_offset=(3, 3),
            shadow_color="#000000",
            shadow_alpha=0.6,
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text,
            style=style,
            position=TextPosition.BOTTOM,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.3,
            name="TikTok Caption"
        )

    @staticmethod
    def create_twitter_post(
        username: str,
        tweet_text: str,
        start_frame: int = 0,
        end_frame: int = 250
    ) -> List[TextOverlay]:
        """Create Twitter/X-style post overlay.

        Perfect for: Twitter/X quotes, social proof

        Args:
            username: Twitter handle (without @)
            tweet_text: Tweet content
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            List of TextOverlay objects (username + tweet)
        """
        # Username style
        username_style = TextStyle(
            font_family="Arial",
            font_size=28,
            color="#1DA1F2",  # Twitter blue
            alpha=1.0,
            bold=True,
            background_color="#FFFFFF",
            background_alpha=0.95,
            background_padding=15,
            alignment=TextAlignment.LEFT
        )

        # Tweet text style
        tweet_style = TextStyle(
            font_family="Arial",
            font_size=24,
            color="#000000",
            alpha=1.0,
            bold=False,
            background_color="#FFFFFF",
            background_alpha=0.95,
            background_padding=15,
            alignment=TextAlignment.LEFT
        )

        username_overlay = TextOverlay(
            text=f"@{username}",
            style=username_style,
            position=TextPosition.CUSTOM,
            custom_position=(100, 200),
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.4,
            name="Twitter Username"
        )

        tweet_overlay = TextOverlay(
            text=tweet_text,
            style=tweet_style,
            position=TextPosition.CUSTOM,
            custom_position=(100, 250),
            start_frame=start_frame + 20,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.4,
            name="Twitter Tweet"
        )

        return [username_overlay, tweet_overlay]

    @staticmethod
    def create_linkedin_quote(
        author: str,
        quote_text: str,
        start_frame: int = 0,
        end_frame: int = 300
    ) -> List[TextOverlay]:
        """Create LinkedIn-style professional quote.

        Perfect for: Business content, testimonials, professional quotes

        Args:
            author: Quote author name
            quote_text: Quote content
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            List of TextOverlay objects (quote + author)
        """
        # Quote style
        quote_style = TextStyle(
            font_family="Georgia",
            font_size=36,
            color="#FFFFFF",
            alpha=1.0,
            bold=False,
            background_color="#0A66C2",  # LinkedIn blue
            background_alpha=0.9,
            background_padding=25,
            alignment=TextAlignment.CENTER
        )

        # Author style
        author_style = TextStyle(
            font_family="Arial",
            font_size=24,
            color="#FFFFFF",
            alpha=0.9,
            bold=True,
            background_color="#0A66C2",
            background_alpha=0.9,
            background_padding=15,
            alignment=TextAlignment.CENTER
        )

        quote_overlay = TextOverlay(
            text=f'"{quote_text}"',
            style=quote_style,
            position=TextPosition.CENTER,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.6,
            name="LinkedIn Quote"
        )

        author_overlay = TextOverlay(
            text=f"- {author}",
            style=author_style,
            position=TextPosition.CUSTOM,
            custom_position=(640, 650),
            start_frame=start_frame + 30,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.4,
            name="LinkedIn Author"
        )

        return [quote_overlay, author_overlay]

    @staticmethod
    def create_facebook_headline(
        text: str,
        start_frame: int = 0,
        end_frame: int = 200
    ) -> TextOverlay:
        """Create Facebook-style headline overlay.

        Perfect for: Facebook videos, news-style content

        Args:
            text: Headline text
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with Facebook styling
        """
        style = TextStyle(
            font_family="Arial",
            font_size=42,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            background_color="#1877F2",  # Facebook blue
            background_alpha=0.95,
            background_padding=20,
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text,
            style=style,
            position=TextPosition.TOP,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.SLIDE_IN_TOP,
            animation_duration=0.5,
            name="Facebook Headline"
        )

    @staticmethod
    def create_clickbait_title(
        text: str,
        start_frame: int = 0,
        end_frame: int = 180
    ) -> TextOverlay:
        """Create eye-catching clickbait-style title.

        Perfect for: Attention-grabbing openers, viral content

        Args:
            text: Title text (should be exciting!)
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            TextOverlay with clickbait styling
        """
        style = TextStyle(
            font_family="Impact",
            font_size=56,
            color="#FFFF00",  # Yellow for attention
            alpha=1.0,
            bold=True,
            outline_width=5,
            outline_color="#FF0000",  # Red outline
            shadow_offset=(5, 5),
            shadow_color="#000000",
            shadow_alpha=0.8,
            alignment=TextAlignment.CENTER
        )

        return TextOverlay(
            text=text.upper(),  # ALL CAPS for maximum impact
            style=style,
            position=TextPosition.CENTER,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.ZOOM_IN,
            animation_duration=0.4,
            name="Clickbait Title"
        )

    @staticmethod
    def create_podcast_intro(
        podcast_name: str,
        episode: str,
        start_frame: int = 0,
        end_frame: int = 240
    ) -> List[TextOverlay]:
        """Create podcast-style intro overlay.

        Perfect for: Podcast clips, audio content videos

        Args:
            podcast_name: Name of the podcast
            episode: Episode title or number
            start_frame: Starting frame
            end_frame: Ending frame

        Returns:
            List of TextOverlay objects (name + episode)
        """
        # Podcast name style
        name_style = TextStyle(
            font_family="Arial",
            font_size=48,
            color="#FFFFFF",
            alpha=1.0,
            bold=True,
            background_color="#9146FF",  # Podcast purple
            background_alpha=0.9,
            background_padding=20,
            alignment=TextAlignment.CENTER
        )

        # Episode style
        episode_style = TextStyle(
            font_family="Arial",
            font_size=28,
            color="#FFFFFF",
            alpha=0.9,
            bold=False,
            background_color="#7B2FFF",
            background_alpha=0.85,
            background_padding=15,
            alignment=TextAlignment.CENTER
        )

        name_overlay = TextOverlay(
            text=podcast_name,
            style=name_style,
            position=TextPosition.CENTER,
            start_frame=start_frame,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.6,
            name="Podcast Name"
        )

        episode_overlay = TextOverlay(
            text=episode,
            style=episode_style,
            position=TextPosition.CUSTOM,
            custom_position=(640, 600),
            start_frame=start_frame + 40,
            end_frame=end_frame,
            animation=AnimationType.FADE_IN,
            animation_duration=0.5,
            name="Podcast Episode"
        )

        return [name_overlay, episode_overlay]

    # ========== UTILITY METHODS ==========

    @staticmethod
    def get_all_templates() -> Dict[str, callable]:
        """Get dictionary of all available templates.

        Returns:
            Dict mapping template names to creation functions
        """
        return {
            "Centered Title": TextTemplates.create_centered_title,
            "Lower Third": TextTemplates.create_lower_third,
            "Subtitle": TextTemplates.create_subtitle,
            "End Credits": TextTemplates.create_end_credits,
            "YouTube Intro": TextTemplates.create_youtube_intro,
            "Instagram Caption": TextTemplates.create_instagram_caption,
            "TikTok Caption": TextTemplates.create_tiktok_caption,
            "Twitter Post": TextTemplates.create_twitter_post,
            "LinkedIn Quote": TextTemplates.create_linkedin_quote,
            "Facebook Headline": TextTemplates.create_facebook_headline,
            "Clickbait Title": TextTemplates.create_clickbait_title,
            "Podcast Intro": TextTemplates.create_podcast_intro,
            "Warning Banner": TextTemplates.create_warning_banner,
            "Call to Action": TextTemplates.create_call_to_action
        }

    @staticmethod
    def get_template_categories() -> Dict[str, List[str]]:
        """Get templates organized by category.

        Returns:
            Dict mapping category names to template names
        """
        return {
            "Titles": ["Centered Title", "Clickbait Title"],
            "Broadcast": ["Lower Third", "Subtitle"],
            "Credits": ["End Credits"],
            "Social Media": [
                "YouTube Intro",
                "Instagram Caption",
                "TikTok Caption",
                "Twitter Post",
                "LinkedIn Quote",
                "Facebook Headline"
            ],
            "Podcast": ["Podcast Intro"],
            "Informational": ["Warning Banner", "Call to Action"]
        }

    @staticmethod
    def get_template_description(template_name: str) -> str:
        """Get description for a template.

        Args:
            template_name: Name of template

        Returns:
            Template description
        """
        descriptions = {
            "Centered Title": "Large centered title for openings and chapters",
            "Lower Third": "Professional name/title overlay (broadcast style)",
            "Subtitle": "Classic subtitle/caption for dialogue",
            "End Credits": "Scrolling credits for acknowledgments",
            "YouTube Intro": "Branded channel intro with name and tagline",
            "Instagram Caption": "Bold caption for stories and reels",
            "TikTok Caption": "Impact-style caption for TikTok and short-form videos",
            "Twitter Post": "Twitter/X-style quote with username and tweet text",
            "LinkedIn Quote": "Professional quote with LinkedIn branding",
            "Facebook Headline": "Facebook-style headline with brand colors",
            "Clickbait Title": "Eye-catching title with bold colors for viral content",
            "Podcast Intro": "Podcast branding with show name and episode info",
            "Warning Banner": "High-visibility warning or alert",
            "Call to Action": "Engaging CTA button (subscribe, visit, etc.)"
        }
        return descriptions.get(template_name, "Custom text overlay template")
