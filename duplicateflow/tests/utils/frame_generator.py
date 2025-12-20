"""
Frame generation utilities for algorithm testing.

Provides helper functions to create synthetic test frames programmatically
without requiring actual video files.
"""

import numpy as np
from typing import Tuple


def create_black_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """
    Create an all-black frame.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels

    Returns:
        NumPy array of shape (height, width, 3) with all zeros
    """
    return np.zeros((height, width, 3), dtype=np.uint8)


def create_white_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """
    Create an all-white frame.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels

    Returns:
        NumPy array of shape (height, width, 3) with all 255s
    """
    return np.ones((height, width, 3), dtype=np.uint8) * 255


def create_color_frame(width: int = 640, height: int = 480,
                       r: int = 0, g: int = 0, b: int = 0) -> np.ndarray:
    """
    Create a solid color frame.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels
        r: Red channel value (0-255)
        g: Green channel value (0-255)
        b: Blue channel value (0-255)

    Returns:
        NumPy array of shape (height, width, 3) with specified color
    """
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = r
    frame[:, :, 1] = g
    frame[:, :, 2] = b
    return frame


def create_noise_frame(width: int = 640, height: int = 480, seed: int = None) -> np.ndarray:
    """
    Create a random noise frame.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels
        seed: Random seed for reproducibility (optional)

    Returns:
        NumPy array of shape (height, width, 3) with random values
    """
    if seed is not None:
        np.random.seed(seed)
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)


def create_gradient_frame(width: int = 640, height: int = 480,
                          direction: str = 'horizontal') -> np.ndarray:
    """
    Create a gradient frame.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels
        direction: 'horizontal', 'vertical', or 'diagonal'

    Returns:
        NumPy array of shape (height, width, 3) with gradient
    """
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    if direction == 'horizontal':
        for x in range(width):
            intensity = int((x / width) * 255)
            frame[:, x, :] = intensity
    elif direction == 'vertical':
        for y in range(height):
            intensity = int((y / height) * 255)
            frame[y, :, :] = intensity
    elif direction == 'diagonal':
        for y in range(height):
            for x in range(width):
                intensity = int(((x + y) / (width + height)) * 255)
                frame[y, x, :] = intensity
    else:
        raise ValueError(f"Invalid direction: {direction}. Use 'horizontal', 'vertical', or 'diagonal'")

    return frame


def create_checkerboard_frame(width: int = 640, height: int = 480,
                              square_size: int = 32) -> np.ndarray:
    """
    Create a checkerboard pattern frame.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels
        square_size: Size of each square in pixels

    Returns:
        NumPy array of shape (height, width, 3) with checkerboard pattern
    """
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            square_x = x // square_size
            square_y = y // square_size
            if (square_x + square_y) % 2 == 0:
                frame[y, x, :] = 255

    return frame


def add_noise(frame: np.ndarray, noise_level: int = 10, seed: int = None) -> np.ndarray:
    """
    Add random noise to a frame.

    Args:
        frame: Input frame (NumPy array)
        noise_level: Maximum noise deviation (±noise_level)
        seed: Random seed for reproducibility (optional)

    Returns:
        Noisy frame (clipped to 0-255 range)
    """
    if seed is not None:
        np.random.seed(seed)

    noise = np.random.randint(-noise_level, noise_level, frame.shape, dtype=np.int16)
    noisy = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


def adjust_brightness(frame: np.ndarray, factor: float = 1.2) -> np.ndarray:
    """
    Adjust frame brightness.

    Args:
        frame: Input frame (NumPy array)
        factor: Brightness multiplier (1.0 = unchanged, >1.0 = brighter, <1.0 = darker)

    Returns:
        Brightness-adjusted frame (clipped to 0-255 range)
    """
    adjusted = np.clip(frame.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    return adjusted


def adjust_contrast(frame: np.ndarray, factor: float = 1.5) -> np.ndarray:
    """
    Adjust frame contrast.

    Args:
        frame: Input frame (NumPy array)
        factor: Contrast multiplier (1.0 = unchanged, >1.0 = more contrast)

    Returns:
        Contrast-adjusted frame
    """
    mean = frame.mean()
    adjusted = np.clip((frame - mean) * factor + mean, 0, 255).astype(np.uint8)
    return adjusted


def create_similar_frames(base_frame: np.ndarray = None,
                         similarity: float = 0.95,
                         seed: int = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create two similar frames for testing similarity algorithms.

    Args:
        base_frame: Base frame to derive from (creates random if None)
        similarity: How similar frames should be (0.0-1.0)
        seed: Random seed for reproducibility

    Returns:
        Tuple of (frame1, frame2) with specified similarity level
    """
    if seed is not None:
        np.random.seed(seed)

    if base_frame is None:
        base_frame = create_noise_frame(seed=seed)

    # Create second frame with controlled differences
    noise_level = int((1.0 - similarity) * 50)  # Map similarity to noise level
    frame2 = add_noise(base_frame, noise_level=max(1, noise_level))

    return base_frame.copy(), frame2


def resize_frame(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    """
    Resize a frame using nearest neighbor interpolation.

    Args:
        frame: Input frame
        width: Target width
        height: Target height

    Returns:
        Resized frame
    """
    from scipy.ndimage import zoom

    h, w = frame.shape[:2]
    zoom_factors = (height / h, width / w, 1)

    return zoom(frame, zoom_factors, order=1).astype(np.uint8)


def create_test_frame_pair(scenario: str = 'identical') -> Tuple[np.ndarray, np.ndarray]:
    """
    Create a pair of test frames for specific testing scenarios.

    Args:
        scenario: Testing scenario:
            - 'identical': Two identical frames
            - 'very_similar': Two very similar frames (95% similar)
            - 'similar': Two similar frames (80% similar)
            - 'different': Two completely different frames
            - 'black_white': One black, one white
            - 'noise': Two random noise frames

    Returns:
        Tuple of (frame1, frame2)
    """
    if scenario == 'identical':
        frame = create_noise_frame(seed=42)
        return frame.copy(), frame.copy()

    elif scenario == 'very_similar':
        return create_similar_frames(similarity=0.95, seed=42)

    elif scenario == 'similar':
        return create_similar_frames(similarity=0.80, seed=42)

    elif scenario == 'different':
        frame1 = create_black_frame()
        frame2 = create_white_frame()
        return frame1, frame2

    elif scenario == 'black_white':
        return create_black_frame(), create_white_frame()

    elif scenario == 'noise':
        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=43)
        return frame1, frame2

    else:
        raise ValueError(f"Unknown scenario: {scenario}")
