#pragma once

#include "graphics.h"

#define G_IMG_FLAG_TRANSPARENT 0b10000000
#define G_IMG_FLAG_COLORMODE 0b01110000
#define G_IMG_FLAG_INDEXED 0b00001000
#define G_IMG_FLAG_INDEXSIZE 0b00000100

typedef enum {
    G_IMG_COLORMODE_MONO = 0b00000000,
    G_IMG_COLORMODE_GRAY = 0b00010000,
    G_IMG_COLORMODE_RGB565 = 0b00100000,
    G_IMG_COLORMODE_RGB888 = 0b00110000,
    G_IMG_COLORMODE_RGBA5658 = 0b01000000,
    G_IMG_COLORMODE_RGBA8888 = 0b01010000
} g_img_colormode_t;

typedef enum {
    G_IMG_INDEXSIZE_BIT = 0b00000000,
    G_IMG_INDEXSIZE_BYTE = 0b00000100
} g_img_indexsize_t;

typedef struct {
    g_size_t width;
    g_size_t height;
    uint8_t flags;
    uint8_t palette_size;
    uint8_t transparent_index;
    uint8_t frame_count;
} g_img_header_t;

/*typedef struct {
    uint8_t palette_size;
    g_color_t* palette;
} g_palette_t;*/

typedef struct {
    int fd;
    uint8_t current_frame;
    g_img_header_t header;
    g_color_t* palette;
    uint8_t* bitmap;
} g_img_t;


g_img_t* g_img_open(const char* filename);
void g_img_close(g_img_t* img);

void g_img_load_next(g_img_t* img);
void g_img_load_prev(g_img_t* img);
void g_img_load_first(g_img_t* img);

esp_err_t g_img_draw(g_coord_t x, g_coord_t y, g_img_t* img);
