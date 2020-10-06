import json
import ntptime
from machine import RTC

expected_toasting_time = 120


def connect_and_subscribe():
  global client_id, config, topic_sub
  print('Tryng to connect')
  client = MQTTClient(client_id, config["mqtt-server"], port=config["mqtt-port"], keepalive=10)
  power = {}
  power['state'] = 'off'
  client.set_last_will(power_topic, json.dumps(power), retain=True)
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
  global toasting_start
  global expected_toasting_time
  duration = time.time() - toasting_start
  toast = {}
  toast['state'] = 'toasting' if state else 'ejected'
  toast['duration'] = '{:02.0f}:{:02.0f}'.format(duration / 60, duration % 60)
  toast['progress'] = duration / expected_toasting_time * 100
  print('Toasting message: %s', toast)
  client.publish(toasting_topic, json.dumps(toast))


def pin_cb(value):
#   print('Pin state %s' % value)
  global toasting_switch_cur_value
  toasting_switch_cur_value = value


def is_toasting():
    global toasting_switch_cur_value
    return toasting_switch_cur_value == False


rtc = RTC()

# synchronize with ntp
# need to be connected to wifi
try:
  ntptime.settime()  # set the rtc datetime from the remote server
except OSError as e:
  print('Failed to get time, try later or not')
# print('Time %s' % rtc.datetime())   # get the date and time in UTC

print('Connect and subscribe to MQTT broker.')
try:
  toasting_switch.set_callback(pin_cb)
  toasting_switch_cur_value = toasting_switch.value
  client = connect_and_subscribe()
  power = {}
  power['state'] = 'on'
  client.publish(power_topic, json.dumps(power), retain=True)
except OSError as e:
  restart_and_reconnect()

toasting_start = 0

while True:
  try:
    client.check_msg()
    toasting = is_toasting()
    now = time.time()
    if last_toasting_state != toasting:
#       print('state %s, last state %s' % (toasting, last_toasting_state))
      last_toasting_state = toasting
      if toasting :
        toasting_start = now
        last_message = now
      post_toasting_message(toasting)
    elif toasting == True and (now - last_message) > message_interval:
      post_toasting_message(toasting)
      last_message = now
  except OSError as e:
    print(e)
    restart_and_reconnect()
    
