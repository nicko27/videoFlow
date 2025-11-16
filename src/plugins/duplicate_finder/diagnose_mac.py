"""
Diagnostic script for macOS to check why pyacoustid might not be working.
"""

import sys
import subprocess
import os

def check_import(module_name):
    """Check if a Python module can be imported."""
    try:
        __import__(module_name)
        print(f"✓ {module_name} is installed")
        return True
    except ImportError:
        print(f"✗ {module_name} is NOT installed")
        return False

def check_command(cmd, name):
    """Check if a command-line tool is available."""
    try:
        result = subprocess.run(
            [cmd, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ {name} found: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ {name} not found (returncode: {result.returncode})")
            return False
    except FileNotFoundError:
        print(f"✗ {name} not found in PATH")
        return False
    except Exception as e:
        print(f"✗ {name} check failed: {e}")
        return False

def test_pyacoustid():
    """Test pyacoustid functionality."""
    try:
        import acoustid
        import chromaprint

        print("\n=== Testing pyacoustid functionality ===")

        # Try to extract fingerprint from a test file
        # (This will fail if no file provided, but we just want to see if the API works)
        test_file = "/dev/null"  # Dummy file
        try:
            duration, fp = acoustid.fingerprint_file(test_file)
            print(f"✗ Unexpected success with null file")
        except Exception as e:
            # Expected to fail with null file, but shows the API is accessible
            print(f"✓ acoustid.fingerprint_file API is accessible ({type(e).__name__})")

        # Test chromaprint decode
        try:
            # This should fail with invalid data, but shows API is accessible
            chromaprint.decode_fingerprint("invalid")
        except Exception as e:
            print(f"✓ chromaprint.decode_fingerprint API is accessible ({type(e).__name__})")

        return True

    except Exception as e:
        print(f"✗ Error testing pyacoustid: {e}")
        return False

def check_path():
    """Check PATH for ffmpeg, fpcalc, etc."""
    print("\n=== Checking PATH ===")
    path = os.environ.get('PATH', '')
    print(f"PATH directories:")
    for directory in path.split(':'):
        if 'brew' in directory.lower() or 'local' in directory.lower():
            print(f"  - {directory}")

def check_brew():
    """Check if Homebrew packages are installed."""
    print("\n=== Checking Homebrew ===")

    try:
        # Check if brew is installed
        result = subprocess.run(['brew', '--version'], capture_output=True, text=True)
        print(f"✓ Homebrew installed")

        # Check for chromaprint
        result = subprocess.run(['brew', 'list', 'chromaprint'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ chromaprint installed via Homebrew")
        else:
            print(f"✗ chromaprint NOT installed via Homebrew")
            print(f"  Run: brew install chromaprint")

        # Check for ffmpeg
        result = subprocess.run(['brew', 'list', 'ffmpeg'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ ffmpeg installed via Homebrew")
        else:
            print(f"✗ ffmpeg NOT installed via Homebrew")
            print(f"  Run: brew install ffmpeg")

    except FileNotFoundError:
        print(f"✗ Homebrew not found")
        print(f"  Install from: https://brew.sh")

def main():
    """Run all diagnostics."""
    print("=" * 60)
    print("macOS Scene Detection Diagnostic Tool")
    print("=" * 60)

    print("\n=== Checking Python Modules ===")
    has_acoustid = check_import('acoustid')
    has_chromaprint = check_import('chromaprint')
    has_numpy = check_import('numpy')
    has_scipy = check_import('scipy')

    print("\n=== Checking Command-Line Tools ===")
    has_fpcalc = check_command('fpcalc', 'fpcalc (chromaprint)')
    has_ffmpeg = check_command('ffmpeg', 'ffmpeg')
    has_ffprobe = check_command('ffprobe', 'ffprobe')

    check_path()
    check_brew()

    if has_acoustid and has_chromaprint:
        test_pyacoustid()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    issues = []

    if not has_acoustid or not has_chromaprint:
        issues.append("⚠️  pyacoustid/chromaprint not installed properly")
        print("\nInstall with:")
        print("  pip3 install pyacoustid chromaprint")

    if not has_fpcalc:
        issues.append("⚠️  fpcalc not found in PATH")
        print("\nInstall with:")
        print("  brew install chromaprint")

    if not has_ffmpeg or not has_ffprobe:
        issues.append("⚠️  ffmpeg/ffprobe not found")
        print("\nInstall with:")
        print("  brew install ffmpeg")

    if not has_scipy:
        print("\nOptional (for Shazam algorithm):")
        print("  pip3 install scipy")

    if len(issues) == 0:
        print("\n✅ All dependencies are installed!")
        print("\nIf scene detection still doesn't work, the issue might be:")
        print("1. Videos are too different (try lowering min_match_ratio to 70%)")
        print("2. Videos are too long (use 'Long Video Sampling' algorithm)")
        print("3. pyacoustid can't read your video format")
    else:
        print(f"\n❌ Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  {issue}")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
