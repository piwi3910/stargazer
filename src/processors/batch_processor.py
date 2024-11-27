import numpy as np
import cupy as cp
import astroalign
from concurrent.futures import ProcessPoolExecutor
import traceback
import time

class BatchProcessor:
    def __init__(self, gpu_ops=None, cpu_count=1):
        """Initialize batch processor with optional GPU operations"""
        self.gpu_ops = gpu_ops
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

    def align_image(self, args):
        """Align a single image with optimized memory usage (CPU version)"""
        data, reference, is_color = args
        try:
            if is_color:
                if data.shape[0] == 3:
                    data = np.transpose(data, (1, 2, 0))
                if reference.shape[0] == 3:
                    reference = np.transpose(reference, (1, 2, 0))
                
                transform = astroalign.find_transform(data[:,:,1], reference[:,:,1])
                
                aligned_data = np.empty_like(data)
                for channel in range(3):
                    aligned_data[:,:,channel] = astroalign.apply_transform(transform[0], 
                                                                         data[:,:,channel], 
                                                                         reference[:,:,channel])[0]
                return aligned_data
            else:
                transform = astroalign.find_transform(data, reference)
                return astroalign.apply_transform(transform[0], data, reference)[0]
        except Exception as e:
            print(f"Failed to align image: {str(e)}")
            traceback.print_exc()
            return None

    def process_batch_gpu(self, batch_data, current_stack, is_color, start_idx):
        """Process multiple images in parallel on GPU"""
        try:
            batch_size = len(batch_data)
            
            # Move reference stack to GPU
            gpu_stack = cp.asarray(current_stack)
            
            # Pre-allocate GPU memory and move all data at once
            if is_color:
                gpu_batch = cp.stack([cp.asarray(img) for img in batch_data])  # Shape: [B, H, W, C]
                gpu_aligned = cp.zeros_like(gpu_batch)
            else:
                gpu_batch = cp.stack([cp.asarray(img) for img in batch_data])  # Shape: [B, H, W]
                gpu_aligned = cp.zeros_like(gpu_batch)
            
            valid_mask = cp.ones(batch_size, dtype=bool)  # Track valid alignments
            
            try:
                if is_color:
                    # Process all images in parallel for each channel
                    for channel in range(3):
                        # Download reference channel once
                        ref_channel = cp.asnumpy(gpu_stack[:,:,channel])
                        
                        # Process each image in the batch
                        for i in range(batch_size):
                            try:
                                # Compute transform (still using CPU astroalign)
                                img_channel = cp.asnumpy(gpu_batch[i,:,:,channel])
                                transform = astroalign.find_transform(img_channel, ref_channel)
                                
                                # Apply transform on GPU
                                gpu_aligned[i,:,:,channel] = cp.asarray(
                                    astroalign.apply_transform(transform[0], img_channel, ref_channel)[0]
                                )
                            except Exception:
                                valid_mask[i] = False
                else:
                    # Process monochrome images
                    ref_data = cp.asnumpy(gpu_stack)
                    
                    # Process each image in the batch
                    for i in range(batch_size):
                        try:
                            # Compute transform
                            img_data = cp.asnumpy(gpu_batch[i])
                            transform = astroalign.find_transform(img_data, ref_data)
                            
                            # Apply transform on GPU
                            gpu_aligned[i] = cp.asarray(
                                astroalign.apply_transform(transform[0], img_data, ref_data)[0]
                            )
                        except Exception:
                            valid_mask[i] = False
                
                # Update running average for all valid alignments
                valid_count = int(cp.sum(valid_mask))
                if valid_count > 0:
                    if start_idx == 0:
                        # First batch
                        weights = cp.zeros(batch_size)
                        weights[valid_mask] = 1.0 / valid_count
                        # Add batch and height/width dimensions for broadcasting
                        weights = weights.reshape(-1, 1, 1)
                        if is_color:
                            weights = weights.reshape(-1, 1, 1, 1)
                        gpu_stack = cp.sum(gpu_aligned[valid_mask] * weights, axis=0)
                    else:
                        # Subsequent batches
                        weights = cp.zeros(batch_size)
                        weights[valid_mask] = 1.0 / (start_idx + cp.arange(valid_count) + 1)
                        # Add batch and height/width dimensions for broadcasting
                        weights = weights.reshape(-1, 1, 1)
                        if is_color:
                            weights = weights.reshape(-1, 1, 1, 1)
                        
                        # Update running average
                        current_weight = 1.0 - weights[0]  # Weight for current stack
                        gpu_stack = gpu_stack * current_weight + cp.sum(gpu_aligned[valid_mask] * weights, axis=0)
                
                # Move result back to CPU
                current_stack = cp.asnumpy(gpu_stack)
                
                # Clear GPU memory
                del gpu_batch
                del gpu_aligned
                del gpu_stack
                self.gpu_ops.clear_memory()
                
                return current_stack, valid_count
                
            except Exception as e:
                print(f"Error in GPU batch processing: {str(e)}")
                traceback.print_exc()
                return current_stack, 0
                
        except Exception as e:
            print(f"Error setting up GPU batch processing: {str(e)}")
            traceback.print_exc()
            return current_stack, 0

    def process_batch(self, batch_data, current_stack, is_color, start_idx):
        """Process a batch of images"""
        try:
            self._reset_timings()
            start_total = time.time()

            if self.gpu_ops and self.gpu_ops.use_cuda:
                # Use parallel GPU processing
                t0 = time.time()
                current_stack, valid_count = self.process_batch_gpu(
                    batch_data, current_stack, is_color, start_idx
                )
                self.timings['total_processing'] = time.time() - t0
                
            else:
                # CPU-based processing
                align_args = [(data, current_stack, is_color) for data in batch_data]
                valid_count = 0
                
                # Use ProcessPoolExecutor for CPU parallel processing
                with ProcessPoolExecutor(max_workers=self.cpu_count) as executor:
                    aligned_results = list(executor.map(self.align_image, align_args))
                
                # Accumulate aligned images
                for aligned_data in aligned_results:
                    if aligned_data is not None:
                        if valid_count == 0:
                            weight = start_idx / (start_idx + 1)
                            current_stack = current_stack * weight + aligned_data * (1 - weight)
                        else:
                            weight = (start_idx + valid_count) / (start_idx + valid_count + 1)
                            current_stack = current_stack * weight + aligned_data * (1 - weight)
                        valid_count += 1
            
            # Print timing breakdown for GPU processing
            if self.gpu_ops and self.gpu_ops.use_cuda:
                print("\nGPU Processing Time Breakdown:")
                total = self.timings['total_processing']
                print(f"Total batch processing time: {total:.3f}s")
                print(f"Images processed: {valid_count}")
                if valid_count > 0:
                    print(f"Average time per image: {total/valid_count:.3f}s")
            
            return current_stack, valid_count
            
        except Exception as e:
            print(f"Error processing batch: {str(e)}")
            traceback.print_exc()
            return current_stack, 0

    def estimate_optimal_batch_size(self, image_shape, is_color, available_memory):
        """Estimate optimal batch size based on image size and available memory"""
        # Calculate memory needed per image
        if is_color:
            bytes_per_image = np.prod(image_shape) * 3 * 4  # float32 = 4 bytes
        else:
            bytes_per_image = np.prod(image_shape) * 4  # float32 = 4 bytes
            
        # Account for GPU memory overhead (alignment buffers, etc.)
        if self.gpu_ops and self.gpu_ops.use_cuda:
            overhead_factor = 3.0  # Conservative estimate
            memory_per_image = bytes_per_image * overhead_factor
            
            # For parallel processing, use larger batches
            max_batch_size = min(8, available_memory // memory_per_image)
        else:
            overhead_factor = 2.0
            memory_per_image = bytes_per_image * overhead_factor
            max_batch_size = min(16, available_memory // memory_per_image)
        
        return max(2, max_batch_size)  # Ensure at least 2 images per batch
