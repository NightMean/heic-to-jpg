import logging
import sys
import io
import argparse
from pathlib import Path
from PIL import Image, ImageCms
from pillow_heif import read_heif
import pyexiv2

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def apply_orientation(image, orientation):
    """
    Applies the EXIF orientation to the image.

    Args:
        image (PIL.Image): The image to be oriented.
        orientation (int): The EXIF orientation value.

    Returns:
        PIL.Image: The oriented image.
    """
    if orientation == 1:
        return image
    elif orientation == 3:
        return image.rotate(180, expand=True)
    elif orientation == 6:
        return image.rotate(270, expand=True)
    elif orientation == 8:
        return image.rotate(90, expand=True)
    else:
        return image

def convert_heic_to_jpg(heic_path, output_dir, quality):
    """
    Converts a HEIC file to JPEG while retaining the ICC profile and EXIF data.

    Args:
        heic_path (str or Path): The path to the HEIC file.
        output_dir (str or Path): The directory to save the converted JPEG file.
        quality (int): The quality of the converted JPEG file.

    Returns:
        Path: The path to the converted JPEG file, or None if conversion fails.
    """
    file_name = Path(heic_path).name
    logging.info(f"Converting {heic_path} to JPEG with quality={quality}...")
    try:
        # Enable BMFF support for reading EXIF data
        pyexiv2.enableBMFF()

        heif_file = read_heif(heic_path)

        # Convert the HEIF image to a Pillow Image
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )

        # Extract the ICC profile
        icc_profile = heif_file.info.get('icc_profile')
        if icc_profile:
            icc_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
            image.info['icc_profile'] = icc_profile.tobytes()
            logging.info(f"ICC profile extracted and applied to {file_name}")
        else:
            logging.warning(f"No ICC profile found in {file_name}")

        # Convert the image to RGB
        image = image.convert("RGB")

        # Extract EXIF data using pyexiv2
        heif_metadata = pyexiv2.Image(str(heic_path))
        exif_data = heif_metadata.read_exif()

        # Apply the orientation based on EXIF data
        orientation = exif_data.get("Exif.Image.Orientation", 1)
        orientation = int(orientation)
        image = apply_orientation(image, orientation)

        # Save the image as JPEG without EXIF data
        jpg_path = Path(output_dir) / Path(heic_path).with_suffix('.jpg').name
        image.save(jpg_path, "JPEG", quality=quality, icc_profile=image.info.get('icc_profile'))

        # Apply EXIF data to the new JPEG file
        jpg_metadata = pyexiv2.Image(str(jpg_path))
        jpg_metadata.modify_exif(exif_data)
        jpg_metadata.close()
        heif_metadata.close()

        logging.info(f"Successfully converted {heic_path} to JPEG: {jpg_path}")
        return jpg_path
    except Exception as e:
        logging.exception(f"Failed to convert {file_name} to JPEG")
        return None

def convert_all_heic_to_jpg(input_dir, output_dir, recursive, quality):
    """
    Converts all HEIC files in the specified directory to JPEG.

    Args:
        input_dir (str or Path): The directory containing HEIC files to convert.
        output_dir (str or Path): The directory to save the converted JPEG files.
        recursive (bool): Whether to convert files in subdirectories recursively.
        quality (int): The quality of the converted JPEG files.
    """
    logging.info(f"Starting conversion in directory: {input_dir} with recursive={recursive}")
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        logging.error(f"The specified directory does not exist: {input_dir}")
        return

    heic_files = list(input_dir.rglob('*.heic')) if recursive else list(input_dir.glob('*.heic'))
    if not heic_files:
        logging.info(f"No HEIC files found in directory: {input_dir}")
        return

    for heic_path in heic_files:
        convert_heic_to_jpg(heic_path, output_dir, quality)

    logging.info("Conversion process complete.")

def main():
    """
    Main function to convert HEIC files in a specified directory to JPEG.
    """
    parser = argparse.ArgumentParser(description="Convert HEIC files to JPEG.", allow_abbrev=False)
    parser.add_argument('-d', '--dir', type=str, default=None,
                        help="The directory containing HEIC files to convert. Default is the current working directory.")
    parser.add_argument('-o', '--output', type=str, default=Path.cwd(),
                        help="The directory to save the converted JPEG files. Default is the current working directory.")
    parser.add_argument('-r', '--recursive', action='store_true',
                        help="Convert files in subdirectories recursively.")
    parser.add_argument('-q', '--quality', type=int, default=95,
                        help="The quality of the converted JPEG files (1-100). Default is 95%.")
    parser.add_argument('-y', '--yes', action='store_true',
                        help="Suppress the confirmation prompt if no input directory is specified.")
    args = parser.parse_args()

    input_dir = args.dir or Path.cwd()
    output_dir = Path(args.output)

    if args.quality < 1 or args.quality > 100:
        logging.error("Quality must be between 1 and 100.")
        return

    if not args.dir and not args.yes:
        confirm = input(f"No input directory specified. Continue in the current directory ({input_dir})? [y/N]: ")
        if confirm.lower() != 'y':
            logging.info("Operation cancelled by the user.")
            return

    logging.info(f"No argument for quality specified, using default (95%)" if args.quality == 95 else f"Using specified quality={args.quality}%")
    logging.info(f"Script started with input directory: {input_dir}, output directory: {output_dir}, and recursive={args.recursive}")
    convert_all_heic_to_jpg(input_dir, output_dir, args.recursive, args.quality)

if __name__ == '__main__':
    main()
