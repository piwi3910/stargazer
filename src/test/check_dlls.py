import os
import sys
import ctypes
from ctypes import windll, c_buffer

def check_dll_dependencies(dll_path):
    print(f"Checking dependencies for: {dll_path}")
    
    try:
        # Try to load the DLL
        handle = windll.kernel32.LoadLibraryW(dll_path)
        if handle:
            print(f"Successfully loaded {dll_path}")
            
            # Get the list of dependent DLLs
            size = 1024
            while True:
                buffer = c_buffer(size)
                length = windll.kernel32.GetModuleFileNameW(handle, buffer, size)
                if length == 0:
                    break
                if length < size:
                    break
                size *= 2
            
            # Free the library
            windll.kernel32.FreeLibrary(handle)
            
            return True
    except Exception as e:
        print(f"Failed to load {dll_path}: {str(e)}")
        return False

def check_directory_dlls(directory, pattern=None):
    print(f"\nChecking DLLs in {directory}:")
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return
    
    for file in os.listdir(directory):
        if file.endswith('.dll'):
            if pattern is None or pattern in file:
                dll_path = os.path.join(directory, file)
                check_dll_dependencies(dll_path)

def main():
    # Check cv2.pyd
    venv_site_packages = os.path.join('D:\\', 'dev', 'stargazer', 'venv', 'Lib', 'site-packages')
    cv2_path = os.path.join(venv_site_packages, 'cv2', 'cv2.pyd')
    print(f"\nChecking cv2.pyd at: {cv2_path}")
    
    if not os.path.exists(cv2_path):
        print(f"cv2.pyd not found at {cv2_path}")
        return
    
    # Check cv2.pyd dependencies
    check_dll_dependencies(cv2_path)
    
    # Check OpenCV DLLs
    cv2_dir = os.path.dirname(cv2_path)
    check_directory_dlls(cv2_dir)
    
    # Check CUDA DLLs
    cuda_bin = os.path.join('C:\\', 'Program Files', 'NVIDIA GPU Computing Toolkit', 'CUDA', 'v11.0', 'bin')
    check_directory_dlls(cuda_bin, 'cudart64')
    check_directory_dlls(cuda_bin, 'cublas64')
    check_directory_dlls(cuda_bin, 'cufft64')
    check_directory_dlls(cuda_bin, 'curand64')
    check_directory_dlls(cuda_bin, 'cusolver64')
    check_directory_dlls(cuda_bin, 'cusparse64')
    check_directory_dlls(cuda_bin, 'nppc64')
    check_directory_dlls(cuda_bin, 'nppial64')
    check_directory_dlls(cuda_bin, 'nppicc64')
    check_directory_dlls(cuda_bin, 'nppidei64')
    check_directory_dlls(cuda_bin, 'nppif64')
    check_directory_dlls(cuda_bin, 'nppig64')
    check_directory_dlls(cuda_bin, 'nppim64')
    check_directory_dlls(cuda_bin, 'nppist64')
    check_directory_dlls(cuda_bin, 'nppisu64')
    check_directory_dlls(cuda_bin, 'nppitc64')
    check_directory_dlls(cuda_bin, 'npps64')

if __name__ == "__main__":
    main()
