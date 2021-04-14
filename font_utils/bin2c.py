#!/usr/bin/python3

import os
import math
import json
from argparse import ArgumentParser

HEADER = \
"#include <font.h>\n\
\n\
static const g_font_t {name}_font = {{\n\
    .monospace = {monospace:s},\n\
    .width = {width:d},\n\
    .height = {height:d},\n\
    .ascii_offset = {ascii_offset:d},\n\
    .glyphs = {{\n"

FOOTER = \
"    }\n\
};"


if __name__ == '__main__':
    parser = ArgumentParser(description=" -- Font binary to C file parser")
    parser.add_argument('-f', '--font', dest="font_name",
                        help="Font used to map string. "
                             "Must match a folder within the FONT_DIR directory.",
                        type=str, required=True)
    parser.add_argument('-d', '--fontdir', dest="font_dir",
                        help="Directory where fonts are stored. "
                             "Default is ./fonts",
                        type=str, default='fonts')
    parser.add_argument('-o', '--output',
                        help="Path where the generated C file will be saved. "
                             "Default is '<font_dir>/<font_name>/<font_name>.c'",
                        type=str, default=None)
    args = parser.parse_args()


    font_file = os.path.join(args.font_dir,
                             args.font_name,
                             f"{args.font_name.replace(' ', '_')}.bmf")
    if not os.path.isfile(font_file):
        parser.error(f"Font file '{font_file}' not found. Make sure it is "
                     f"in the '{os.path.join(args.font_dir, args.font_name)}' folder")

    charmap_file = os.path.join(args.font_dir,
                                args.font_name,
                                f"{args.font_name.replace(' ', '_')}_map.json")
    if os.path.isfile(charmap_file):
        with open(charmap_file, 'r') as f:
            charmap = json.load(f)
            char_list = list(charmap.keys())
    else:
        char_list = None

    if args.output is None:
        args.output = os.path.join(args.font_dir,
                                   args.font_name,
                                   f"{args.font_name.replace(' ', '_')}.h")

    with open(font_file, 'rb') as f:
        font_width, font_height, ascii_offset = f.read(3)
        monospace = not font_width & 0x80
        font_width &= 0x7F
        glyphs = f.read()

    with open(args.output, 'w') as c_file:
        c_file.write(HEADER.format(
            name = args.font_name.replace(' ', '_').lower(),
            monospace = 'true' if monospace else 'false',
            width = font_width,
            height = font_height,
            ascii_offset = ascii_offset
        ))

        glyph_width = font_height * math.ceil(font_width / 8)
        for i, glyph_bytes in enumerate(zip(*(iter(glyphs),) * glyph_width)):
            c_file.write("        ")
            c_file.write(', '.join(f"0x{b:02x}" for b in glyph_bytes))
            if char_list is not None:
                c_file.write(f", // '{char_list[i]}'\n")
            else:
                c_file.write(",\n")

        c_file.write(FOOTER)
