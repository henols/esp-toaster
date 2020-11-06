import json

expected_toasting_time = 120
toasting_times_file = 'toasting_times.json'
toasting_times = []


def set_up_ui():
    global power_topic
    global toasting_topic
    global mqtt_dash_ui_topic 
    
    filepath = 'mqtt-dashboard-config.json'
    print('Publishing ui {}'.format(filepath))
    try:
        with open(filepath, 'r') as file :
            ui = json.load(file) 
        file.close()
    except OSError:  # open failed
        print('Ui {} not found'.format(filepath))
        return
    gc.collect()
    print('Adding topics to ui')
    
    topics = {'power_topic': str(power_topic, 'utf8'),
              'toasting_topic': str(toasting_topic, 'utf8')}

    for tile in ui['tiles']:
        if tile['topic'] in topics:
            tile['topic'] = topics[tile['topic']]

    result = json.dumps(ui)
    print('Publishing ui to topic {}'.format(str(mqtt_dash_ui_topic, 'utf8')))

    client.publish(mqtt_dash_ui_topic, result)
    print('Ui published')
    gc.collect()


def connect_and_subscribe():
    global client_id, config, topic_sub
    client = MQTTClient(client_id, config["mqtt-server"], port=config["mqtt-port"], keepalive=10)
    power = {}
    power['state'] = 'off'
    client.set_last_will(power_topic, json.dumps(power), retain=True)
    client.connect()
    print('Connected to {} MQTT broker'.format(config["mqtt-server"]))
    return client

def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    print('mem_alloc: {}, mem_free: {}'.format(gc.mem_alloc() , gc.mem_free()))
    time.sleep(10)
    machine.reset()

def post_toasting_message(state):
    global toasting_topic
    global toasting_start
    global expected_toasting_time
    duration = time.time() - toasting_start
    toast = {}
    toast['state'] = 'toasting' if state else 'ejected'
    toast['duration'] = '{:02.0f}:{:02.0f}'.format(int(duration / 60), duration % 60)
    toast['progress'] = int(duration / expected_toasting_time * 100)
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
        
    print('Calculated toasting time: {}, samples: {}, last duration {}'.format(total / samples, samples, duration))

    return total / samples

    
try:
    f = open(toasting_times_file, "r")
    toasting_times = json.load(f) 
    f.close()
except OSError:  # open failed
    toasting_times = [90]
    
print('Connect and subscribe to MQTT broker.')
try:
    toasting_switch.set_callback(pin_cb)
    toasting_switch_cur_value = toasting_switch.value
    client = connect_and_subscribe()
    power = {}
    power['state'] = 'on'
    print('Toaster message: {}'.format(power))
    client.publish(power_topic, json.dumps(power), retain=True)
    set_up_ui()
except OSError as e:
    restart_and_reconnect()

toasting_start = 0

print('Toaster is started')

while True:
    try:
        client.check_msg()
        toasting = is_toasting()
        now = time.time()
        if last_toasting_state != toasting:
            # print('state %s, last state %s' % (toasting, last_toasting_state))
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
    
