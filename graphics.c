#include "graphics.h"

#include "fonts/base.h"

static g_disp_t* _g_disp = NULL;
static const g_font_t* _g_font = &base_font;

#define DEBUG_REGION(text, reg) ESP_LOGI("GRAPHICS", "%s [%d:%d, %d:%d]", text, reg.x0, reg.x1, reg.y0, reg.y1)

#define MAX(a, b) ( ((a) > (b)) ? (a) : (b) )
#define MIN(a, b) ( ((a) < (b)) ? (a) : (b) )
#define ABS(a)    ( ((a) < 0) ? (-(a)) : (a) )


esp_err_t g_init() {
    esp_err_t ret;
    if((ret = display_init()) != ESP_OK) return ret;

    _g_disp = malloc(sizeof(g_disp_t));
    _g_disp->width = DISP_WIDTH;
    _g_disp->height = DISP_HEIGHT;

    // VDB1
    _g_disp->vdb1.buf = heap_caps_malloc(VDB_SIZE * sizeof(g_color_t), MALLOC_CAP_DMA);
    if(_g_disp->vdb1.buf == NULL) { free(_g_disp); return ESP_ERR_NO_MEM; }
    memset(_g_disp->vdb1.buf, 0, VDB_SIZE * sizeof(g_color_t));

    // VDB2
    _g_disp->vdb2.buf = heap_caps_malloc(VDB_SIZE * sizeof(g_color_t), MALLOC_CAP_DMA);
    if(_g_disp->vdb2.buf == NULL) { free(_g_disp->vdb1.buf); free(_g_disp); return ESP_ERR_NO_MEM; }
    memset(_g_disp->vdb2.buf, 0xFF, VDB_SIZE * sizeof(g_color_t));
    
    _g_disp->vdb_size = VDB_SIZE;
    _g_disp->vdb = &_g_disp->vdb1;

    return ESP_OK;
}

esp_err_t g_refresh_region(const g_region_t* refresh_region, g_draw_t draw_cb) {
    // Sliding draw window properties
    g_coord_t y_step = _g_disp->vdb_size / g_region_width(refresh_region);
    g_coord_t refresh_height = g_region_height(refresh_region);
    if(y_step > refresh_height) y_step = refresh_height;
    
    // Move window along refresh region
    for(int y = refresh_region->y0; y < refresh_region->y1 - 1; y += y_step) {
        g_vdb_t* vdb = _g_disp->vdb;

        // Set updated region
        vdb->region.x0 = refresh_region->x0;
        vdb->region.y0 = y;
        vdb->region.x1 = refresh_region->x1;
        vdb->region.y1 = y + y_step - 1;

        draw_cb(refresh_region);
        g_vdb_flush();
    }

    // TODO: Draw last window sub-region if it has smaller size
    
    return ESP_OK;
}

esp_err_t g_vdb_flush() {
    g_vdb_t* vdb = _g_disp->vdb;
    size_t region_size = g_region_width(&vdb->region) * g_region_height(&vdb->region);
    
    display_send_color16(
        vdb->region.x0, vdb->region.y0,
        vdb->region.x1, vdb->region.y1,
        vdb->buf, region_size);

    // Swap buffers
    _g_disp->vdb = vdb == &_g_disp->vdb2 ? &_g_disp->vdb1 : &_g_disp->vdb2;
    
    return ESP_OK;
}

esp_err_t g_draw_pixel(g_coord_t x, g_coord_t y, g_color_t color) {
    g_vdb_t* vdb = _g_disp->vdb;
    if(x < vdb->region.x0 || y < vdb->region.y0 || x > vdb->region.x1 || y > vdb->region.y1) return ESP_OK;

    vdb->buf[(y - vdb->region.y0) * g_region_width(&vdb->region) + x - vdb->region.x0] = color;
    return ESP_OK;
}

esp_err_t g_draw_rect(g_region_t* region, g_color_t color, g_size_t thickness) {
    g_vdb_t* vdb = _g_disp->vdb;

    // Get relative coordinates of the rect to the VDB
    g_region_t fill_region;
    fill_region.x0 = region->x0 <= vdb->region.x0 ? 0 : region->x0 - vdb->region.x0;
    fill_region.y0 = region->y0 <= vdb->region.y0 ? 0 : region->y0 - vdb->region.y0;
    fill_region.x1 = region->x1 > vdb->region.x1 ? g_region_width(&vdb->region)-1 : region->x1 - vdb->region.x0;
    fill_region.y1 = region->y1 > vdb->region.y1 ? g_region_height(&vdb->region)-1 : region->y1 - vdb->region.y0;
    
    // Check if rect is out of VDB bounds
    if(fill_region.x1 <= 0 || fill_region.y1 <= 0 || fill_region.y0 > fill_region.y1 || fill_region.x0 > fill_region.x1) return ESP_OK;

    size_t vdb_width = g_region_width(&vdb->region);

    if(thickness == G_FILLED) {
        // Get first row to be drawn
        g_color_t* buf = &vdb->buf[fill_region.y0 * vdb_width];
        
        // Fill first row with color
        for(g_coord_t c = fill_region.x0; c <= fill_region.x1; c++)
            buf[c] = color;
        
        // Use first row region as reference
        g_color_t* buf_first_row_x0 = &buf[fill_region.x0];
        size_t buf_row_region_size = g_region_width(&fill_region) * sizeof(g_color_t);
        buf += vdb_width; // Skip first row

        // Copy first row region to the rest of rows
        for(g_coord_t r = fill_region.y0 + 1; r <= fill_region.y1; r++) {
            memcpy(&buf[fill_region.x0], buf_first_row_x0, buf_row_region_size);
            buf += vdb_width; // Next row 
        }
    } else {
        g_draw_hline(region->x0, region->y0, g_region_width(region), color, thickness);
        g_draw_hline(region->x0, region->y1, g_region_width(region), color, thickness);
        g_draw_vline(region->x0, region->y0, g_region_height(region), color, thickness);
        g_draw_vline(region->x1, region->y0, g_region_height(region), color, thickness);
    }

    return ESP_OK;
}

esp_err_t g_draw_hline(g_coord_t x, g_coord_t y, g_size_t width, g_color_t color, g_size_t thickness) {
    if(thickness < 1) return ESP_OK;

    if(thickness == 1) {
        g_vdb_t* vdb = _g_disp->vdb;
        if(y < vdb->region.y0 || y > vdb->region.y1) return ESP_OK;

        size_t vdb_width = g_region_width(&vdb->region);

        g_coord_t _x = (x < vdb->region.x0) ? 0 : x - vdb->region.x0;
        g_coord_t x1 = (x + width - 1 > vdb->region.x1) ? vdb_width : x + width - vdb->region.x0; 
        for(;_x < x1; _x++)
            vdb->buf[(y - vdb->region.y0) * vdb_width + _x] = color;

    } else {
        g_region_t region = {
            .x0 = x,
            .y0 = y - thickness/2,
            .x1 = x + width - 1,
            .y1 = y + thickness/2
        };
        g_draw_rect(&region, color, G_FILLED);
    }
    return ESP_OK;
}

esp_err_t g_draw_vline(g_coord_t x, g_coord_t y, g_size_t height, g_color_t color, g_size_t thickness) {
    if(thickness < 1) return ESP_OK;

    if(thickness == 1) {
        g_vdb_t* vdb = _g_disp->vdb;
        if(x < vdb->region.x0 || x > vdb->region.x1) return ESP_OK;

        size_t vdb_width = g_region_width(&vdb->region);

        g_coord_t _y = (y < vdb->region.y0) ? 0 : y - vdb->region.y0;
        g_coord_t y1 = (y + height - 1 > vdb->region.y1) ? g_region_height(&vdb->region) : y + height - vdb->region.y0; 
        for(;_y < y1; _y++)
            vdb->buf[_y * vdb_width + x - vdb->region.x0] = color;

    } else {
        g_region_t region = {
            .x0 = x - thickness/2,
            .y0 = y,
            .x1 = x + thickness/2,
            .y1 = y + height - 1
        };
        g_draw_rect(&region, color, G_FILLED);
    }
    return ESP_OK;
}

esp_err_t g_draw_line(g_coord_t x0, g_coord_t y0, g_coord_t x1, g_coord_t y1, g_color_t color, g_size_t thickness) {
    if(x0 == x1) return g_draw_vline(MIN(x0,x1), MIN(y0,y1), ABS(y1-y0) + 1, color, thickness);
    if(y0 == y1) return g_draw_hline(MIN(x0,x1), MIN(y0,y1), ABS(x1-x0) + 1, color, thickness);

    // TODO: Clip line to display
    
    int16_t dx = ABS(x1 - x0);
    int8_t sx = x0 < x1 ? 1 : -1;
    int16_t dy = ABS(y1 - y0);
    int8_t sy = y0 < y1 ? 1 : -1;
    int16_t e, e_xy = (dx > dy ? dx : -dy) / 2;

    while(1) {
        g_draw_pixel(x0, y0, color);
        if(x0 == x1 && y0 == y1) break;

        e = e_xy;
        if(e > -dx) { e_xy -= dy; x0 += sx; }
        if(e < dy) { e_xy += dx; y0 += sy; }
    };

    return ESP_OK;
}

esp_err_t g_draw_circle(g_coord_t cx, g_coord_t cy, g_size_t r, g_color_t color, g_size_t thickness) {
    g_coord_t x = r, y = 0;

    g_coord_t d = 3 - 2 * r;

    if(thickness == G_FILLED)
        while(y <= x) {  // less than 45 degrees
            g_draw_hline(cx-y, cy-x, 2 * y + 1, color, 1);  // top octaves
            g_draw_hline(cx-x, cy-y, 2 * x + 1, color, 1);  // mid-top octaves
            g_draw_hline(cx-x, cy+y, 2 * x + 1, color, 1);  // mid-bottom octaves
            g_draw_hline(cx-y, cy+x, 2 * y + 1, color, 1);  // bottom octaves

            y++;
            if(d > 0) { x--; d = d + 4 * (y - x) + 10; }
            else d = d + 4 * y + 6;
        }
    else
        while(y <= x) {  // less than 45 degrees
            g_draw_pixel(cx + x, cy - y, color);    // 0-45
            g_draw_pixel(cx + y, cy - x, color);    // 45-90
            g_draw_pixel(cx - y, cy - x, color);    // 90-135
            g_draw_pixel(cx - x, cy - y, color);    // 135-180
            g_draw_pixel(cx - x, cy + y, color);    // 180-225
            g_draw_pixel(cx - y, cy + x, color);    // 225-270
            g_draw_pixel(cx + y, cy + x, color);    // 270-315
            g_draw_pixel(cx + x, cy + y, color);    // 315-360

            y++;
            if(d > 0) { x--; d += 4 * (y - x) + 10; }
            else d += 4 * y + 6;            
        }
    return ESP_OK;
}

void _draw_polygon_fill(g_point_t* points, g_size_t len, g_color_t color) {
    g_size_t i, j;     // Index of current and last point

    // Calculate polygon limits on Y axis
    g_coord_t y = DISP_HEIGHT - 1, ymax = 0;
    for(i = 0; i < len; i++) {
        if(y > points[i].y) y = points[i].y;
        if(ymax < points[i].y) ymax = points[i].y;
    }
    if(y < _g_disp->vdb->region.y0) y = _g_disp->vdb->region.y0;
    if(ymax > _g_disp->vdb->region.y1) ymax = _g_disp->vdb->region.y1;

    g_coord_t nodes[64];    // Intersections (on X axis) of a row with a polygon segment
    uint8_t count = 0;

    // Loop through display rows
    for(; y <= ymax; y++) {
        count = 0;
        j = len - 1;
        // Loop through all polygon segments
        for(i = 0; i < len; j = i++)
            // Check if segment intersects row
            if( (points[i].y < y && points[j].y >= y) || (points[j].y < y && points[i].y >= y) )
                // Interpolate to get intersection between segment and row
                nodes[count++] = (g_coord_t)(points[i].x + (y - points[i].y) / (points[j].y - points[i].y) * (points[j].x - points[i].x));

        // Sort intersections (bubble sort)
        g_coord_t aux;
        for(i = 0; i < count - 1;) {
            if(nodes[i] > nodes[i+1]) {
                aux = nodes[i];
                nodes[i] = nodes[i+1];
                nodes[i+1] = aux;
                if(i) i--;
            } else
                i++;
        }

        // Fill row segments between nodes
        for(i = 0; i < count; i += 2)
            g_draw_hline(nodes[i], y, nodes[i+1] - nodes[i] + 1, color, 1);
    }
}

void g_draw_polygon(g_point_t* points, g_size_t len, g_color_t color, g_size_t thickness) {
    if(thickness == G_FILLED)
        _draw_polygon_fill(points, len, color);
    else {
        for(g_size_t i = 0, j = len - 1; i < len; j = i++)
            g_draw_line(points[j].x, points[j].y, points[i].x, points[i].y, color, thickness);
    }
}

esp_err_t g_draw_bitmap_mono(g_coord_t x, g_coord_t y, const uint8_t* bitmap, g_size_t width, g_size_t height, g_color_t color) {
    g_size_t width_bytes = ceil((double)width / 8);

    for(g_coord_t v = 0; v < height; v++) {
        for(g_coord_t u = 0; u < width; u++) {
            // bmp_byte = bitmap[width_bytes * v + (u // 8)]
            // bit = 0b10000000 >> (u % 8) = 1 << (7 - (u % 8))
            if(bitmap[width_bytes * v + (u >> 3)] & (1 << (~u & 7)))
                g_draw_pixel(x + u, y + v, color);
        }
    }

    return ESP_OK;
}

esp_err_t g_draw_char(g_coord_t x, g_coord_t y, char character, g_color_t color) {
    const uint8_t* glyph = &_g_font->glyphs[(character - _g_font->ascii_offset) * g_font_glyph_size(_g_font)];
    
    // TODO: Draw in baseline (substracting descent)
    return g_draw_bitmap_mono(x, y, glyph, _g_font->width, _g_font->height, color);
}

inline uint8_t _rightmost_bit(uint8_t byte) {
    if(!byte) return 8;
    return __builtin_ctz(byte);
}

uint8_t _glyph_width_multibytes(char character) {
    uint8_t width_bytes = ceil((double)_g_font->width / 8);
    const uint8_t* glyph = &_g_font->glyphs[(character - _g_font->ascii_offset) * g_font_glyph_size(_g_font)];
    
    uint8_t glyph_bits[width_bytes];
    memset(glyph_bits, 0, width_bytes);
    // Apply OR to all glyph lines, byte by byte
    for(int b = 0; b < width_bytes * _g_font->height; b++) {
        glyph_bits[b % width_bytes] |= glyph[b];
    }

    // Find rightmost '1', right to left
    uint8_t right_bit_pos;
    for(int b = width_bytes - 1; b >= 0; b--) {
        right_bit_pos = _rightmost_bit(glyph_bits[b]);

        if(right_bit_pos < 8)  // '1' found in this byte
            return (8 * b) + (8 - right_bit_pos);
    }
    return 0;
}

uint8_t _glyph_width(char character) {
    if(_g_font->width > 8)
        return _glyph_width_multibytes(character);
    
    uint8_t glyph_bits = 0;
    const uint8_t* glyph = &_g_font->glyphs[(character - _g_font->ascii_offset) * g_font_glyph_size(_g_font)];
    
    // Apply OR to all glyph lines
    for(int y = 0; y < _g_font->height; y++)
        glyph_bits |= glyph[y];

    return 8 - _rightmost_bit(glyph_bits);
}

esp_err_t g_draw_string(g_coord_t x, g_coord_t y, const char* string, g_color_t color) {
    if(!string) return ESP_ERR_INVALID_ARG;
    
    uint8_t line_gap = 1;
    uint8_t char_gap = _g_font->monospace ? 0 : 1;
    uint8_t empty_gap = _g_font->width / 4;

    uint8_t char_width;
    uint8_t last_char_width = 0; // Width of last non-special char
    bool combining_mode = false;
    g_coord_t _cx, cx = 0, cy = 0; // Relative cursor position
    char c;
    for(g_size_t i = 0; (c = string[i]) != 0; i++) {
        switch(c) {
            case '\x1B':    // Escape \e
                cx -= last_char_width + char_gap;
                combining_mode = true;
                break;
            case '\n':      // New line \n
                last_char_width = 0;
                cx = 0;
                cy += _g_font->height + line_gap;
                break;
            case ' ':
                combining_mode = false;
                last_char_width = empty_gap;
                cx += last_char_width + char_gap;
                break;
            default:
                if(c < _g_font->ascii_offset) break;

                char_width = _g_font->monospace ? _g_font->width : _glyph_width(c);

                _cx = cx;
                if(combining_mode && !_g_font->monospace)
                    _cx += (last_char_width - char_width + 1)/2;
                else {
                    last_char_width = char_width;
                    if(last_char_width == 0)
                        last_char_width = empty_gap;
                }

                if(char_width > 0)
                    g_draw_char(x + _cx, y + cy, c, color);
                
                combining_mode = false;
                cx += last_char_width + char_gap;
                break;
        }
    }
    return ESP_OK;
}
