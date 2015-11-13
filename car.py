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

###############################
#
# The car: position & physics
#
##############################

class Car(object):
    def __init__(self, traffic, road):
        self.road = road
        self.traffic = traffic

        # position of the car
        self.xPos = 0.0
        self.zPos = 0.0

        # current heading of the car
        self.xHeading = 1.0
        self.zHeading = 0.0
        self.angleHeading = 0.0

        # current velocity of the car
        self.xVelocity = globals.CARSTARTSPEED
        self.zVelocity = 0.0

        # current speed of the car
        self.xAccel = 0.0
        self.zAccel = 0.0

        self.accelerationInput = 0.0 # received input from the gas pedal
        self.accelerationFactor = 3.5 # 3.5 m/s^2 is a very average car. 1 unit = 1 meter

        self.breakInput = 0.0 # input received from the break pedal
        self.breakFactor = 0.01 # multiplier for breakInput
        self.breakPower = 0.0 # current breaking energy
        # break vector
        self.xBreak = 0.0
        self.zBreak = 0.0

        self.latFricFactor = 1.3 # friction at right angles to the direction of the car
        self.backFricFactor = 0.06 # friction from road/air
        self.currentSpeed = 0.0 # current speed in m/s
        self.currentWheelAngle = 0.0 # angle the front wheels are positioned at
        self.modelOffset = 0.25

        self.collisionCooldown = 0.0 # cooldown timer for car contact registration

        self.blinkerCooldown = 0.0 # cooldown until the bliner becomes available again
        self.lastBlinkerTime = 0.0 # last time blinker was used
        self.lastBlinkerDir = -1 # previously used blinker
        self.blinkerPracWarning = 0.0 # time the incorrect blinker use warning has been on screen

        self.prevRoadPos = 0.0 # previous position along the road
        self.laneCrossDist = 0.0
        self.overtakePoints = [globals.ESTIMATED_OVERTAKE_POINT, globals.ESTIMATED_OVERTAKE_POINT, globals.ESTIMATED_OVERTAKE_POINT] # initial guess of the distance to the next car when overtaking

        #self.rumblestrip = pyglet.media.Player()
        #bump = pyglet.media.load('bump.wav', streaming=False)
        #self.rumblestrip.queue(bump)

        self.rumblerTime = 0.0 # time since last bump of the rumbler strip was hit
        self.offroadTime = 0.0 # accumulated time the car has been off-road

        self.autoPilot = False#True # auto-pilot along the road at fixed speed
        self.inSafeZone = False # no other cars can hit the car if True

    # reset all the car values
    def reset(self, road):
        (x, z, heading, hx, hz) = road.getLanePosition(1.0, globals.RIGHT_LANE)
        self.xPos = x
        self.zPos = -z

        self.xHeading = hx
        self.zHeading = hz
        self.angleHeading = heading

        self.xVelocity = globals.CARSTARTSPEED
        self.zVelocity = 0.0
        self.xAccel = 0.0
        self.zAccel = 0.0

        self.breakInput = 0.0
        self.accelerationInput = 0.0
        self.activeBlinker = -1
        self.lastBlinkerTime = 0.0
        self.lastBlinkerDir = -1

        #self.rumblestrip = None

        self.rumblerTime = 0.0
        self.offroadTime = 0.0

        self.blinkerPracWarning = 0.0

        self.road = road

    def bindRoad(self, road):
        self.road = road

    def bindTraffic(self, traffic):
        self.traffic = traffic

    # set the camera to look out of the front window
    def look(self):
        yOff = self.rumble()

        glRotatef(90.0,0.0,1.0,0.0) # camera should point down the x-axis (default state)
        glTranslatef(0.15,0,0.2) # driver offset from the center of the vehicle
        glRotatef(-self.angleHeading,0.0,1.0,0.0) # encorporate heading
        glTranslatef(self.xPos,-0.93+yOff,self.zPos+0.0) # put camera in the driver seat


    # returns the amount of vertical motion induced by driving off-road
    def rumble(self):

        yOff = 0.0
        if self.isOffRoad():
            yOff = globals.noise.noise2(0, self.xPos)*0.03
        else:
            yOff = globals.noise.noise2(0, self.xPos)*0.001

        return yOff

    def saveOvertakePoint(self):
        self.overtakePoints.append(self.laneCrossDist)

    def getAvgOvertakePoint(self):
        last = self.overtakePoints[-3:]
        return (last[0]+last[1]+last[2]) / 3.0

    def isOffRoad(self):
        (xr, zr) = self.road.getSplineCenterpoint(-self.xPos)
        dist = zr - (-self.zPos)

        if abs(dist) > (self.road.r - 0.5):
            return True

        return False
        #print 'road:' + str(zr)+ ' car: ' + str(self.zPos)+' dist: '+str(dist)

    def incrementDamage(self):
        globals.bonusCounter =  max(0.0, globals.bonusCounter - globals.DAMAGE_PENALTY)

    def mirrorLook(self):
        glRotatef(-90.0,0.0,1.0,0.0) # camera should point down the x-axis (default state)
        glRotatef(self.angleHeading,0.0,1.0,0.0) # encorporate heading
        glTranslatef(self.xPos+2.0,-1.0,self.zPos)

    def powerSteer(self, angle):
        thresAngle = 40.0

        return min(1.0, (1/(thresAngle*thresAngle)) * angle*angle)

    def updateDrivingInput(self, dt):
        #global hasWheel, joystick
        self.accelerationInput = 0.0
        self.breakInput = 0.0

        if globals.hasWheel:
            self.steer(globals.joystick.x, dt, globals.DEVICE_WHEEL)
            #print globals.joystick.buttons
            if globals.joystick.y < 0: # accelerating
                self.accelerationInput = max(0.0, -globals.joystick.y)
            else:
                self.breakInput = globals.joystick.y

            if globals.joystick.buttons[globals.JOY_BLINK_LEFT]:
                if self.activeBlinker < 0:
                    self.setBlinker(globals.LEFT_BLINKER)

            if globals.joystick.buttons[globals.JOY_BLINK_RIGHT]:
                if self.activeBlinker < 0:
                    self.setBlinker(globals.RIGHT_BLINKER)

        if helpers.findKey('d') >= 0: # right turn
            self.steer(2, dt, globals.DEVICE_KEYBOARD)
        if helpers.findKey('a') >= 0: # left turn
            self.steer(-2, dt, globals.DEVICE_KEYBOARD)
        if helpers.findKey('w') >= 0: # accelerate
            self.accelerationInput = 1.0
        if helpers.findKey('s') >= 0: # break
            self.accelerationInput = 0.0
            self.breakInput = 1.0
        if helpers.findKey('q') >= 0: # left blinker
            if self.activeBlinker < 0:
                self.setBlinker(globals.LEFT_BLINKER)
        if helpers.findKey('e') >= 0: # right blinker
            if self.activeBlinker < 0:
                self.setBlinker(globals.RIGHT_BLINKER)

    def setBlinker(self, direction):
        global db

        self.activeBlinker = direction
        d = 'L'
        if (direction == globals.RIGHT_BLINKER):
            d = 'R'
        self.blinkerCooldown = 1.0

        self.lastBlinkerDir = d
        self.lastBlinkerTime = helpers.currentTime()

        blinkSound = pyglet.resource.media('blinker.wav')
        blinkSound.play()

        globals.db['blinker'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'direction', d, 'condtime', r3(helpers.conditionTime()),  'block', block,
                               'time', r3(helpers.currentTime())], True)

    def steer(self, steerAmount, dt, device):

        # some tweaks to make driving 'feel' better
        maxAngle = globals.TOTAL_STEERING_ANGLE*0.5
        if device == globals.DEVICE_KEYBOARD:
            maxAngle = 8

        self.currentWheelAngle = maxAngle*steerAmount

        power = self.powerSteer(self.currentWheelAngle)

        #print self.currentWheelAngle
        steeringAngle = self.currentWheelAngle*globals.STEERING_FACTOR
        steeringAngle = min(steeringAngle, 20.0)

        steeringAngle *= self.currentSpeed / (globals.MAX_SPEED) # prevent car from turning when standing still

        steeringAngle *= power

        #print 'WA: '+str(self.currentWheelAngle)+' SA: '+str(steeringAngle)+' PS: '+str(power)

        (nx, nz) = self.rotateY(self.xHeading, self.zHeading, steeringAngle)
        if device == globals.DEVICE_KEYBOARD:
            (nx, nz) = self.lerpVectors(self.xHeading, self.zHeading, nx, nz, dt)
        #print '('+str(nx)+','+str(nz)+')\n'

        # change in heading angle between default and current heading
        #self.angleHeading = (atan2(nx, nz) - atan2(1.0, 0.0))*RAD2DEG
        #self.angleHeading = math.degrees(atan2(0.7, 0.7) - atan2(1.0, 0.0))
        #print str(self.angleHeading)

        nl = sqrt((nx*nx) + (nz*nz))
        self.xHeading = nx/nl
        self.zHeading = nz/nl
        #self.updateAcceleration()

    def updateAcceleration(self):
        self.xAccel = self.xHeading * self.accelerationInput * self.accelerationFactor
        self.zAccel = self.zHeading * self.accelerationInput * self.accelerationFactor
        #self.xAccel = EXPECTED_SPEED

    def updateBreaking(self):
        self.xBreak = self.xHeading * self.breakInput * self.breakFactor
        self.zBreak = self.zHeading * self.breakInput * self.breakFactor
        self.breakPower = 1 - (self.breakInput * self.breakFactor)

    def updatePosition(self, dt):

        if self.autoPilot:
            x = self.xPos
            xnew = x-globals.kphToMps(90.0)*dt
            (xl, zl, heading, hx, hz) = self.road.getLanePosition(xnew, globals.LEFT_LANE)
            self.xPos = xnew
            self.zPos = zl
            self.xHeading = hx
            self.zHeading = hz
        else:
            self.prevRoadPos = self.getRoadPosition() #self.zPos
            roadPos = self.prevRoadPos

            self.updateAcceleration()
            self.updateBreaking()

            self.collisionCooldown = max(0.0, self.collisionCooldown - dt)
            self.blinkerCooldown = max(0.0, self.blinkerCooldown - dt)
            self.blinkerPracWarning = max(0.0, self.blinkerPracWarning - dt)

            self.traffic.calcPassingStates(self)

            # Hit a fast moving car (left lane)
            (idx, collisionId, collisionZone) = self.traffic.foundFastCollisions(self)
            if collisionId >= 0:

                if self.collisionCooldown < 0.001:
                    self.collisionCooldown = 1.0

                    self.traffic.removeFastCar(idx)

                    self.incrementDamage()
                    globals.db['collision'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'zone', collisionZone, 'carType', 'fast',  'block', block,
                                        'carNum', collisionId ,'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)

                    if globals.debug: print 'Collision detected with fast car ['+str(idx)+', zone: '+str(collisionZone)+']'

            # hit a slow moving car (right lane)
            (idx, collisionId, collisionZone) = self.traffic.foundSlowCollisions(self)
            if collisionId >= 0:

                if collisionZone == FRONT:

                    mul = 0.9
                    self.xVelocity = min(self.xVelocity*mul, self.traffic.staticSpeed*mul)
                    self.zVelocity = min(self.zVelocity*mul, self.traffic.staticSpeed*mul)

                else: # BACK
                    bumpspeed = self.traffic.staticSpeed
                    ratio = bumpspeed / self.currentSpeed
                    self.xVelocity *= ratio*1.2
                    self.zVelocity *= ratio*1.2

                    self.currentSpeed = self.lenVector(self.xVelocity, self.zVelocity)
                    self.xPos -= self.xVelocity*dt
                    self.zPos -= self.zVelocity*dt

                if self.collisionCooldown < 0.001:
                    #print 'boem! '+str(collisionZone)
                    self.collisionCooldown = 1.0
                    self.incrementDamage()
                    globals.db['collision'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'zone', collisionZone, 'carType', 'slow',  'block', block,
                                        'carNum', collisionId ,'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)

                    if globals.debug: print 'Collision detected with slow car ['+str(idx)+', zone: '+str(collisionZone)+']'

                roadPos = self.getRoadPosition()

            else:
                dotProd = sum(map( operator.mul, (self.xHeading, self.zHeading), (self.xVelocity, self.zVelocity)))
                #print dotProd
                xLatVel = self.xHeading * dotProd
                zLatVel = self.zHeading * dotProd

                xLatFric = 0#-xLatVel*self.latFricFactor
                zLatFric = 0#-zLatVel*self.latFricFactor
                xBackFric = -self.xVelocity*self.backFricFactor
                zBackFric = -self.zVelocity*self.backFricFactor

                #print xLatFric
                self.xVelocity += (xBackFric + xLatFric) * dt
                self.zVelocity += (zBackFric + zLatFric) * dt

                #print self.xVelocity

                dm = self.currentSpeed*dt
                self.currentSpeed = self.lenVector(self.xVelocity, self.zVelocity)
                if self.currentSpeed < globals.MAX_SPEED:
                    self.xVelocity += self.xAccel * dt
                    self.zVelocity += self.zAccel * dt
                    self.xVelocity *= self.breakPower
                    self.zVelocity *= self.breakPower
                    #self.xVelocity = max(0.0001*self.xVelocity, self.xVelocity - self.xBreak * dt)
                    #self.zVelocity = max(0.0001*self.zVelocity, self.zVelocity - self.zBreak * dt)

                self.xPos -= self.xVelocity*dt
                self.zPos -= self.zVelocity*dt
                #self.xPos -= self.xHeading*dm
                #self.zPos -= self.zHeading*dm

                vHx = self.currentSpeed*self.xHeading
                vHz = self.currentSpeed*self.zHeading

                latFactor = 0.2
                (x,z) = self.lerpVectors(vHx, vHz, self.xVelocity, self.zVelocity, latFactor)
                self.xVelocity = x
                self.zVelocity  = z

                self.angleHeading = (atan2(self.xVelocity, self.zVelocity) - atan2(1.0, 0.0))*globals.RAD2DEG

                roadPos = self.getRoadPosition()

            if self.prevRoadPos <= 0.0 and roadPos > 0.0: # left lane transition
                if globals.flow.drivingCondition == 'complex':
                    (cid, x) = self.traffic.findNextStaticCar(self)
                    dist = x - (-self.xPos)

                    self.laneCrossDist = dist

                    if globals.debug: print 'Lane transition to left lane at ' + str(-self.xPos) + '. Distance to next static car ('+str(cid)+'): '+str(dist)
                else:
                    if globals.debug: print 'Lane transition to left lane at ' + str(-self.xPos)

                self.checkBlinkerUse('L')

            elif self.prevRoadPos >= 0.0 and roadPos < 0.0: #right lane transition
                if globals.debug: print 'Lane transition to right lane at ' + str(-self.xPos)

                self.checkBlinkerUse('R')

        self.testRumbleStrip()

        if self.isOffRoad():
            self.offroadTime += dt

        if self.offroadTime >= 1.0:
            globals.bonusCounter = max(0.0, globals.bonusCounter - globals.OFFROAD_PENALTY)
            self.offroadTime = 0.0

        # See if we're next to a car we're overtaking
        self.inSafeZone = False
        if self.traffic.recentPassedCar+1 < len(self.traffic.staticCars):
            try:
                nextx = self.traffic.staticCars[self.traffic.recentPassedCar+1].x
            except IndexError:
                nextx = -1

            if nextx > 0.0:
                #print 'next: '+str(nextx)+' car: '+str(self.xPos)
                d = abs(nextx - -self.xPos)
                #print 'distance to next car: '+str(d)
                if (d < 6.0 and self.prevRoadPos > 0.1) or d < -1.0:
                    #print 'safe!'
                    self.inSafeZone = True

    def testRumbleStrip(self):
        cW = self.traffic.mustang.maxX
        pos = self.getRoadPosition()

        if (pos+cW*0.6 > 0 and pos+cW*0.3 < 0) or (pos-cW*0.6 < 0 and pos-cW*0.3 > 0):
            #print 'rumble'
            if helpers.conditionTime() - self.rumblerTime > 0.2:
                rumbler = pyglet.resource.media('bump.wav')
                rumbler.play()

                self.rumblerTime = helpers.conditionTime()

            #if not self.rumblestrip.playing:
                #self.rumblestrip.play()


    def checkBlinkerUse(self, cardir):
        curtime = helpers.currentTime()
        if curtime - self.lastBlinkerTime > globals.MAX_TRANSITION_LAG_TIME:
            if globals.debug: print 'No blinker was used during a lane transition'
            if doPractice and block < 2:
                self.blinkerPracWarning = 1.5

            globals.bonusCounter = max(0.0, globals.bonusCounter - globals.BLINKER_PENALTY)
            globals.db['lanetransition'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'blinkerused', '0', 'blinkdir', '?', 'block', globals.flow.block,
                                'cardir', cardir, 'congruent', '0', 'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)
        else:
            if (cardir == 'L' and self.lastBlinkerDir == 'L') or (cardir == 'R' and self.lastBlinkerDir == 'R'):
                globals.db['lanetransition'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'blinkerused', '1', 'blinkdir', self.lastBlinkerDir, 'block', globals.flow.block,
                                'cardir', cardir, 'congruent', '1', 'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)
                if globals.debug: print 'Correct use of blinker during lane transition'
            else:
                globals.db['lanetransition'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'blinkerused', '1', 'blinkdir', self.lastBlinkerDir, 'block', globals.flow.block,
                                'cardir', cardir, 'congruent', '0', 'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)
                if globals.debug: print 'Incorrect use of blinker during lane transition'
                globals.bonusCounter -= BLINKER_PENALTY



    def getLaneDeviation(self):
        centerDist = self.road.getCenterDeviation(self.xPos, self.zPos)

        dist = centerDist + self.road.r*0.5
        return dist

    def getRoadPosition(self):
        return self.road.getCenterDeviation(self.xPos, self.zPos)

    def rotateY(self, x, z, angle):
        theta = math.radians(angle)

        cs = cos(theta)
        sn = sin(theta)

        nx = x * cs - z * sn
        nz = x * sn + z * cs

        return (nx, nz)

    def lerpVectors(self, x1, z1, x2, z2, dt):
        (nx, nz) = helpers.lerp(x1, z1, x2, z2, dt)

        return (nx, nz)

    def lenVector(self, x, z):
        return sqrt((x*x) + (z*z))

    def keyPressed(self, symbol, modifiers):

        if symbol == key.W:
            helpers.pressedKeys.append('w')
        if symbol == key.A:
            helpers.pressedKeys.append('a')
        if symbol == key.D:
            helpers.pressedKeys.append('d')
        if symbol == key.S:
            helpers.pressedKeys.append('s')
        if symbol == key.Q:
            helpers.pressedKeys.append('q')
        if symbol == key.E:
            helpers.pressedKeys.append('e')
        if symbol == key._1:
            helpers.pressedKeys.append('1')
        if symbol == key._2:
            helpers.pressedKeys.append('2')
        if symbol == key._3:
            helpers.pressedKeys.append('3')
        if symbol == key.SPACE:
            helpers.pressedKeys.append('space')

    def keyReleased(self, symbol, modifiers):

        if symbol == key.W:
            helpers.pressedKeys.remove('w')
        if symbol == key.A:
            helpers.pressedKeys.remove('a')
        if symbol == key.D:
            helpers.pressedKeys.remove('d')
        if symbol == key.S:
            helpers.pressedKeys.remove('s')
        if symbol == key.Q:
            helpers.pressedKeys.remove('q')
        if symbol == key.E:
            helpers.pressedKeys.remove('e')
        if symbol == key._1:
            helpers.pressedKeys.remove('1')
        if symbol == key._2:
            helpers.pressedKeys.remove('2')
        if symbol == key._3:
            helpers.pressedKeys.remove('3')
        if symbol == key.SPACE:
            helpers.pressedKeys.remove('space')
