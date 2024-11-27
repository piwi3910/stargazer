import os
import sys
import ctypes
from ctypes import windll, c_buffer

def try_load_dll(dll_path):
    try:
        dll = ctypes.CDLL(dll_path)
        print(f"Successfully loaded: {dll_path}")
        return True
    except Exception as e:
        print(f"Failed to load {dll_path}: {e}")
        return False

def main():
    cv2_dir = os.path.join('D:\\', 'dev', 'stargazer', 'venv', 'Lib', 'site-packages', 'cv2')
    
    # First, try to load the CUDA runtime
    cuda_dlls = [
        'cudart64_110.dll',
        'cublas64_11.dll',
        'cufft64_10.dll',
        'curand64_10.dll',
        'cusolver64_10.dll',
        'cusparse64_11.dll',
        'nppc64_11.dll',
        'nppial64_11.dll',
        'nppicc64_11.dll',
        'nppidei64_11.dll',
        'nppif64_11.dll',
        'nppig64_11.dll',
        'nppim64_11.dll',
        'nppist64_11.dll',
        'nppisu64_11.dll',
        'nppitc64_11.dll',
        'npps64_11.dll'
    ]
    
    print("\nTrying to load CUDA DLLs:")
    for dll in cuda_dlls:
        dll_path = os.path.join(cv2_dir, dll)
        try_load_dll(dll_path)
    
    # Then try to load OpenCV DLLs
    print("\nTrying to load OpenCV DLLs:")
    opencv_dlls = [
        'opencv_world410.dll',
        'opencv_ffmpeg410_64.dll',
        'opencv_cuda410_64.dll'
    ]
    
    for dll in opencv_dlls:
        dll_path = os.path.join(cv2_dir, dll)
        try_load_dll(dll_path)
    
    # Finally try to load cv2.pyd
    print("\nTrying to load cv2.pyd:")
    cv2_path = os.path.join(cv2_dir, 'cv2.pyd')
    try_load_dll(cv2_path)
    
    # Print directory contents
    print("\nDirectory contents:")
    if os.path.exists(cv2_dir):
        for file in os.listdir(cv2_dir):
            print(f"  {file}")
    else:
        print(f"Directory not found: {cv2_dir}")

if __name__ == "__main__":
    main()
