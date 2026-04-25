// Copy this into your TFT_eSPI User_Setup_Select.h include chain.
// It maps TFT to Node B pin plan in firmware/README.md.

#define ST7735_DRIVER

#define TFT_WIDTH 128
#define TFT_HEIGHT 128

#define TFT_MOSI 13
#define TFT_SCLK 14
#define TFT_CS   15
#define TFT_DC   2
#define TFT_RST  -1

#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF

#define SPI_FREQUENCY  20000000
#define SPI_READ_FREQUENCY  20000000
