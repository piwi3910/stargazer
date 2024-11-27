# Configuration Guide

This document details the configuration options available in Stargazer for optimizing image processing performance and quality.

## System Configuration

### CPU Settings

```python
CPU_CONFIG = {
    'threads': 'auto',         # Number of processing threads
    'chunk_size': 1000000,     # Memory chunk size for large files
    'parallel_loads': 4,       # Parallel file loading
    'enable_simd': True        # Use SIMD instructions
}
```

## Processing Parameters

### Star Detection

```python
STAR_DETECTION = {
    'detection_threshold': 5.0,  # Sigma threshold for star detection
    'min_star_size': 3,         # Minimum star size in pixels
    'max_star_size': 25,        # Maximum star size in pixels
    'edge_margin': 50,          # Pixel margin from image edges
    'saturation_limit': 0.95    # Maximum pixel value for valid stars
}
```

### Image Alignment

```python
ALIGNMENT = {
    'max_control_points': 50,    # Maximum stars used for alignment
    'min_matches': 10,          # Minimum required star matches
    'tolerance': 0.5,           # Pixel tolerance for matching
    'interpolation': 'cubic',   # Interpolation method
    'edge_crop': True           # Crop edges after alignment
}
```

### Stacking

```python
STACKING = {
    'method': 'average',        # Stacking method (average/median/kappa-sigma)
    'kappa': 2.5,              # Kappa-sigma clipping threshold
    'iterations': 3,           # Rejection iterations
    'weights': 'snr',          # Frame weighting method
    'normalize': True          # Normalize frames before stacking
}
```

## File Handling

### Input Formats

```python
FILE_FORMATS = {
    'fits': {
        'enabled': True,
        'extensions': ['.fit', '.fits', '.fts'],
        'verify_checksum': False
    },
    'raw': {
        'enabled': True,
        'extensions': ['.cr2', '.nef', '.arw'],
        'use_libraw': True
    }
}
```

### Output Settings

```python
OUTPUT = {
    'format': 'fits',          # Output file format
    'compression': None,       # FITS compression
    'bit_depth': 32,          # Output bit depth
    'create_preview': True,    # Generate preview image
    'save_metadata': True      # Include processing metadata
}
```

## Quality Control

### Calibration

```python
CALIBRATION = {
    'dark_scaling': True,      # Temperature-based dark scaling
    'flat_normalize': True,    # Normalize flat frames
    'bias_overscan': True,     # Use overscan region
    'hot_pixel_threshold': 5.0 # Hot pixel detection threshold
}
```

### Rejection Parameters

```python
REJECTION = {
    'snr_threshold': 3.0,      # Minimum SNR for frame inclusion
    'star_threshold': 100,     # Minimum stars for frame inclusion
    'max_shift': 50,          # Maximum allowed alignment shift
    'outlier_threshold': 3.0   # Statistical outlier threshold
}
```

## Performance Tuning

### Memory Management

```python
MEMORY = {
    'max_ram_usage': 0.75,     # Maximum RAM utilization
    'swap_threshold': 0.9,     # RAM threshold for swap usage
    'clear_interval': 5,       # Garbage collection interval
    'preload_frames': 2        # Number of frames to preload
}
```

### Cache Settings

```python
CACHE = {
    'enabled': True,           # Enable disk caching
    'max_size': '10GB',        # Maximum cache size
    'min_free_space': '50GB',  # Minimum required disk space
    'cleanup_threshold': 0.9   # Cache cleanup threshold
}
```

## Logging

### Log Configuration

```python
LOGGING = {
    'level': 'INFO',          # Logging level
    'file_logging': True,     # Enable file logging
    'console_logging': True,  # Enable console logging
    'log_directory': 'logs',  # Log file location
    'max_log_size': '100MB',  # Maximum log file size
    'backup_count': 5         # Number of log backups
}
```

### Progress Reporting

```python
PROGRESS = {
    'update_interval': 0.5,    # Progress update interval (seconds)
    'detailed_status': True,   # Show detailed status messages
    'eta_calculation': True,   # Show estimated time remaining
    'stage_reporting': True    # Report processing stages
}
```

## Environment Variables

The following environment variables can override default settings:

```bash
# Processing Configuration
STARGAZER_MAX_THREADS=8
STARGAZER_BATCH_SIZE=8

# File Handling
STARGAZER_TEMP_DIR=/path/to/temp
STARGAZER_CACHE_DIR=/path/to/cache

# Logging
STARGAZER_LOG_LEVEL=INFO
STARGAZER_LOG_DIR=/path/to/logs
```

## Configuration File

Settings can be specified in a `config.yaml` file:

```yaml
processing:
  star_detection:
    threshold: 5.0
    min_size: 3
  alignment:
    max_points: 50
    tolerance: 0.5
  stacking:
    method: average
    normalize: true

system:
  threads: auto
  cache_enabled: true
  log_level: INFO
```

## Applying Configuration

```python
from stargazer.config import Configuration

# Load configuration
config = Configuration.load('config.yaml')

# Override settings
config.processing.star_detection.threshold = 4.5

# Apply configuration
processor = ImageProcessor(config)
```

## Best Practices

1. **CPU Optimization**
   - Set threads to physical core count
   - Enable SIMD for compatible CPUs
   - Monitor system memory usage

2. **Memory Management**
   - Configure based on system RAM
   - Enable caching for large datasets
   - Monitor memory usage during processing

3. **Quality Settings**
   - Balance quality vs. performance
   - Adjust based on image characteristics
   - Use appropriate rejection parameters

4. **Batch Processing**
   - Adjust batch size based on available RAM
   - Monitor system resources
   - Balance throughput vs. responsiveness

5. **Logging**
   - Enable detailed logging during setup
   - Reduce logging in production
   - Regularly rotate log files
