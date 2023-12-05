#boot.py - executed on every boot (including wake-boot from deepsleep)
#The boot file connects to the specified wifi network. It should be as simple as possible, because main.py won't run if boot has any errors. 

##USER INPUT##
networkname = 'your_network_name_here'
password = 'your_password_here'

##################################################################################
#import necessary packages
import esp
import network
import time
import machine

#Wifi setup:
print('running boot') #for troubleshooting
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

if wlan.isconnected():
    print('connected')
    wlan.disconnect()
    
if not wlan.isconnected():
    print('connecting to network...')
    wlan.connect(networkname, password) 
    tries = 0
    #attempt to connect 20 times
    while not wlan.isconnected() and tries < 20:
        print('...')
        # wlan.connect(networkname, password)
        time.sleep(5)
        tries = tries + 1
    #print a fail message or a success message
    print('network config:', wlan.ifconfig())
    if wlan.isconnected():
        print("WiFi connected at", wlan.ifconfig()[0])
    else:
        print("Mission failed")
        
# print current date and time using real-time clock
from machine import RTC
print("inquire RTC time")
rtc = machine.RTC()
rtc.datetime()
print(rtc.datetime())