import os
import random
import pyglet
import subprocess
#from mutagen.mp3 import MP3
import pygame
import time
import globals
from helpers import r3
from datacollector import DataCollector


class Radio(object):

    def __init__(self, show=-1):
        self.started = False

        self.condition = ''
        self.fullCondition = '?'

        self.preselectedShow = show

        self.clip = 0
        self.lastClip = 0
        self.conversation = 0

        self.player = pyglet.media.ManagedSoundPlayer()
        self.llPlayer = None
        self.clipDuration = 0
        self.clipStartTime = 0
        self.currentClip = None
        self.curShow = None

        #sound = pyglet.resource.media(BALL_SOUND, streaming=False)

        #self.hardConvDB = ['show1', 'show2']
        #self.easyConvDB = ['show3', 'show4']
        #self.convAnswers = []
        self.shows = [['show3', 'show4'], ['show1', 'show2']] # easy / hard
        self.numFragments = [[1,1], [32,34]]
        self.answers = []
        #self.convPool = range(len(self.convDB))

        self.questionOrder = []
        self.questionIndx = 0
        self.correctAnswer = 0

        self.responded = False
        self.playedLetter = False
        self.playedRepeat = False
        self.phase = 0

        self.responseCountdown = 0.0
        self.responseLimit = 5.0
        self.clipInterval = 1.5
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

        datacond = '_' + self.roadCond + '_hard'

        if self.doPractice and self.run == 0:
            datacond = '_prac' + datacond

        if cond == 'hard':
            self.db = DataCollector('Radio DB', 'data/'+globals.participant+datacond+'_radio.dat', ['pp', 'cond', 'correct',
                                                                               'answer', 'conversation', 'question',
                                                                               'condtime', 'time'])
            self.db.open()

        self.started = True
        self.pickConversation()

        self.startNextClip()

    def stopTask(self):
        self.started = False

        if not self.llPlayer is None:
            self.llPlayer.terminate()
            self.llPlayer = None

        #if self.player.playing:
            #self.player.next()

        if self.condition == 'hard':
            self.db.close()

    def pickConversation(self):
        cond = 0
        if self.run == 0 and self.doPractice:
            self.curShow = 'practice'
            self.lastClip = 8
            self.clip = -1
        else:
            if self.condition == 'hard':
                cond = 1

            if len(self.shows[cond]) > 0:
                idx = random.sample(range(0,len(self.shows[cond])), 1)[0]
                self.curShow = self.shows[cond][idx]
                self.lastClip = self.numFragments[cond][idx]

                del self.shows[cond][idx]
                del self.numFragments[cond][idx]

                self.clip = -1
            else:
                self.started = False

    def startNextClip(self):
        if self.started:
            self.responseCountdown = 0.0
            self.isi = 0.0
            self.responded = False
            self.playedLetter = False
            self.phase = 0

            if self.clip+1 >= self.lastClip:
                #self.pickConversation()
                self.clip = -1
                self.stopTask()
            else:

                self.clip += 1

                #self.currentClip = pyglet.media.load('radio/'+self.convglobals.db[self.conversation]+'_'+str(self.clip+1)+'.mp3', streaming=False)
                if self.condition == 'hard':
                    currentClip = 'radio/'+self.curShow+'/'+self.curShow+'frag'+str(self.clip+1)+'.mp3'
                    self.playAudio(currentClip)
                else:
                    currentClip = 'radio/'+self.curShow+'/'+self.curShow+'.mp3'
                    self.playAudio(currentClip)
                    #audio_file = os.getcwd()+'/radio/show1/show1frag1q.mp3'
                    #print audio_file

                    #self.playAudio(audio_file)
                    #self.llPlayer = subprocess.Popen(["afplay", audio_file], shell=False)
                    #pid = p.pid()
                    #p.terminate()

    def draw(self):
        return 0

    def update(self, dt):
        if self.started:
            if self.condition == 'hard':
                #print str(self.player.time)+' - '+str(self.currentClip.duration)
                if not self.audioIsPlaying() and not self.responded:
                    if self.phase == 0: # clip finished, play question
                        currentClip = 'radio/'+self.curShow+'/'+self.curShow+'frag'+str(self.clip+1)+'q.mp3'
                        self.playAudio(currentClip)

                        self.questionOrder = [0, 1, 2]
                        random.shuffle(self.questionOrder)
                        #print self.questionOrder
                        self.questionIdx = 0
                        self.correctAnswer = self.questionOrder.index(0)
                        self.phase = 1

                    elif self.phase == 1: # questions finished, play options
                        if self.questionIdx > 2:
                            # repeat question after answers
                            if self.playedRepeat:
                                currentClip = 'radio/'+self.curShow+'/'+self.curShow+'frag'+str(self.clip+1)+'q.mp3'
                                self.playAudio(currentClip)
                                self.playedRepeat = False

                                self.phase = 2 # options finished, go to response phase

                            else: # say 'repeat'
                                currentClip = 'radio/herhaal.mp3'
                                self.playAudio(currentClip)
                                self.playedRepeat = True
                        else:
                            letters = ['a', 'b', 'c']
                            number = self.questionOrder[self.questionIdx]
                            letter = letters[number]

                            if self.playedLetter:
                                currentClip = 'radio/'+self.curShow+'/'+self.curShow+'frag'+str(self.clip+1)+letter+'.mp3'
                                self.playAudio(currentClip)

                                self.playedLetter = False
                                self.questionIdx += 1
                            else: # play the answer letter clip first
                                currentClip = 'radio/'+letters[self.questionIdx]+'.mp3'
                                self.playAudio(currentClip)

                                self.playedLetter = True
                elif self.phase == 2:
                    self.responseCountdown += dt
                    #print self.responseCountdown

                    if self.responseCountdown >= self.responseLimit:
                        self.processResponse(-1)

                elif self.phase == 3: # feedback
                    self.isi += dt
                    if self.isi >= self.clipInterval:
                        self.startNextClip()
            #else: # easy
                #a = 1
                #if not self.player.playing: # get next clip
                    #print 'finished'
                    #self.startNextClip()

    def processResponse(self, button):

        if self.started and not self.responded and self.phase == 2:
            #self.player.pause()
            #self.player.next()
            correct = 0

            let = ['A', 'B', 'C']

            if button >= 0 and button < 4:
                if self.audioIsPlaying():
                    if self.llPlayer is not None:
                        self.llPlayer.terminate()
                        self.llPlayer = None

                print 'Answer '+let[button]+' was selected. Correct answer was '+let[self.correctAnswer]
                if button ==  self.correctAnswer:
                    correct = 1
            else:
                print 'No answer was selected. Correct answer was '+let[self.correctAnswer]

            if correct:
                correctSound = pyglet.resource.media('correct.wav')
                correctSound.play()
                globals.bonusCounter += globals.RADIO_QUIZ_BONUS
                #self.correctSound.play()
            else:
                incorrectSound = pyglet.resource.media('incorrect.wav')
                incorrectSound.play()
                #self.incorrectSound.play()

            self.phase = 3
            self.responded = True

            self.db.addData(['pp', globals.participant, 'cond', self.fullCondition, 'correct', correct,
                            'answer', button, 'conversation', self.conversation, 'question', self.clip,
                            'condtime', r3(globals.conditionTime()), 'time', r3(globals.currentTime())], True)

    def checkInput(self):

        if self.started:
            if self.condition == 'hard':
                if not self.responded and self.phase > 0:

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
        #filename2 = 'radio/'+self.curShow+'/'+self.curShow+'frag'+str(self.clip+1)+'.ogg'
        clip = pyglet.media.load(filename, streaming=False)
        self.clipDuration = clip.duration
        #print 'clip duration'
        #print clip.duration
        #audio = MP3(filename2)
        #print 'mutagen'
        #print audio.info.length
        #txt = ''
        #try:
            #subprocess.check_output(["ffmpeg", "-i", filename])
        #except subprocess.CalledProcessError, e:
            ##print "Ping stdout output:\n", e.output
            #txt = e.output

        #ffmpeg -i show1frag1.mp3 2>&1|sed -n "s/.*Duration: \([^,]*\).*/\1/p"
        #print txt
        self.clipStartTime = time.time()
        #print 'clip start time'
        #print self.clipStartTime
        clip = None

        if globals.onOSX:
            # using command prompt because pyglet media player is really buggy...
            self.llPlayer = subprocess.Popen(["afplay", filename], shell=False)
            if self.clipDuration > 5.0:
                print 'Audio PID: '+str(self.llPlayer.pid)+' (kill with "kill <PID>" in bash)'
        else:
            # windows requires mplayer to be installed
            self.llPlayer = subprocess.Popen(["mplayer", filename, "-ss", "30"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def audioIsPlaying(self):
        if not self.llPlayer is None:
            tm = time.time()
            #print str(tm-self.clipStartTime)+' - '+str(tm)+' - '+str(self.clipStartTime+self.clipDuration)
            if tm-self.clipStartTime >= self.clipDuration:
                #print 'end time'
                #print tm
                if self.llPlayer is not None:
                    if not globals.onOSX:
                        self.llPlayer.stdin.write("q")    
                    self.llPlayer.terminate()
                    self.llPlayer = None

                return False

        return True
