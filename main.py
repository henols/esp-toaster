import json
import ntptime
from machine import RTC

expected_toasting_time = 120
toasting_times_file = 'toasting_times.json'
toasting_times = []

def connect_and_subscribe():
  global client_id, config, topic_sub
  client = MQTTClient(client_id, config["mqtt-server"], port=config["mqtt-port"], keepalive=10)
  power = {}
  power['state'] = 'off'
  client.set_last_will(power_topic, json.dumps(power), retain=True)
  client.connect()
#  client.subscribe(topic_sub)
  print('Connected to {} MQTT broker'.format(config["mqtt-server"]))
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
  print('Toaster message: {}'.format(toast))
  client.publish(toasting_topic, json.dumps(toast))
  
  # Only update the calculated toasting time if we are not toasting and
  # if the duration is 10% of the expected time, we don't want a failure 
  # to push down the tray or a change of mind manipulate the expected toasting
  # time. 
  if state == False and duration > expected_toasting_time / 10:
      expected_toasting_time = calculate_expected_toasting_time(duration)
      toasting_start = 0;

def pin_cb(value):
#   print('Pin state %s' % value)
  global toasting_switch_cur_value
  toasting_switch_cur_value = value


def is_toasting():
    global toasting_switch_cur_value
    return toasting_switch_cur_value == False

def calculate_expected_toasting_time(duration):
    global toasting_times
    toasting_times.append(duration)
    samples = len(toasting_times)
    if samples > 10:
        toasting_times.remove(0)
        samples = 10
      
    # Save toasting times
    f = open(toasting_times_file, "w")
    f.write(json.dumps(toasting_times)) 
    f.close()
    
    total = 0  
    for value in toasting_times:
        total += value
        
    print('Calculated toasting time: {}, samples: {}, last duration {}'.format(total/samples, samples, duration))

    return total / samples
    
try:
    f = open(toasting_times_file, "r")
    toasting_times = json.load(f) 
    f.close()
except OSError:  # open failed
    toasting_times = [90]
    
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
  print('Toaster message: {}'.format(power))
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
    
