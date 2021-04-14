#!/usr/bin/python3

import cv2
import math
import numpy as np
from argparse import ArgumentParser


COLOR_SUPERASCENT = (0, 127, 255)
COLOR_ASCENT = (255, 0, 0)
COLOR_DESCENT = (255, 0, 0)
COLOR_NULL = (0, 0, 255)

if __name__ == '__main__':
    parser = ArgumentParser(description=" -- Pattern generator for font bitmaps",
                            add_help=False)
    parser.add_argument('-H', '--help',
                        help='Show this help message and exit',
                        action='help')
    parser.add_argument('-w', "--width",
                        help="Width of each glyph in pixels",
                        metavar="[1-127]",
                        type=int, required=True)
    parser.add_argument('-h', "--height",
                        help="Height of each glyph in pixels",
                        type=int, required=True)
    parser.add_argument('-a', '--ascent',
                        help="Ascent (space over typical glyph height) in pixels. "
                             "Default: 2",
                        type=int, default=2)
    parser.add_argument('-s', '--superascent',
                        help="Superascent (space over common characters, "
                             "usually for accent marks) in pixels. "
                             "Default: 2",
                        type=int, default=2)
    parser.add_argument('-d', '--descent',
                        help="Descent (space below typical glyph height) in pixels. "
                             "Default: 2",
                        type=int, default=2)
    parser.add_argument('-c', '--chars', dest='char_count',
                        help="Amount of characters/glyphs in the pattern. "
                             "Default: 112",
                        type=int, default=112)
    parser.add_argument('-l', '--chars-per-line', dest="chars_per_line",
                        help="Amount of characters/glyphs in each image row. "
                             "Default: 8",
                        type=int, default=8)
    parser.add_argument('-t', '--alpha', '--transparency', dest='alpha',
                        help="Alpha value of drawn pattern colors. "
                             "Default: 127",
                        type=int, default=127)
    parser.add_argument('-o', '--output',
                        help="Output filename. Default: 'pattern'",
                        type=str, default='pattern')
    args = parser.parse_args()

    bits = 8 * math.ceil(args.width / 8)
    null_bits = bits - args.width

    char_lines = math.ceil(args.char_count / args.chars_per_line)
    pattern_width = args.chars_per_line * bits
    pattern_height = args.height * char_lines
    pattern_img = np.zeros((pattern_height, pattern_width, 4))

    for line_index in range(char_lines):
        y = line_index * args.height

        if args.superascent > 0:
            cv2.rectangle(pattern_img,
                          (0, y),
                          (pattern_width, y + args.superascent - 1),
                          (*COLOR_SUPERASCENT, args.alpha), cv2.FILLED)

        if args.ascent > 0:
            cv2.rectangle(pattern_img,
                          (0, y + args.superascent),
                          (pattern_width, y + args.superascent + args.ascent - 1),
                          (*COLOR_ASCENT, args.alpha), cv2.FILLED)

        if args.descent > 0:
            cv2.rectangle(pattern_img,
                          (0, y + args.height - args.descent),
                          (pattern_width, y + args.height - 1),
                          (*COLOR_DESCENT, args.alpha), cv2.FILLED)

    if null_bits > 0:
        for char_index in range(args.chars_per_line):
            x = char_index * bits
            cv2.rectangle(pattern_img,
                          (x + bits - null_bits, 0),
                          (x + bits - 1, pattern_height),
                          (*COLOR_NULL, args.alpha), cv2.FILLED)

    cv2.imwrite(f'{args.output}.png', pattern_img)
