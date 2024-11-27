from astropy.io import fits
import cv2
import os
import traceback
import psutil
from processors.base_processor import BaseProcessor
from processors.analysis import ImageAnalysis
from processors.batch import CPUBatchProcessor

class ImageProcessor(BaseProcessor):
    def __init__(self):
        """Initialize the image processor with all components"""
        super().__init__()
        
        # Initialize components
        self.analyzer = ImageAnalysis()
        self.batch_processor = CPUBatchProcessor(self.cpu_count)

    def debayer_image(self, data, header):
        """Convert Bayer pattern to RGB"""
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
            data_uint16 = data.astype('uint16')
            return cv2.cvtColor(data_uint16, pattern_map[pattern])
        except Exception as e:
            print(f"Debayering error: {str(e)}")
            return data

    def normalize_image(self, data):
        """Normalize image data"""
        return self.analyzer.normalize_image(data)

    def analyze_image(self, data):
        """Analyze image and compute statistics"""
        return self.analyzer.analyze_image(data)

    def detect_stars(self, image):
        """Detect stars in the image"""
        return self.analyzer.detect_stars(image)

    def process_batch(self, batch_data, current_stack, is_color, start_idx):
        """Process a batch of images"""
        return self.batch_processor.process_batch(batch_data, current_stack, is_color, start_idx)

    def process_images(self, file_paths, progress_callback=None, update_callback=None, preview_callback=None):
        """Process a list of FITS images"""
        try:
            if progress_callback:
                progress_callback(f"CPU threads available: {self.cpu_count}", "INFO")
                progress_callback(f"Batch size: {self.batch_size} images per batch", "INFO")
            
            headers = []
            is_color = None
            current_stack = None
            processed_count = 0
            
            # Process first image
            with fits.open(file_paths[0]) as hdul:
                first_data = hdul[0].data
                first_header = hdul[0].header
                is_color = self.is_color_image(first_header, first_data)
                
                if progress_callback:
                    progress_callback(f"Image type detection: {'Color' if is_color else 'Monochrome'}", "INFO")
                
                if is_color and 'BAYERPAT' in first_header:
                    first_data = self.debayer_image(first_data, first_header)
                
                current_stack = first_data.astype('float32')
                headers.append(first_header)
                processed_count += 1
                
                if preview_callback:
                    preview_callback(current_stack, first_header)
                if update_callback:
                    update_callback(1, len(file_paths))
            
            # Update batch size based on image characteristics
            self.batch_size = self.batch_processor.estimate_optimal_batch_size(
                first_data.shape,
                is_color,
                psutil.virtual_memory().available
            )
            
            if progress_callback:
                progress_callback(f"Adjusted batch size: {self.batch_size} images", "INFO")
            
            # Process remaining images in batches
            remaining_files = file_paths[1:]
            for batch_start in range(0, len(remaining_files), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(remaining_files))
                batch_files = remaining_files[batch_start:batch_end]
                
                if progress_callback:
                    progress_callback(f"Processing batch {(batch_start // self.batch_size) + 1}", "INFO")
                
                batch_data = []
                for file_path in batch_files:
                    try:
                        with fits.open(file_path) as hdul:
                            data = hdul[0].data.astype('float32')
                            header = hdul[0].header
                            headers.append(header)
                            
                            if is_color and 'BAYERPAT' in header:
                                data = self.debayer_image(data, header)
                            
                            batch_data.append(data)
                    except Exception as e:
                        if progress_callback:
                            progress_callback(f"Failed to load {os.path.basename(file_path)}: {str(e)}", "ERROR")
                        continue
                
                current_stack, valid_count = self.process_batch(
                    batch_data, current_stack, is_color, processed_count
                )
                processed_count += valid_count
                
                if preview_callback:
                    preview_callback(current_stack, headers[-1])
                if update_callback:
                    update_callback(processed_count, len(file_paths))
            
            # Prepare result
            result_header = self.merge_headers(headers)
            result_header['NCOMBINE'] = processed_count
            result_header.add_history(f'Stacked {processed_count} frames using astroalign')
            result_header.add_history(f'Reference frame: {os.path.basename(file_paths[0])}')
            result_header['COLORIMG'] = is_color
            result_header.add_history(f'CPU threads: {self.cpu_count}')
            
            result_header, fits_data = self.setup_fits_header(result_header, current_stack, is_color)
            
            if preview_callback:
                preview_callback(current_stack, result_header)
            
            if progress_callback:
                progress_callback(f"Stacking completed using CPU ({self.cpu_count} threads)", "SUCCESS")
            
            return True, fits_data, result_header
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error processing images: {str(e)}", "ERROR")
            traceback.print_exc()
            raise
