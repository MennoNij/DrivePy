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
###############################
#
# The road: positioning and geometry
#
##############################
class SplineNode(object):

    def __init__(self, x, y):
        self.x = x
        self.y = y

class FoliageNode(object):

    def __init__(self, x, z, idx):
        self.x = x
        self.z = z
        self.idx = idx

class Road(object):
    def __init__(self):
        self.length = 0
        self.nodeArray = []
        self.xVals = []
        self.r = 5.0 # typical european road has 3.5m lanes
        self.y = 0.01
        self.pathSeed = 0.0
        self.pathAmplitude = 0.0
        self.pathLength = 0.0
        self.numSegs = 0
        self.sz = 2

        self.envTile = 60.0

        self.vertices = []
        self.texcoords = []
        self.normals = []
        self.foliage = []
        self.tFoliage = []
        self.signs = []
        self.tSigns = []

        self.miniF = 20.0
        self.mini = []
        self.miniC = []

    def reset(self):
        self.vertices = []
        self.texcoords = []
        self.normals = []
        self.foliage = []
        self.tFoliage = []
        self.signs = []
        self.tSigns = []

        self.miniF = 20.0
        self.mini = []
        self.miniC = []

    def addNode(self, x, y):
        #print '('+str(x)+','+str(y)+')\n'
        self.nodeArray.append(SplineNode(x, y))
        self.xVals.append(x)

    def genPath(self, length, amplitude, seed):
        self.pathAmplitude = amplitude
        self.pathSeed = seed
        self.pathLength = length*globals.SEGLEN
        self.numSegs = length

        self.envTile = length*3

        for t in xrange(-20, self.pathLength, self.sz):
            self.addNode(t, helpers.pertubation(amplitude, (self.pathSeed+t)*0.2))

        #for t in xrange(-100,length,self.sz):
            #self.addNode(t, 0.0)

    def getNearestNode(self, t):
        idx = min(range(len(self.xVals)), key=lambda i: abs(self.xVals[i]-t))
        val = self.nodeArray[idx].x
        if val > t:
            idx -= 1

        return idx

    def getRoadCenterpoint(self, t):
        nodeIdx = self.getNearestNode(t)
        x1 = self.nodeArray[nodeIdx].x
        z1 = self.nodeArray[nodeIdx].y
        x2 = self.nodeArray[nodeIdx+1].x
        z2 = self.nodeArray[nodeIdx+1].y

        xRelative = (t - x1) / (x2-x1)
        (xt, zt) = helpers.lerp(x1, z1, x2, z2, xRelative)
        return (xt, zt)

    def getSplineCenterpoint(self, t):
        return (t, helpers.pertubation(self.pathAmplitude, (self.pathSeed+t)*0.2))

    def getLanePosition(self, t, lane):
        # get position
        (xc, zc) = self.getSplineCenterpoint(t)
        (xc2, zc2) = self.getSplineCenterpoint(t-0.1)

        # get the normal direction
        nx = xc-xc2
        nz = zc-zc2

        # normalize heading
        nl = sqrt((nx*nx) + (nz*nz))
        nx = nx/nl
        nz = nz/nl
        #small-axis is perpendicular to tangent
        #ax = -nz
        #az = nx

        # calculate angle
        angle = (atan2(nx, nz) - atan2(1.0, 0.0))*globals.RAD2DEG

        if lane == globals.RIGHT_LANE:
            zc += (self.r*0.5)
        else:
            zc -= (self.r*0.5)

        return (xc, zc, angle, nx, nz)


    def getCenterDeviation(self, x, z):
        (xt, zt) = self.getSplineCenterpoint(x)
        dist = z - zt

        return dist

    def genVertices(self):

        if len(self.nodeArray) > 3: # need at least three points for a spline

            vertices = []
            normals = []
            texcoords = []

            mini = []
            miniC = []

            sectionIdx = 0

            #make sure segments join together properly
            xPrevNorm = 0 #basicly a hack to set the first normal
            yPrevNorm = 1

            for seg in xrange(0,len(self.nodeArray)-3):
                #print 'segment: '+str(seg)+'\n'
                #get points
                (x1,y1) = (self.nodeArray[seg].x, self.nodeArray[seg].y)
                (x2,y2) = (self.nodeArray[seg+1].x, self.nodeArray[seg+1].y)
                (x3,y3) = (self.nodeArray[seg+2].x, self.nodeArray[seg+2].y)
                (x4,y4) = (self.nodeArray[seg+3].x, self.nodeArray[seg+3].y)

                centerSpline = [(x2, y2)]

                #xCoeffs = self.genSplineCoeffs(x1, x2, x3, x4)
                #yCoeffs = self.genSplineCoeffs(y1, y2, y3, y4)

                for t in globals.ROAD_SUBDIV: # calculate all the points of the spline segment
                    #xt = self.genSplinePoint(xCoeffs, t)
                    #yt = self.genSplinePoint(yCoeffs, t)

                    xt = 0.5 * ((-x1 + 3*x2 - 3*x3 + x4)*t*t*t
                            + (2*x1 - 5*x2 + 4*x3 - x4)*t*t
                            + (-x1+x3)*t
                            + 2*x2)
                    yt = 0.5 * ((-y1 + 3*y2 - 3*y3 + y4)*t*t*t
                            + (2*y1 - 5*y2 + 4*y3 - y4)*t*t
                            + (-y1+y3)*t
                            + 2*y2)

                    centerSpline.append( (xt, yt) )

                centerSpline.append( (x3, y3) )

                splineNormals = [(xPrevNorm, yPrevNorm)] #set first normal to last one of the previous segment for cont.

                # generate normals for each spline rib
                for point in xrange( 1,len(centerSpline)-1 ):
                    (x0, y0) = centerSpline[point]
                    (x1, y1) = centerSpline[point+1]

                    ax = x1-x0
                    ay = y1-y0

                    #normal is perpendicular to tangent
                    nx = -ay
                    ny = ax

                    #normalize
                    nlen = sqrt(nx*nx + ny*ny)

                    nx = nx/nlen
                    ny = ny/nlen

                    splineNormals.append( (nx, ny) )
                splineNormals.append( splineNormals[ len(centerSpline)-2 ] )

                (xPrevNorm, yPrevNorm) = splineNormals[ len(centerSpline)-1 ] #set new first normal for the next segment

                curX = 0.0
                # generate the geometry of this section
                for point in xrange( len(centerSpline) ):
                    (y0, x0) = centerSpline[point]
                    (ny, nx) = splineNormals[point]

                    x1 = x0 - nx*self.r
                    y1 = y0 - ny*self.r
                    x2 = x0 + nx*self.r
                    y2 = y0 + ny*self.r

                    vertices.extend([y1, self.y, x1,  y2, self.y, x2])
                    normals.extend([0.0, 1.0, 0.0, 0.0, 1.0, 0.0])
                    #if seg > 0 and point > 0:

                    # add degenerate triangles
                    vertices.extend([y1, self.y, x1,  y2, self.y, x2])
                    normals.extend([0.0, 1.0, 0.0, 0.0, 1.0, 0.0])

                    texcoords.extend([0.0, 0.0, 0.0, 1.0])

                    texcoords.extend([1.0, 0.0, 1.0, 1.0])

                    # debug mini map stuff
                    mini.extend([(x0/globals.MINISCALE), y0/globals.MINISCALE])
                    miniC.extend([0.0, 0.0, 0.0])

                    curT = y2

                if curT > sectionIdx*globals.SEGLEN+globals.SEGLEN: # a road section is 'filled'
                    self.vertices.append(vertices)
                    self.normals.append(normals)
                    self.texcoords.append(texcoords)

                    self.mini.append(mini)
                    self.miniC.append(miniC)

                    sectionIdx += 1
                    vertices = []
                    normals = []
                    texcoords = []

                    mini = []
                    miniC = []

                        #print '('+str(x1)+','+str(y1)+') to ('+str(x2)+','+str(y2)+')\n'

    def genFoliage(self):
        numPlants = 1000
        xPlantPos =  random.sample(range(self.pathLength-10), numPlants)
        xPlantPos.sort()

        # generate some z positions near the road for each scrub
        for x in xPlantPos:
            (xr, zr) = self.getRoadCenterpoint(x)

            siderand = random.randint(0, 1)
            ftype = random.randint(0, 2)
            side = 1 - 2*siderand
            dist = random.randint(0, 10)
            zloc = zr + (self.r + 0.5 + dist)*side

            self.foliage.append(FoliageNode(xr, zloc, ftype))
            self.tFoliage.append(xr)
            #print '('+str(xr)+','+str(zloc)+')\n'

        signInterval = 5000
        self.tSigns = xrange(0, self.pathLength, signInterval)

        for x in self.tSigns:
            (xr, zr) = self.getRoadCenterpoint(x)
            zloc = zr + (self.r + 0.5)
            self.signs.append(FoliageNode(xr, zloc, 1))


    #generates the spline coefficients in 1 dimension
    def genSplineCoeffs(self, d1, d2, d3, d4):
        Ad = -d1 + 3*d2 - 3*d3 + d4
        Bd = 3*d1 - 6*d2 + 3*d3
        Cd = -3*d1 + 3*d3
        Dd = d1 + 4*d2 + d3

        return (Ad, Bd, Cd, Dd)

    #calculates the b-spline at t in 1 dimension
    def genSplinePoint(self, coeffs, t):
        (A, B, C, D) = coeffs
        return 0.166666667 * ( ((A*t + B)*t + C)*t + D )

    def getSegIdx(self, car):

        inSeg = -(car.xPos / globals.SEGLEN)
        segIdx = int(math.floor(inSeg))

        if segIdx >= len(self.vertices)-1:
            segIdx = len(self.vertices)-2
        elif segIdx < 1:
            segIdx = 1

        return segIdx

    def draw(self, car):

        ## DRAW GROUND
        m = self.envTile

        glBindTexture(GL_TEXTURE_2D, globals.texture[1].id)
        pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                ('v3f', (-10.0, 0.0, -self.pathLength,
                                         -10.0, 0.0, self.pathLength,
                                         self.pathLength, 0.0, self.pathLength,
                                         self.pathLength, 0.0, -self.pathLength)),
                                ('n3f', (0.0, 1.0, 0.0,
                                         0.0, 1.0, 0.0,
                                         0.0, 1.0, 0.0,
                                         0.0, 1.0, 0.0)),
                                ('t2f', (0.0, 0.0,
                                        0.0, m*1.0,
                                        m*1.0, m*1.0,
                                        m*1.0, 0.0))
                            )

        # only draw region around the car
        segIdx = self.getSegIdx(car)

        segVerts = self.vertices[segIdx-1] + self.vertices[segIdx] + self.vertices[segIdx+1]
        segNorms = self.normals[segIdx-1] + self.normals[segIdx] + self.normals[segIdx+1]
        segTex = self.texcoords[segIdx-1] + self.texcoords[segIdx] + self.texcoords[segIdx+1]

        # DRAW ROAD
        np = len(segVerts) // 3
        roadVerts = pyglet.graphics.vertex_list(np, ('v3f', tuple(segVerts)),
                                                    ('n3f', tuple(segNorms)),
                                                    ('t2f', tuple(segTex)))

        glBindTexture(GL_TEXTURE_2D, globals.texture[0].id)
        roadVerts.draw(pyglet.gl.GL_TRIANGLE_STRIP)
        roadVerts.delete()

        # DRAW FOLIAGE
        fsize = 0.6
        iMin = bisect.bisect(self.tFoliage, -car.xPos - 20.0) # get plants close to the car
        iMax = bisect.bisect(self.tFoliage, -car.xPos + 50.0)

        plants = self.foliage[iMin:iMax]
        #print len(plants)

        for p in plants:
            glBindTexture(GL_TEXTURE_2D, globals.scrubs[p.idx].id)
            pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                    ('v3f', (p.x, 0.0, p.z-fsize,
                                             p.x, fsize, p.z-fsize,
                                             p.x, fsize, p.z+fsize,
                                             p.x, 0.0, p.z+fsize)),
                                    ('t2f', (0.0, 0.0,
                                            0.0, 1.0,
                                            1.0, 1.0,
                                            1.0, 0.0))
                                )

        # DRAW SIGNS
        fsize = 0.6
        iMin = bisect.bisect(self.tSigns, -car.xPos - 20.0) # get plants close to the car
        iMax = bisect.bisect(self.tSigns, -car.xPos + 50.0)

        signs = self.signs[iMin:iMax]
        #print len(plants)

        fsize = 1.8
        for p in signs:
            glBindTexture(GL_TEXTURE_2D, globals.scrubs[3].id)
            pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                    ('v3f', (p.x, 0.0, p.z-fsize,
                                             p.x, fsize, p.z-fsize,
                                             p.x, fsize, p.z+fsize,
                                             p.x, 0.0, p.z+fsize)),
                                    ('t2f', (0.0, 0.0,
                                            0.0, 1.0,
                                            1.0, 1.0,
                                            1.0, 0.0))
                                )
    def drawDebug(self, car):
        segIdx = self.getSegIdx(car)

        segVerts = self.mini[segIdx-1] + self.mini[segIdx] + self.mini[segIdx+1]
        segCols = self.miniC[segIdx-1] + self.miniC[segIdx] + self.miniC[segIdx+1]

        np = len(segVerts) // 2
        roadVerts = pyglet.graphics.vertex_list(np, ('v2f', tuple(segVerts)),
                                                    ('c3f', tuple(segCols))
                )
        roadVerts.draw(pyglet.gl.GL_LINES)
        roadVerts.delete()

        glPushMatrix()
        glTranslatef(self.r/MINISCALE, 0.0, 0.0)
        roadVerts.draw(pyglet.gl.GL_LINE_STRIP)
        glTranslatef(-2*(self.r/MINISCALE), 0.0, 0.0)
        roadVerts.draw(pyglet.gl.GL_LINE_STRIP)
        glPopMatrix()
