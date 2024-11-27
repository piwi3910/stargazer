import numpy as np
import traceback
import time

class BaseBatchProcessor:
    def __init__(self, cpu_count=1):
        """Initialize base batch processor"""
        self.cpu_count = cpu_count
        self.timings = {}  # Store timing information

    def _reset_timings(self):
        """Reset timing information"""
        self.timings = {
            'data_transfer_to_gpu': 0,
            'data_transfer_from_gpu': 0,
            'alignment_compute': 0,
            'transform_apply': 0,
            'memory_management': 0,
            'total_processing': 0
        }

    def estimate_optimal_batch_size(self, image_shape, is_color, available_memory):
        """Estimate optimal batch size based on image size and available memory"""
        # Calculate memory needed per image
        if is_color:
            bytes_per_image = np.prod(image_shape) * 3 * 4  # float32 = 4 bytes
        else:
            bytes_per_image = np.prod(image_shape) * 4  # float32 = 4 bytes
            
        # Account for memory overhead (alignment buffers, etc.)
        overhead_factor = 2.0
        memory_per_image = bytes_per_image * overhead_factor
        max_batch_size = min(16, available_memory // memory_per_image)
        
        return max(2, max_batch_size)  # Ensure at least 2 images per batch

    def process_batch(self, batch_data, current_stack, is_color, start_idx):
        """Process a batch of images - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement process_batch")
