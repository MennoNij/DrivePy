import itertools
import random

from radiotask import Radio
from tablettask import Tablet
from road import Road
from datacollector import DataCollector

import globals
import helpers
from helpers import r3

###############################
#
# The flow: experiment logic and current state
#
##############################

class FlowEl(object):

    def __init__(self, type, id, dur=0.0, secondary='none'):
        self.type = type
        self.id = id
        self.secondary = secondary
        self.duration = dur

class Flow(object):

    def __init__(self):

        # ID of the current driving condition, defaults to 'simple'
        self.drivingCondition = 'simple'
        # Contains the order of conditions and screens in the experiment
        self.flow = []
        # The currently active condition or screen
        self.flowIdx = 0
        # Order of the available secondary tasks
        self.secondOrder = ['tablet', 'none', 'easy', 'hard']
        # Current experimental block, defaults to -1
        self.block = -1
        # Duration in seconds of a block
        self.blockDuration = 0.0
        # If True, then a predefined order based on the participant ID is used
        self.fixedOrder = False
        # All permutations of the conditions
        self.conditionPerms = list(itertools.permutations(range(0, len(self.secondOrder))))
        # If True, practice blocks are placed before the main experimental blocks
        self.doPractice = True

        # available tasks
        self.radioTask = Radio()
        self.tabletTask = Tablet()
        self.shows = [1, 2] # the shows for radio/tablet with questions, probably needs a better place to be defined

        # Currently active secondary task
        self.secondary = self.radioTask
        self.roads = []

    def setConditions(self):
        # set the flow of the experiment
        self.flow = []
        print 'Setting up experiment flow'

        if self.block < 0:
            print 'Added Instructions'
            # globals.flow = globals.flow + [FlowEl('screen', 'introduction'), FlowEl('screen','instruct'), FlowEl('screen', 'instruct2'),
            #         FlowEl('screen', 'secondary'), FlowEl('screen', 'secondary2')]
            self.flow = self.flow + [FlowEl('screen', 'introduction')]

            if self.doPractice:
                print 'Added Practice Blocks'
                self.flow = self.flow + [FlowEl('screen', 'practice'), FlowEl('drive', 'none', globals.PRACTICE_DURATION, 'none'),
                                FlowEl('screen', 'secondpractice'), FlowEl('drive', 'complex', globals.PRACTICE_DURATION, 'tablet')]
                self.radioTask.doPractice = True
                self.tabletTask.doPractice = True
            else:
                self.block = 1

        if self.block < 2:
            self.flow = self.flow + [FlowEl('screen', self.secondOrder[0]+'_pause'),
                     FlowEl('drive', self.drivingCondition, globals.DRIVE_DURATION, self.secondOrder[0])]
            print 'Added Block 1'

        if self.block < 3:
            self.flow = self.flow + [FlowEl('screen', 'completed1'), FlowEl('screen', self.secondOrder[1]+'_pause'),
                     FlowEl('drive', self.drivingCondition, globals.DRIVE_DURATION, self.secondOrder[1])]
            print 'Added Block 2'

        if self.block < 4:
            self.flow = self.flow + [FlowEl('screen', 'completed2'), FlowEl('screen', self.secondOrder[2]+'_pause'),
                     FlowEl('drive', self.drivingCondition, globals.DRIVE_DURATION, self.secondOrder[2])]
            print 'Added Block 3'

        if self.block < 5:
            self.flow = self.flow + [FlowEl('screen', 'completed3'), FlowEl('screen', self.secondOrder[3]+'_pause'),
                     FlowEl('drive', self.drivingCondition, globals.DRIVE_DURATION, self.secondOrder[3]),
                     FlowEl('screen','conclusion')]
            print 'Added Block 4'

        self.secondary.roadCond = self.drivingCondition

    def getCondition(self):
        if self.doPractice and self.block < 2:
            return 'prac_' + self.flow[self.flowIdx].id + '_' + self.flow[self.flowIdx].secondary
        else:
            return self.flow[self.flowIdx].id + '_' + self.flow[self.flowIdx].secondary

    def startNextState(self, car, traffic, renderer):

        state = self.flow[self.flowIdx]

        if state.type == 'screen':
            renderer.textScreens[self.flow[self.flowIdx].id].start()

        elif state.type == 'drive':
            self.block += 1
            self.blockDuration = state.duration

            # reset damage counter after practice
            if self.doPractice and self.block == 2:
                globals.bonusCounter = globals.STARTING_BONUS
                self.radioTask.doPractice = False
                self.tabletTask.doPractice = False

            print '\n########\nSTARTING BLOCK '+str(self.block-1)+'\n########\n'+state.id+' & '+state.secondary+', length: '+str(self.blockDuration)
            print 'Current bonus: '+str(globals.bonusCounter/10.0)

            # set up databases for driving
            globals.db['blinker'] = DataCollector('Blinker DB', 'data/'+globals.participant+'_'+self.getCondition()+'_blinker.dat',
                                            ['pp', 'condition', 'direction', 'block', 'condtime', 'time'])
            globals.db['lanetransition'] = DataCollector('Lane Transitions DB', 'data/'+globals.participant+'_'+self.getCondition()+'_transition.dat',
                                            ['pp', 'condition', 'blinkerused', 'blinkdir', 'cardir', 'congruent', 'block', 'condtime', 'time'])
            globals.db['overtake'] = DataCollector('Overtaken Slow Traffic DB', 'data/'+globals.participant+'_'+self.getCondition()+'_overtake.dat',
                                            ['pp', 'condition', 'state', 'carNum', 'carDist', 'block', 'condtime', 'time'])
            globals.db['collision'] = DataCollector('Collision DB', 'data/'+globals.participant+'_'+self.getCondition()+'_collision.dat',
                                            ['pp', 'condition', 'zone', 'carType', 'carNum', 'block', 'condtime', 'time'])
            globals.db['car'] = DataCollector('Car DB', 'data/'+globals.participant+'_'+self.getCondition()+'_car.dat', ['pp', 'condition',
                                        'speed', 'wheelangle', 'yposition', 'deviation', 'accel', 'break', 'xposition', 'block', 'condtime', 'time'])
            globals.db['slowcars'] = DataCollector('Slow Car DB', 'data/'+globals.participant+'_'+self.getCondition()+'_slowcars.dat', ['pp', 'condition',
                                        'id', 'speed', 'xposition', 'distance', 'block', 'condtime', 'time'])
            globals.db['fastcars'] = DataCollector('Fast Car DB', 'data/'+globals.participant+'_'+self.getCondition()+'_fastcars.dat', ['pp', 'condition',
                                        'id', 'speed', 'xposition', 'distance', 'block', 'condtime', 'time'])
            globals.db['blinker'].open()
            globals.db['lanetransition'].open()
            globals.db['car'].open()
            globals.db['overtake'].open()
            globals.db['collision'].open()
            globals.db['slowcars'].open()
            globals.db['fastcars'].open()

            # traffic.road = self.roads[self.block]
            # car.bindRoad(self.roads[self.block])

            traffic.reset(self.roads[self.block])
            car.reset(self.roads[self.block])

            # populate road with traffic
            if state.id == 'complex':
                sDiff = abs(globals.EXPECTED_SPEED - globals.SLOW_SPEED)
                dist = sDiff * globals.DRIVE_DURATION
                overtakes = globals.COMPLEX_OVERTAKES
                duration = globals.DRIVE_DURATION

                if doPractice and block < 2: # practice blocks
                    duration = globals.PRACTICE_DURATION
                    overtakes = globals.PRACTICE_OVERTAKES

                interval = dist / overtakes
                #print interval
                #interval = 20.0
                print 'Generating complex traffic'
                traffic.genStaticCars(overtakes, globals.EXPECTED_SPEED, globals.SLOW_SPEED, duration, globals.RIGHT_LANE)
            else:
                sDiff = abs(globals.EXPECTED_SPEED - globals.FAST_SPEED)
                dist = sDiff * globals.DRIVE_DURATION
                interval = dist / globals.SIMPLE_OVERTAKERS
                #print interval
                print 'Generating simple traffic'
                traffic.genStaticCars(globals.SIMPLE_OVERTAKERS, globals.EXPECTED_SPEED, globals.FAST_SPEED, globals.DRIVE_DURATION, globals.LEFT_LANE)

            if state.secondary != 'none':
                print 'Starting secondary task'
                if state.secondary == 'tablet':
                    print 'Tablet task selected'
                    self.secondary = self.tabletTask
                else:
                    print 'Radio task selected'
                    self.secondary = self.radioTask

                if (not self.doPractice or (self.block > 1)) and state.secondary != 'easy':
                    print 'Loading hard task conditions (quiz or tablet)'

                    curShow = 0

                    if self.fixedOrder:
                        print 'Quiz show order fixed on participant ID'
                        ppid = globals.participant.split('D') # names have the form SDXX or CDXX with XX between 01 and 24

                        even = False
                        if len(ppid) > 1:
                            ppidx = int(ppid[1])
                            if (ppidx % 2) == 0:
                                even = True

                        if even:
                            if state.secondary == 'tablet':
                                curShow = 0
                            else:
                                curShow = 1
                        else: # odd
                            if state.secondary == 'tablet':
                                curShow = 1
                            else:
                                curShow = 0

                    else:
                        print 'Picking quiz show randomly'
                        # pick a show
                        idx = random.sample(range(0,len(self.shows)), 1)[0]
                        curShow = self.shows[idx]

                        del self.shows[idx]

                    print 'Playing show '+str(curShow)
                    self.secondary.setConversation(curShow)

                self.secondary.startTask(state.secondary, state.id)

            print 'Beginning driving section'

            globals.conditionStartTime = helpers.currentTime()

    def endState(self, car, traffic, renderer, window):
        if self.flow[self.flowIdx].type == 'drive':
            globals.db['blinker'].close()
            globals.db['lanetransition'].close()
            globals.db['car'].close()
            globals.db['overtake'].close()
            globals.db['collision'].close()
            globals.db['slowcars'].close()
            globals.db['fastcars'].close()

        self.secondary.stopTask()
        self.secondary.clearConversation()

        self.flowIdx += 1

        if self.flowIdx < len(self.flow):
            self.startNextState(car, traffic, renderer)
        else:
            finalbonus = globals.bonusCounter
            if self.drivingCondition == 'complex':
                finalbonus = min(globals.MAX_BONUS, finalbonus + globals.HARD_BONUS_OFFSET)

            finalbonus /= 10.0

            #print 'Final bonus: '+str(finalbonus)
            print 'Final payout: '+str(round(20.0+finalbonus,2))
            window.close()

    def addTextState(self, screenName):
        self.flow = self.flow + [FlowEl('screen', screenName)]

    def addDrivingState(self, conditionName, secondaryTask, duration):
            self.flow = self.flow+ [FlowEl('drive', conditionName, duration, secondaryTask)]

    def measureData(self, car, traffic, dt):

        if self.flowIdx < len(self.flow) and self.flow[self.flowIdx].type == 'drive':
            # get all the car measurements
            laneDeviation = car.getLaneDeviation()
            roadPos = car.getRoadPosition()
            wheelAngle = car.currentWheelAngle
            speed = (car.currentSpeed * 3600) * 0.001
            acceleration = car.accelerationInput
            breaking = car.breakInput
            xpos = car.xPos

            globals.db['car'].addData(['pp', globals.participant, 'condition', self.getCondition(), 'deviation', r3(laneDeviation), 'yposition', r3(roadPos),
                            'speed', r3(speed), 'wheelangle', r3(wheelAngle), 'accel', r3(acceleration), 'break', r3(breaking),
                            'xposition', r3(xpos), 'block', self.block, 'condtime', r3(helpers.conditionTime()), 'time', r3(helpers.currentTime())], True)

            traffic.reportNearbyStaticCars(car)
            traffic.reportNearbyFastCars(car)

    def preloadData(self):

        maxMeters = globals.DRIVE_DURATION*globals.MAX_SPEED
        print 'Road length: '+str(maxMeters)

        pracMeters = globals.PRACTICE_DURATION*globals.MAX_SPEED

        roadLen = maxMeters / 50
        pracLen = pracMeters / 50
        roadLen = 200

        self.roads = [Road(), Road(), Road(), Road(), Road(), Road()]

        print 'Building practice roads...'
        self.roads[0].genPath(int(pracLen), globals.ROAD_CURVYNESS, 0.0)
        self.roads[0].genVertices()
        #roads[0].genFoliage()

        self.roads[1].genPath(int(pracLen), globals.ROAD_CURVYNESS, 0.0)
        self.roads[1].genVertices()
        #roads[1].genFoliage()

        # for i in range(2,6):
        for i in range(2,3):
            print 'Building road '+str(i)+'...'
            self.roads[i].genPath(int(roadLen), globals.ROAD_CURVYNESS, 0.0)
            self.roads[i].genVertices()
            self.roads[i].genFoliage()

        print 'Finished building roads'

    def getScreenType(self):
        return self.flow[self.flowIdx].type

    def getScreenID(self):
        return self.flow[self.flowIdx].id

    def randomizeConditions(self):
        random.shuffle(self.secondOrder)

    def pickConditionPerm(self, idx):
        self.secondOrder = [self.secondOrder[i] for i in self.conditionPerms[idx]]
        self.fixedOrder = True

    def resizeSecondaryTasks(self, w, h):
        self.tabletTask.ww = w
        self.tabletTask.hh = h

    def isTextScreenDone(self, renderer):
        return renderer.textScreens[self.flow[self.flowIdx].id].done()
