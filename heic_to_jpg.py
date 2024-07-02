import os
import subprocess
import sys
import platform

# Function to check if ImageMagick (magick command) is available
def check_imagemagick():
    try:
        # Attempt to run 'magick' command to check if ImageMagick is installed
        subprocess.run(['magick', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return False

# Function to prompt user for ImageMagick installation on Linux
def prompt_install_imagemagick_linux():
    print("ImageMagick is required for HEIC to JPEG conversion.")
    print("Do you want to install ImageMagick? (yes/no)")
    user_input = input().strip().lower()
    if user_input == 'yes' or user_input == 'y':
        # Install ImageMagick using package manager (assuming apt for Debian/Ubuntu)
        try:
            subprocess.run(['sudo', 'apt', 'install', 'imagemagick'], check=True)
            print("ImageMagick installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing ImageMagick: {e}")
            sys.exit(1)
    else:
        print("Exiting script.")
        sys.exit(1)

# Function to convert HEIC to JPEG using ImageMagick
def convert_heic_to_jpg(heic_path, jpg_path):
    try:
        subprocess.run(['magick', heic_path, jpg_path], check=True)
        print(f"Converted {heic_path} to {jpg_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {heic_path} to JPEG:", e)
        sys.exit(1)

# Main function
def main():
    # Check if ImageMagick is installed
    if not check_imagemagick():
        if platform.system() == 'Linux':
            prompt_install_imagemagick_linux()
        else:
            print("Unsupported platform. Please install ImageMagick manually.")
            sys.exit(1)

    # Directory where the script is located
    script_directory = os.path.dirname(os.path.abspath(__file__))
    heic_files = [f for f in os.listdir(script_directory) if f.lower().endswith('.heic')]

    if not heic_files:
        print("No HEIC files found in the current directory.")
        return

    for heic_file in heic_files:
        heic_path = os.path.join(script_directory, heic_file)
        jpg_path = os.path.splitext(heic_path)[0] + '.jpg'
        convert_heic_to_jpg(heic_path, jpg_path)

    print("Conversion completed.")

if __name__ == "__main__":
    main()
