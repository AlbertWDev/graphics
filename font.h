#pragma once

#include "region.h"
#include <math.h>

typedef struct g_font_t {
    bool monospace;
    uint8_t width;
    uint8_t height;
    uint8_t ascii_offset;
    const uint8_t glyphs[];
} g_font_t;


inline g_size_t g_font_glyph_size(const g_font_t* font){
    return (g_size_t)ceil((double)font->width / 8) * font->height;
}
