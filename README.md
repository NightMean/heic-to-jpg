<p align="center"><img src="https://github.com/NightMean/heic_to_jpg/assets/5726996/ed5cb922-0e68-445f-9c1b-b693820a1cc5" width="25%" ></p>
<h1 align="center">HEIC/HEIF to JPEG converter</h1>

Designed for **HEIF/HEIC** images typically used by Apple iPhones, iPads or some newer Android devices. \
This script converts them to JPEG format while retaining EXIF metadata and ICC profiles. 

It supports batch processing, multi-threading for faster conversions, and provides the option to maintain the original directory structure.

## Prerequisites

- **[Python 3.x](https://www.python.org/downloads/)**
- [Pillow library](https://github.com/python-pillow/Pillow)
- [Pyexiv2 library](https://github.com/LeoHsiao1/pyexiv2)
- [Pillow_heif library](https://github.com/bigcat88/pillow_heif)
- [Tqdm library](https://github.com/tqdm/tqdm)
  
## How to install
### Linux:

#### 1. Clone the repository:
   ```bash
   git clone https://github.com/NightMean/heic_to_jpg.git
   ```
#### 2. Change directory to the cloned directory:
   ```bash
   cd heic_to_jpg
   ```
#### 3. Install dependencies using pip:
  ```bash
  pip install -r requirements.txt
  ```
### Windows: 

1. Click the green `Code` button at the top and press `Download ZIP`
2. Extract the ZIP to your desired directory
3. Hold `SHIFT + Right click` with mouse on empty space within the directory and click `Open Powershell Here`
4. Install Python dependencies using `pip`:
  ```bash
  pip install -r requirements.txt
  ```
 > [!NOTE]
 > This requires Python to be included in the [system's PATH environment variable](https://realpython.com/add-python-to-path/) to execute pip commands successfully.
  
# Usage
### Windows:
  ```bash
  python heic_to_jpg.py --progress
  ```
 ### Linux: 
  ```bash
  python3 heic_to_jpg.py --progress
  ```
  > [!TIP]
  > Unless the `--dir` argument is specified, the script defaults to using the current working directory. \
  > To specify an output directory for converted files, use the `--output` argument.



#### Linux example with arguments:
```bash
python3 heic_to_jpg.py --dir /path/to/heic/files --output /path/to/save/jpeg/files --preserve-structure --recursive --progress
```

## Arguments 
```
usage: heic_to_jpg_exif_test.py [-h] [-d DIR] [-o OUTPUT] [-r] [-q QUALITY] [-y] [-v] [-l LOG] [--delete] [-p] [-w WORKERS] [--progress] [-c]

Converts HEIF/HEIC files to JPEG while preserving EXIF metadata and ICC Profile.

options:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     The directory containing HEIF/HEIC files to convert. Default is the current working directory.
  -o OUTPUT, --output OUTPUT
                        The directory to save the converted JPEG files. Default is the current working directory.
  -r, --recursive       Convert files in subdirectories recursively.
  -q QUALITY, --quality QUALITY
                        The quality of the converted JPEG files (1-100). Default is 95%.
  -y, --yes             Suppress the confirmation prompt if no input directory is specified.
  -v, --verbose         Enable verbose logging.
  -l LOG, --log LOG     Save log output to the specified file.
                        Log should be used as last argument
  --delete              Automatically delete original HEIF/HEIC files after conversion.
  -p, --preserve-structure
                        Preserve directory structure by creating subdirectories in the output folder for each
                        subdirectory found in the input folder. Only works with -r or --recursive.
  -w WORKERS, --workers WORKERS
                        Number of threads to process images concurrently. Default is 4.
  --progress            Show a progress bar for the conversion process.
  -c, --character-normalization
                        Normalize filenames by replacing special characters.

                        WARNING: Files will be renamed only if their filenames are altered during normalization.
                        If a file with the same normalized name already exists in the input directory, it will be
                        renamed with a '_renamed_1', '_renamed_2', etc. suffix.
```
# Notes
- By default, files with special characters in their filenames will not have EXIF metadata applied due to limitations in pyexiv2 library. \
  To address this, use the `--character-normalization` argument provided by the script. \
  Alternatively, you can rename the files beforehand using tools like [FileBot](https://www.filebot.net/download.html)
- If the original image does not have metadata, the script will log a warning and proceed with the conversion.
#

 > [!WARNING]
 > This project provides built-in support for BMFF files (HEIF/HEIC) via pyexiv2 library. \
 > BMFF Support may be the subject of patent rights. \
 > Pyexiv2 shall not be held responsible for identifying any such patent rights or the legal consequences of using this code.
 > 
 > Please read the Exiv2 [statement on BMFF](https://github.com/exiv2/exiv2#BMFF) patents before using this project.

## How to inspect embedded metadata
[ExifTool](https://exiftool.org/) is a command-line application for Windows and Linux for reading and writing EXIF data with large support for different file types 
```bash
exiftool /path/to/your/photo
```

## Alternatives
### CLI based
 - [ImageMagick](https://imagemagick.org/) (Recommended)

### Web based
 - [PicFlow](https://picflow.com/convert/heic-to-jpg) - Fast, produces best quality - Most likely uses ImageMagick in the background
 - [ILoveIMG](https://www.iloveimg.com/convert-to-jpg/heic-to-jpg) - Similiar quality, smaller size

## References
 - [exiv2](https://exiv2.org/) is a powerful C++ library for reading and writing image metadata, offering command-line tools for versatile usage.
 - [pyexiv2](https://github.com/LeoHsiao1/pyexiv2) is a Python library for reading and writing image metadata in various image formats, with BMFF support.
 - [Pillow](https://github.com/python-pillow/Pillow) is a Python imaging library (fork of PIL) that provides extensive support for opening, manipulating, and saving many different image file formats.
 - [Pillow-heif](https://github.com/bigcat88/pillow_heif) is a Python library for working with HEIF images and plugin for Pillow.