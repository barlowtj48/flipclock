# Developed by Thomas Barlow
# Free for Private Use
# More information at https://thomasjbarlow.com/flip_clock


import RPi.GPIO as GPIO
import time
from enum import Enum
import datetime
import geocoder
import json
import requests

Flip_To = Enum("Flip_To", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D"], start=0)
weather_associations = {1 : "AD",
                        2 : "AC", 
                        3 : "AB", 
                        4 : "AB", 
                        9 : "BB", 
                        10: "BC", 
                        11: "CB", 
                        13: "DB", 
                        50: "AB"}

class ServoController:
    def __init__(self, m_servos):
        self.servos = m_servos
        self.sub_steps = [[0, 0, 0, 1],
                            [0, 0, 1, 1],
                            [0, 0, 1, 0],
                            [0, 1, 1, 0],
                            [0, 1, 0, 0],
                            [1, 1, 0, 0],
                            [1, 0, 0, 0],
                            [1, 0, 0, 1]]
        self.step_order = [36, 37, 36, 37, 36, 37, 36, 37, 36, 37, 36, 37, 37, 37]

    def servos_done(self):
        done = 0
        for i in range(4):
            if(self.servos[i].done):
                done += 1
        if done == 4:
            for i in range(4):
                self.servos[i].done = False
            return True
        else:
            return False

    def sum_step_order(self, index, distance):
        added = 0
        for i in range(distance):
            added += self.step_order[index]
            index += 1
            if(index == 14):
                index = 0
        return added

    def get_total_steps(self, output_str):
        output = [str(d) for d in str(output_str)]
        steps = []
        for i, val in zip(range(4), output):
            index_offset = self.servos[i].get_flap_offset(Flip_To[val].value)
            steps.append(self.sum_step_order(self.servos[i].current_flap, index_offset))
        return steps

    def Output(self, output_str):
        total_steps = self.get_total_steps(output_str)
        while(not self.servos_done()):
            for substep in self.sub_steps:
                for i in range(4):
                    if(not self.servos[i].current_step == total_steps[i]):
                        self.servos[i].substep(substep)
                    else:
                        self.servos[i].done = True
                        self.servos[i].stop()

                time.sleep(.001)

class Servo:
    def __init__(self, m_pins):
        self.pins = m_pins
        self.current_flap = 0
        self.current_step = 0
        self.current_substep = 0
        self.done = False

    def stop(self):
        for i in range(4):
            GPIO.output(self.pins[i], 0)
    
    def substep_increment(self):
        if(self.current_substep == 7):
            self.current_substep = 0
            self.current_step += 1
            if(self.current_step == 512):
                self.current_step = 0
        else:
            self.current_substep += 1

    def substep(self, step):
        for pin, bit in zip(self.pins, step):
            GPIO.output(pin, bit)
        self.substep_increment()
    
    def get_flap_offset(self, index):
        offset = 0
        if(index < self.current_flap):
            offset = (14-self.current_flap) + index
        else:
            offset = index - self.current_flap
        return offset
        
def format_time():
    now = datetime.datetime.now()
    output = str(now.strftime("%I%M"))
    if(output[0] == "0"):
        output = "A" + output[1:]
    return output

def format_weather():
    api_key = "13e8ca16379a0c6dc6af97307803b009"
    location = geocoder.ip('me')
    url = "https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude={part}&appid={api}".format(lat=location.latlng[0], lon=location.latlng[1], part="hourly,minutely,alerts,daily", api=api_key)

    response = requests.get(url)
    data = response.json()

    temperature = float(data['current']['temp'])
    icon = data['current']['weather'][0]['icon'][:-1]

    temperature = round((temperature - 273.15) * 9/5 + 32)
    temperature = "{:02d}".format(temperature)
    icon = weather_associations[int(icon)]

    output = str("{}{}".format(temperature, icon))
    return output

        
servos = [Servo([17, 27, 22, 23]), Servo([10,9,11,0]), Servo([5,6,13,19]), Servo([25,8,7,1])]
sc = ServoController(servos)

GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setwarnings(False)
for servo in servos:
    for i in servo.pins:
        GPIO.setup(i, GPIO.OUT)

while(True):
    duration = 0
    while(GPIO.input(24) == False):
        duration += .01
        time.sleep(.01)
    if(duration > .1 and duration < 1):
        sc.Output(format_weather())
        time.sleep(10)
    elif(duration > 2 and duration < 10):
        time.sleep(1)
        while(GPIO.input(24) == True):
            sc.Output("AAAA")
        time.sleep(2)
    elif(duration > 10):
        sc.Output("0000")
        quit()
    else:
        sc.Output(format_time())
