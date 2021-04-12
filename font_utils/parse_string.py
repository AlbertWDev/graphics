#!/usr/bin/python3

import os
import sys
import cv2
import json
import math
import numpy as np
from string import hexdigits
from argparse import ArgumentParser
from dataclasses import dataclass, field

@dataclass
class Font:
    monospace: bool
    width: int
    height: int
    ascii_offset: int
    glyphs: bytes = field(repr=False)

# TODO:
# - Add 'dotaccent' (ȧėȯu̇ẏ, ȦĖİȮU̇Ẏ)
# - Add 'ring' (åe̊i̊o̊ůẙ, ÅE̊I̊O̊ŮY̊) (also consonants)
# - Add 'caron' (ǎěǐǒǔ, ǍĚǏǑǓ)
# - Fix 'cedilla' (¸)

SPECIAL_CHARS = {
    '°': ('degree',),
    '¿': ('question_open',),
    '¡': ('exclamation_open',),
    'ç': ('lowercase_cedilla',),
    'Ç': ('uppercase_cedilla',),
    'º': ('small_o',),
    'ª': ('small_a',),
    'ñ': ('n', 'lowercase_tilde'),
    'Ñ': ('N', 'uppercase_tilde'),
    '´': ('lowercase_acute',),
    'á': ('a', 'lowercase_acute'),
    'é': ('e', 'lowercase_acute'),
    'í': ('i', 'lowercase_acute'),
    'ó': ('o', 'lowercase_acute'),
    'ú': ('u', 'lowercase_acute'),
    'Á': ('A', 'uppercase_acute'),
    'É': ('E', 'uppercase_acute'),
    'Í': ('I', 'uppercase_acute'),
    'Ó': ('O', 'uppercase_acute'),
    'Ú': ('U', 'uppercase_acute'),
    '`': ('lowercase_grave',),
    'à': ('a', 'lowercase_grave'),
    'è': ('e', 'lowercase_grave'),
    'ì': ('i', 'lowercase_grave'),
    'ò': ('o', 'lowercase_grave'),
    'ù': ('u', 'lowercase_grave'),
    'À': ('A', 'uppercase_grave'),
    'È': ('E', 'uppercase_grave'),
    'Ì': ('I', 'uppercase_grave'),
    'Ò': ('O', 'uppercase_grave'),
    'Ù': ('U', 'uppercase_grave'),
    'â': ('a', 'lowercase_circumflex'),
    'ê': ('e', 'lowercase_circumflex'),
    'î': ('i', 'lowercase_circumflex'),
    'ô': ('o', 'lowercase_circumflex'),
    'û': ('u', 'lowercase_circumflex'),
    'Â': ('A', 'uppercase_circumflex'),
    'Ê': ('E', 'uppercase_circumflex'),
    'Î': ('I', 'uppercase_circumflex'),
    'Ô': ('O', 'uppercase_circumflex'),
    'Û': ('U', 'uppercase_circumflex'),
    '¨': ('lowercase_umlaut',),
    'ä': ('a', 'lowercase_umlaut'),
    'ë': ('e', 'lowercase_umlaut'),
    'ï': ('i', 'lowercase_umlaut'),
    'ö': ('o', 'lowercase_umlaut'),
    'ü': ('u', 'lowercase_umlaut'),
    'Ä': ('A', 'uppercase_umlaut'),
    'Ë': ('E', 'uppercase_umlaut'),
    'Ï': ('I', 'uppercase_umlaut'),
    'Ö': ('O', 'uppercase_umlaut'),
    'Ü': ('U', 'uppercase_umlaut'),
    '˙': ('lowercase_dot',),

}

def preprocess_string(string, charmap):
    out_string = []
    for char in string:
        if char in charmap:
            out_string.append(charmap[char])

        elif char in SPECIAL_CHARS:
            basic_characters = SPECIAL_CHARS[char]
            for i, basic_char in enumerate(basic_characters):
                if basic_char in charmap:
                    out_string.append(charmap[basic_char])
                else:
                    print(f"Warning: Combined character '{char}' contains '{basic_char}', "
                          "which is not supported by this font. Using ' ' instead",
                          file=sys.stderr)
                    out_string.append(' ')

                # Add combining/scape indicator between characters
                if i < len(basic_characters) - 1:
                    out_string.append(ord('\x1B'))

        elif char in ['\n', '\b']:
            out_string.append(ord(char))

        else:
            print(f"Warning: Character '{char}' not supported by this font. Using ' ' instead",
                  file=sys.stderr)
            out_string.append(' ')

    return out_string

def char_repr(char):
    if isinstance(char, str):
        if char == '\\':
            return '\\\\'
        if char == '"':
            return '\\"'
        return char
    if char == ord('\b'):
        return '\\b'
    if char == ord('\n'):
        return '\\n'
    return repr(chr(char)).replace("'", '')

def draw_char(img, x, y, char: int, font: Font):
    width_bytes = math.ceil(font.width / 8)
    glyph_size = width_bytes * font.height
    glyph_index = (char - font.ascii_offset) * glyph_size
    glyph = font.glyphs[glyph_index:glyph_index + glyph_size]

    for v in range(font.height):
        for u in range(font.width):
            if glyph[width_bytes * v + (u >> 3)] & (1 << (~u & 7)):
                img[y + v, x + u] = 255

def binary(bytes):
    return ''.join(bin(b)[2:].zfill(8) for b in bytes)

def rightmost_bit(byte):
    b = binary(byte)
    len_without_trailing_zeros = len(b.rstrip('0'))
    if len_without_trailing_zeros == 0:
        return 0
    return len(b) - len_without_trailing_zeros + 1

def glyph_width(char: int, font: Font):
    width_bytes = math.ceil(font.width / 8)
    glyph_size = width_bytes * font.height
    glyph_index = (char - font.ascii_offset) * glyph_size
    glyph = list(font.glyphs[glyph_index:glyph_index + glyph_size])

    # TODO: Optimization: apply OR to all glyph_lines and get last 1 of the result
    min_bits = width_bytes * 8
    for i in range(font.height):
        glyph_line = glyph[i * width_bytes : (i+1) * width_bytes]
        #print(f"{binary(glyph_line)} -> {rightmost_bit(glyph_line)}")

        right_bit_pos = rightmost_bit(glyph_line)
        if right_bit_pos != 0 and right_bit_pos < min_bits:
            min_bits = right_bit_pos
    return (8 * width_bytes) - min_bits + 1

def draw_string(img, string, font):
    x_offset = 0 if font.monospace else 1

    last_char_width = 0     # Width of last non-special char
    combining_mode = False
    cx = 0  # Cursor X position
    cy = 0  # Cursor Y position

    for char in string:
        char = ord(char) if isinstance(char, str) else char
        char_width = font.width if font.monospace else glyph_width(char, font)

        if char == ord('\x1B'):
            cx -= last_char_width + x_offset
            combining_mode = True

        elif char == ord('\n'):
            last_char_width = 0
            cx = 0
            cy += font.height + 1

        elif char < font.ascii_offset:
            pass

        else:
            _cx = cx
            if combining_mode and not font.monospace:
                _cx += int(last_char_width/2)
            else:
                last_char_width = char_width

            combining_mode = False
            draw_char(img, _cx, cy, char, font)
            cx += last_char_width + x_offset


if __name__ == '__main__':
    parser = ArgumentParser(description=" -- String mapper for specific fonts")
    string_grp = parser.add_mutually_exclusive_group(required=True)
    string_grp.add_argument('-s', '--string',
                            help="Input string",
                            type=str)
    string_grp.add_argument('-i', '--file',
                            help="File containing the input string",
                            type=str)
    parser.add_argument('-f', '--font', dest="font_name",
                        help="Font used to map string. "
                             "Must match a folder within the FONT_DIR directory.",
                        type=str, required=True)
    parser.add_argument('-d', '--fontdir', dest="font_dir",
                        help="Directory where fonts are stored. "
                             "Default is ./fonts",
                        type=str, default='fonts')
    parser.add_argument('-o', '--output',
                        help="Output name where image is saved. "
                             "Image is displayed if not provided.")
    parser.add_argument('-n', '--no-image',
                        help="Don't draw the expected string to an image.",
                        action="store_true")
    args = parser.parse_args()


    charmap_file = os.path.join(args.font_dir,
                                args.font_name,
                                f"{args.font_name.replace(' ', '_')}_map.json")
    if not os.path.isfile(charmap_file):
        parser.error(f"Charmap file '{charmapfile}' not found")

    font_file = os.path.join(args.font_dir,
                             args.font_name,
                             f"{args.font_name.replace(' ', '_')}.bmf")
    if not args.no_image and not os.path.isfile(font_file):
        parser.error(f"Font file '{font_file}' not found. "
                     f"Move it to the '{os.path.join(args.font_dir, args.font_name)}' folder "
                     "or use --no-image")

    if args.file and not os.path.isfile(args.file):
        parser.error(f"Input file '{args.file}' not found.")


    with open(charmap_file, 'r') as f:
        charmap = json.load(f)

    if args.string:
        string = args.string
    elif args.file:
        with open(args.file, 'r', encoding='utf8') as f:
            string = f.read()

    processed_string = preprocess_string(string, charmap)

    print('"', end='')
    for char, next_char in zip(processed_string, [*processed_string[1:], None]):
        char = char_repr(char)
        print(char, end='')
        # Cut C string in two if this char is represented as hex and the following
        # starts with hex-valid characters
        # This avoids \x3aA from being interpreted as [0x3AA] instead of [0x3A, 'A']
        if char.startswith('\\x') \
                and next_char is not None \
                and char_repr(next_char)[0] in hexdigits:
            print('""', end='')
    print('"')

    if not args.no_image:
        with open(font_file, 'rb') as f:
            font_width, font_height, ascii_offset = f.read(3)
            glyphs = f.read()
            font = Font(not (font_width & 0x80),
                        font_width & 0x7F,
                        font_height,
                        ascii_offset,
                        glyphs)

        img_width = (font.width + 1) * max(len(s) for s in string.split('\n'))
        img_height = (font.height + 1) * (string.count('\n') + 1)
        string_img = np.zeros((img_height, img_width, 1))

        draw_string(string_img, processed_string, font)

        if args.output:
            cv2.imwrite(args.output, string_img)
        else:
            cv2.imshow('string',
                       cv2.resize(string_img, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
            cv2.waitKey(0)
