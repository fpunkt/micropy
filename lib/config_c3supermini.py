# ESP32 C3 super mini board configuration
import board
board.LED = board.Led(8, onvalue=0)  # on board LED is active low
