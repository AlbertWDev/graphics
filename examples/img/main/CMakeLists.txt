idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS ""
)

spiffs_create_partition_image(data ./data FLASH_IN_PROJECT)
#spiffs_create_partition_image(data ./data)
