from astropy.io import fits
import sys
import traceback
import numpy as np

def analyze_fits_file(filepath):
    try:
        print(f"\nAnalyzing file: {filepath}")
        print("-" * 50)
        
        with fits.open(filepath) as hdul:
            print(f"Number of HDUs: {len(hdul)}")
            
            for i, hdu in enumerate(hdul):
                print(f"\nHDU {i} info:")
                print(f"Type: {type(hdu).__name__}")
                
                if hasattr(hdu, 'data') and hdu.data is not None:
                    print(f"Data shape: {hdu.data.shape}")
                    print(f"Data type: {hdu.data.dtype}")
                    try:
                        if isinstance(hdu.data, np.ndarray):
                            print(f"Min value: {np.nanmin(hdu.data)}")
                            print(f"Max value: {np.nanmax(hdu.data)}")
                            print(f"Data dimensions: {len(hdu.data.shape)}")
                            if len(hdu.data.shape) == 3:
                                print("Channel information:")
                                for c in range(hdu.data.shape[0]):
                                    print(f"  Channel {c} - Min: {np.nanmin(hdu.data[c])}, Max: {np.nanmax(hdu.data[c])}")
                    except Exception as e:
                        print(f"Could not compute data statistics: {str(e)}")
                else:
                    print("No data in this HDU")
                
                print("\nHeader information:")
                for card in hdu.header.cards:
                    print(f"{card.keyword}: {card.value}")

    except Exception as e:
        print(f"Error analyzing file: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()

def main():
    try:
        original_file = "src/test/Light_M 42_10.0s_LP_20241124-005130.fit"
        stacked_file = "src/test/Stargazer.fits"
        
        print("\nAnalyzing original file...")
        analyze_fits_file(original_file)
        
        print("\nAnalyzing stacked file...")
        analyze_fits_file(stacked_file)
        
    except Exception as e:
        print(f"Error in main: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
