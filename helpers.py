
import time
import math
from pyglet.gl import *

from math import cos, pi, sin, sqrt, atan2

pressedKeys = []
startTime = time.time()
conditionStartTime = time.time()


def findKey(key):
    global pressedKeys

    index = -1
    try:
        index = pressedKeys.index(key)
    except:
        index = -1

    return index

def clearKeyPress(key):
    pressedKeys.remove(key)

def currentTime():
    return time.time() - startTime

def conditionTime():
    global conditionStartTime
    return currentTime() - conditionStartTime

def r3(n):
    return round(n, 3)

def kphToMps(kph):
    return (kph*1000.0)/3600.0

def mpsToKph(mps):
    return (mps*3600.0)/1000.0

def lerp(x1, z1, x2, z2, t):
    nx = x1*t + x2*(1-t)
    nz = z1*t + z2*(1-t)

    return (nx, nz)

def vec(*args):
    return (GLfloat * len(args))(*args)

def pertubation(amplitude, t):
    # the wickens tracking task
    pi2t = math.pi*2*t*0.2
    pos = (55*sin(pi2t*0.05) + 39*sin(pi2t*0.2) + 24*sin(pi2t*0.08))*amplitude
    # print(str(t)+','+str(pos)+' ')
    #pos = 0.0

    return pos

def determineCollision(c1x, c1z, h1x, h1z, c2x, c2z, h2x, h2z, cW, cL, s=1.0):
    # determine bounding circle positions for both cars
    c1Xs = [c1x + h1x*cL*0.6, c1x - h1x*cL*0.6]
    c1Zs = [c1z + h1z*cL*0.6, c1z - h1z*cL*0.6]

    c2Xs = [c2x + h2x*cL*0.6, c2x - h2x*cL*0.6]
    c2Zs = [c2z + h2z*cL*0.6, c2z - h2z*cL*0.6]

    r = cW*s

    for i in [0, 1]:
        for j in [0, 1]:
            if circlesIntersect(c1Xs[i], c1Zs[i], c2Xs[j], c2Zs[j], r):
                return (True, j)

    return (False, -1)

def circlesIntersect(x1, y1, x2, y2, r):
    dist = (x1-x2)*(x1-x2) + (y1-y2)*(y1-y2)

    if dist <= (r+r)*(r+r):
        return True
    else:
        return False
