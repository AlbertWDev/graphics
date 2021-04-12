#!/usr/bin/python3

from argparse import ArgumentParser

import os
import json
import math
import cv2


def parse_font_descriptor(font_descriptor):
    if os.path.isfile(font_descriptor):
        font_file = font_descriptor
        font_dir = os.path.dirname(os.path.realpath(font_file))
    elif os.path.isdir(font_descriptor):
        font_file = os.path.join(
            font_descriptor,
            f"{os.path.basename(os.path.normpath(font_descriptor))}.json")
        font_dir = font_descriptor
    else:
        print(f"Error: '{font_descriptor}' is not a valid file or directory.")
        return None

    try:
        with open(font_file, 'r') as file:
            font = json.load(file)
    except ValueError:
        print(f"Error: '{font_file}' is not a valid JSON file")
        return None
    except FileNotFoundError:
        print(f"Error: '{font_file}' doesn't exist")
        return None

    mandatory_keys = ('glyphs', 'width', 'height', 'charmap')
    key_exists = list(k in font for k in mandatory_keys)
    if not all(key_exists):
        print("Error: Missing info in JSON file:",
              [k for i, k in enumerate(mandatory_keys) if not key_exists[i]])
        return None

    font['glyphs_file'] = os.path.join(font_dir, font['glyphs'])
    if not os.path.isfile(font['glyphs_file']):
        print(f"Error: The bitmap file '{font['glyphs']}' doesn't exist."
              "Make sure its path is relative to the JSON font descriptor file")
        return None

    if font['width'] > 127:
        print(f"Error: Font width ({font['witdh']}) must be lower than 128 pixels.")
        return None

    if 'name' not in font:
        font['name'] = os.path.splitext(os.path.basename(font_file))[0]
        print(f"Warning: No 'name' specified. Using '{font['name']}'")

    if 'ascii_offset' not in font:
        font['ascii_offset'] = 32
        print("Warning: No 'ascii_offset' specified."
              f"Using default ({font['ascii_offset']})")

    if 'monospace' not in font:
        font['monospace'] = False
        print(f"Warning: 'monospace' not specified. Assuming variable-width font.")

    return font

def glyph2bytes(glyph_img):
    _bytes = []
    for y in range(glyph_img.shape[0]):
        line = list(glyph_img[y])
        bytes_per_line = int(math.ceil(len(line) / 8))
        # Add extra bits to fill the byte
        line += [0 for i in range(8 * bytes_per_line - len(line))]
        for byte_index in range(bytes_per_line):
            byte = 0
            for i, bit in enumerate(line[8*byte_index:8*byte_index+8][::-1]):
                byte |= (1 if bit else 0) << i
            _bytes.append(byte)

    return _bytes

if __name__ == '__main__':
    parser = ArgumentParser(description=" -- Font to binary parser")
    parser.add_argument('font',
                        help="JSON file with font specification. "
                             "A directory can also be provided if the JSON filename "
                             "is the same as the folder.")
    parser.add_argument('-o', '--output', dest='output_dir',
                        help="Output directory where font folder is created. "
                             "Defaults to current directory.",
                        type=str, default='.')
    args = parser.parse_args()

    font = parse_font_descriptor(args.font)
    if font is None:
        exit(1)

    glyphs_img = cv2.imread(font['glyphs_file'], cv2.IMREAD_GRAYSCALE)
    if glyphs_img is None:
        print(f"Error: The bitmap file '{font['glyphs']}' is not supported.")
        exit(1)

    output_dir = os.path.join(args.output_dir, font['name'])
    os.makedirs(output_dir, exist_ok=True)

    glyph_width = 8 * math.ceil(font['width'] / 8)
    glyph_height = font['height']
    glyphs_per_row = glyphs_img.shape[1] // glyph_width
    if glyphs_per_row * glyph_width != glyphs_img.shape[1]:
        print("Error: Glyph width not aligned with bitmap width."
              "Make sure glyph and bitmap widths are multiple of 8")
        exit(1)

    font_map = {}
    with open(os.path.join(output_dir, f"{font['name'].replace(' ', '_')}.bmf"), 'wb') as f:
        f.write(bytes([
            font['width'] | (0 if font['monospace'] else 0x80),
            font['height'],
            font['ascii_offset']
        ]))

        for glyph_index, glyph_name in enumerate(font['charmap']):
            # Null glyphs are not mapped, but must be added to the bytearray
            # to keep indexing order
            if glyph_name is not None:
                ascii_index = glyph_index + font['ascii_offset']
                if ascii_index > 31 and ascii_index < 127:
                    font_map[glyph_name] = chr(ascii_index)
                else:
                    font_map[glyph_name] = ascii_index

            x = glyph_width * (glyph_index % glyphs_per_row)
            y = glyph_height * (glyph_index // glyphs_per_row)
            glyph_img = glyphs_img[y:y+font['height'], x:x+font['width']]
            glyph_bytes = glyph2bytes(glyph_img)

            f.write(bytes(glyph_bytes))

    with open(os.path.join(output_dir, f"{font['name'].replace(' ', '_')}_map.json"), 'w') as f:
        json.dump(font_map, f, indent=4)
