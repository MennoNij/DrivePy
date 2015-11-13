import math
import os
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
from model import obj, geometric

import globals
import helpers
###############################
#
# Traffic: other cars on the road
#
##############################
class CarNode(object):

    def __init__(self, id, x, z, heading, xh, zh, color):
        self.id = id
        self.x = x
        self.z = z
        self.heading = heading
        self.xH = xh
        self.zH = zh
        self.speed = 0.0
        self.color = color
        self.relativePassPoint = 0.0
        self.passState = globals.PASS_BEHIND_CAR
        self.beingOvertaken = False
        self.passTime = 0.0
        self.inProxTime = -1.0
        self.speedingAway = False

        self.decided = False
        self.kind = 'none'
        self.zOff = 0.0

    def update(self, x, z, heading, xh, zh):
        self.x = x
        self.z = z
        self.heading = heading
        self.xH = xh
        self.zH = zh

class DynamicCar(object):
    def __init__(self, relativeDist, chance, minroom, gendist, jitter):
        self.distanceFactor = relativeDist
        self.genChance = chance
        self.jitterFactor = jitter
        self.minRoom = minroom
        self.generateDistance = gendist

class Traffic(object):
    def __init__(self, road):

        self.road = road

        objfile = os.path.join(os.path.split(__file__)[0], 'cars/mustang.obj')
        #self.mustang = obj.OBJ(objfile)
        self.mustang = obj.OBJ('cars/mustang.obj')
        self.cars = [obj.OBJ('cars/mustang.obj'), obj.OBJ('cars/mustang-y.obj'), obj.OBJ('cars/mustang-r.obj'), obj.OBJ('cars/mustang-g.obj')]

        self.staticCars = []
        self.tStaticCars = []
        self.staticLane =  globals.RIGHT_LANE
        self.beingOvertaken = []
        self.beenOvertaken = []

        self.recentPassedCar = -1
        self.staticSpeed = helpers.kphToMps(10.0)
        self.staticInterval = 150.0

        self.numFastCars = 0
        self.fastCars = []
        self.tFastCars = []
        self.fastCar1 = []
        self.fastCar2 = []

        self.dynamicCarTypes = []

        self.waitingForLaneTransition = False
        self.waitingForLaneTransTime = 0.0

    def reset(self, road):
        self.numFastCars = 0
        self.recentPassedCar = -1
        self.staticCars = []
        self.tStaticCars = []
        self.beingOvertaken = []
        self.beenOvertaken = []
        self.fastCars = []
        self.tFastCars = []
        self.fastCar1 = []
        self.fastCar2 = []

        self.waitingForLaneTransition = False
        self.waitingForLaneTransTime = 0.0

        self.road = road

    def genStaticCars(self, numCars, expectedSpeed, staticSpeed, duration, lane=globals.RIGHT_LANE):
        # determine number of cars to generate
        self.staticSpeed = staticSpeed
        self.staticLane = lane

        extra = 30

        sDiff = abs(expectedSpeed - staticSpeed)
        dist = sDiff * duration
        interval = dist / numCars
        self.staticInterval = interval
        if globals.debug: print 'Interval between cars: '+str(interval)

        #speedLimit = EXPECTED_SPEED
        roadLen = self.road.pathLength
        #duration = roadLen / speedLimit

        traveled = self.staticSpeed * duration
        rMax = roadLen - traveled
        #numCars = abs(int(math.ceil(rMax / self.staticInterval)))

        offset = 0.0
        if lane == globals.LEFT_LANE:
            offset = duration*expectedSpeed - duration*staticSpeed#-(numCars*interval)

        #print offset
        # DEBUG CAR
        #(xl, zl, heading, hx, hz) = self.road.getLanePosition(10.0, self.staticLane)
        #self.staticCars.append(CarNode(0, xl, zl, heading, hx, hz, 1))
        #self.tStaticCars.append(xl)

        # make sure 50% of trials has a critical and a non-critical fast car
        fastNum = int(math.ceil((numCars+extra)*0.5))
        self.fastCars1 = [1]*fastNum + [0]*((numCars+extra)-fastNum)
        self.fastCars2 = [1]*fastNum + [0]*((numCars+extra)-fastNum)
        self.fastCars3 = [1]*fastNum + [0]*((numCars+extra)-fastNum)
        self.fastCars4 = [1]*fastNum + [0]*((numCars+extra)-fastNum)
        self.fastCars5 = [1]*fastNum + [0]*((numCars+extra)-fastNum)
        self.fastCars6 = [1]*fastNum + [0]*((numCars+extra)-fastNum)
        random.shuffle(self.fastCars1)
        random.shuffle(self.fastCars2)
        random.shuffle(self.fastCars3)
        random.shuffle(self.fastCars4)
        random.shuffle(self.fastCars5)
        random.shuffle(self.fastCars6)

        #print self.fastCars1


        for i in xrange(1,numCars+extra): # add a few just in case
            jitter = random.uniform(-self.staticInterval*0.25, self.staticInterval*0.25)
            x = offset + self.staticInterval*i + jitter
            #print x
            (xl, zl, heading, hx, hz) = self.road.getLanePosition(x, self.staticLane)
            self.staticCars.append(CarNode(i, xl, zl, heading, hx, hz, random.randint(0,3)))
            self.staticCars[-1].speed = self.staticSpeed
            self.tStaticCars.append(xl)


    def updateStaticCars(self, car, dt):
        # update position of all slow cars
        for i in xrange(0, len(self.staticCars)):
            x = self.tStaticCars[i]

            # check if driver is close, possibly change speed
            diff =  x - (-car.xPos)
            if self.staticCars[i].decided == False and diff < 30.0:
                self.staticCars[i].decided = True
                odds = random.random()
                if odds > 0.3333:
                    change = random.uniform(5.0, 15.0)
                    self.staticCars[i].speed -= helpers.kphToMps(change)
                    #print 'Static car decides to change speed to' +str(self.staticCars[i].speed)

            xnew = x+self.staticCars[i].speed*dt
            (xl, zl, heading, hx, hz) = self.road.getLanePosition(xnew, self.staticLane)
            self.tStaticCars[i] = xnew
            self.staticCars[i].update(xnew, zl, heading, hx, hz)

    def findNextStaticCar(self, car):
        i = bisect.bisect(self.tStaticCars, -car.xPos)

        if i >= len(self.tStaticCars):
            return (-1, 0.0)
        else:
            return (self.staticCars[i].id, self.staticCars[i].x)

    def reportNearbyStaticCars(self, car):
        iMin = bisect.bisect(self.tStaticCars, -car.xPos - 25.0)
        iMax = bisect.bisect(self.tStaticCars, -car.xPos + 25.0)

        speed = (self.staticSpeed * 3600) * 0.001
        for i in xrange(iMin, iMax):
            s = self.staticCars[i]

            globals.db['slowcars'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'id', s.id, 'type', 'slow',
                                    'speed', r3(speed), 'xposition', r3(s.x), 'distance', r3(s.x-(-car.xPos)), 'block', globals.flow.block,
                                    'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)

    def foundFastCollisions(self, car):
        if not car.inSafeZone:
            mW = self.mustang.maxX
            mH = self.mustang.maxZ

            for i, c in enumerate(self.fastCars):
                (collFound, zone) = helpers.determineCollision(c.x, c.z, c.xH, c.zH,
                                                      -car.xPos, -car.zPos, car.xHeading, car.zHeading, mW, mH, 1.9)
                if collFound:
                    return (i, self.fastCars[i].id, zone)

        return (-1, -1, -1)

    def foundSlowCollisions(self, car):
        mW = self.mustang.maxX
        mH = self.mustang.maxZ

        iMin = bisect.bisect(self.tStaticCars, -car.xPos - 20.0)
        iMax = bisect.bisect(self.tStaticCars, -car.xPos + 20.0)

        for i in xrange(iMin, iMax):
            s = self.staticCars[i]
            (collFound, zone) = helpers.determineCollision(s.x, s.z, s.xH, s.zH,
                                                  -car.xPos, -car.zPos, car.xHeading, car.zHeading, mW, mH, 1.1)
            if collFound:
                return (i, s.id, zone)

        return (-1, -1, -1)

    def calcPassingStates(self, car):
        iMin = bisect.bisect(self.tStaticCars, -car.xPos - 20.0)
        iMax = bisect.bisect(self.tStaticCars, -car.xPos + 20.0)

        for i in xrange(iMin, iMax):

            if self.waitingForLaneTransition: # don't generate new cars until the particpant is back on the right lane
                if car.getRoadPosition() < 0.0 or helpers.conditionTime() -  self.waitingForLaneTransTime > 10.0:
                    if car.getRoadPosition() < 0.0:
                        if globals.debug: print 'Participant returned to right lane after overtaking a car'
                    else:
                        if globals.debug: print 'Participant is sticking left too long, generating cars anyway'
                    self.waitingForLaneTransition = False

                    oldNews = [j for j,v in enumerate(self.beingOvertaken) if v > self.staticCars[i].id]
                    if len(oldNews) == 0: # participant has not started overtaking another car yet
                        #rand = random.random()
                        #if rand < 1.0 - NO_OVERTAKES_CHANCE:
                        if self.recentPassedCar+1 < len(self.staticCars):
                            try:
                                approxDist = self.staticCars[self.recentPassedCar+1].x - (-car.xPos)
                            except IndexError:
                                approxDist = -1
                            if globals.debug: print 'Distance to next car: '+str(approxDist)

                            #critRand = random.random()
                            #secRand = random.random()
                            #if secRand <= 0.50:
                            ad = approxDist
                            if approxDist > -1:
                                #if random.random() >= 0.5:
                                for dynCar in self.dynamicCarTypes:
                                    if random.random() <= dynCar.genChance and approxDist > dynCar.minRoom:
                                        self.genDynamicCar(dynCar.distanceFactor*approxDist + random.uniform(-dynCar.jitterFactor*ad, dynCar.jitterFactor*ad), dynCar.generateDistance)

                                # if self.recentPassedCar < len(self.fastCars3):
                                #     if self.fastCars3[self.recentPassedCar]:
                                #         self.genDynamicCar(0.9*ad + random.uniform(-0.05*ad, 0.05*ad), random.uniform(40.0, 41.0))
                                #
                                # #if random.random() >= 0.5:
                                # if self.recentPassedCar < len(self.fastCars4) and approxDist > 75.0:
                                #     if self.fastCars4[self.recentPassedCar]:
                                #         self.genDynamicCar(0.7*ad + random.uniform(-0.05*ad, 0.05*ad), random.uniform(60.0, 61.0))
                                #
                                #
                                # secLoc = 0.5*approxDist + random.uniform(-0.05*approxDist, 0.05*approxDist)
                                # if self.recentPassedCar < len(self.fastCars1):
                                #     if self.fastCars1[self.recentPassedCar]:
                                #         if approxDist > 20.0:
                                #             #print 'Non-critical fast car generated after overtaking ' + str(self.recentPassedCar)+' at '+str(secLoc)
                                #             self.genDynamicCar(secLoc, random.uniform(71.0, 85.0))
                                #
                                #if random.random() > 0.001 and approxDist > 80.0:
                                    #self.genDynamicCar(0.3*ad + random.uniform(-0.05*ad, 0.05*ad), random.uniform(100.0, 101.0))

                                #if random.random() >= 0.5 and overtakePoint * 3 < 0.3*ad:
                                # overtakePoint = car.getAvgOvertakePoint()
                                #
                                # if self.recentPassedCar < len(self.fastCars5) and approxDist > 75.0:
                                #     if self.fastCars5[self.recentPassedCar]:
                                #         self.genDynamicCar(overtakePoint*3, random.uniform(110.0, 111.0))
                                #
                                # if self.recentPassedCar < len(self.fastCars2):
                                #     if self.fastCars2[self.recentPassedCar]:
                                #         critLoc = overtakePoint
                                #         self.genDynamicCar(critLoc, random.uniform(135.0, 145.0))
                                #         if globals.debug: print 'Critical fast car generated after overtaking ' + str(self.recentPassedCar) + ', will overtake at distance '+str(critLoc)
                                #     #else:
                                #         #print 'Not generating any fast cars after overtaking ' + str(self.staticCars[i].id)
                                #
                                # # tailer
                                # #if random.random() >= 0.5:
                                # if self.recentPassedCar < len(self.fastCars6):
                                #     if self.fastCars6[self.recentPassedCar]:
                                #     #if 1:
                                #         if self.genDynamicCar(0.0, random.uniform(155.0, 161.0)):
                                #             if len(self.fastCars) > 0:
                                #                 self.fastCars[-1].kind = 'tailer'
                                #
            #print 'car '+str(i)
            oldState = self.staticCars[i].passState
            (state, dist) = self.determinePassingState(car,self.staticCars[i])
            if oldState < globals.PASS_COMPLETE:
                self.staticCars[i].passState = state

                if not self.staticCars[i].beingOvertaken:
                    if state == globals.PASS_ALONG_CAR and oldState == globals.PASS_BEHIND_CAR:
                        if globals.debug: print 'Starting overtake [slow car ID: ' + str(self.staticCars[i].id) +']'

                        self.staticCars[i].beingOvertaken = True
                        self.beingOvertaken.append(self.staticCars[i].id)
                        globals.db['overtake'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'state', 'start',
                                                'carNum', self.staticCars[i].id, 'carDist', car.laneCrossDist, 'block', globals.flow.block,
                                                'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)

                else:
                    if state == globals.PASS_INFRONT_CAR and dist > 2.0:
                        if globals.debug: print 'Finished overtake [slow car ID: ' + str(self.staticCars[i].id) +']'
                        globals.db['overtake'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'state', 'complete',
                                                'carNum', self.staticCars[i].id, 'carDist', car.laneCrossDist, 'block', globals.flow.block,
                                                'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)

                        self.staticCars[i].passState = globals.PASS_COMPLETE
                        self.beingOvertaken.remove(self.staticCars[i].id)
                        self.beenOvertaken.append(self.staticCars[i].id)
                        self.recentPassedCar = i
                        car.saveOvertakePoint()

                        self.fastCars = []
                        self.tFastCars = []

                        self.waitingForLaneTransition = True
                        self.waitingForLaneTransTime = helpers.conditionTime()

                    elif state == globals.PASS_BEHIND_CAR and dist < -9.0:

                        self.staticCars[i].beingOvertaken = False
                        globals.db['overtake'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'state', 'failed',
                                                'carNum', self.staticCars[i].id, 'carDist', car.laneCrossDist, 'block', globals.flow.block,
                                                'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)
                        if globals.debug: print 'Overtake incomplete [slow car ID: ' + str(self.staticCars[i].id) +']'

                    #print 'car '+str(i)+' state '+str(state)+' dist '+str(dist)

    def determinePassingState(self, car, sc):
        mH = self.mustang.maxZ

        # front of the car
        cx = -car.xPos + mH*car.xHeading
        cz = -car.zPos + mH*car.zHeading
        # back of the car
        dx = -car.xPos - mH*car.xHeading
        dz = -car.zPos - mH*car.zHeading

        # determine bounding planes of the slow car, tangent to heading
        # back of slow car
        b1x = sc.x - mH*sc.xH
        b1z = sc.z - mH*sc.zH
        b2x = b1x - sc.zH # perpendicular
        b2z = b1z + sc.xH

        bcDot = (b2x-b1x)*(cz-b1z) - (b2z-b1z)*(cx-b1x)
        bdDot = (b2x-b1x)*(dz-b1z) - (b2z-b1z)*(dx-b1x)

        #print 'SC -  car: ('+str(cx)+','+str(cz)+') A1: ('+str(a1x)+','+str(a1z)+') A2: ('+str(a2x)+','+str(a2z)+' dot: '+str(dot)

        # front of slow car
        a1x = sc.x + mH*sc.xH
        a1z = sc.z + mH*sc.zH
        a2x = a1x - sc.zH # perpendicular
        a2z = a1z + sc.xH

        acDot = (a2x-a1x)*(cz-a1z) - (a2z-a1z)*(cx-a1x)
        adDot = (a2x-a1x)*(dz-a1z) - (a2z-a1z)*(dx-a1x)

        #print 'SC -  car: ('+str(cx)+','+str(cz)+') B1: ('+str(a1x)+','+str(a1z)+') B2: ('+str(a2x)+','+str(a2z)+' dot: '+str(bDot)

        passState = globals.PASS_ALONG_CAR
        if acDot > 0 and bcDot > 0 and adDot > 0 and bdDot > 0:
            passState = globals.PASS_BEHIND_CAR
        elif acDot < 0 and bcDot < 0 and adDot < 0 and bdDot < 0:
            passState = globals.PASS_INFRONT_CAR

        return (passState, -adDot) #bDot = distance to the front of the slow car to back of own car

    def addDynamicCarType(self, relativeDist, genChance, minroom, gendist, jitterFactor):
        self.dynamicCarTypes = self.dynamicCarTypes + [DynamicCar(relativeDist, genChance, minroom, gendist, jitterFactor)]

    def genDynamicCar(self, relDist, distOff=25.0):
        if self.recentPassedCar+1 < len(self.staticCars) and self.recentPassedCar+1 > -1:

            mp = self.staticCars[self.recentPassedCar+1].x - relDist

            if mp > (-car.xPos+10.0): # there's enough distance to the next car for an overtaker

                x = -car.xPos - distOff
                (xl, zl, heading, hx, hz) = self.road.getLanePosition(x, globals.LEFT_LANE)
                self.fastCars.append(CarNode(self.numFastCars, xl, zl, heading, hx, hz, random.randint(0,3)))
                self.tFastCars.append(xl)

                self.numFastCars += 1

                self.fastCars[-1].relativePassPoint = relDist # distance before next slow car the pp should be passed

                if globals.debug: print ' [Generating fast car at '+str(x)+' (distance: '+str(distOff)+'). Expected overtake point at '+str(mp) +']'

                return True

        return False

    def updateFastCar(self, car, dt):
        for i, fc in enumerate(self.fastCars):
            if self.recentPassedCar+1 < len(self.staticCars):
                try:
                    mp = self.staticCars[self.recentPassedCar+1].x - fc.relativePassPoint
                except IndexError:
                    mp = -1

                if mp > -1:
                    d = fc.x - (-car.xPos)

                    if d > 100.0:
                        if globals.debug: print 'Removed fast car ' +str(i) + '(' + str(self.fastCars[i].id) + ')'
                        del self.fastCars[i]
                        del self.tFastCars[i]
                    else:
                        self.updateFastCarPosition(car, i, mp, dt)

    def updateFastCarPosition(self, car, idx, meetPoint, dt):
        xCar = -car.xPos
        sDiff = car.currentSpeed - self.staticSpeed # speed diff between next slow car and participant
        d = meetPoint - xCar # distance from participant to meetpoint
        xFast = self.fastCars[idx].x

        fDiff = xFast - xCar

        if not self.fastCars[idx].speedingAway:
            if self.fastCars[idx].kind == 'none' and fDiff > FAST_OVERTAKE_DISTANCE: # fast car is passing, ride off into the sunset!
                self.fastCars[idx].speedingAway = True
            elif self.fastCars[idx].kind == 'tailer' and fDiff > -2.0: # change speed
                self.fastCars[idx].speed *= 1 - (dt*0.2)
            elif self.fastCars[idx].kind == 'tailer' and d < 5.0: # change lane
                transSpeed = 2.5
                if self.fastCars[idx].zOff < 4.0:
                    self.fastCars[idx].zOff += transSpeed*dt
                self.fastCars[idx].speed *= 1 - (dt*0.2)
            elif d > 10.0: # recompute fast car speed for accuracy until its close enough to the participant

                ttx = d / sDiff # time to the meetpoint
                ep = xCar + (ttx * car.currentSpeed) # expected road position of the meetpoint

                dFast = ep - xFast # distance between the meetpoint and the fast car
                sf = dFast / ttx # fast car speed required to hit the meetpoint at the right moment
                #print 'car speed: '+str(globals.mpsToKph(sf))
                self.fastCars[idx].speed = sf
                #print 'ep: '+str(ep)+' ttx: '+str(ttx)+' dFast: '+str(dFast)+' sf: '+str(sf)

            #print 'mp: '+str(meetPoint)+' car.x: '+str(tc)+' fast.x: '+str(tf)+' dist: '+str(d)
            if self.fastCars[idx].inProxTime < 0.0:
                if fDiff > -8.0:
                    self.fastCars[idx].inProxTime = helpers.currentTime() # set the tailgaiting timer
                    if globals.debug: print '[starting tailgaiting timer]'
            else:
                if helpers.currentTime() - self.fastCars[idx].inProxTime > 5.0:
                    self.fastCars[idx].speedingAway = True
                    if globals.debug: print '[tailgaiting timer exceeded]'
        else:
            self.fastCars[idx].speed *= 1 + (dt*0.1)

        #self.fastCars[idx].speed = min(globals.kphToMps(140.0), self.fastCars[idx].speed)
        xnew = xFast + self.fastCars[idx].speed*dt
        if car.inSafeZone: # fastcar can't collide with participant
            #print 'xnew: '+str(xnew)+' xcar: '+str(xCar)
            xnew = min(xCar - 20.0, xnew)

        (xl, zl, heading, hx, hz) = self.road.getLanePosition(xnew, globals.LEFT_LANE)
        self.fastCars[idx].update(xnew, zl+self.fastCars[idx].zOff, heading, hx, hz)
        self.tFastCars[idx] = xnew

    def removeFastCar(self, idx):
        del self.fastCars[idx]
        del self.tFastCars[idx]

    def reportNearbyFastCars(self, car):
        iMin = bisect.bisect(self.tFastCars, -car.xPos - 25.0) # get plants close to the car
        iMax = bisect.bisect(self.tFastCars, -car.xPos + 25.0)

        for i in xrange(iMin, iMax):
            f = self.fastCars[i]

            speed = (f.speed * 3600) * 0.001
            globals.db['fastcars'].addData(['pp', globals.participant, 'condition', globals.flow.getCondition(), 'id', f.id, 'type', 'fast',
                                    'speed', r3(speed), 'xposition', r3(f.x), 'distance', r3(f.x-(-car.xPos)), 'block', globals.flow.block,
                                    'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)


    def draw(self, car):
        iMin = bisect.bisect(self.tStaticCars, -car.xPos - 40.0)
        iMax = bisect.bisect(self.tStaticCars, -car.xPos + 100.0)

        slow = self.staticCars[iMin:iMax] # this will always draw at least one car, but who cares

        for s in slow:
            glPushMatrix()
            glTranslatef(s.x, 0.0, s.z)
            glRotatef(-90.0,0.0,1.0,0.0) # rotate car model the correct way
            glRotatef(s.heading,0.0,1.0,0.0) # encorporate heading
            self.cars[s.color].draw()
            glPopMatrix()

        for s in self.fastCars:
            glPushMatrix()
            glTranslatef(s.x, 0.0, s.z)
            glRotatef(-90.0,0.0,1.0,0.0) # rotate car model the correct way
            glRotatef(s.heading,0.0,1.0,0.0) # encorporate heading
            self.cars[s.color].draw()
            glPopMatrix()
