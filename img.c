#include "img.h"

#include <fcntl.h>
#include <esp_vfs.h>

#define SIGNATURE_SIZE 4
#define HEADER_SIZE 8
#define PALETTE_OFFSET (SIGNATURE_SIZE + HEADER_SIZE)
#define PALETTE_SIZE(img) ((img->header.flags & G_IMG_FLAG_INDEXED) ? (sizeof(g_color_t) * (img->header.palette_size + 1)) : 0)

const char* colormode2str(g_img_colormode_t colormode) {
    switch(colormode) {
        case G_IMG_COLORMODE_MONO:
            return "MONO";
        case G_IMG_COLORMODE_GRAY:
            return "GRAY";
        case G_IMG_COLORMODE_RGB565:
            return "RGB565";
        case G_IMG_COLORMODE_RGB888:
            return "RGB888";
        default:
            return "Unknown";
    }
}

g_img_t* g_img_open(const char* filename) {
    g_img_t* img = malloc(sizeof(g_img_t));
    if(!img) return NULL;
    img->bitmap = NULL;

    img->fd = open(filename, O_RDONLY, 0);
    if (img->fd == -1) {
        printf("ERROR: Can't read file\n");
        goto exit_free;
    }

    ssize_t read_bytes;

    char signature[SIGNATURE_SIZE];
    read_bytes = read(img->fd, signature, SIGNATURE_SIZE);
    printf("Reading file: %c%c%c (%d)\n", signature[0], signature[1], signature[2], signature[3]);
    if(strncmp(signature, "EBG", 3) != 0 || signature[3] != 0x01) goto exit_close;

    read_bytes = read(img->fd, &img->header, sizeof(g_img_header_t));
    printf("Header size: %d/%d\n", read_bytes, sizeof(g_img_header_t));
    for(int i = 0; i < read_bytes; i++) {
        printf("0x%02X ", ((uint8_t*)img)[i]);
    }
    printf("\n");

    printf("Width: %d\nHeight: %d\n", img->header.width, img->header.height);
    printf("Flags\n\t- Transparent: %s\n\t- Color mode: %s\n\t- Indexed: %s\n\t- Index size: %s\n",
        (img->header.flags & G_IMG_FLAG_TRANSPARENT) ? "YES": "NO",
        colormode2str(img->header.flags & G_IMG_FLAG_COLORMODE),
        (img->header.flags & G_IMG_FLAG_INDEXED) ? "YES" : "NO",
        (img->header.flags & G_IMG_FLAG_INDEXSIZE) ? "BYTE" : "BIT");
    printf("Palette size: %d\n", img->header.palette_size + 1);
    printf("Transparent index: %d\n", img->header.transparent_index);
    printf("Frame count: %d\n", img->header.frame_count);

    // Read palette if required
    if(img->header.flags & G_IMG_FLAG_INDEXED) {
        img->palette = malloc((img->header.palette_size + 1) * sizeof(g_color_t));
        if(!img->palette) {
            goto exit_close;
        }
        read(img->fd, img->palette, (img->header.palette_size + 1) * sizeof(g_color_t));

        printf("Palette:\n\t");
        for(int i = 0; i < img->header.palette_size + 1; i++) {
            printf("0x%04X ", img->palette[i]);
            if((i+1) % 16 == 0) printf("\n\t");
        }
        printf("\n");
    }

    // Read first frame
    img->bitmap = malloc(img->header.width * img->header.height);
    read_bytes = read(img->fd, img->bitmap, img->header.width * img->header.height);
    printf("Bitmap read: %d/%d\n", read_bytes, img->header.width * img->header.height);
    img->current_frame = 1;

    if(img->header.frame_count == 1) {
        // If there is only one frame in the image, file is not needed anymore
        close(img->fd);
        img->fd = -1;
    }

    return img;

exit_close:
    close(img->fd);

exit_free:
    free(img->bitmap);
    free(img);
    return NULL;
}

void g_img_close(g_img_t* img) {
    if(img->fd > -1) close(img->fd);
    if(img->header.flags & G_IMG_FLAG_INDEXED) free(img->palette);
    free(img->bitmap);
    free(img);
}

void g_img_load_next(g_img_t* img) {
    if(img->current_frame >= img->header.frame_count) return;

    ssize_t read_bytes;
    read_bytes = read(img->fd, img->bitmap, img->header.width * img->header.height);
    printf("[Next frame] Bitmap read: %d/%d\n", read_bytes, img->header.width * img->header.height);
    img->current_frame++;
}

void g_img_load_prev(g_img_t* img){
    if(img->current_frame <= 1) return;

    lseek(img->fd, -2 * (img->header.width * img->header.height), SEEK_CUR);
    ssize_t read_bytes;
    read_bytes = read(img->fd, img->bitmap, img->header.width * img->header.height);
    printf("[Prev frame] Bitmap read: %d/%d\n", read_bytes, img->header.width * img->header.height);
}

void g_img_load_first(g_img_t* img) {
    lseek(img->fd, PALETTE_OFFSET + PALETTE_SIZE(img), SEEK_SET);

    ssize_t read_bytes;
    read_bytes = read(img->fd, img->bitmap, img->header.width * img->header.height);
    printf("[First frame] Bitmap read: %d/%d\n", read_bytes, img->header.width * img->header.height);
    img->current_frame = 1;
}

esp_err_t g_img_draw(g_coord_t x, g_coord_t y, g_img_t* img) {
    if(img->header.flags & G_IMG_FLAG_INDEXED) {
        if(img->header.flags & G_IMG_FLAG_TRANSPARENT)
            return g_draw_bitmap_palette_transparent(x, y, img->bitmap, img->header.width, img->header.height, img->palette, img->header.transparent_index);
        else
            return g_draw_bitmap_palette(x, y, img->bitmap, img->header.width, img->header.height, img->palette);
    }
        
    
    return ESP_ERR_NOT_SUPPORTED;
}
