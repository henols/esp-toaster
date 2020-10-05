import json
import ntptime
from machine import RTC

def connect_and_subscribe():
  global client_id, config, topic_sub
  print('Tryng to connect')
  client = MQTTClient(client_id, config["mqtt-server"], port = config["mqtt-port"],keepalive = 10)
  power = {}
  power['state'] = 'off'
  client.set_last_will(power_topic,json.dumps(power), retain=True)
  client.connect()
#  client.subscribe(topic_sub)
  print('Connected to %s MQTT broker' % (config["mqtt-server"]))
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  machine.reset()

def post_toasting_message(state):
  global toasting_topic
  print('toasting %s' % state ,rtc.datetime())
  toast = {}
  toast['state'] = 'toasting' if state else 'ejected'
  toast['duration'] = 0
  toast['progress'] = 100
  
  client.publish(toasting_topic, json.dumps(toast))

def pin_cb(value):
  print('Pin state %s' % value)
  global toasting_switch_cur_value
  toasting_switch_cur_value = value

def is_toasting():
    global toasting_switch_cur_value
    return toasting_switch_cur_value == False

rtc = RTC()

# synchronize with ntp
# need to be connected to wifi
try:
  ntptime.settime() # set the rtc datetime from the remote server
except OSError as e:
  print('Failed to get time, try later or not')
#print('Time %s' % rtc.datetime())   # get the date and time in UTC

print('Connect and subscribe to MQTT broker.')
try:
  toasting_switch.set_callback(pin_cb)
  toasting_switch_cur_value = toasting_switch.value
  client = connect_and_subscribe()
  power = {}
  power['state'] = 'on'
  client.publish(power_topic, json.dumps(power))
except OSError as e:
  restart_and_reconnect()

while True:
  try:
    client.check_msg()
    toasting = is_toasting()
    if last_toasting_state != toasting:
      print('state %s, last state %s' % (toasting, last_toasting_state))
      last_toasting_state = toasting
      if toasting == True:
        last_message = time.time()
      post_toasting_message(toasting)
    elif toasting == True and (time.time() - last_message) > message_interval:
      post_toasting_message(toasting)
      last_message = time.time()
  except OSError as e:
    print(e)
    restart_and_reconnect()
    