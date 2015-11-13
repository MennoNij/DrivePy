# The MIT License (MIT)
#
# Copyright (c) 2015 Menno Nijboer
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# GETTING IT RUNNING:
# Install pyglet 1.2:
# Go into the pyglet install folder
# Open a terminal window
# Do: python setup.py install

# install AVbin from AVbin10.pkg (for OSX)

# Running the program:
# drive.py -p <participantID> -c <simple|complex> -o <fixed|random|cond1,cond2,cond3,cond4> -t <yes|no> -b [1..4] -s [0.0...10.0]#

import os
import math
import operator
import ctypes
import pyglet
import random
import bisect
import time
import sys, getopt
import itertools

from math import cos, pi, sin, sqrt, atan2

from pyglet.gl import *
from pyglet import image
from pyglet.window import key

import globals
import helpers
from helpers import r3

from renderer import Renderer
from traffic import Traffic
from car import Car
from road import Road
from textscreen import TextScreen
from datacollector import DataCollector
from flow import FlowEl
from radiotask import Radio
from tablettask import Tablet
import perlin
from model import obj, geometric

windowHeight = 1024
windowWidth = 786

# Setup screen display based on current screen size
renderer = Renderer()
renderer.setScreenSize(windowWidth, windowHeight)
globals.flow.resizeSecondaryTasks(windowWidth, windowHeight)

try:
    # Try and create a window with multisampling (antialiasing)
    config = Config(depth_size=16, double_buffer=True,vsync=False)
    window = pyglet.window.Window(resizable=True, config=config)
except pyglet.window.NoSuchConfigException:
    # Fall back to no multisampling for old hardware
    window = pyglet.window.Window(resizable=True)


# DEFINE THE TEXT SCREENS

renderer.addTextScreen('introduction', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
In dit experiment ga je een roadtrip maken!<br><br>
<img src="img/roadtrip.jpg" /><br><br>
Je zal in deze auto simulator met een authentieke Mustang door de Noord Amerikaanse Mojave desert rijden.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('instruct', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
Je kunt de auto besturen met het stuur, en de pedalen onder de tafel. Het linker pedaal is de rem, het rechter de
gas. Aan de achterkant van het stuur zitten twee grote knoppen die je naar je toe kan klikken: dit zijn de linker en
rechter richtingaanwijzers, waarmee je aangeeft wanneer je van rijbaan wisselt.<br><br>
<img src="img/racewheel-info.jpg" /><br><br>
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('instruct2', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
Het is de bedoeling dat je een snelheid van 80 km/u aanhoud, zoveel mogelijk rechts rijdt,
en richting aangeeft bij het inhalen. <br><br>Rij veilig, maar niet te langzaam, dan duurt het experiment langer.
Houd verder een veilige afstand tot andere auto's: gebruik bijvoorbeeld de 2 seconden regel.<br>
<img src="img/rules-info.jpg" /><br><br>
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('secondary', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
Soms zal de radio aanstaan: we hebben een interessante talk show uitgekozen om naar te luisteren.<br><br>
Er kunnen vragen gesteld worden over deze show. Deze vragen zijn multiple-choice, en je kunt de knoppen op de rechterkant van het
stuur gebruiken om een keuze te maken. Van boven naar beneden zijn de keuzes A, B, en C.<br><br><img src="img/racewheel-info.jpg" /><br>
Na het voorleggen van de antwoorden zal de vraag herhaald worden: je kunt dan al antwoord geven als je wilt.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('secondary2', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
Daarnaast kan het zijn dat je een interview moet volgen op de tablet. Het beantwoorden van de
multiple choce vragen zal hetzelfde zijn als tijdens het radio luisteren. Net als bij de radio show zal het juist beantwoorden
van vragen bonus punten opleveren, die zorgen voor een hogere uitbetaling.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('damage', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
Het is mogelijk extra geld te verdienen door middel van bonus punten.<br>
Je begint al met een aantal punten: elke keer als je een andere auto raakt zal hier 2 punten van worden afgetrokken.<br>
Daarnaast kost het vergeten de richtingaanwijzers te gebruiken 1.5 punt.<br>
Elke seconde dat je naast de weg rijdt kost 1 punt.<br><br>
Het is mogelijk om punten te verdienen met de multiple choice vragen die je soms zal krijgen (1 punt per vraag).<br><br>
Aan het eind van de studie wordt het aantal bonus punten omgerekend tot een geld bedrag wat je bovenop het basis bedrag krijgt.<br>
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('practice', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
Eerst zal er een korte oefensessie plaatsvinden om gewend te raken aan het rijden.<br>
Zoals je zal merken zijn de strepen op de weg verhoogd, waardoor ze geluid maken als je er overheen rijdt.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('secondpractice', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+2>
Nu volgt een tweede oefensessie, waarbij je ook vragen over de tablet tekst moet beantwoorden.<br>
Het juist beantwoorden van een vraag leverd 1 bonus punt op.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('waiting', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
De omgeving wordt gegenereerd, een ogenblik geduld.
</font>
</center>
''')

renderer.addTextScreen('none_pause', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Neem een korte pauze voordat je doorgaat.<br>In het komende blok van 30 minuten is er geen radio.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('completed1', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Je hebt blok 1 van de 4 voltooid.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('completed2', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Je hebt blok 2 van de 4 voltooid.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('completed3', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Je hebt blok 3 van de 4 voltooid.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('easy_pause', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Neem een korte pauze voordat je doorgaat.<br>In het komende blok van 30 minuten hoef je <b>geen</b> vragen over de
radio te beantwoorden.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('hard_pause', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Neem een korte pauze voordat je doorgaat.<br>In het komende block van 30 minuten krijg je vragen over de radio.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('tablet_pause', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Neem een korte pauze voordat je doorgaat.<br>In het komende block van 30 minuten krijg je vragen over de tabet tekst.
<br><br>Druk op spatie om door te gaan.
</font>
</center>
''')

renderer.addTextScreen('startrealexp', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Je hebt de trainingsessie voltooid. Nu zal het echte experiment beginnen. Jouw bonuspunten worden eenmalig gereset!<br><br>
Druk op spatie om door te gaan.
</font>
</center>
''')

#You can notify the experimenter that you are done.
renderer.addTextScreen('conclusion', '''
<center>
<font color="#FFFFFF" face="Helvetica,Arial" size=+3>
Bedankt voor het meewerken aan deze studie!<br>
Je kunt aangeven bij de aanwezige begeleider dat je klaar bent.<br><br>
In deze studie willen we kijken onder welke omstandigheden afleiding en positief effect danwel een negatief effect kan
hebben op de rijprestatie. Wij verwachten dat afleiding de rijprestatie verbeterd wanneer het rijden heel saai is, maar
problemen kan opleveren wanneer de verkeersituatie ingewikkeld is.
</font>
</center>
''')


###############################
#
# The window and main loop
#
##############################

@window.event
def on_resize(width, height):
    global windowWidth, windowHeight, renderer
    windowWidth = width
    windowHeight = height

    renderer.setScreenSize(windowWidth, windowHeight)

    return pyglet.event.EVENT_HANDLED

# The main loop function, called by pyglet
def update(dt):
    global window, renderer
    global car, traffic
    #global hasWHeel, joystick

    if globals.flow.getScreenType() == 'screen':
        if globals.flow.isTextScreenDone(renderer):
            globals.flow.endState(car, traffic, renderer, window)
    elif globals.flow.getScreenType() == 'drive':
        if helpers.conditionTime() <= globals.flow.blockDuration:
            traffic.updateStaticCars(car, dt)
            traffic.updateFastCar(car, dt)
            car.updateDrivingInput(dt)
            car.updatePosition(dt)

            globals.flow.secondary.update(dt)
            globals.flow.secondary.checkInput()
        else:
            globals.flow.endState(car, traffic, renderer, window)

pyglet.clock.schedule(update)

@window.event
def on_close():
    global renderer

    globals.flow.secondary.stopTask()
    renderer.cleanup()

    finalbonus = globals.bonusCounter
    if globals.flow.drivingCondition == 'complex':
        finalbonus = min(globals.MAX_BONUS, finalbonus + globals.HARD_BONUS_OFFSET)

    finalbonus /= 10.0

    print 'Final payout: '+str(round(20.0+finalbonus,2))
    print 'Closing program'

@window.event
def on_draw():
    global renderer, traffic, car

    if globals.flow.getScreenType() == 'screen':
        renderer.drawText()

    elif globals.flow.getScreenType() == 'drive':
        renderer.drawSim(traffic.road, car, traffic, globals.flow.secondary)

def measureContinuousData(dt):
    global car, traffic

    globals.flow.measureData(car, traffic, dt)

pyglet.clock.schedule_interval(measureContinuousData, 0.01) # fastest rate seems around 33Hz

@window.event
def on_key_press(symbol, modifiers):
    global car

    car.keyPressed(symbol, modifiers)

@window.event
def on_key_release(symbol, modifiers):
    global car

    car.keyReleased(symbol, modifiers)

def main(argv):
    global renderer, car, traffic

    try:
        opts, args = getopt.getopt(argv,"p:c:o:t:w:b:s:",["pp=","cond=","order=","train=","block=","score="])
    except getopt.GetoptError:
        print 'Usage: drive.py -p <participantID> -c <simple|complex> -o <fixed|random|cond1,cond2,cond3> -t <yes|no> -b [1..4] -s [0.0...10.0]'
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-p", "--pp"):
            globals.participant = arg
        elif opt in ("-c", "--cond"):
            globals.flow.drivingCondition = arg
        elif opt in ("-o", "--order"):
            if arg == 'random':
                globals.flow.randomizeConditions()
            elif arg == 'fixed':
                ppid = globals.participant.split('D') # names have the form SDXX or CDXX with XX between 01 and 24

                ppidx = 1
                if len(ppid) > 1:
                    ppidx = int(ppid[1])
                ppidx = (ppidx % 24) - 1

                globals.flow.pickConditionPerm(ppidx)

                if ppid[0][0] == 'S':
                    print 'simple!'
                    globals.flow.drivingCondition = 'simple'
                elif ppid[0][0] == 'C':
                    print 'hard!'
                    globals.flow.drivingCondition = 'complex'
            else:
                secondOrder = arg.split(',')
            print 'Set condition order: '+globals.flow.secondOrder[0][0]+', '+globals.flow.secondOrder[1][0]+', '+globals.flow.secondOrder[2][0]+ ', '+globals.flow.secondOrder[3][0]
        elif opt in ("-t", "--train"):
            if arg == 'no':
                globals.flow.doPractice = False
            else:
                globals.flow.doPractice = True
        elif opt in ("-b", "--block"):
            globals.flow.block = int(arg)

        elif opt in ("-s", "--score"):
            globals.bonusCounter = float(arg)*10.0

    # INITIALIZE EXPERIMENT
    renderer.loadTextures()
    renderer.setup()
    renderer.mirrorSetup()

    road = Road()
    traffic = Traffic(road)
    car = Car(traffic, road)

    globals.flow.setConditions()
    globals.flow.preloadData()
    globals.flow.startNextState(car, traffic, renderer)

    pyglet.app.run()

if __name__ == "__main__":
    main(sys.argv[1:])
