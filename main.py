#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
KspReadout

This is a script that uses krpc to feed data from Kerbal Space Program to an Arduino in real time. The outputs
are a string of cat'ed numbers, eg. 0200254, 03011

Outputs are this format:
[type][id][value]
type: 2-digits representing what the information is for in range 00-99
 02: Temperature of Super CoolTemps
 03: Whether radiator is extended (outputs 0 for retracted and 1 for extended)
 04: Temperature of active radiators
 05: Percent efficiency of active radiators (available in window)
 06: Temperature of fuel tanks
 07: Temperature of engines
 08: Temperature of skins of fuel tanks
 09: Temperature of root part
 note 00 and 01 are currently not used
id: 2-digits representing the id of the part going in range 00-99
value: numbers representing the value
 Can be ints or floats according to round parameter of Readout constructor
  Type05 is the exception to this, the rounding can go from 0 to 2 and is determined by attribute parameter

So many things can go wrong with this, so here are the exit codes:
 0: None, this should never happen because this runs on an while True
 10: Module not found - make sure to install krpc and pyserial
 20: Connection Refused - krpc is probably not running
 21: No Active Vessel - probably in wrong context ingame
 30: Serial Resource Busy - something else such as Serial Monitor might be up
 31: No Correct Response - arduino is not plugged in or not flashed with the correct software or CH34x not installed
 40: Num Greater Than 99 - Readout constructor parameter 'num' must be in range 0-99
 41: Typ Length Not 2 - Readout constructor parameter 'num' must have length 2
"""

__all__ = ["main"]
__author__ = "Kenny Kim"
__credits__ = ["Kenny Kim"]
__version__ = "1.0.0"
__maintainer__ = "Kenny Kim"
__email__ = "kennykim11@gmail.com"
__status__ = "Prototype"




print('\nSTARTING')



# === IMPORTS ===
print('Importing... ')
try:
    from krpc import connect
    from krpc.error import RPCError
    from serial import Serial
    from serial.tools.list_ports import comports
    from time import sleep
except ModuleNotFoundError as e:
    print(e.args[0])
    exit(10)
print(' Finished')



# === SETTINGS ===
SERIAL_ADDRESS = ''
ser = None
debug = False



# === KRPC CONNECTION ===
print('Connecting to KSP... ')
try:
    conn = connect(name='Arduino Readout')
except ConnectionRefusedError:
    print("Connection Refused, are Kerbal Space Program and krpc running?")
    exit(20)
try:
    vessel = conn.space_center.active_vessel
except RPCError:
    print("No Active Vessel, Make sure that you are focused on a vessel when starting.")
    exit(21)
sun = conn.space_center.bodies['Sun']
print(' Finished')



# === FUNCTIONS ===
print('Defining Structures... ')
def send(str):
    ser.write(str.encode('utf-8'))



# === CLASSES ===
class Readout:
    obj = None
    lastValue = -1
    typ = '01'
    num = ''
    attribute = 'temperature'
    round = -1
    values = []

    def __init__(self, obj, typ, num, attribute, round=-1, values=None):
        """
        Creates a new readout
        :param obj: The actual krpc part
        :param typ: 2-digit string of what kind of readout
        :param num: int of id number, will be turned into 2-digit string
        :param attribute: string of what attribute of function of the part, aka temperature
        :param round: int of what place to round to
        :param values: list of string values of which the return should be the index of value in values
        """
        if num > 99:
            print("Cannot have num greater than 99!")
            exit(40)
        num = str(num) if num > 9 else '0'+str(num)
        if len(typ) != 2:
            print("Cannot have typ length other than 2!")
            exit(41)
        self.obj, self.typ, self.num, self.attribute, self.round, self.values = obj, typ, num, attribute, round, values

    def update(self, resend=False):
        global value
        try:
            value = eval('self.obj.'+self.attribute) #getting the field or return of function
        except IndexError: #this happens during animations when events menu has length 0
            if debug: print("Index", self.typ)
            return
        if self.values:
            try:
                value = self.values.index(value) #getting the index from list of possible values
            except ValueError: #this happens if display is not in options, aka ['Retract', 'Extend']
                return
        elif self.round > -1:
            try:
                value = float(value)
                if self.round == 0:
                    value = round(value) #round(7.9, 0) -> 8.0; round(7.9) -> 8
                else:
                    value = round(value, self.round) #rounding the value, likely to an int
            except TypeError: #this happens when the value is unroundable to a number, aka round('Idle')
                if debug: print("Type", self.typ)
                return
            except ValueError:  #this happens if the value given is not a number, like if the thermal control systems have no electricity
                if debug: print("Value", self.typ, value)
                value = 0
        if debug: print(self.typ, value)
        if value != self.lastValue or resend:
            self.lastValue = value
            print(self.typ + self.num + str(value)) #For debugging
            send(self.typ + self.num + str(value)+'\n') #send to Arduino
            sleep(0.006) #Arduino timeout set to 5 milliseconds

print(' Finished')



# === SERIAL ===
print('Setting up Serial... ')
if SERIAL_ADDRESS == '':
    print(" No default port")
    openPorts = reversed([I for I in comports()]) #'/dev/cu.wchusbserial14410', '/dev/cu.usbmodem14641'
    for port in openPorts:
        print(" Attempting port at:",port.device)
        try:
            serTry = Serial(port.device, 115200, timeout=0.1)
        except OSError as e:
            if e.errno == 16:
                print("Resource is busy, is Serial Monitor up?")
            exit(30)
        sleep(2) #give time for Arduino to start Serial
        serTry.write('#'.encode('utf-8'))
        sleep(0.2)
        if b'!' in serTry.readline(): #Check for Arduino response
            SERIAL_ADDRESS = port.device
            print(" Arduino Found!")
            ser = serTry
            break
    if SERIAL_ADDRESS == '':
        print("No port found")
        exit(31)
else: #if default is set
    ser = Serial(SERIAL_ADDRESS, 115200, timeout=0.1)
print(' Finished')



# === PARTS ===
print('Making lists of parts and modules... ')
#Temperature of Super CoolTemps
tempSensor_parts = vessel.parts.with_module("TempReadout")
tempSensors_temp = [Readout(tempSensor_parts[I], '02', I, 'temperature', 0) for I in range(len(tempSensor_parts))]
#Extend status of deployable radiators
deployableRadiator_parts = vessel.parts.with_module("ModuleDeployableRadiator")
deployableRadiator_modules = [II for I in deployableRadiator_parts for II in I.modules if II.name == "ModuleDeployableRadiator"]
deployableRadiator_extended = [Readout(deployableRadiator_modules[I], '03', I, 'events[0]', None, ['Extend Radiator', 'Retract Radiator']) for I in range(len(deployableRadiator_modules))]
#Temperature and efficiency of active radiators
activeRadiator_parts = [I.part for I in vessel.parts.radiators]
activeRadiator_temp = [Readout(activeRadiator_parts[I], '04', I, 'temperature', 0) for I in range(len(activeRadiator_parts))]
activeRadiator_modules = [II for I in activeRadiator_parts for II in I.modules if II.name == "ModuleActiveRadiator"]
activeRadiator_effi = [Readout(activeRadiator_modules[I], '05', I, 'get_field("Cooling")[:-2]', 0) for I in range(len(activeRadiator_modules))]
#Fuel tanks temperature and skin temperature
tank_parts = [I.part for I in vessel.resources.all]
tank_temp = [Readout(tank_parts[I], '06', I, 'temperature', 0) for I in range(len(tank_parts))]
tank_skinTemp = [Readout(tank_parts[I], '08', I, 'skin_temperature', 0) for I in range(len(tank_parts))]
#Engine temperature
engine_parts = [I.part for I in vessel.parts.engines]
engine_temp = [Readout(engine_parts[I], '07', I, 'temperature', 0) for I in range(len(engine_parts))]
#Cabin temperature (assuming that the command is the root part, there's not many good ways to filter parts with crew)
cabin_temp = [Readout(vessel.parts.root, '09', 0, 'temperature', 0)]
#Total of all Readouts
readouts = tempSensors_temp + deployableRadiator_extended + activeRadiator_temp + activeRadiator_effi \
           + tank_temp + tank_skinTemp + engine_temp + cabin_temp
print(' Finished')



# === LOOP ===
print('\nLOOP BEGIN')
while True:
    #Getting inputs
    input = str(ser.readline())[2:-5].split(';')[0]
    if input:
        print('INPUT:', input)
        if input.startswith('togRad'): #Toggle deployable radiator
            print('TOGGLING RADIATOR')
            targetModule = deployableRadiator_modules[int(input[6:])] #Get specific radiator
            targetModule.trigger_event(targetModule.events[0]) #Trigger the only event
            sleep(2) #Wait for animation
        if input.startswith('resend'):
            for I in readouts:
                I.update(True)
    #Outputting any new info
    for I in readouts:
        I.update()
