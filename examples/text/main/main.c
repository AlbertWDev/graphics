#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_system.h>

#include "graphics.h"

#include <esp_log.h>
static const char* TAG = "EXAMPLE-TEXT";

static const char* sample_text = "The quick brown fox jumps over the lazy dog\n"
"El veloz murcie\x1b\x82lago hindu\x1b\x82 comi\x1b\x82""a feliz cardillo y kiwi\n"
"La cigu\x1b\x85""en\x1b\x81""a tocaba el saxofo\x1b\x82n detra\x1b\x82s del palenque de paja.\n"
"123456789=*+-_.,:;\x86?\x87![](){}<>\x80\x88\x8e\x8f\x82`^\x85$ #&%\"\\|/@ \n"
"a\x1b\x82""e\x1b\x82i\x1b\x82o\x1b\x82u\x1b\x82""A\x1b\x8a""E\x1b\x8aI\x1b\x8aO\x1b\x8aU\x1b\x8a\n";


void draw(const g_region_t* region) {
    g_region_t reg = (g_region_t){.x0=0, .y0=0, .x1=DISP_WIDTH-1, .y1=DISP_HEIGHT-1};
    g_draw_rect(&reg, 0xFFFF, G_FILLED);

    g_draw_string(10, 20, sample_text, 0x0000);
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
    if(g_init() != ESP_OK) {
        ESP_LOGE(TAG, "Unable to initialize graphics");
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