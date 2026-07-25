from machine import Pin, SPI
import ssd1306

# Software- oder Hardware-SPI, hier Hardware-SPI(1)
spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(4), mosi=Pin(6))

dc  = Pin(5, Pin.OUT)
rst = Pin(7, Pin.OUT)
cs  = Pin(10, Pin.OUT)

def init_display():
    oled = ssd1306.SSD1306_SPI(72, 40, spi, dc, rst, cs)
    oled.fill(0)
    oled.text("Hallo Frank", 0, 0, 1)
    oled.show()
    print("Display initialized and text displayed.")

init_display()
