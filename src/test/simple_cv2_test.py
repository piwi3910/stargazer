try:
    import cv2
    print(f"OpenCV version: {cv2.__version__}")
    print(f"CUDA available: {cv2.cuda.getCudaEnabledDeviceCount() > 0}")
except Exception as e:
    import sys
    print(f"Error: {e}")
    print(f"Python version: {sys.version}")
    print(f"Python path:")
    for p in sys.path:
        print(f"  - {p}")
