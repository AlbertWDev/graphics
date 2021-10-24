'''
Convert image to Embedded Bitmap Graphics (EBG)
'''
import os
import re
from argparse import ArgumentParser, ArgumentTypeError

import cv2
import numpy as np

from ebg import EBG, Palette, Utils

# TODO: Implement color modes (rgb565, rgb888, etc.)

def color(value):
    if value.startswith('#') or value.startswith('0x'):
        # Hexadecimal
        # TODO: Check if RGB565 or RGB888
        return Utils.rgb565_to_rgb(int(value.strip('#'), 16))

    elif ',' in value or ' ' in value:
        # RGB color
        return [
            int(d2)
            for d1 in value.strip('()').split(',')
            for d2 in d1.split(' ')
            if len(d2) > 0
        ]
    
    elif value.isnumeric() and len(value) <= 3:
        # Gray color
        return [int(value) for i in range(3)]

    elif value.isalnum():
        # Hexadecimal
        # TODO: Check if RGB565 or RGB888
        return Utils.rgb565_to_rgb(int(value, 16))

    else:
        raise ArgumentTypeError(f"invalid color value: '{value}'")

def sorted_alphanumeric(data):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(data, key=alphanum_key)

def get_frames(files, split_rows=1, split_cols=1):
    frames = []

    if len(files) == 1:
        file = files[0]

        if os.path.isdir(file):
            for filename in sorted_alphanumeric(os.listdir(file)):
                frames.append(cv2.imread(os.path.join(file, filename)))

        elif file.endswith('.gif'):
            if split_rows * split_cols != 1:
                raise ValueError("Can't split GIF frames by rows and columns")

            gif = cv2.VideoCapture(file)
            while True:
                ret, img = gif.read()
                if not ret:
                    break
                frames.append(img)
            gif.release()

        else:
            img = cv2.imread(file)
            if img is None:
                raise FileNotFoundError(f"Image file '{file}' does not exist or is not supported")

            row_size = img.shape[0] // split_rows
            col_size = img.shape[1] // split_cols

            for row in range(split_rows):
                for col in range(split_cols):
                    frames.append(img[row:row+row_size, col:col+col_size])

    else:
        for file in files:
            img = cv2.imread(file)
            if img is None:
                raise FileNotFoundError(f"Image file '{file}' does not exist or is not supported")

            frames.append(img)
    
    if len(frames) == 0:
        raise ValueError('Invalid input file(s)')

    if any(f.shape != frames[0].shape for f in frames[1:]):
        raise ValueError('All input frames must have the same size')
    
    return frames


if __name__ == '__main__':
    parser = ArgumentParser()
    
    quantize_group = parser.add_argument_group()
    palette_group = quantize_group.add_mutually_exclusive_group()
    palette_group.add_argument('-k', '--colors', type=int, help="Number of colors in the palette", default=8)
    quantize_group.add_argument('--first-only', action='store_true', help="Use only first frame for color quantization. Might be useful to avoid huge memory consumption for large frames.")
    
    palette_group.add_argument('-p', '--palette', type=str, help="Palette file", required=False, default=None)
    
    quantize_group.add_argument('-s', '--save-palette', action='store_true', help="Save generated palette")
    quantize_group.add_argument('-g', '--save-graphic-palette', action='store_true', help="Save a visual representation of the palette")

    parser.add_argument('image', nargs='+', type=str, help="Input image files (folder and GIF files are supported).")
    parser.add_argument('--rows', type=int, help="Number of frame rows if the image is a decomposition of an animation", default=1)
    parser.add_argument('--cols', type=int, help="Number of frame columns if the image is a decomposition of an animation", default=1)
    parser.add_argument('-t', '--transparent', type=color, help="Transparent color", default=None)

    parser.add_argument('-o', '--output', type=str, help='Saved image filename. Default: {image_name}', default=None)
    parser.add_argument('-c', '--export-c-header', action='store_true', help="Save C header with EBG image as byte-array")

    args = parser.parse_args()

    if args.save_palette and not (args.colors or args.palette):
        parser.error("Argument -s/--save-palette only allowed when either -k/--colors or -p/--palette are provided.")

    output_filename = args.output if args.output else os.path.splitext(args.image[0])[0]
    output_path = os.path.dirname(output_filename)
    if len(output_path) > 0:
        os.makedirs(output_path, exist_ok=True)

    try:
        frames = get_frames(args.image, args.rows, args.cols)
    except Exception as e:
        parser.error(e)
    
    (h, w, c) = frames[0].shape

    if args.palette or args.colors:
        if args.palette:
            # Palette provided
            if not os.path.isfile(args.palette):
                parser.error(f"Palette file '{args.palette}' does not exist")

            try:
                palette = Palette.load(args.palette, transparent_color=args.transparent)
            except:
                parser.error(f"Invalid palette file: '{args.palette}'")

            if palette.channels != c:
                parser.error("Number of channels in palette colors do not match input image")

        else:
            # No palette, quantize image based on number of colors
            if args.first_only:
                full_img = frames[0]
            else:
                full_img = np.hstack(frames)

            palette = Palette.from_img(full_img, args.colors, transparent_color=args.transparent)

        if args.save_palette:
            palette.save(f'{output_filename}_palette.json')
        
        if args.save_graphic_palette:
            palette.save_img(f'{output_filename}_palette.png')

        quantized_bitmaps = [palette.quantize(frame) for frame in frames]

        img = EBG(w, h, quantized_bitmaps, palette=palette)
        
        img.save(f"{output_filename}.ebg")

        if args.export_c_header:
            img.save_c_header(f"{output_filename}.h")

    else:
        # Full-color image, no palette applied
        parser.error("Non-quantized images not supported yet.")
