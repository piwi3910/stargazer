import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
from processors.batch.alignment import AlignmentUtils
from processors.analysis import ImageAnalysis
from photutils.detection import DAOStarFinder
from photutils.background import Background2D, MedianBackground
from scipy.ndimage import gaussian_filter

def enhance_image(data):
    """Enhance image for better star detection"""
    # Apply Gaussian smoothing to reduce noise
    smoothed = gaussian_filter(data, sigma=1.0)
    
    # Calculate percentile-based limits for contrast stretching
    vmin, vmax = np.percentile(smoothed, (1, 99))
    if vmax > vmin:
        enhanced = np.clip((smoothed - vmin) / (vmax - vmin), 0, 1)
    else:
        enhanced = smoothed - vmin
    
    return enhanced

def detect_stars_with_params(data, fwhm=3.0, threshold=3.0, box_size=50):
    """Detect stars with given parameters"""
    try:
        # Enhance image
        enhanced = enhance_image(data)
        
        # Estimate and subtract local background
        bkg_estimator = MedianBackground()
        bkg = Background2D(enhanced, (box_size, box_size), 
                          filter_size=(3, 3),
                          bkg_estimator=bkg_estimator)
        
        data_sub = enhanced - bkg.background
        
        # Calculate robust statistics for thresholding
        mean = np.mean(data_sub)
        median = np.median(data_sub)
        mad = np.median(np.abs(data_sub - median))  # Median Absolute Deviation
        std = mad * 1.4826  # Convert MAD to std estimate
        
        # Detect stars
        daofind = DAOStarFinder(fwhm=fwhm, 
                               threshold=threshold*std,
                               sharplo=0.2,  # More permissive shape constraints
                               sharphi=1.0,
                               roundlo=-1.0,
                               roundhi=1.0)
        sources = daofind(data_sub)
        
        if sources is None:
            return []
        
        # Extract star information
        stars = []
        for source in sources:
            stars.append((source['xcentroid'], source['ycentroid'], source['flux']))
        
        # Sort by flux and limit to brightest stars
        stars.sort(key=lambda x: x[2], reverse=True)
        return stars[:100]  # Limit to top 100 stars
        
    except Exception as e:
        print(f"Error in star detection: {str(e)}")
        return []

def analyze_image(file_path):
    """Analyze a test image to understand alignment issues"""
    print(f"\nAnalyzing image: {os.path.basename(file_path)}")
    
    # Load image
    with fits.open(file_path) as hdul:
        data = hdul[0].data
        header = hdul[0].header
    
    print(f"Image shape: {data.shape}")
    print(f"Data type: {data.dtype}")
    print(f"Value range: [{np.min(data)}, {np.max(data)}]")
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(file_path), 'analysis')
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Original image analysis
    fig = plt.figure(figsize=(20, 15))
    
    # Try different detection parameters
    thresholds = [2.0, 3.0, 5.0]
    fwhms = [2.0, 3.0, 4.0]
    box_sizes = [50, 100, 150]
    
    plot_idx = 1
    for threshold in thresholds:
        for fwhm in fwhms:
            ax = plt.subplot(3, 3, plot_idx)
            
            # Show image with adjusted contrast
            vmin, vmax = np.percentile(data, (1, 99))
            ax.imshow(data, cmap='gray', vmin=vmin, vmax=vmax)
            
            # Detect and plot stars
            stars = detect_stars_with_params(data, fwhm=fwhm, threshold=threshold)
            if stars:
                x_coords = [x for x, _, _ in stars]
                y_coords = [y for _, y, _ in stars]
                ax.scatter(x_coords, y_coords, c='red', marker='+', alpha=0.6)
            
            ax.set_title(f'FWHM={fwhm}, Threshold={threshold}σ\n{len(stars)} stars')
            ax.set_xticks([])
            ax.set_yticks([])
            plot_idx += 1
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{base_name}_analysis.png'))
    
    # Enhanced image analysis
    enhanced = enhance_image(data)
    fig = plt.figure(figsize=(20, 15))
    
    plot_idx = 1
    for threshold in thresholds:
        for fwhm in fwhms:
            ax = plt.subplot(3, 3, plot_idx)
            
            # Show enhanced image
            ax.imshow(enhanced, cmap='gray')
            
            # Detect and plot stars
            stars = detect_stars_with_params(enhanced, fwhm=fwhm, threshold=threshold)
            if stars:
                x_coords = [x for x, _, _ in stars]
                y_coords = [y for _, y, _ in stars]
                ax.scatter(x_coords, y_coords, c='red', marker='+', alpha=0.6)
            
            ax.set_title(f'Enhanced: FWHM={fwhm}, Threshold={threshold}σ\n{len(stars)} stars')
            ax.set_xticks([])
            ax.set_yticks([])
            plot_idx += 1
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{base_name}_enhanced_analysis.png'))
    
    # Print statistics
    print("\nImage Statistics:")
    print(f"Mean: {np.mean(data):.2f}")
    print(f"Median: {np.median(data):.2f}")
    print(f"Std Dev: {np.std(data):.2f}")
    print(f"Dynamic Range: {np.max(data) - np.min(data)}")
    
    # Calculate percentiles
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    print("\nPercentiles:")
    for p in percentiles:
        print(f"{p}%: {np.percentile(data, p):.2f}")
    
    # Create histograms
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Linear scale histogram
    ax1.hist(data.flatten(), bins=100)
    ax1.set_title('Intensity Histogram (Linear)')
    ax1.set_xlabel('Intensity')
    ax1.set_ylabel('Count')
    
    # Log scale histogram
    ax2.hist(data.flatten(), bins=100, log=True)
    ax2.set_title('Intensity Histogram (Log)')
    ax2.set_xlabel('Intensity')
    ax2.set_ylabel('Count (log)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{base_name}_histograms.png'))
    
    # Best parameters found
    print("\nBest star detection results:")
    best_stars = []
    best_params = None
    for threshold in thresholds:
        for fwhm in fwhms:
            stars = detect_stars_with_params(enhanced, fwhm=fwhm, threshold=threshold)
            if len(stars) > len(best_stars):
                best_stars = stars
                best_params = (fwhm, threshold)
    
    if best_params:
        print(f"Best parameters: FWHM={best_params[0]}, Threshold={best_params[1]}σ")
        print(f"Stars detected: {len(best_stars)}")
        if best_stars:
            fluxes = [flux for _, _, flux in best_stars]
            print(f"Star flux range: [{min(fluxes):.2f}, {max(fluxes):.2f}]")
            print(f"Mean star flux: {np.mean(fluxes):.2f}")
    else:
        print("No successful star detection")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_files_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        test_file = os.path.join(test_files_dir, sys.argv[1])
        if os.path.exists(test_file):
            analyze_image(test_file)
        else:
            print(f"File not found: {test_file}")
            # List available test files
            print("\nAvailable test files:")
            for file in os.listdir(test_files_dir):
                if file.endswith('.fit'):
                    print(f"  {file}")
    else:
        print("Usage: python analyze_test_image.py <filename>")
        print("Example: python analyze_test_image.py Light_M 42_10.0s_LP_20241124-005056.fit")
