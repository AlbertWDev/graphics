#pragma once

#include <math.h>

#include "display_driver.h"
#include "region.h"
#include "font.h"

#define VDB_SIZE DISP_WIDTH * 160


#define HEX_TO_COLOR(HEX) ((((HEX) & 0xFF) << 8) | (((HEX) >> 8) & 0xFF))
typedef color16_t g_color_t;


typedef struct g_vdb_t {
    g_region_t region;
    g_color_t* buf;
} g_vdb_t;  // Virtual mapped region of the screen

typedef struct g_disp_t {
    g_vdb_t vdb1;
    g_vdb_t vdb2;
    g_vdb_t* vdb;
    size_t vdb_size;

    g_size_t width;
    g_size_t height;
} g_disp_t;


esp_err_t g_init();

typedef void (*g_draw_t)(const g_region_t* region);
esp_err_t g_refresh_region(const g_region_t* refresh_region, g_draw_t draw_cb);
esp_err_t g_vdb_flush();


#define G_FILLED 0
esp_err_t g_draw_pixel(g_coord_t x, g_coord_t y, g_color_t color);
esp_err_t g_draw_rect(g_region_t* region, g_color_t color, g_size_t thickness);
esp_err_t g_draw_hline(g_coord_t x, g_coord_t y, g_size_t width, g_color_t color, g_size_t thickness);
esp_err_t g_draw_vline(g_coord_t x, g_coord_t y, g_size_t height, g_color_t color, g_size_t thickness);
esp_err_t g_draw_line(g_coord_t x0, g_coord_t y0, g_coord_t x1, g_coord_t y1, g_color_t color, g_size_t thickness);
esp_err_t g_draw_circle(g_coord_t x, g_coord_t y, g_size_t r, g_color_t color, g_size_t thickness);
void g_draw_polygon(g_point_t* points, g_size_t len, g_color_t color, g_size_t thickness);

esp_err_t g_draw_bitmap_mono(g_coord_t x, g_coord_t y, const uint8_t* bitmap, g_size_t width, g_size_t height, g_color_t color);
esp_err_t g_draw_char(g_coord_t x, g_coord_t y, char character, g_color_t color);
esp_err_t g_draw_string(g_coord_t x, g_coord_t y, const char* string, g_color_t color);
