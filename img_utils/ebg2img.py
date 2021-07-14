import os
from argparse import ArgumentParser
from enum import Enum
from ebg import EBG

class OutputFormat(Enum):
    IMAGE = 'image'
    GIF = 'gif'
    FOLDER = 'folder'

    def __str__(self):
        return self.value


if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('image', type=str, help="Input image")
    parser.add_argument('-f', '--format', type=OutputFormat, choices=list(OutputFormat), help="Output format. Default=image", default=OutputFormat.IMAGE)
    parser.add_argument('-o', '--output', type=str,
                        help="Saved image filename. Default: {input}_preview", default=None)

    args = parser.parse_args()

    output_filename = args.output if args.output else f"{os.path.splitext(args.image)[0]}_preview"

    img = EBG.load(args.image)
    img.save_img(output_filename, mode=str(args.format))
