"""
Some tools to debug the WLAN connection"""

import network
import board
import time
import fsmqtt
import net

network.country('DE')
wlan = network.WLAN(network.STA_IF) 

def scan():
    wlan.active(False)
    time.sleep_ms(100)
    wlan.active(True)
    for ap in wlan.scan():
        ssid, bssid, channel, RSSI, security, hidden = ap
        bssi = net.format_mac(bssid)
        print(f"SSID: {ssid.decode():20s} RSSI: {RSSI:4d} dBm {security} {hidden} {bssi}")

def rssi():
    wlan.active(True)
    while True:
        time.sleep(0.5)
        rssi = wlan.status('rssi')
        board.PRINTF('RSSI: {} dBm', rssi)
        board.MQTT.publish('info/rssi', rssi)
