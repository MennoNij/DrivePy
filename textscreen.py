import time
from pyglet.gl import *
from pyglet import image
from pyglet.window import key

import globals
import helpers

class TextScreen(object):

    def __init__(self, txt):
        self.text = txt
        self.state = 0
        self.startTime = 0.0

    def draw(self, ww):
        label = pyglet.text.HTMLLabel(self.text, x=0, y=0,
                            width=ww-0,
                            multiline=True,
                          anchor_x='center', anchor_y='center')
        label.draw()

    def start(self):
        self.startTime = time.time()

    def end(self):
        self.state = 1

    def done(self):
        global hasWheel

        if time.time() - self.startTime > 0.5:
            if self.state > 0:
                self.state = 0
                #return True

            #if globals.hasWheel:
                #if globals.joystick.buttons[1]:
                    #return True

            if helpers.findKey('space') >= 0:
                return True

        return False
