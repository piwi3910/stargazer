import numpy as np
import astroalign
import traceback
from scipy.ndimage import gaussian_filter

class AlignmentUtils:
    @staticmethod
    def align_mono_image(data, reference):
        """Align a monochrome image using astroalign"""
        try:
            # Preprocess images
            data_proc = gaussian_filter(data.astype(np.float32), sigma=1.0)
            ref_proc = gaussian_filter(reference.astype(np.float32), sigma=1.0)
            
            # Use astroalign for registration
            aligned_data, transform = astroalign.register(data_proc, ref_proc)
            
            if aligned_data is None or transform is None:
                print("Alignment failed")
                return None, None
            
            return aligned_data, transform
            
        except Exception as e:
            print(f"Error in image alignment: {str(e)}")
            traceback.print_exc()
            return None, None
