import numpy as np
import multiprocessing
import psutil
import os
from concurrent.futures import ProcessPoolExecutor
import traceback

class BaseProcessor:
    def __init__(self):
        """Initialize the base image processor"""
        # Get number of CPU cores for parallel processing
        self.cpu_count = multiprocessing.cpu_count()
        # Calculate optimal batch size based on available memory
        available_memory = psutil.virtual_memory().available
        self.batch_size = max(4, min(16, available_memory // (1024 * 1024 * 1024)))  # 1GB per image estimate

    def is_color_image(self, header, data):
        """Determine if image is color based on header and data"""
        if 'NAXIS3' in header:
            return True
        if 'COLORIMG' in header:
            return header['COLORIMG']
        if 'BAYERPAT' in header:
            return True
        if len(data.shape) == 3 and (data.shape[2] == 3 or data.shape[0] == 3):
            return True
        return False

    def merge_headers(self, headers):
        """Merge FITS headers preserving important metadata"""
        result = headers[0].copy()
        
        for header in headers[1:]:
            if 'HISTORY' in header:
                for history in header['HISTORY']:
                    result.add_history(history)
        
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
        new_header['SIMPLE'] = True
        new_header['BITPIX'] = -32
        
        if is_color:
            if len(data.shape) == 3:
                if data.shape[0] == 3:
                    data = np.transpose(data, (1, 2, 0))
            new_header['NAXIS'] = 3
            new_header['NAXIS1'] = data.shape[1]
            new_header['NAXIS2'] = data.shape[0]
            new_header['NAXIS3'] = 3
        else:
            new_header['NAXIS'] = 2
            new_header['NAXIS1'] = data.shape[1]
            new_header['NAXIS2'] = data.shape[0]
                
        return new_header, data
