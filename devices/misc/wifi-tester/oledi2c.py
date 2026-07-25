from machine import Pin, I2C
import ssd1306

i2c = I2C(0, scl=Pin(6), sda=Pin(5), freq=400000)
print(i2c.scan())  # zur Kontrolle, sollte z.B. [60] (0x3C) zeigen


class SSD1306_Custom(ssd1306.SSD1306_I2C):
    def show(self):
        x0 = 28
        x1 = x0 + self.width - 1
        self.write_cmd(0x21)          # SET_COL_ADDR
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(0x22)          # SET_PAGE_ADDR
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)

oled = SSD1306_Custom(72, 40, i2c)
oled.fill(0)
oled.text("Hallo Frank", 0, 0, 1)
oled.text('World', 0, 10)

oled.show()

