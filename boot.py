import time
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
esp.osdebug(None)
from switch import Switch
import json

import gc
gc.collect()


file = open("config.json", "r")
 
config = json.load(file) 
file.close()

client_id = ubinascii.hexlify(machine.unique_id())
power_topic = b'toaster/power'
toasting_topic = b'toaster/toasting'

message_interval = 2

toasting_pin = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)

toasting_switch = Switch(toasting_pin)
last_toasting_state = False;
toasting_switch_cur_value = False 

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(config["ssid"], config["password"])

while station.isconnected() == False:
  pass

print('Connecting to {}, successful'.format(config["ssid"]))
print(station.ifconfig())