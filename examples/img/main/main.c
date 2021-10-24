#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_system.h>

#include <esp_spiffs.h>

#include <graphics.h>
#include <img.h>

#include <esp_log.h>
static const char* TAG = "EXAMPLE-IMG";


g_img_t* img;

void draw(const g_region_t* region) {
    g_region_t reg = (g_region_t){.x0=0, .y0=0, .x1=DISP_WIDTH-1, .y1=DISP_HEIGHT-1};

    g_draw_rect(&reg, 0x0000, G_FILLED);
    
    g_img_draw(0, 0, img);
}


int64_t elapsed;
void fpsTask(void *pvParameter)
{
    while(1) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        ESP_LOGI(TAG, "FPS: %f (%lld us/frame)", 1000000./elapsed, elapsed);
    }
    vTaskDelete(NULL);
}

void imgTask(void *pvParameter)
{
    while(1) {
        vTaskDelay(pdMS_TO_TICKS(200));
        if(img->current_frame < img->header.frame_count)
            g_img_load_next(img);
        else
            g_img_load_first(img);
    }
    vTaskDelete(NULL);
}

void app_main()
{
    esp_err_t ret;
    
    ret = g_init();
    if(ret != ESP_OK) {
        ESP_LOGE(TAG, "Unable to initialize graphics");
        return;
    }

    esp_vfs_spiffs_conf_t conf = {
        .base_path = "/data",
        .partition_label = "data",
        .max_files = 5,
        .format_if_mount_failed = true
    };
    ret = esp_vfs_spiffs_register(&conf);
    if (ret != ESP_OK) {
        if (ret == ESP_FAIL) {
            ESP_LOGE(TAG, "Error: Failed to mount or format /system");
        } else if (ret == ESP_ERR_NOT_FOUND) {
            ESP_LOGE(TAG, "Error: System storage partition not found");
        } else {
            ESP_LOGE(TAG, "Error: SPIFFS initialization failed (%s)", esp_err_to_name(ret));
        }
    }

    img = g_img_open("/data/loading.ebg");
    if(!img) {
        ESP_LOGE(TAG, "Unable to read image");
        return;
    }
    
    g_region_t refresh_region = {
        .x0 = 0,
        .y0 = 0,
        .x1 = DISP_WIDTH - 1,
        .y1 = DISP_HEIGHT - 1
    };

    xTaskCreate(&fpsTask, "fps", 2048, NULL, 5, NULL);
    xTaskCreate(&imgTask, "img", 2048, NULL, 5, NULL);

    // Render loop
    while(1) {
        uint64_t start = esp_timer_get_time();
        
        g_refresh_region(&refresh_region, draw);

        elapsed = esp_timer_get_time() - start;
        vTaskDelay(pdMS_TO_TICKS(20));
    }

    g_img_close(img);
}
