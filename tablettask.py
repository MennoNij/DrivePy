import os
import random
import pyglet
import subprocess
import pygame
import time
import globals
from helpers import r3
from datacollector import DataCollector

from pyglet.gl import *
from pyglet import image


class Tablet(object):

    def __init__(self, show=-1):
        self.started = False

        self.condition = ''
        self.fullCondition = '?'

        self.preselectedShow = show

        self.clip = 0
        self.lastClip = 0
        self.conversation = 0

        self.clipLines = []
        self.minLineIdx = 0
        self.maxLineIdx = 0
        self.clipDuration = 0
        self.lineInterval = 0
        self.clipStartTime = 0
        self.currentClip = None
        self.curShow = None
        self.clipQuestion = None

        self.tabletTexture = image.load('img/dashboard-tablet.png').texture
        self.hh = 1.0
        self.ww = 1.0
        self.tabletDisplayText = ''
        self.maxDisplayLength = 10 # max num of lines displayed
        self.tabletLineWidth = 40

        self.allShows = ['show1', 'show2'] # easy / hard
        self.allNumFragments = [32,34]
        self.shows = self.allShows
        self.numFragments = self.allNumFragments

        self.answers = []

        self.questionOrder = []
        self.questionIndx = 0
        self.correctAnswer = 0

        self.responded = False
        self.playedLetter = False
        self.playedRepeat = False
        self.phase = 0

        self.responseCountdown = 0.0
        self.responseLimit = 15.0
        self.clipInterval = 1.5
        self.lastLineTime = 0.0
        self.isi = 0.0

        self.run = -1
        self.doPractice = False
        self.roadCond = 'simple'

        #self.incorrectSound = pyglet.resource.media('incorrect.wav')
        #self.correctSound = pyglet.resource.media('correct.wav')

        self.db = None

    def setConversation(self, show):
        self.preselectedShow = show

    def clearConversation(self):
        self.preselectedShow = -1

    def startTask(self, cond, driving='?', blockNum=0):
        self.condition = cond
        self.fullCondition = driving+'_'+cond
        self.run += 1

        datacond = '_' + self.roadCond + '_tablet'

        if self.doPractice:
            datacond = '_prac' + datacond

        self.db = DataCollector('Tablet DB', 'data/'+globals.participant+datacond+'_tablet.dat', ['pp', 'cond', 'correct',
                                                                           'answer', 'conversation', 'question',
                                                                           'condtime', 'time'])
        self.db.open()

        self.started = True
        self.pickConversation()

        self.startNextClip()

    def stopTask(self):
        self.started = False

        #if self.player.playing:
            #self.player.next()

        self.db.close()

    def pickConversation(self):
        if self.doPractice:
            self.curShow = 'practice'
            self.lastClip = 8
            self.clip = -1
            print 'Loaded practice show'
        else:
            if self.preselectedShow > -1:
                self.curShow = self.allShows[self.preselectedShow]
                self.lastClip = self.allNumFragments[self.preselectedShow]

                self.clip = -1
                print 'Loaded preselected:'+self.curShow
            else:
                if len(self.shows) > 0:
                    idx = random.sample(range(0,len(self.shows)), 1)[0]
                    self.curShow = self.shows[0] #self.shows[idx]
                    self.lastClip = self.numFragments[idx]

                    del self.shows[idx]
                    del self.numFragments[idx]

                    self.clip = -1

                    print 'Loaded random:'+self.curShow
                else:
                    print 'No shows left to load'
                    self.started = False

    def startNextClip(self):
        if self.started:
            self.responseCountdown = 0.0
            self.isi = 0.0
            self.responded = False
            self.playedLetter = False
            self.phase = 1
            self.minLineIdx = -1
            self.maxLineIdx = -1
            self.lastLineTime = 0
            self.clipLines = []

            if self.clip+1 >= self.lastClip:
                #self.pickConversation()
                self.clip = -1
                self.stopTask()
            else:

                self.clip += 1
                #self.clip = 0

                #print 'play clip: ' + str(self.clip+1) + ' of '+ str(self.lastClip)
                with open('tablet/'+str(self.curShow)+'/'+str(self.curShow)+'frag'+str(self.clip+1)+'.txt') as f:
                    lines = f.readlines()

                    duration = lines[0]
                    duration = duration.split(':')
                    self.clipDuration = (float(duration[0])*60 + float(duration[1]))
                    #print 'Duration of clip: '+str(self.clipDuration)

                    i = 1
                    while len(lines[i]) > 2:
                        l = lines[i].split(' - ')
                        #print str(len(lines[i]))
                        #print lines[i]
                        #print l[0]
                        #print l[1]
                        self.clipLines.append(ClipLine(l[0], l[1]))
                        i += 1

                    self.lineInterval = self.clipDuration / len(self.clipLines)
                    #print 'Line interval: '+str(self.clipDuration)

                    #print 'Question: '+lines[i+1]
                    self.clipQuestion = Question(lines[i+1], lines[i+2], lines[i+3], lines[i+4])

                self.clipStartTime = globals.currentTime()

                #currentClip = 'radio/'+self.curShow+'/'+self.curShow+'frag'+str(self.clip+1)+'.mp3'
                #self.playAudio(currentClip)

    def updateTabletText(self, dt):
        time = globals.currentTime()
        if time - self.lastLineTime >= self.lineInterval and self.phase < 2: # time to show the next line on screen
            #print 'Show new line. maxLineIdx from '+str(self.maxLineIdx)+' to '+str(self.maxLineIdx+1)
            #self.minLineIdx += 1
            self.maxLineIdx += 1
            self.lastLineTime = time

            if self.maxLineIdx < len(self.clipLines):
                #print 'Still new lines left to show'
                totalLen = 0 # determine total displayed text length in lines (approx)
                for i in range(self.minLineIdx+1, self.maxLineIdx+1):
                    totalLen += self.clipLines[i].lineLen(self.tabletLineWidth)

                #print 'Total length: '+str(totalLen)

                # displayed text will be too long, strip oldest lines until it fits
                if totalLen > self.maxDisplayLength:
                    #print 'Got to remove some lines from the display'
                    difference = totalLen - self.maxDisplayLength
                    while difference > 0:
                        ll = self.clipLines[self.minLineIdx+1].lineLen(self.tabletLineWidth)
                        difference -= ll
                        self.minLineIdx += 1

                # update displayed text
                self.tabletDisplayText = '<font face="Helvetica,Arial" size=+1>'
                for i in range(self.minLineIdx+1, self.maxLineIdx+1):
                    self.tabletDisplayText += self.clipLines[i].output()+'<br><br>'

                self.tabletDisplayText += '</font>'

                correctSound = pyglet.resource.media('message.wav')
                correctSound.play()
                #self.tabletText.append(self.clipLines[self.lineIdx].output())

    def clipFinished(self):

        time = globals.currentTime()
        if time - self.clipStartTime < self.clipDuration + self.lineInterval:
            return False

        return True

    def draw(self):
        if self.started:
            yOff = 0

            screenRatio = float(self.hh) / float(self.ww)
            glPushMatrix()
            glBindTexture(GL_TEXTURE_2D, self.tabletTexture.id)
            pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                    ('v3f', (-0.8*screenRatio, -1.0+yOff, 0.0,
                                             -0.8*screenRatio, -0.2+yOff, 0.0,
                                             -0.25*screenRatio, -0.2+yOff, 0.0,
                                             -0.25*screenRatio, -1.0+yOff, 0.0)),
                                    ('t2f', (0.0, 0.0,
                                            0.0, 1.0,
                                            1.0, 1.0,
                                            1.0, 0.0))
                                )
            glPopMatrix()
            self.set_text()

            displayText = None

            #if self.phase < 2:
            displayText = self.tabletDisplayText
            #else:
                #displayText = self.tabletDisplayQuestion

            #print displayText
            text = pyglet.text.HTMLLabel(displayText,
                          x=int(0.3*self.ww), y=int(0.17*self.hh),
                          multiline=True,
                          width=int(0.48*self.ww),
                          height=(0.3*self.hh),
                          #color=(0,0,0,255),
                          anchor_x='center', anchor_y='center')
            text.draw()

            self.set_2d()

    def set_2d(self):
        w = self.ww
        h = self.hh
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-1, 1, -1, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set_text(self):
        w = self.ww
        h = self.hh
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, w, 0, h, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()


    def update(self, dt):
        if self.started:
            if self.phase == 1:
                if not self.clipFinished() and not self.responded: # clip is still running on the tablet
                    self.updateTabletText(dt)

                else: # clip is finished playing
                    self.phase = 2

                    self.buildQuestion()

                    questionSound = pyglet.resource.media('question.wav')
                    questionSound.play()
            elif self.phase == 2:

                self.responseCountdown += dt
                #print self.responseCountdown

                if self.responseCountdown >= self.responseLimit:
                    self.processResponse(-1)

            elif self.phase == 3: # feedback
                self.isi += dt
                if self.isi >= self.clipInterval:
                    self.startNextClip()

    def buildQuestion(self):
        self.tabletDisplayText = '<font face="Helvetica,Arial" size=+1>'

        self.tabletDisplayText += self.clipQuestion.question+'<br><br>'
        alph = ['A','B','C']
        self.questionOrder = [0, 1, 2]
        random.shuffle(self.questionOrder)
        self.correctAnswer = self.questionOrder.index(0)

        for i in range(0,3):
            self.tabletDisplayText += '<b>'+alph[i]+'.</b> '+self.clipQuestion.ans[self.questionOrder[i]]+'<br><br>'

        self.tabletDisplayText += '</font>'

    def processResponse(self, button):

        if self.started and not self.responded and self.phase == 2:
            #self.player.pause()
            #self.player.next()
            correct = 0

            let = ['A', 'B', 'C']

            if button >= 0 and button < 4:

                print 'Answer '+let[button]+' was selected. Correct answer was '+let[self.correctAnswer]
                if button ==  self.correctAnswer:
                    correct = 1
            else:
                print 'No answer was selected. Correct answer was '+let[self.correctAnswer]

            if correct:
                correctSound = pyglet.resource.media('correct.wav')
                correctSound.play()
                globals.bonusCounter += globals.TABLET_QUIZ_BONUS
                #self.correctSound.play()
            else:
                incorrectSound = pyglet.resource.media('incorrect.wav')
                incorrectSound.play()
                #self.incorrectSound.play()

            self.phase = 3
            self.responded = True
            self.tabletDisplayText = ''

            self.db.addData(['pp', globals.participant, 'cond', self.fullCondition, 'correct', correct,
                            'answer', button, 'conversation', self.conversation, 'question', self.clip,
                            'condtime', r3(globals.conditionTime()), 'time', r3(globals.currentTime())], True)

    def checkInput(self):

        if self.started:
            if not self.responded and self.phase > 1:

                if globals.hasWheel:
                    if globals.joystick.buttons[3]: #or globals.joystick.buttons[3]:
                        self.processResponse(0)
                    elif globals.joystick.buttons[2]: #or globals.joystick.buttons[5]:
                        self.processResponse(1)
                    elif globals.joystick.buttons[0]: #or globals.joystick.buttons[7]:
                        self.processResponse(2)

                if globals.findKey('1') >= 0:
                    self.processResponse(0)
                elif globals.findKey('2') >= 0:
                    self.processResponse(1)
                elif globals.findKey('3') >= 0:
                    self.processResponse(2)

    def setCondition(self, cond):
        self.condition = cond

    def playAudio(self, filename):
        return False

    def audioIsPlaying(self):
        return False

class ClipLine(object):

    def __init__(self, speaker, text):
        self.speaker = speaker
        self.text = text

    def output(self):
        line = '<b>'+self.speaker+': </b>' + self.text

        return line

    def lineLen(self, lineWidth):

        return len(self.speaker+self.text) / lineWidth + 1

class Question(object):

    def __init__(self, q, a, b, c):
        self.question = q
        self.ans = []
        self.ans.append(a)
        self.ans.append(b)
        self.ans.append(c)
