from concurrent.futures import ProcessPoolExecutor
import traceback
import time
import numpy as np
from .base_processor import BaseBatchProcessor
from .alignment import AlignmentUtils

class CPUBatchProcessor(BaseBatchProcessor):
    def __init__(self, cpu_count=1):
        """Initialize CPU batch processor"""
        super().__init__(cpu_count)

    def _align_single_image(self, args):
        """Align a single image (for parallel processing)"""
        data, reference, is_color = args
        try:
            # Handle color images channel by channel
            if is_color:
                aligned_data = np.zeros_like(data)
                for channel in range(3):
                    result = AlignmentUtils.align_mono_image(
                        data[:,:,channel], 
                        reference[:,:,channel]
                    )
                    if result[0] is not None:
                        aligned_data[:,:,channel] = result[0]
                    else:
                        return None
                return aligned_data
            else:
                # Handle monochrome images
                result = AlignmentUtils.align_mono_image(data, reference)
                return result[0] if result[0] is not None else None
            
        except Exception as e:
            print(f"Failed to align image: {str(e)}")
            traceback.print_exc()
            return None

    def process_batch(self, batch_data, current_stack, is_color, start_idx):
        """Process a batch of images using CPU parallel processing"""
        try:
            self._reset_timings()
            start_total = time.time()
            
            # Prepare alignment arguments
            align_args = [(data, current_stack, is_color) for data in batch_data]
            valid_count = 0
            
            # Use ProcessPoolExecutor for parallel processing
            with ProcessPoolExecutor(max_workers=self.cpu_count) as executor:
                aligned_results = list(executor.map(self._align_single_image, align_args))
            
            # Accumulate aligned images using running average
            for aligned_data in aligned_results:
                if aligned_data is not None:
                    # Update running average
                    if valid_count == 0:
                        current_stack = aligned_data
                    else:
                        weight = 1.0 / (valid_count + 1)
                        current_stack = current_stack * (1 - weight) + aligned_data * weight
                    valid_count += 1
            
            self.timings['total_processing'] = time.time() - start_total
            
            return current_stack, valid_count
            
        except Exception as e:
            print(f"Error processing batch: {str(e)}")
            traceback.print_exc()
            return current_stack, 0

    def estimate_optimal_batch_size(self, image_shape, is_color, available_memory):
        """Estimate optimal batch size for CPU processing"""
        # For CPU processing, we can handle larger batches
        base_size = super().estimate_optimal_batch_size(image_shape, is_color, available_memory)
        return min(base_size * 2, 16)  # Allow larger batches but cap at 16
