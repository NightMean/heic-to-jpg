# Version 1.0

# Pip package versions used during testing:
# pyexiv2==2.12.0
# pillow_heif==0.16.0
# pillow==10.4.0
# tqdm==4.65.0

import logging
import sys
import io
import argparse
import pillow_heif
import pyexiv2
import unicodedata
from pathlib import Path
from PIL import Image, ImageCms
from pillow_heif import read_heif
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from argparse import RawTextHelpFormatter

# Function to set up logging
def setup_logging(verbose, log_file, use_tqdm):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set to the lowest level to ensure all messages are processed

    class TqdmLoggingHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                tqdm.write(msg)
                self.flush()
            except Exception:
                self.handleError(record)

    # Console handler
    if use_tqdm:
        console_handler = TqdmLoggingHandler(sys.stdout)
    else:
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

# Function to properly rotate the image upon conversion
def rotate_image(image, orientation):
    """Rotate image according to the EXIF orientation."""
    if orientation in (1, 2, 3, 4, 5, 6, 7, 8):
        return image
    else:
        return image

# Function to read HEIF file and convert to PIL Image
def read_heif_file(heif_path):
    heif_file = pillow_heif.read_heif(heif_path)
    image = Image.frombytes(
        heif_file.mode,
        heif_file.size,
        heif_file.data,
        "raw",
        heif_file.mode,
        heif_file.stride,
    )
    return image, heif_file

# Function to apply ICC profile to image
def apply_icc_profile(image, heif_file, file_name):
    icc_profile = heif_file.info.get('icc_profile')
    if (icc_profile):
        icc_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
        image.info['icc_profile'] = icc_profile.tobytes()
        logging.info(f"ICC profile extracted and applied to {file_name}")
    else:
        logging.warning(f"No ICC profile found in {file_name}")
    return image

# Function to read EXIF metadata and rotate image
def process_exif_data(image, heif_path, file_name):
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
        elif "Failed to open the data source" in str(e):
            logging.error(f"Error reading EXIF metadata from {file_name}: The file name contains special characters. Please rename the file and try again.")
            exif_data = {}
        else:
            logging.warning(f"Error reading EXIF metadata from {file_name}: {e}")
            exif_data = {}
    return image, exif_data

# Function to save image as JPEG in 4:4:4 Subsampling
def save_image_as_jpeg(image, jpg_path, quality, file_name):
    try:
        image.convert("YCbCr").save(jpg_path, "JPEG", quality=quality, subsampling=0, icc_profile=image.info.get('icc_profile'))
    except Exception as e:
        logging.error(f"Failed to save JPEG file: {jpg_path}. Error: {e}")
        return False
    return True

# Function to write EXIF data to JPEG
def write_exif_data_to_jpeg(jpg_path, exif_data, file_name):
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

# Function to handle output directory creation
def handle_output_directory(output_dir, preserve_structure, input_dir, heif_path):
    if preserve_structure and input_dir:
        relative_path = heif_path.relative_to(input_dir)
        output_subdir = output_dir / relative_path.parent
        if not output_subdir.exists():
            output_subdir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {output_subdir}")
    else:
        output_subdir = output_dir
        if not output_subdir.exists():
            output_subdir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {output_subdir}")
    return output_subdir

# Function to normalize filenames by removing special characters
def normalize_filename(file_path):
    normalized_name = unicodedata.normalize('NFKD', file_path.stem).encode('ascii', 'ignore').decode('ascii')
    normalized_path = file_path.with_name(normalized_name + file_path.suffix)
    return normalized_path

# Function to rename files to normalized names
def rename_files(files):
    normalized_files = []
    for file_path in files:
        normalized_path = normalize_filename(file_path)
        if normalized_path != file_path:
            # Check if the normalized path already exists
            if normalized_path.exists():
                # Find a unique name
                counter = 1
                while True:
                    new_name = f"{normalized_path.stem}_renamed_{counter}{normalized_path.suffix}"
                    new_path = normalized_path.with_name(new_name)
                    if not new_path.exists():
                        normalized_path = new_path
                        break
                    counter += 1
            file_path.rename(normalized_path)
        normalized_files.append(normalized_path)
    return normalized_files

# Main conversion function
def convert_heif_to_jpg(heif_path, output_dir, quality, delete_original, preserve_structure=False, input_dir=None, index=None, total=None):
    file_name = Path(heif_path).name
    if index is not None and total is not None:
        logging.info(f"Processing file {index} of {total}: {heif_path}")
    logging.info(f"Converting {heif_path} to JPEG with quality={quality}")
    try:
        # Required to enable HEIC/HEIF support by pyexiv2
        pyexiv2.enableBMFF()
        
        image, heif_file = read_heif_file(heif_path)
        image = apply_icc_profile(image, heif_file, file_name)
        image, exif_data = process_exif_data(image, heif_path, file_name)
        image = image.convert("RGB")

        output_subdir = handle_output_directory(output_dir, preserve_structure, input_dir, heif_path)
        jpg_path = output_subdir / Path(heif_path).with_suffix('.jpg').name

        if not save_image_as_jpeg(image, jpg_path, quality, file_name):
            return None

        write_exif_data_to_jpeg(jpg_path, exif_data, file_name)
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
        return [f for f in directory.rglob('*') if f.suffix.lower() in ['.heic', '.heif']]
    else:
        return [f for f in directory.glob('*') if f.suffix.lower() in ['.heic', '.heif']]

def process_images(heif_files, output_dir, quality, delete_original, preserve_structure, input_dir, workers, show_progress):
    total_files = len(heif_files)
    progress_bar = tqdm(total=total_files, desc="Converting", unit="file") if show_progress else None

    def convert_wrapper(file_path, index):
        logging.info(f"Processing file {index + 1} of {total_files}: {file_path}")
        convert_heif_to_jpg(file_path, output_dir, quality, delete_original, preserve_structure, input_dir)
        if progress_bar:
            progress_bar.update(1)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(convert_wrapper, heif_files[i], i): i for i in range(total_files)}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error occurred during file processing: {e}")

    if progress_bar:
        progress_bar.close()

def convert_all_heif_to_jpg(input_dir, output_dir, recursive, quality, delete_original, preserve_structure, workers, show_progress, char_norm):
    logging.info(f"Starting conversion in directory: {input_dir} with recursive={recursive}")
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        logging.error(f"The specified directory does not exist: {input_dir}")
        return

    heif_files = find_heif_files(input_dir, recursive)
    if not heif_files:
        logging.info(f"No HEIF/HEIC files found in directory: {input_dir}")
        return

    if char_norm:
        heif_files = rename_files(heif_files)

    process_images(heif_files, output_dir, quality, delete_original, preserve_structure, input_dir, workers, show_progress)
    logging.info("Conversion process complete.")

def main():
    parser = argparse.ArgumentParser(description="Converts HEIF/HEIC files to JPEG while preserving EXIF metadata and ICC Profile.", formatter_class=RawTextHelpFormatter, allow_abbrev=False)
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
                        help="Save log output to the specified file. \nLog should be used as last argument")
    parser.add_argument('--delete', action='store_true', 
                        help="Automatically delete original HEIF/HEIC files after conversion.")
    parser.add_argument('-p', '--preserve-structure', action='store_true',
                        help="Preserve directory structure by creating subdirectories in the output folder for each \nsubdirectory found in the input folder. Only works with -r or --recursive.")
    parser.add_argument('-w', '--workers', type=int, default=4,
                        help="Number of threads to process images concurrently. Default is 4.")
    parser.add_argument('--progress', action='store_true', 
                        help="Show a progress bar for the conversion process.")
    parser.add_argument('-c', '--character-normalization', action='store_true',
                        help="Normalize filenames by replacing special characters.\n\nWARNING: Files will be renamed only if their filenames are altered during normalization.\nIf a file with the same normalized name already exists in the input directory, it will be\nrenamed with a '_renamed_1', '_renamed_2', etc. suffix.")

    args = parser.parse_args()
    use_tqdm = args.progress
    setup_logging(args.verbose, args.log, use_tqdm)

    if args.preserve_structure and not args.recursive:
        logging.error("The --preserve-structure argument can only be used with -r or --recursive.")
        sys.exit(1)

    input_dir = Path(args.dir) if args.dir else Path.cwd()
    output_dir = Path(args.output)

    if args.quality < 1 or args.quality > 100:
        logging.error("Quality must be between 1 and 100.")
        return

    if not args.dir and not args.yes:   
        confirm = input(f"No argument for input directory specified. \nContinue in the current directory ({input_dir})? [y/N]: ")
        if confirm.lower() != 'y':
            logging.info("Operation cancelled by the user.")
            return

    logging.info(f"No argument for quality specified, using default (95%%)" if args.quality == 95 else f"Using specified quality={args.quality}%")
    logging.info(f"HEIC to JPG script started with input directory: {input_dir}, output directory: {output_dir}, recursive={args.recursive}, and workers={args.workers}")

    convert_all_heif_to_jpg(input_dir, output_dir, args.recursive, args.quality, args.delete, args.preserve_structure, args.workers, args.progress, args.character_normalization)

if __name__ == '__main__':
    main()