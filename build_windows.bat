@echo off
echo Building Stargazer Windows Executable...

REM Create and activate virtual environment
python -m venv venv
call venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt
pip install pyinstaller

REM Build executable
pyinstaller --name stargazer ^
    --windowed ^
    --icon=resources/icon.ico ^
    --add-data "resources;resources" ^
    --hidden-import astropy.io.fits.compression ^
    --hidden-import astropy.io.fits.hdu ^
    --hidden-import astropy.io.fits.header ^
    --hidden-import astropy.io.fits.convenience ^
    --hidden-import astropy.io.fits.card ^
    --hidden-import astropy.io.fits.verify ^
    --hidden-import astropy.io.fits.util ^
    --hidden-import astropy.utils.xml ^
    --hidden-import astropy.utils.xml.writer ^
    --hidden-import astropy.utils.xml.check ^
    --hidden-import astropy.utils.xml.validate ^
    --hidden-import astropy.utils.xml.unify ^
    --hidden-import astropy.utils.xml.iterparser ^
    --hidden-import astropy.utils.xml.writer ^
    --hidden-import numpy.random.common ^
    --hidden-import numpy.random.bounded_integers ^
    --hidden-import numpy.random.entropy ^
    --hidden-import photutils.detection ^
    --hidden-import photutils.background ^
    --hidden-import photutils.segmentation ^
    --hidden-import photutils.utils ^
    --hidden-import astroalign ^
    src/main.py

REM Copy additional files
xcopy /s /y docs dist\stargazer\docs\
copy README.md dist\stargazer\
copy LICENSE dist\stargazer\

echo Build complete. Executable is in dist/stargazer/stargazer.exe
