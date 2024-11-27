import os
import sys
import subprocess
import urllib.request
import ssl
import certifi

def log(message, level="INFO"):
    print(f"[{level}] {message}")

def download_wheel():
    url = "https://github.com/cudawarped/opencv-python-cuda-wheels/releases/download/4.10.0.84/opencv_contrib_python-4.10.0.84-cp37-abi3-win_amd64.whl"
    wheel_name = "opencv_contrib_python-4.10.0.84-cp37-abi3-win_amd64.whl"
    
    log(f"Downloading {url}")
    
    # Create HTTPS context with certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    try:
        with urllib.request.urlopen(url, context=ssl_context) as response:
            with open(wheel_name, 'wb') as out_file:
                out_file.write(response.read())
        return wheel_name
    except Exception as e:
        log(f"Download failed: {str(e)}", "ERROR")
        return None

def uninstall_existing():
    log("Uninstalling existing OpenCV packages...")
    packages = [
        "opencv-python",
        "opencv-contrib-python",
        "opencv-python-headless",
        "opencv-contrib-python-headless"
    ]
    for package in packages:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", package],
                     capture_output=True)

def install_wheel(wheel_path):
    log(f"Installing {wheel_path}")
    result = subprocess.run([sys.executable, "-m", "pip", "install", wheel_path],
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        log(f"Installation failed: {result.stderr}", "ERROR")
        return False
    
    log(result.stdout)
    return True

def main():
    # Download the wheel
    wheel_path = download_wheel()
    if not wheel_path:
        return False
    
    try:
        # Uninstall existing OpenCV packages
        uninstall_existing()
        
        # Install the wheel
        success = install_wheel(wheel_path)
        
        # Clean up
        if os.path.exists(wheel_path):
            os.remove(wheel_path)
        
        if success:
            log("Installation completed successfully!")
        else:
            log("Installation failed!", "ERROR")
        
        return success
    
    except Exception as e:
        log(f"Error during installation: {str(e)}", "ERROR")
        if os.path.exists(wheel_path):
            os.remove(wheel_path)
        return False

if __name__ == "__main__":
    main()
