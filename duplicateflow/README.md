# DuplicateFlow

**CLI tool for detecting long video scenes (20min-1h) in longer videos (several hours) using 19 comparison algorithms.**

## 🎯 Features

- **19 Algorithms**: Statistical, structural, temporal, audio, ML, and deep learning methods
- **MD5 Caching**: Smart file identification for fast duplicate detection
- **Parallel Execution**: Processes multiple pairs and algorithms concurrently
- **Pipeline System**: Flexible filtering, weighting, and hybrid modes
- **Minimal CLI**: Simple command-line interface with tqdm progress bars
- **100% Free**: All algorithms use open-source libraries

## 🚀 Quick Start

### Installation

```bash
# Minimal installation (9 core algorithms)
pip install duplicateflow

# With audio support (12 algorithms)
pip install duplicateflow[audio]

# With ML algorithms (16 algorithms)
pip install duplicateflow[audio,ml]

# Full installation (19 algorithms, requires GPU for best performance)
pip install duplicateflow[full]
```

### Basic Usage

```bash
# Scan a video pair
duplicateflow scan --short scene.mp4 --long movie.mp4

# Run benchmark on test set
duplicateflow benchmark --test-set default

# Find duplicate files
duplicateflow duplicates scan /path/to/videos

# List available algorithms
duplicateflow algorithms list
```

## 📊 Algorithms

### Core (9 algorithms)
1. **Color Histogram** - Statistical color distribution
2. **Edge Pattern** - Structural edge detection
3. **Motion Analysis** - Temporal motion vectors
4. **Optical Flow** - Dense motion flow
5. **DCT Coefficients** - Frequency domain analysis
6. **SSIM** - Structural similarity
7. **Feature Matching** - Geometric feature points
8. **Frame Hash** - Perceptual hashing
9. **Subsequence Detection** - Multi-method temporal matching

### Audio (3 algorithms - requires `[audio]`)
10. **Audio Chromaprint** - Local audio fingerprinting
11. **MFCC** - Mel-frequency cepstral coefficients
12. **Audio Spectral** - Spectral similarity

### ML (4 algorithms - requires `[ml]`)
13. **NCD** - Normalized compression distance
14. **HOG** - Histogram of oriented gradients
15. **Wavelet** - Wavelet transform coefficients
16. **MS-SSIM** - Multi-scale SSIM

### Deep Learning (3 algorithms - requires `[dl]`, GPU recommended)
17. **ResNet Features** - CNN feature extraction
18. **CLIP Embeddings** - Vision-language model
19. **Action Recognition** - Temporal action detection

## 📖 Documentation

See [docs/](docs/) for complete documentation:
- [Architecture](docs/architecture.md)
- [Algorithm Details](docs/algorithms.md)
- [Pipeline Configuration](docs/pipelines.md)
- [API Reference](docs/api.md)

## 🛠️ Development

```bash
# Clone repository
git clone https://github.com/yourusername/duplicateflow
cd duplicateflow

# Install in development mode
pip install -e .[audio,ml,dev]

# Run tests
pytest

# Generate architecture.json
python scripts/generate_architecture_json.py
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

Built with:
- OpenCV, NumPy, SciPy
- scikit-image, librosa
- PyTorch, Transformers
- Click, tqdm, Pydantic

---

**Version**: 1.0.0
**Status**: Beta
**Python**: 3.10+
