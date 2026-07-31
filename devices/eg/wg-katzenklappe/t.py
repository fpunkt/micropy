from machine import Pin, PWM
import time

# Servo-Pin definieren (Beispiel: GPIO 4)
servo = PWM(Pin(10), freq=50)

def set_angle(angle):
    # Winkel (0-180) in Duty-Cycle umrechnen
    # duty_ns: 500000 ns (0°) bis 2500000 ns (180°)
    min_ns = 500000
    max_ns = 2500000
    ns = min_ns + (max_ns - min_ns) * angle // 180
    servo.duty_ns(ns)

set_angle(0)
time.sleep(1)
set_angle(90)
time.sleep(1)
set_angle(180)
time.sleep(1)