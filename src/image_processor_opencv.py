import numpy as np
import cv2
from astropy.io import fits
import astroalign
from photutils.detection import DAOStarFinder
from photutils.background import Background2D, MedianBackground
import ccdproc
from astropy.nddata import CCDData
import astropy.units as u
from astropy.stats import sigma_clip
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing
import psutil

class ImageProcessor:
    def __init__(self):
        """Initialize the image processor"""
        # Check if CUDA is available and properly initialized
        self.use_cuda = False
        try:
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                # Try to initialize CUDA context
                cv2.cuda.setDevice(0)
                test_mat = cv2.cuda_GpuMat()
                self.use_cuda = True
                self.cuda_device = cv2.cuda.getDevice()
                self.cuda_device_name = cv2.cuda.getDeviceInfo(self.cuda_device).name()
                print(f"Successfully initialized CUDA device: {self.cuda_device_name}")
            else:
                print("No CUDA-capable devices found")
        except Exception as e:
            print(f"Failed to initialize CUDA: {str(e)}")
            self.use_cuda = False
        
        # Get number of CPU cores for parallel processing
        self.cpu_count = multiprocessing.cpu_count()
        # Calculate optimal batch size based on available memory
        available_memory = psutil.virtual_memory().available
        self.batch_size = max(4, min(16, available_memory // (1024 * 1024 * 1024)))  # 1GB per image estimate
        
    def is_color_image(self, header, data):
        """Determine if image is color based on header and data"""
        # Check header for color information
        if 'NAXIS3' in header:
            return True
        if 'COLORIMG' in header:
            return header['COLORIMG']
        if 'BAYERPAT' in header:
            return True
        # Check data dimensions
        if len(data.shape) == 3 and (data.shape[2] == 3 or data.shape[0] == 3):
            return True
        return False
    
    def debayer_image(self, data, header):
        """Convert Bayer pattern to RGB using GPU if available"""
        if 'BAYERPAT' not in header:
            return data
        
        pattern = header['BAYERPAT'].upper()
        pattern_map = {
            'RGGB': cv2.COLOR_BAYER_RG2RGB,
            'BGGR': cv2.COLOR_BAYER_BG2RGB,
            'GRBG': cv2.COLOR_BAYER_GR2RGB,
            'GBRG': cv2.COLOR_BAYER_GB2RGB
        }
        
        if pattern not in pattern_map:
            return data
        
        try:
            data_uint16 = data.astype(np.uint16)
            if self.use_cuda:
                with cv2.cuda_GpuMat() as gpu_data:
                    gpu_data.upload(data_uint16)
                    try:
                        result = cv2.cuda.cvtColor(gpu_data, pattern_map[pattern])
                        return result.download()
                    except cv2.error as e:
                        print(f"GPU debayering failed: {str(e)}, falling back to CPU")
                        return cv2.cvtColor(data_uint16, pattern_map[pattern])
            else:
                return cv2.cvtColor(data_uint16, pattern_map[pattern])
        except Exception as e:
            print(f"Debayering error: {str(e)}")
            return data
    
    def align_image(self, args):
        """Align a single image with optimized memory usage"""
        data, reference, is_color = args
        try:
            if is_color:
                # Ensure data is in HWC format and use green channel for alignment
                if data.shape[0] == 3:
                    data = np.transpose(data, (1, 2, 0))
                if reference.shape[0] == 3:
                    reference = np.transpose(reference, (1, 2, 0))
                
                # Compute transformation using green channel
                transform = astroalign.find_transform(data[:,:,1], reference[:,:,1])
                
                # Preallocate output array
                aligned_data = np.empty_like(data)
                for channel in range(3):
                    aligned_data[:,:,channel] = astroalign.apply_transform(transform[0], 
                                                                         data[:,:,channel], 
                                                                         reference[:,:,channel])[0]
                return aligned_data
            else:
                transform = astroalign.find_transform(data, reference)
                return astroalign.apply_transform(transform[0], data, reference)[0]
        except Exception:
            return None

    def process_batch(self, batch_data, current_stack, is_color, start_idx):
        """Process a batch of images efficiently"""
        align_args = [(data, current_stack, is_color) for data in batch_data]
        
        # Use context manager for proper resource cleanup
        with ProcessPoolExecutor(max_workers=self.cpu_count) as executor:
            aligned_results = list(executor.map(self.align_image, align_args))
        
        # Pre-allocate accumulator array
        accumulator = np.zeros_like(current_stack, dtype=np.float64)
        valid_count = 0
        
        # Accumulate aligned images
        for aligned_data in aligned_results:
            if aligned_data is not None:
                accumulator += aligned_data
                valid_count += 1
        
        if valid_count > 0:
            # Update running average efficiently
            weight = start_idx / (start_idx + valid_count)
            current_stack *= weight
            current_stack += accumulator * (1 - weight) / valid_count
        
        return current_stack, valid_count
    
    def process_images(self, file_paths, progress_callback=None, update_callback=None, preview_callback=None):
        """Process a list of FITS images with improved batch processing"""
        try:
            # Log hardware utilization
            if progress_callback:
                if self.use_cuda:
                    progress_callback(f"GPU acceleration enabled - Using {self.cuda_device_name}", "INFO")
                    progress_callback(f"CUDA version: {cv2.cuda.getCompiledVersion()}", "INFO")
                    progress_callback(f"OpenCV version: {cv2.__version__}", "INFO")
                else:
                    progress_callback("GPU acceleration disabled - Using CPU mode", "INFO")
                    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                        progress_callback("Note: CUDA-capable GPU detected but initialization failed", "WARNING")
                progress_callback(f"CPU threads available: {self.cpu_count}", "INFO")
                progress_callback(f"Batch size: {self.batch_size} images per batch", "INFO")
            
            headers = []
            is_color = None
            current_stack = None
            processed_count = 0
            
            # First pass: determine image type and load first image
            with fits.open(file_paths[0]) as hdul:
                first_data = hdul[0].data
                first_header = hdul[0].header
                is_color = self.is_color_image(first_header, first_data)
                
                if progress_callback:
                    progress_callback(f"Image type detection: {'Color' if is_color else 'Monochrome'}", "INFO")
                    if is_color and self.use_cuda:
                        progress_callback("Using GPU acceleration for debayering", "INFO")
                
                if is_color and 'BAYERPAT' in first_header:
                    first_data = self.debayer_image(first_data, first_header)
                
                current_stack = first_data.astype(np.float32)
                headers.append(first_header)
                processed_count += 1
                
                if preview_callback:
                    preview_callback(current_stack, first_header)
                if update_callback:
                    update_callback(1, len(file_paths))
            
            # Process remaining images in optimized batches
            remaining_files = file_paths[1:]
            
            for batch_start in range(0, len(remaining_files), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(remaining_files))
                batch_files = remaining_files[batch_start:batch_end]
                
                if progress_callback:
                    progress_callback(f"Processing batch {(batch_start // self.batch_size) + 1} with {len(batch_files)} images using {self.cpu_count} threads", "INFO")
                
                # Load batch data efficiently
                batch_data = []
                for file_path in batch_files:
                    try:
                        with fits.open(file_path) as hdul:
                            data = hdul[0].data.astype(np.float32)
                            header = hdul[0].header
                            headers.append(header)
                            
                            if is_color and 'BAYERPAT' in header:
                                data = self.debayer_image(data, header)
                            
                            batch_data.append(data)
                    except Exception as e:
                        if progress_callback:
                            progress_callback(f"Failed to load {os.path.basename(file_path)}: {str(e)}", "ERROR")
                        continue
                
                # Process batch
                current_stack, valid_count = self.process_batch(
                    batch_data, current_stack, is_color, processed_count
                )
                processed_count += valid_count
                
                if preview_callback:
                    preview_callback(current_stack, headers[-1])
                if update_callback:
                    update_callback(processed_count, len(file_paths))
            
            # Merge headers and update metadata
            result_header = self.merge_headers(headers)
            result_header['NCOMBINE'] = processed_count
            result_header.add_history(f'Stacked {processed_count} frames using astroalign')
            result_header.add_history(f'Reference frame: {os.path.basename(file_paths[0])}')
            result_header['COLORIMG'] = is_color
            
            # Add processing information to header
            result_header.add_history(f'Processing mode: {"GPU" if self.use_cuda else "CPU"}')
            if self.use_cuda:
                result_header.add_history(f'GPU device: {self.cuda_device_name}')
                result_header.add_history(f'CUDA version: {cv2.cuda.getCompiledVersion()}')
            else:
                result_header.add_history(f'CPU threads: {self.cpu_count}')
            result_header.add_history(f'Batch size: {self.batch_size}')
            
            # Set up proper FITS header structure
            result_header, fits_data = self.setup_fits_header(result_header, current_stack, is_color)
            
            if preview_callback:
                preview_callback(current_stack, result_header)
            
            if progress_callback:
                if self.use_cuda:
                    progress_callback(f"Stacking completed using GPU ({self.cuda_device_name})", "SUCCESS")
                else:
                    progress_callback(f"Stacking completed using CPU ({self.cpu_count} threads)", "SUCCESS")
            
            return True, fits_data, result_header
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error processing images: {str(e)}", "ERROR")
            raise

    # [Rest of the methods remain unchanged]
    def merge_headers(self, headers):
        """Merge FITS headers preserving important metadata"""
        result = headers[0].copy()
        
        # Update history
        for header in headers[1:]:
            if 'HISTORY' in header:
                for history in header['HISTORY']:
                    result.add_history(history)
        
        # Preserve common metadata
        metadata_keys = [
            'TELESCOP', 'INSTRUME', 'OBSERVER', 'OBJECT',
            'FOCALLEN', 'APERTURE', 'FILTER', 'GAIN',
            'XPIXSZ', 'YPIXSZ', 'XBINNING', 'YBINNING',
            'BAYERPAT', 'CCD-TEMP'
        ]
        
        for key in metadata_keys:
            values = set()
            for header in headers:
                if key in header:
                    values.add(str(header[key]))
            if len(values) == 1:
                result[key] = headers[0][key]
            elif len(values) > 1:
                result[key] = 'Multiple'
        
        return result
    
    def setup_fits_header(self, header, data, is_color):
        """Set up proper FITS header for the data structure"""
        new_header = header.copy()
        
        # Set basic FITS keywords
        new_header['SIMPLE'] = True
        new_header['BITPIX'] = -32  # 32-bit float
        
        # Set proper NAXIS values based on data shape
        if is_color:
            # For color images, ensure data is in HWC format
            if len(data.shape) == 3:
                if data.shape[0] == 3:
                    data = np.transpose(data, (1, 2, 0))
            new_header['NAXIS'] = 3
            new_header['NAXIS1'] = data.shape[1]  # width
            new_header['NAXIS2'] = data.shape[0]  # height
            new_header['NAXIS3'] = 3  # RGB channels
        else:
            new_header['NAXIS'] = 2
            new_header['NAXIS1'] = data.shape[1]  # width
            new_header['NAXIS2'] = data.shape[0]  # height
                
        return new_header, data
    
    def detect_stars(self, image):
        """Detect stars using DAOStarFinder"""
        try:
            # If color image, use green channel for star detection
            if len(image.shape) == 3:
                if image.shape[0] == 3:  # If channels first, transpose
                    image = np.transpose(image, (1, 2, 0))
                data = image[:,:,1]  # Green channel
            else:
                data = image
            
            # Ensure data is positive
            data = data - np.min(data)
            
            # Estimate background
            bkg_estimator = MedianBackground()
            bkg = Background2D(data, (50, 50), filter_size=(3, 3),
                             bkg_estimator=bkg_estimator)
            
            # Subtract background
            data_sub = data - bkg.background
            
            # Create DAOStarFinder object
            mean, median, std = np.mean(data_sub), np.median(data_sub), np.std(data_sub)
            daofind = DAOStarFinder(fwhm=3.0, threshold=5.*std)
            
            # Find stars
            sources = daofind(data_sub)
            
            if sources is None:
                return []
            
            # Return star positions and fluxes
            stars = []
            for source in sources:
                stars.append((source['xcentroid'], source['ycentroid'], source['flux']))
            
            # Sort by flux (brightest first)
            stars.sort(key=lambda x: x[2], reverse=True)
            return stars
            
        except Exception as e:
            print(f"Error detecting stars: {str(e)}")
            return []
    
    def normalize_image(self, data):
        """Normalize image data to positive values"""
        # Handle color images
        if len(data.shape) == 3:
            if data.shape[0] == 3:  # If channels first, transpose
                data = np.transpose(data, (1, 2, 0))
            normalized = np.zeros_like(data, dtype=np.float32)
            
            if self.use_cuda:
                # Process each channel on GPU
                for i in range(3):
                    channel = data[:,:,i]
                    gpu_channel = cv2.cuda_GpuMat()
                    gpu_channel.upload(channel.astype(np.float32))
                    
                    # Normalize on GPU
                    min_val = float(np.min(channel))
                    channel_shifted = cv2.cuda.subtract(gpu_channel, min_val)
                    clipped = sigma_clip(channel_shifted.download(), sigma=3, maxiters=5)
                    max_val = float(np.max(clipped))
                    
                    if max_val > 0:
                        normalized[:,:,i] = channel_shifted.download() / max_val
            else:
                # CPU processing
                for i in range(3):
                    channel = data[:,:,i]
                    min_val = np.min(channel)
                    channel = channel - min_val
                    clipped = sigma_clip(channel, sigma=3, maxiters=5)
                    max_val = np.max(clipped)
                    if max_val > 0:
                        normalized[:,:,i] = channel / max_val
            return normalized
        else:
            # Monochrome image processing
            if self.use_cuda:
                gpu_data = cv2.cuda_GpuMat()
                gpu_data.upload(data.astype(np.float32))
                min_val = float(np.min(data))
                data_shifted = cv2.cuda.subtract(gpu_data, min_val)
                clipped = sigma_clip(data_shifted.download(), sigma=3, maxiters=5)
                max_val = float(np.max(clipped))
                if max_val > 0:
                    return data_shifted.download() / max_val
                return data_shifted.download()
            else:
                min_val = np.min(data)
                data = data - min_val
                clipped = sigma_clip(data, sigma=3, maxiters=5)
                max_val = np.max(clipped)
                if max_val > 0:
                    data = data / max_val
                return data
    
    def analyze_image(self, data):
        """Analyze a single image using photutils"""
        try:
            # If color image, use green channel for analysis
            if len(data.shape) == 3:
                if data.shape[0] == 3:  # If channels first, transpose
                    data = np.transpose(data, (1, 2, 0))
                analyze_data = data[:,:,1]  # Green channel
            else:
                analyze_data = data
            
            # Normalize data for analysis
            norm_data = self.normalize_image(analyze_data)
            
            # Detect stars
            stars = self.detect_stars(norm_data)
            star_count = len(stars)
            
            # Calculate basic statistics
            if self.use_cuda:
                gpu_data = cv2.cuda_GpuMat()
                gpu_data.upload(analyze_data.astype(np.float32))
                mean = float(cv2.cuda.mean(gpu_data)[0])
                std = float(cv2.cuda.meanStdDev(gpu_data)[1][0])
            else:
                mean = np.mean(analyze_data)
                std = np.std(analyze_data)
            
            snr = mean / std if std > 0 else 0
            
            # Calculate average star intensity
            star_intensities = [flux for _, _, flux in stars]
            avg_star_intensity = np.mean(star_intensities) if star_intensities else 0
            
            return {
                "mean": mean,
                "std": std,
                "snr": snr,
                "star_count": star_count,
                "avg_star_intensity": avg_star_intensity
            }
            
        except Exception as e:
            raise Exception(f"Error analyzing image: {str(e)}")
