
import os
import math
import operator
import ctypes
import pyglet
import random
import bisect
import time

from math import cos, pi, sin, sqrt, atan2
from flow import Flow
import perlin
import helpers

# GLOBAL VARIABLES

# Variables regarding the participant

# Is the program being run on OSX. (Important for audio playing)
onOSX = True
# Name/ID of the current participant, defaults to 'none'
participant = 'none'

# If True debug text is printed in the prompt
debug = False

# Static values

EXPECTED_SPEED = helpers.kphToMps(80.0) # speed participant should be driving
MAX_SPEED = helpers.kphToMps(100.0) # car speed is limited to this value
CARSTARTSPEED = helpers.kphToMps(85.0) # speed the car is moving at when the block starts
SLOW_SPEED = helpers.kphToMps(70.0) # average speed of 'slow' static cars
FAST_SPEED = helpers.kphToMps(100.0) # average speed of 'fast' static cars
ROAD_CURVYNESS = 0.001 # multiplier for the amplitude of the road curvature function
FAST_OVERTAKE_DISTANCE = -4.0
MAX_TRANSITION_LAG_TIME = 6.0

MEASUREINTERVAL = 1.0/100.0 # Frequency of measurements
DRIVE_DURATION = 60.0*30 # Duration in seconds of a block
PRACTICE_DURATION = 60.0*5 # Duration in seconds of a practice block
COMPLEX_OVERTAKES = 60 # Total number of right lane cars that can be overtaken by the participant
PRACTICE_OVERTAKES = 6 # Number of cars that can be overtaken in a practice block
SIMPLE_OVERTAKERS = 12 # Number of left lane cars in the simple condition
NO_OVERTAKES_CHANCE = 0.2
ESTIMATED_OVERTAKE_POINT = 20.0 # Initial expected distance to the next car when the participant overtakes

STARTING_BONUS = 40.0 # Bonus the participant starts at at the start of the first real block
DAMAGE_PENALTY = 2.0 # Bonus deduction when the participant hits another car
BLINKER_PENALTY = 1.5 # Bonus penalty when the participant does not use the blinker correctly
OFFROAD_PENALTY = 1.0 # Bonus penalty when the participant goes off the road
HARD_BONUS_OFFSET = 20.0 # Extra initial bonus for participant in the hard experimental group
MAX_BONUS = 100.0 # The maximal bonus that can be earned

TABLET_QUIZ_BONUS = 0.75 # Additional bonus when correctly answering a tablet quiz question
RADIO_QUIZ_BONUS = 0.75 # Additional bonus when correctly answering a radio quiz question

JOY_BLINK_LEFT = 5 # Steering wheel button corresponding to the left blinker
JOY_BLINK_RIGHT = 4 # Steering wheel button corresponding to the left blinker
TOTAL_STEERING_ANGLE = 240 # Total steering angle the wheel has
STEERING_FACTOR = 0.013 # Scaling for the steering wheel sensitivity

# Counter of the bonus score
bonusCounter = STARTING_BONUS

# Do not modify the globals below

LEFT_LANE = 0
RIGHT_LANE = 1
TICKS_PER_SEC = 120
DEVICE_KEYBOARD = 0
DEVICE_WHEEL = 1
ROAD_SUBDIV = [0.3, 0.7]
RAD2DEG = 57.2957795
DEG2RAD = 0.0174532925
MINISCALE = 20.0
SEGLEN = 50
FRONT = 0
REAR = 1
PASS_BEHIND_CAR = 0
PASS_ALONG_CAR = 1
PASS_INFRONT_CAR = 2
PASS_COMPLETE = 3
LEFT_BLINKER = 1
RIGHT_BLINKER = 2

flow = Flow()
db = {} # database list

hasWheel = False
joysticks = pyglet.input.get_joysticks()
joystick = 0

if joysticks:
    # x-axis: steering wheel left/right
    # y-axis: gass & brake
    joystick = joysticks[0]
    joystick.open()
    hasWheel = True

noise = perlin.SimplexNoise()
texture = []
scrubs = []
