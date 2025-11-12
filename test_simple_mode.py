#!/usr/bin/env python3
"""Test script for Simple Mode implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_settings():
    """Test that settings include new simple mode parameters."""
    print("Testing settings...")
    from src.plugins.video_converter.settings import ConversionSettings

    settings = ConversionSettings()

    # Check new attributes exist
    assert hasattr(settings, 'simple_mode'), "Missing simple_mode attribute"
    assert hasattr(settings, 'simple_strategy'), "Missing simple_strategy attribute"
    assert hasattr(settings, 'balanced_auto_crf'), "Missing balanced_auto_crf attribute"
    assert hasattr(settings, 'balanced_quality_factor'), "Missing balanced_quality_factor attribute"

    # Check default values
    assert settings.simple_mode == False, "simple_mode should default to False"
    assert settings.simple_strategy == 'balanced', "simple_strategy should default to 'balanced'"
    assert settings.balanced_auto_crf == False, "balanced_auto_crf should default to False"
    assert settings.balanced_quality_factor == 1.0, "balanced_quality_factor should default to 1.0"

    print("✓ Settings test passed")

def test_balanced_crf():
    """Test balanced CRF calculation."""
    print("\nTesting balanced CRF calculation...")
    from src.plugins.video_converter.converter import calculate_balanced_crf, get_video_resolution

    # Test with default resolution (will use default 1920x1080)
    test_path = Path("/nonexistent/video.mp4")

    # Test neutral quality factor (1.0)
    crf = calculate_balanced_crf(test_path, 1.0)
    print(f"  CRF for FHD @ 1.0x quality: {crf}")
    assert 18 <= crf <= 35, f"CRF {crf} out of valid range"
    assert crf == 25, f"Expected CRF 25 for FHD @ 1.0x, got {crf}"

    # Test better quality (0.5)
    crf_better = calculate_balanced_crf(test_path, 0.5)
    print(f"  CRF for FHD @ 0.5x quality: {crf_better}")
    assert crf_better < crf, "Lower quality factor should give lower CRF"

    # Test more compression (2.0)
    crf_more = calculate_balanced_crf(test_path, 2.0)
    print(f"  CRF for FHD @ 2.0x quality: {crf_more}")
    assert crf_more > crf, "Higher quality factor should give higher CRF"

    print("✓ Balanced CRF test passed")

def test_simple_view_import():
    """Test that SimpleCompressorView can be imported."""
    print("\nTesting SimpleCompressorView import...")
    try:
        from src.plugins.video_converter.ui.simple_view import SimpleCompressorView
        print("✓ SimpleCompressorView import successful")
        return True
    except Exception as e:
        print(f"✗ SimpleCompressorView import failed: {e}")
        return False

def test_settings_serialization():
    """Test that settings can be serialized with new parameters."""
    print("\nTesting settings serialization...")
    from src.plugins.video_converter.settings import ConversionSettings

    settings = ConversionSettings()
    settings.simple_mode = True
    settings.simple_strategy = 'quality'
    settings.balanced_auto_crf = True
    settings.balanced_quality_factor = 0.8

    # Convert to dict
    data = settings.to_dict()
    assert 'simple_mode' in data, "simple_mode not in serialized data"
    assert 'simple_strategy' in data, "simple_strategy not in serialized data"
    assert 'balanced_auto_crf' in data, "balanced_auto_crf not in serialized data"
    assert 'balanced_quality_factor' in data, "balanced_quality_factor not in serialized data"

    # Recreate from dict
    settings2 = ConversionSettings.from_dict(data)
    assert settings2.simple_mode == True, "simple_mode not preserved"
    assert settings2.simple_strategy == 'quality', "simple_strategy not preserved"
    assert settings2.balanced_auto_crf == True, "balanced_auto_crf not preserved"
    assert settings2.balanced_quality_factor == 0.8, "balanced_quality_factor not preserved"

    print("✓ Settings serialization test passed")

if __name__ == '__main__':
    print("=" * 60)
    print("Testing Simple Mode Implementation")
    print("=" * 60)

    try:
        test_settings()
        test_balanced_crf()
        test_simple_view_import()
        test_settings_serialization()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
