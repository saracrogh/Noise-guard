#main.py - runs automatically after boot.

#main.py connects to the specified adafruit server, sets up the microphone to recieve the proper input,
#then continually processes the audio into its average amplitude value, publishing it to adafruit and
#turning on the LED and buzzer if it crosses the specified threshhold

##USER INPUT##
adafruitUsername = "XX"
adafruitAioKey = "XX"
feedName = "XX"
limit = 440 #AUDIO AMPLITUDE LIMIT where buzzer/LED/SMS will be triggered (around 400-600 should be fine)
wait_time = 0.5 #Time to wait between loops of sampling audio
samplesize = 25600 # desired sample size in bytes (must be a multiple of 6400)

#import necessary packages
from machine import Pin, PWM, Timer
from machine import I2S
import struct
from umqtt.simple import MQTTClient
import umqtt1
from math import sin
import network
import sys
import time
import machine

######################################## Adafruit setup
# Check wifi connection
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
ip = wlan.ifconfig()[0]
if ip == '0.0.0.0':
    print("no wifi connection")
    sys.exit()
else:
    print("connected to WiFi at IP", ip)

# Set up Adafruit connection
myMqttClient = "TestClient"
adafruitIoUrl = "io.adafruit.com"

# Connect to Adafruit server
print("Connecting to Adafruit")
mqtt = umqtt1.MQTTClient(myMqttClient, adafruitIoUrl, 0, adafruitUsername, adafruitAioKey)
time.sleep(0.5) #delay increases stability
mqtt.connect()
print("Connected!")

######################### Buzzer/LED set up
#Variables for buzzer sequence (can be changed if desired)
numloops=2 #loops of the buzzer sequence played
wait_buzzer = 0.5 #time between low and high tones
wait_loop = 1 #time between loops
cycle=500 #half duty cycle (can be 0-1023)
C3=2000 #low tone frequency in Hz
G3=3000 #high tone frequency in Hz

pin_buzzer=Pin(15, mode=Pin.OUT) #defining the pin that the buzzer circuit is connected to
L1= PWM(pin_buzzer, freq=1, duty=cycle) #defines L1 as a PWM output
led = machine.Pin(26, machine.Pin.OUT) #defining the pin that the LED is connected to
led.value(0)

################### Mic setup
#Specify data pins:
sck_pin = Pin(12) #clock pin
ws_pin = Pin(13) #channel select pin
sd_pin = Pin(27) #data pin
#Also connect L/R and GND to common ground, and VDD to 3V source

#constructor object for I2S protocol in micropython:
audio_in = I2S(0,               #identifies an i2s bus - in this case, bus 0
               sck=sck_pin,     #specify serial clock line
               ws=ws_pin,       #specify word select line
               sd=sd_pin,       #specify serial data line
               #no need to specify a master clock line
               mode=I2S.RX,     #.RX sets the esp32 to 'recieve' mode (.TX would be transmit mode)
               bits=16,         #Sample size is signed 16 bits (each sample represents a value from −32,768 to 32,767)
               format=I2S.MONO, #Specifies mono audio
               rate=16000,      #Sets sampling rate to 16kHz (frequency of ws signal)
               ibuf=16000)      #specifies internal buffer length


###################################### Main loop
collectdata = 1
while collectdata: #always true
    led.value(0) #Turn LED off if it was previously on
    
    ################################ Reading data and finding average magnitude
    mic_samples = bytearray(6400) #blank allocated memory
    mic_samples_mv = memoryview(mic_samples) #use memoryview to avoid making a copy of the data in memory multiple times
    runningsum=0 #variable for calculating average
    numsamples=0 #variable for calculating average
    
    #Repeat 6400 byte sampling until the desired sample size is reached
    for i in range(0, (samplesize/6400)):
        try: #if reading data fails, we don't want the code to stop running
            num_bytes_read_from_mic = audio_in.readinto(mic_samples_mv) #Reads audio samples into the the allocated buffer in memory. Byte ordering is little-endian
            for x in range(0, len(mic_samples_mv), 4): #for each 4 bytes of data in the buffer
                l, r = struct.unpack('<hh', mic_samples_mv[x: x+4]) #convert the 4 bytes into two signed 16 bit numbers for the left and right channels using little endian decoding
                #Note: The microphone was set up for mono recording, so the left and right channels are actually the same.
                #Each sample of mono audio alternates between the left and right channel from the nature how the data was unpacked
                runningsum += (abs(l)+abs(r)) #sum the magnitude of both the left and right samples to the running sum
                numsamples += 2 #increment the number of samples read by 2
        except (KeyboardInterrupt, Exception) as e: #exception for 'try' code block
            print('caught exception {} {}'.format(type(e).__name__, e))
            break
        
    audio_in.deinit() #stop reading audio data
    average = runningsum / numsamples #find the average magnitude of all samples in the sample size by dividing the running sum by the number of samples read
    
    ##################################### Check if the average amplitude is beyond the set limit, and if so, turn on LED, play Buzzer, and send SMS
    if average > limit:
        led.value(1) #Turn LED on
        
        try: #Publish the average value to adafruit. We use 'try' since we don't want the code to stop running if the publishing fails.
            Message = "{}".format(average) #message is the value of average
            mqtt.publish(feedName,Message) #publish message to feedName specified
            print("Published {} to {}.".format(testMessage,feedName)) #for troubleshooting
        except (KeyboardInterrupt, Exception) as e: #exception to 'try'
                print('caught exception {} {}'.format(type(e).__name__, e))
                break
    
        for loop in range(numloops): #Play the hard coded buzzer tone for the number of loops specified
            L1.duty(cycle) #turns buzzer on
            L1.freq(C3) #low tone
            time.sleep(wait_buzzer)
            L1.freq(G3) #high tone
            time.sleep(wait_buzzer)
            L1.freq(C3) #low tone
            time.sleep(wait_buzzer)
            L1.freq(G3) #high tone
            time.sleep(wait_buzzer)
            L1.duty(0) #turn buzzer off
            time.sleep(wait_loop) #time between loops
            #The microphone is not used while the buzzer is playing.
            #Audio will only be read again when the main loop runs, which can only happen once the buzzer is done.
            
    time.sleep(wait_time) #slows down main loop to lower wifi usage.
    #End of main loop
