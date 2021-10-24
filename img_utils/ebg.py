import os
import math
import json
import struct

import cv2
import imageio
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import pairwise_distances_argmin

class Utils:
    @staticmethod
    def bgr_to_rgb(colors):
        length, channels = colors.shape
        colors = colors.reshape((1, length, channels))
        return cv2.cvtColor(colors, cv2.COLOR_BGR2RGB).reshape((length, channels))
    
    @staticmethod
    def rgb_to_lab(colors):
        length, channels = colors.shape
        colors = colors.reshape((1, length, channels))
        return cv2.cvtColor(colors, cv2.COLOR_RGB2LAB).reshape((length, channels))

    @staticmethod
    def rgb_to_rgb565(r, g, b):
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)

    @staticmethod
    def rgb565_to_rgb(color):
        return (color & 0xF800) >> 8, (color & 0x07E0) >> 3, (color & 0x1F) << 3


class Palette:
    def __init__(self, colors, colormode='RGB', transparent=None):
        if colormode == 'RGB':
            self.rgb_colors = colors
        elif colormode == 'BGR':
            self.bgr_colors = colors
        elif colormode == 'LAB':
            self.lab_colors = colors
        else:
            raise ValueError("Unsupported color mode")
        
        self.transparent = transparent

    @staticmethod
    def load(filename, transparent_color=None):
        '''
            Load palette from file
        '''
        with open(filename, 'r') as f:
            colors = np.array(json.load(f), dtype=np.uint8)

        if transparent_color is not None:
            color_matches = np.equal(colors, transparent_color).all(axis=1)
            if any(color_matches):
                transparent_index = np.where(color_matches)[0][0]
            else:
                raise ValueError(f"Required transparent color '{transparent_color}' not found in given palette file '{filename}'")

        return Palette(colors,
                       transparent=None if transparent_color is None else transparent_index)

    @staticmethod
    def from_img(img, k, transparent_color=None):
        '''
            Generate a palette of K colors from a given image
        '''
        (h, w, c) = img.shape
        pixels = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).reshape((h * w, c))
        if transparent_color is not None:
            transparent_color = Utils.rgb_to_lab(np.array([transparent_color], dtype=np.uint8))
            pixels = np.insert(pixels, 0, transparent_color, axis=0)
            transparent_index = 0

        # Check number of colors in the image. If it's less than K, those colors are the palette
        colors = np.unique(pixels, axis=0)

        if len(colors) > k:
            clt = MiniBatchKMeans(n_clusters = k)#, verbose=True)
            clt.fit(pixels)
            colors = np.uint8(clt.cluster_centers_)

            if transparent_color is not None:
                color_matches = np.equal(colors, transparent_color).all(axis=1)

                if any(color_matches):
                    # Transparent color found in cluster centers, take as transparent index
                    transparent_index = np.where(color_matches)[0][0]
                
                elif k > 1:
                    # Transparent color not found, quantize with one color less and add it manually
                    clt = MiniBatchKMeans(n_clusters = k-1)#, verbose=True)
                    clt.fit(colors)
                    colors = np.uint8(clt.cluster_centers_)
                    colors = np.insert(colors, 0, transparent_color, axis=0)
                    transparent_index = 0

        return Palette(colors, colormode='LAB',
                       transparent=None if transparent_color is None else transparent_index)

    def __len__(self):
        return self._length
    
    @property
    def channels(self):
        return self._channels
    
    @property
    def rgb_colors(self):
        return self._colors

    @rgb_colors.setter
    def rgb_colors(self, colors):
        self._length, self._channels = colors.shape
        self._colors = colors
    
    @property
    def rgba_colors(self):
        return np.uint8([
            [*c, 0]
            if self.transparent is not None and i == self.transparent
            else [*c, 255]
            for i, c in enumerate(self.rgb_colors)
        ])

    @property
    def bgr_colors(self):
        colors = self._colors.reshape((1, self._length, self._channels))
        return cv2.cvtColor(colors, cv2.COLOR_RGB2BGR).reshape((self._length, self._channels))

    @bgr_colors.setter
    def bgr_colors(self, colors):
        self._length, self._channels = colors.shape
        self._colors = Utils.bgr_to_rgb(colors)
    
    @property
    def bgra_colors(self):
        return np.uint8([
            [*c, 0]
            if self.transparent is not None and i == self.transparent
            else [*c, 255]
            for i, c in enumerate(self.bgr_colors)
        ])

    @property
    def lab_colors(self):
        return Utils.rgb_to_lab(self._colors)

    @lab_colors.setter
    def lab_colors(self, colors):
        self._length, self._channels = colors.shape
        colors = colors.reshape((1, self._length, self._channels))
        self._colors = cv2.cvtColor(colors, cv2.COLOR_LAB2RGB).reshape((self._length, self._channels))
    
    def save(self, filename):
        '''
            Save palette to file
        '''
        with open(filename, 'w') as f:
            json.dump(self._colors.tolist(), f)

    def save_img(self, filename, size=8, columns=8):
        '''
            Create and save a visual representation of the palette
        '''
        columns = min(columns, len(self._colors))
        rows = math.ceil(len(self._colors) / columns)
        width = size * columns
        height = size * rows

        img = np.zeros((height, width, self.channels), dtype=np.uint8)
        for i, color in enumerate(self.bgr_colors):
            x = i % columns
            y = i // columns
            cv2.rectangle(img,
                (x * size, y * size),
                ((x+1) * size - 1, (y+1) * size - 1),
                color.tolist(),
                cv2.FILLED)

        cv2.imwrite(filename, img)

    def quantize(self, img):
        '''
            Quantize an image using the palette. Returns the palette index per pixel
        '''
        (h, w, c) = img.shape
        pixels = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).reshape((h * w, c))

        pixel_labels = pairwise_distances_argmin(self.lab_colors, pixels, axis=0)

        return pixel_labels

    def apply(self, indices, width, height, colormode='BGR'):
        '''
            Apply the palette to a given list of indices to obtain the actual image
        '''
        if len(indices) != (width * height):
            raise ValueError("Width and height do not match number of palette indices")

        if colormode == 'RGB':
            return self.rgb_colors[indices].reshape((height, width, self.channels))
        elif colormode == 'RGBA':
            return self.rgba_colors[indices].reshape((height, width, self.channels + 1))
        elif colormode == 'BGR':
            return self.bgr_colors[indices].reshape((height, width, self.channels))
        elif colormode == 'BGRA':
            return self.bgra_colors[indices].reshape((height, width, self.channels + 1))
        elif colormode == 'LAB':
            return self.lab_colors[indices].reshape((height, width, self.channels))
        else:
            raise ValueError("Unsupported color mode")


class EBG:
    FLAGS_TRANSPARENT = 0b10000000
    FLAGS_COLORMODE = 0b01110000
    FLAGS_COLORMODE_MONO = 0b00000000
    FLAGS_COLORMODE_GRAY = 0b00010000
    FLAGS_COLORMODE_RGB565 = 0b00100000
    FLAGS_COLORMODE_RGB888 = 0b00110000
    FLAGS_COLORMODE_RGBA5658 = 0b01000000
    FLAGS_COLORMODE_RGBA8888 = 0b01010000
    FLAGS_INDEXED = 0b00001000
    FLAGS_INDEXSIZE = 0b00000100
    FLAGS_INDEXSIZE_BIT = 0b00000000
    FLAGS_INDEXSIZE_BYTE = 0b00000100

    def __init__(self, width, height, bitmaps, palette=None, transparent=None):
        self.width = width
        self.height = height
        self.bitmaps = bitmaps
        self.palette = palette
        self.trasparent = transparent

    @staticmethod
    def load(filename):
        with open(filename, 'rb') as f:
            signature = f.read(4)
            assert signature[:3] == "EBG".encode(), "Invalid EBG file"
            assert signature[3] == 0x01, "Invalid EBG version"

            header = f.read(8)
            width, height, flags, k, transparent_index, frame_count = struct.unpack("<HHBBBB", header)

            palette = None
            if flags & EBG.FLAGS_INDEXED:
                palette = []
                for i in range(k+1):
                    palette.append(Utils.rgb565_to_rgb(*struct.unpack("!H", f.read(2))))
                colors = np.array(palette, dtype=np.uint8)
                palette = Palette(colors, transparent=transparent_index if flags & EBG.FLAGS_TRANSPARENT else None)

            if flags & EBG.FLAGS_INDEXED and flags & EBG.FLAGS_INDEXSIZE_BYTE:
                pixel_size = 1
            else:
                raise NotImplementedError

            bitmaps = []
            for i in range(frame_count):
                bitmap_bytes = f.read(width * height)
                bitmap = []
                for i in range(0, len(bitmap_bytes), pixel_size):
                    bitmap.append(struct.unpack("!B", bitmap_bytes[i:i+pixel_size]))
                bitmaps.append(np.array(bitmap, dtype=np.uint8).reshape(-1))

        return EBG(width, height, bitmaps, palette=palette)

    def save(self, filename):
        '''- ['E', 'B', 'G', '1'] (4 bytes) (???)
        - Width (2 bytes)
        - Height (2 bytes)
        - Flags (1 byte)
            + Transparent color [enable transparent color] (1-bit)
            + Color mode [mono, gray, RGB565, RGB888, RGBA...] (3-bit)
            + Indexed [enable palette] (1-bit)
            + Index size [bit, byte] (1-bit)
            + Reserved (2-bit)
        - Palette size - 1 (1 byte, 1-256)
        - Transparent index (1 byte)
        - Frame count (1 byte)
        - Palette (1-256 * sizeof(color)), includes transparent color if transparent is enabled
        - Bitmap'''

        with open(filename, 'wb') as f:
            f.write(struct.pack("!BBBB", *[ord(c) for c in "EBG"], 1))
            flags = 0
            flags |= EBG.FLAGS_COLORMODE_RGB565
            flags |= EBG.FLAGS_INDEXED
            flags |= EBG.FLAGS_INDEXSIZE_BYTE
            if self.palette.transparent is not None:
                flags |= EBG.FLAGS_TRANSPARENT
            # Header
            f.write(struct.pack("<HHBBBB",
                                self.width,
                                self.height,
                                flags,
                                0 if self.palette is None else len(self.palette) - 1,
                                0 if self.palette.transparent is None else self.palette.transparent,
                                len(self.bitmaps)))

            # Palette
            if self.palette is not None:
                for color in self.palette.rgb_colors:
                    f.write(struct.pack("!H", Utils.rgb_to_rgb565(*color)))

            # Bitmap indices
            for bitmap in self.bitmaps:
                for index in bitmap:
                    f.write(struct.pack("!B", index))

    def save_img(self, filename, mode='image'):
        if self.palette is not None:
            if len(self.bitmaps) < 2:
                img = self.palette.apply(self.bitmaps[0], self.width, self.height, 'BGR' if self.palette.transparent is None else 'BGRA')
                cv2.imwrite(f"{filename}.png", img)

            else:
                if mode == 'image':
                    images = [self.palette.apply(bmp, self.width, self.height, 'BGR' if self.palette.transparent is None else 'BGRA') for bmp in self.bitmaps]
                    cv2.imwrite(f"{filename}.png", np.hstack(images))

                elif mode == 'gif':
                    images = [self.palette.apply(bmp, self.width, self.height, 'RGB' if self.palette.transparent is None else 'RGBA') for bmp in self.bitmaps]
                    imageio.mimsave(f"{filename}.gif", images)

                else:   # 'folder'
                    images = [self.palette.apply(bmp, self.width, self.height, 'BGR' if self.palette.transparent is None else 'BGRA') for bmp in self.bitmaps]

                    os.makedirs(filename, exist_ok=True)
                    for i, image in enumerate(images):
                        cv2.imwrite(os.path.join(filename, f'frame_{i}.png'), image)

        else:
            raise NotImplementedError
  
    def save_c_header(self, filename):
        raise NotImplementedError

        with open(filename, 'w') as f:
            f.write('#include "graphics.h"\n\nconst uint8_t palette[] = {\n\t')
            f.write(', '.join(
                f"0x{hex_repr[0:2]},0x{hex_repr[2:4]}"
                for hex_repr in [
                f"{rgb_to_rgb565(*color):04X}"
                for color in palette
                ]))
            f.write('\n};\n\nconst uint8_t bitmap[] = {\n\t')
            f.write(','.join(f"0x{i:02X}" for i in indices))
            f.write('\n};\n')
