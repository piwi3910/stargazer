# Stargazer - Astrophotography Processing

Stargazer is a powerful astrophotography processing application that provides advanced image stacking and processing capabilities for astronomical images.

## Features

- **Image Stacking**: Advanced stacking algorithms for deep sky images
- **Star Detection**: Automatic star detection and alignment using astroalign
- **Color Processing**: Support for both monochrome and color images
- **FITS Support**: Full support for FITS file format
- **Live Preview**: Real-time preview of processing results
- **Batch Processing**: Efficient handling of large image sets
- **Parallel Processing**: Multi-core CPU utilization for improved performance

## Requirements

- Python 3.10 or higher
- OpenCV for image processing
- Astropy for FITS file handling
- AstroAlign for image registration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/stargazer.git
cd stargazer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Launch the application:
```bash
python src/main.py
```

2. Load your images:
   - Click "Open Files" to select light frames
   - Optionally add dark, flat, and bias frames
   - Configure stacking parameters

3. Process images:
   - Click "Stack" to begin processing
   - Monitor progress in real-time
   - Preview results as they become available

## Documentation

- [Image Processing Pipeline](docs/pipeline.md)
- [Configuration Options](docs/configuration.md)

## Project Structure

```
stargazer/
├── docs/                    # Documentation
├── src/                     # Source code
│   ├── threads/            # Processing threads
│   ├── widgets/            # UI components
│   ├── image_processor.py  # Core processing logic
│   └── main.py            # Application entry point
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Key Components

### Image Processor

The core image processing engine supports:
- Star detection and alignment using astroalign
- Multiple stacking algorithms
- Color calibration
- Noise reduction
- Parallel processing

### User Interface

Built with PyQt6, featuring:
- Intuitive controls
- Real-time preview
- Progress monitoring
- Flexible file management

## Performance

- Efficient parallel processing using multiple CPU cores
- Optimized memory management for large datasets
- Smart batch processing for improved performance
- Automatic resource optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenCV](https://opencv.org/) for image processing capabilities
- [Astropy](https://www.astropy.org/) for FITS file handling
- [AstroAlign](https://astroalign.readthedocs.io/) for image registration
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the user interface
