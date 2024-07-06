# Version 1.0

import logging
import sys
import io
import argparse
import pillow_heif
from pathlib import Path
from PIL import Image, ImageCms
from pillow_heif import read_heif
import pyexiv2
from concurrent.futures import ThreadPoolExecutor

# Function to set up logging
def setup_logging(verbose, log_file):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set to the lowest level to ensure all messages are processed

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if verbose else logging.WARNING)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(logging.INFO)  # Log all INFO level messages to the file
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

# Needed function to properly rotate the image upon conversion

def rotate_image(image, orientation):
    """Rotate image according to the EXIF orientation."""
    if orientation in (1, 2, 3, 4, 5, 6, 7, 8):
        return image
    else:
        return image

def convert_heif_to_jpg(heif_path, output_dir, quality, delete_original, preserve_structure=False, input_dir=None, index=None, total=None):
    file_name = Path(heif_path).name
    if index is not None and total is not None:
        logging.info(f"Processing file {index} of {total}: {heif_path}")
    logging.info(f"Converting {heif_path} to JPEG with quality={quality}")
    try:
        # Enable BMFF (HEIC/HEIF) support by pyexiv2 library
        pyexiv2.enableBMFF()

        heif_file = pillow_heif.read_heif(heif_path)

        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )

        icc_profile = heif_file.info.get('icc_profile')
        if icc_profile:
            icc_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
            image.info['icc_profile'] = icc_profile.tobytes()
            logging.info(f"ICC profile extracted and applied to {file_name}")
        else:
            logging.warning(f"No ICC profile found in {file_name}")

        image = image.convert("RGB")

        try:
            heif_metadata = pyexiv2.Image(str(heif_path))
            exif_data = heif_metadata.read_exif()
            heif_metadata.close()

            orientation = int(exif_data.get("Exif.Image.Orientation", 1))
            image = rotate_image(image, orientation)
            exif_data["Exif.Image.Orientation"] = '1'  # Reset orientation to 'Horizontal (normal)'
        except RuntimeError as e:
            if "XMP Toolkit error 201" in str(e):
                logging.warning(f"No EXIF metadata found in {file_name}")
            elif "Failed to open the data source: No such file or directory (errno = 2)" in str(e):
                logging.error(f"Error reading EXIF metadata from {file_name}: The file name contains special characters. Please rename the file and try again.")
                exif_data = {}
            else:
                logging.warning(f"Error reading EXIF metadata from {file_name}: {e}")
                exif_data = {}

        if preserve_structure and input_dir:
            # Create the same directory structure in the output directory
            relative_path = heif_path.relative_to(input_dir)
            output_subdir = output_dir / relative_path.parent
            output_subdir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {output_subdir}")
        else:
            output_subdir = output_dir

        jpg_path = output_subdir / Path(heif_path).with_suffix('.jpg').name

        # Ensure no subsampling is applied
        try:
            image.convert("YCbCr").save(jpg_path, "JPEG", quality=quality, subsampling=0, icc_profile=image.info.get('icc_profile'))
        except Exception as e:
            logging.error(f"Failed to save JPEG file: {jpg_path}. Error: {e}")
            return None

        try:
            if exif_data:
                jpg_metadata = pyexiv2.Image(str(jpg_path))
                jpg_metadata.modify_exif(exif_data)
                jpg_metadata.close()
                logging.info(f"EXIF metadata successfully written to {jpg_path}")
            else:
                logging.warning(f"No EXIF data to write to {jpg_path}")
        except RuntimeError as e:
            logging.warning(f"Failed to write EXIF metadata to {jpg_path}: {e}")

        logging.info(f"Successfully converted {heif_path} to JPEG: {jpg_path}")

        if delete_original:
            try:
                Path(heif_path).unlink()
                logging.info(f"Deleted original HEIF file: {heif_path}")
            except Exception as e:
                logging.warning(f"Failed to delete original HEIF file: {heif_path}. Error: {e}")

        return jpg_path
    except FileNotFoundError as e:
        logging.error(f"File not found: {heif_path}. Error: {e}")
        return None
    except PermissionError as e:
        logging.error(f"Permission denied: {heif_path}. Error: {e}")
        return None
    except Exception as e:
        logging.exception(f"Failed to convert {file_name} to JPEG due to unexpected error: {e}")
        return None

def find_heif_files(directory, recursive):
    if recursive:
        return [p for p in directory.rglob('*') if p.suffix.lower() in ['.heif', '.heic']]
    else:
        return [p for p in directory.glob('*') if p.suffix.lower() in ['.heif', '.heic']]

def process_images(heif_files, output_dir, quality, delete_original, preserve_structure, input_dir, workers):
    total_files = len(heif_files)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(convert_heif_to_jpg, heif_path, output_dir, quality, delete_original, preserve_structure, input_dir, index + 1, total_files)
            for index, heif_path in enumerate(heif_files)
        ]
        for future in futures:
            future.result()  # Wait for all futures to complete

def convert_all_heif_to_jpg(input_dir, output_dir, recursive, quality, delete_original, preserve_structure, workers):
    logging.info(f"Starting conversion in directory: {input_dir} with recursive={recursive}")
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        logging.error(f"The specified directory does not exist: {input_dir}")
        return

    heif_files = find_heif_files(input_dir, recursive)
    if not heif_files:
        logging.info(f"No HEIF/HEIC files found in directory: {input_dir}")
        return

    process_images(heif_files, output_dir, quality, delete_original, preserve_structure, input_dir, workers)
    logging.info("Conversion process complete.")

def main():
    parser = argparse.ArgumentParser(description="Converts HEIF/HEIC files to JPEG while preserving EXIF metadata and ICC Profile.", allow_abbrev=False)
    parser.add_argument('-d', '--dir', type=str, default=None,
                        help="The directory containing HEIF/HEIC files to convert. Default is the current working directory.")
    parser.add_argument('-o', '--output', type=str, default=Path.cwd(),
                        help="The directory to save the converted JPEG files. Default is the current working directory.")
    parser.add_argument('-r', '--recursive', action='store_true',
                        help="Convert files in subdirectories recursively.")
    parser.add_argument('-q', '--quality', type=int, default=95,
                        help="The quality of the converted JPEG files (1-100). Default is 95%%.")
    parser.add_argument('-y', '--yes', action='store_true',
                        help="Suppress the confirmation prompt if no input directory is specified.")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable verbose logging.")
    parser.add_argument('-l', '--log', type=str,
                        help="Save log output to the specified file.")
    parser.add_argument('--delete', action='store_true',
                        help="Automatically delete original HEIF/HEIC files after conversion.")
    parser.add_argument('-p', '--preserve-structure', action='store_true',
                        help="Preserve directory structure by creating subdirectories in the output folder for each subdirectory found in the input folder. Only works with -r or --recursive.")
    parser.add_argument('-w', '--workers', type=int, default=4,
                        help="Number of threads to process images concurrently. Default is 4.")

    args = parser.parse_args()

    setup_logging(args.verbose, args.log)

    if args.preserve_structure and not args.recursive:
        logging.error("The --preserve-structure argument can only be used with -r or --recursive.")
        sys.exit(1)

    input_dir = Path(args.dir) if args.dir else Path.cwd()
    output_dir = Path(args.output)

    if args.quality < 1 or args.quality > 100:
        logging.error("Quality must be between 1 and 100.")
        return

    if not args.dir and not args.yes:
        confirm = input(f"No input directory specified. Continue in the current directory ({input_dir})? [y/N]: ")
        if confirm.lower() != 'y':
            logging.info("Operation cancelled by the user.")
            return

    logging.info(f"No argument for quality specified, using default (95%%)" if args.quality == 95 else f"Using specified quality={args.quality}%")
    logging.info(f"Script started with input directory: {input_dir}, output directory: {output_dir}, recursive={args.recursive}, and workers={args.workers}")

    convert_all_heif_to_jpg(input_dir, output_dir, args.recursive, args.quality, args.delete, args.preserve_structure, args.workers)

if __name__ == '__main__':
    main()
