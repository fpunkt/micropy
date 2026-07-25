import network
import time

def wifi_connect(ssid, password, timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)

    # Power-Save aus -> stabiler beim Verbindungsaufbau
    wlan.config(pm=network.WLAN.PM_NONE)

    if wlan.isconnected():
        wlan.disconnect()
        time.sleep(0.5)

    wlan.connect(ssid, password)

    t0 = time.time()
    while not wlan.isconnected() and time.time() - t0 < timeout:
        status = wlan.status()
        print("status:", status)
        time.sleep(0.5)

    if wlan.isconnected():
        print("Verbunden:", wlan.ifconfig())
        return True
    else:
        print("Fehlgeschlagen, letzter Status:", wlan.status())
        # Status-Codes (bei den meisten Ports):
        # 0 = IDLE, 1 = CONNECTING, 2 = WRONG_PASSWORD,
        # 3 = NO_AP_FOUND, 4 = CONNECT_FAIL, 5 = GOT_IP
        return False

