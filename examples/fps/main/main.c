#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_system.h>

#include "graphics.h"

#include <esp_log.h>
static const char* TAG = "EXAMPLE-FPS";


void draw(const g_region_t* region) {
    g_region_t reg = (g_region_t){.x0=0, .y0=0, .x1=DISP_WIDTH-1, .y1=DISP_HEIGHT-1};

    g_draw_rect(&reg, 0xFFFF, G_FILLED);
    g_draw_rect(&reg, HEX_TO_COLOR(0xF800), 1);
}


int64_t elapsed;
void fps_task(void *pvParameter)
{
    while(1) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        ESP_LOGI(TAG, "FPS: %f (%lld us/frame)", 1000000./elapsed, elapsed);
    }
    vTaskDelete(NULL);
}

void app_main()
{
    ESP_LOGI(TAG, "Initializing graphics");
    esp_err_t ret;
    if((ret = g_init()) != ESP_OK) {
        ESP_LOGE(TAG, "Unable to initialize graphics: %s", esp_err_to_name(ret));
        return;
    }
    
    g_region_t refresh_region = {
        .x0 = 0,
        .y0 = 0,
        .x1 = DISP_WIDTH - 1,
        .y1 = DISP_HEIGHT - 1
    };

    xTaskCreate(&fps_task, "fps", 2048, NULL, 5, NULL);

    // Render loop
    while(1) {
        uint64_t start = esp_timer_get_time();
        
        g_refresh_region(&refresh_region, draw);

        elapsed = esp_timer_get_time() - start;
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}