#pragma once

#include <stdint.h>

typedef int16_t g_coord_t;
typedef struct __attribute__((__packed__)) g_point_t {
    float x;
	float y;
} g_point_t;
typedef uint16_t g_size_t;
typedef struct g_region_t {
    g_coord_t x0;
    g_coord_t y0;
    g_coord_t x1;
    g_coord_t y1;
} g_region_t;


inline size_t g_region_width(const g_region_t* region){
    return region->x1 - region->x0 + 1;
}

inline size_t g_region_height(const g_region_t* region) {
    return region->y1 - region->y0 + 1;
}