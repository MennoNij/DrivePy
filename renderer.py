import ctypes
from pyglet.gl import *
from pyglet import image
import math
from math import cos, pi, sin, sqrt, atan2

from textscreen import TextScreen
import globals
import helpers

###############################
#
# The renderer: Presentation of the simulator and text screens
#
##############################

class Renderer(object):

    def __init__(self):
        self.fbtex = 0
        self.fbo = gl.GLuint()
        self.depthbuffer = gl.GLuint()

        self.dashboard = []
        self.textScreens = {}

        self.w = 640
        self.h = 480

        self.debugOverlay = 0

        # self.loadTextures()
        # self.setup()
        # self.mirrorSetup()

    # draw the active text screen
    def drawText(self):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        self.set_text(self.w, self.h)
        sid = globals.flow.getScreenID()
        self.textScreens[sid].draw(self.w)

    # render the driving environment
    def drawSim(self, road, car, traffic, secondary):

        self.drawMirror(road, car, traffic)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        self.set_2d(self.w, self.h)
        self.drawBackground()

        self.set_3d(self.w, self.h)

        glLightfv(GL_LIGHT0, GL_POSITION, helpers.vec(.5, .5, 1, 0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, helpers.vec(.5, .5, 1, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, helpers.vec(2, 2, 2, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, helpers.vec(1, 1, 1, 1))

        car.look()

        self.drawWorld(road, car, traffic, 0)

        self.set_2d(self.w, self.h)
        self.drawForeground(road, car, traffic)

        secondary.draw()

        self.set_text(self.w, self.h)

        counter = pyglet.text.Label('Bonus: '+str(globals.bonusCounter)+' punten',
                      font_name='Helvetica',
                      font_size=30,
                      x=int(self.w*0.35), y=-int(self.h*0.4),
                      #color=(0,0,0,255),
                      anchor_x='center', anchor_y='center')
        counter.draw()

        if car.blinkerPracWarning > 0.001:
            counter = pyglet.text.Label('Vergeet niet de richtingaanwijzers te gebruiken',
                      font_name='Helvetica',
                      font_size=30,
                      #x=int(ww*0.5), y=-int(hh*0.5),
                      #color=(0,0,0,255),
                      anchor_x='center', anchor_y='center')
            counter.draw()

    # draw the rear view mirror image
    def drawMirror(self, road, car, traffic):

        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.fbo)

        # now render
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        self.set_2d(512, 256)
        self.drawBackground()

        self.set_3d(512, 256, 50.0)
        car.mirrorLook()
        self.drawWorld(road, car, traffic, 1)

        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)

    # draw the static background image
    def drawBackground(self):

        # fill screen with the background image
        glBindTexture(GL_TEXTURE_2D, globals.texture[2].id)

        glPushMatrix()
        glBegin(GL_QUADS)
        glTexCoord2i(0,0)
        glVertex2i(-1, -1)
        glTexCoord2i(1,0)
        glVertex2i(1, -1)
        glTexCoord2i(1,1)
        glVertex2i(1, 1)
        glTexCoord2i(0,1)
        glVertex2i(-1, 1)
        glEnd()
        glPopMatrix()

    # render the interactive world
    def drawWorld(self, road, car, traffic, mirror):

        road.draw(car)
        traffic.draw(car)
        if not mirror:
            glPushMatrix()
            glRotatef(-90.0,0.0,1.0,0.0) # rotate car model the correct way
            glTranslatef(-car.zPos, 0.0, car.xPos+0.0)
            glRotatef(car.angleHeading,0.0,1.0,0.0) # rotate car model the correct way
            glTranslatef(0.0, 0.0, car.modelOffset)
            traffic.mustang.draw()
            glPopMatrix()
        else:
            glPushMatrix()
            glRotatef(-90.0,0.0,1.0,0.0) # rotate car model the correct way
            glTranslatef(-car.zPos, 0.0, car.xPos+2.0)
            glRotatef(-car.angleHeading,0.0,1.0,0.0) # rotate car model the correct way
            glTranslatef(0.0, -0.1, -1.6)
            traffic.mustang.draw()
            glPopMatrix()

    # draw the dashboard (speedometer & blinkers) and other HUD items (score)
    def drawForeground(self, road, car, traffic):
        global dashboard

        yOff = car.rumble()

        # DRAW MIRROR
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)

        mOff = 0.55
        pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                ('v3f', (mOff+0.31, 0.69+yOff, 0.0,
                                         mOff+0.31, 0.96+yOff, 0.0,
                                         mOff+-0.31, 0.96+yOff, 0.0,
                                         mOff+-0.31, 0.69+yOff, 0.0)),
                                ('c3f', (0.0, 0.0, 0.0,
                                        0.0, 0.0, 0.0,
                                        0.0, 0.0, 0.0,
                                        0.0, 0.0, 0.0,))
                            )

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)

        glBindTexture(GL_TEXTURE_2D, self.fbtex.id)
        pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                ('v3f', (mOff+0.3, 0.7+yOff, 0.0,
                                         mOff+0.3, 0.95+yOff, 0.0,
                                         mOff+-0.3, 0.95+yOff, 0.0,
                                         mOff+-0.3, 0.7+yOff, 0.0)),
                                ('t2f', (0.0, 0.0,
                                        0.0, 1.0,
                                        1.0, 1.0,
                                        1.0, 0.0))
                            )

        # DRAW DASHBOARD
        screenRatio = float(self.h) / float(self.w)
        glBindTexture(GL_TEXTURE_2D, self.dashboard[0].id)
        pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                ('v3f', (-0.3*screenRatio, -0.9+yOff, 0.0,
                                         -0.3*screenRatio, -0.3+yOff, 0.0,
                                         0.3*screenRatio, -0.3+yOff, 0.0,
                                         0.3*screenRatio, -0.9+yOff, 0.0)),
                                ('t2f', (0.0, 0.0,
                                        0.0, 1.0,
                                        1.0, 1.0,
                                        1.0, 0.0))
                            )

        blinkTex = 1
        if car.activeBlinker == globals.LEFT_BLINKER:
            if car.blinkerCooldown <= 0.0:
                car.activeBlinker = -1
            else:
                if car.blinkerCooldown < 0.333 or car.blinkerCooldown > 0.666:
                    blinkTex = 2

        glBindTexture(GL_TEXTURE_2D, self.dashboard[blinkTex].id)
        pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                ('v3f', (-0.50*screenRatio, -0.8+yOff, 0.0,
                                         -0.50*screenRatio, -0.65+yOff, 0.0,
                                         -0.35*screenRatio, -0.65+yOff, 0.0,
                                         -0.35*screenRatio, -0.8+yOff, 0.0)),
                                ('t2f', (0.0, 0.0,
                                        0.0, 1.0,
                                        1.0, 1.0,
                                        1.0, 0.0))
                            )

        blinkTex = 1
        if car.activeBlinker == globals.RIGHT_BLINKER:
            if car.blinkerCooldown <= 0.0:
                car.activeBlinker = -1
            else:
                if car.blinkerCooldown < 0.333 or car.blinkerCooldown > 0.666:
                    blinkTex = 2

        glBindTexture(GL_TEXTURE_2D, self.dashboard[blinkTex].id)
        pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                ('v3f', (0.50*screenRatio, -0.8+yOff, 0.0,
                                         0.50*screenRatio, -0.65+yOff, 0.0,
                                         0.35*screenRatio, -0.65+yOff, 0.0,
                                         0.35*screenRatio, -0.8+yOff, 0.0)),
                                ('t2f', (0.0, 0.0,
                                        0.0, 1.0,
                                        1.0, 1.0,
                                        1.0, 0.0))
                            )

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)
        glLineWidth(3.0)


        degPerKph = 90.0/40.0
        aDt = degPerKph*(car.currentSpeed*3.6)
        angle = 225.0 - aDt

        lx = 0.0 + 0.24 * cos(angle*globals.DEG2RAD)
        ly = -0.6 + (0.24 * sin(angle*globals.DEG2RAD))

        pyglet.graphics.draw(2, pyglet.gl.GL_LINES,
            ('v2f', (0.0, -0.6+yOff, lx*screenRatio, ly+yOff)),
            ('c3f', (0.3, 0.0, 0.0, 1.0, 0.0, 0.0)))


        # draw collision screen
        # collision3 = car.collisionCooldown*car.collisionCooldown*car.collisionCooldown
        # pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
        #                         ('v3f', (-1.0, -1.0, 0.0,
        #                                  -1.0, 1.0, 0.0,
        #                                  1.0, 1.0, 0.0,
        #                                  1.0, -1.0, 0.0)),
        #                         ('c4f', (1.0, 0.0, 0.0, collision3,
        #                                 1.0, 0.0, 0.0, collision3,
        #                                 1.0, 0.0, 0.0, collision3,
        #                                 1.0, 0.0, 0.0, collision3))
        #                     )
        #
        # DRAW DEBUG INFO

        if self.debugOverlay:
            glPushMatrix()
            xP = car.xPos / MINISCALE
            yP = car.zPos / MINISCALE
            xOff = 0.5
            glTranslatef(xOff, xP, 0.0) # general map offset

            road.drawDebug(car)

            mW = traffic.mustang.maxX
            mH = traffic.mustang.maxZ
            cW = traffic.mustang.maxX / MINISCALE
            cH = traffic.mustang.maxZ / MINISCALE

            # slow cars
            iMin = bisect.bisect(traffic.tStaticCars, -car.xPos - 50.0) # get plants close to the car
            iMax = bisect.bisect(traffic.tStaticCars, -car.xPos + 50.0)

            slow = traffic.staticCars[iMin:iMax] # this will always draw at least one car, but who cares

            for p in slow:
                x1 = p.x + p.xH*mH*0.5
                z1 = p.z + p.zH*mH*0.5
                x2 = p.x - p.xH*mH*0.5
                z2 = p.z - p.zH*mH*0.5

                #print '('+str(x1)+','+str(z1)+') to ('+str(x2)+','+str(z2)+')\n'

                col1 = 0.0
                (colli, zone) = helpers.determineCollision(p.x, p.z, p.xH, p.zH, -car.xPos+yP, -car.zPos, car.xHeading, car.zHeading, mW, mH)
                if colli:
                    #print 'boom!'
                    col1 = 1.0

                pz = (p.x / MINISCALE)
                px = p.z / MINISCALE

                glPushMatrix()
                glTranslatef(px, pz, 0.0)
                glRotatef(p.heading, 0.0, 0.0, 1.0)
                pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                        ('v3f', (-cW*screenRatio, -cH, 0.0,
                                                 -cW*screenRatio, cH, 0.0,
                                                 cW*screenRatio, cH, 0.0,
                                                 cW*screenRatio, -cH, 0.0)),
                                        ('c3f', (col1, 0.0, 1.0,
                                                col1, 0.0, 1.0,
                                                col1, 0.0, 1.0,
                                                col1, 0.0, 1.0))
                                    )
                glPopMatrix()


                glEnable(GL_TEXTURE_2D)
                glEnable(GL_LIGHTING)
                glBindTexture(GL_TEXTURE_2D, globals.texture[3].id)
                #print '('+str(x1)+','+str(z1)+') to ('+str(x2)+','+str(z2)+')\n'
                pz = x1 / MINISCALE
                px = z1 / MINISCALE
                glPushMatrix()
                glTranslatef(px, pz, 0.0)
                glRotatef(p.heading, 0.0, 0.0, 1.0)
                pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                        ('v3f', (-cW*screenRatio, -cH/2, 0.0,
                                                 -cW*screenRatio, cH/2, 0.0,
                                                 cW*screenRatio, cH/2, 0.0,
                                                 cW*screenRatio, -cH/2, 0.0)),
                                    ('t2f', (0.0, 0.0,
                                            0.0, 1.0,
                                            1.0, 1.0,
                                            1.0, 0.0)),
                                        ('c3f', (0.0, 0.0, 1.0,
                                                0.0, 0.0, 1.0,
                                                0.0, 0.0, 1.0,
                                                0.0, 0.0, 1.0))
                                    )
                glPopMatrix()

                pz = x2 / MINISCALE
                px = z2 / MINISCALE
                glPushMatrix()
                glTranslatef(px, pz, 0.0)
                glRotatef(p.heading, 0.0, 0.0, 1.0)
                pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                        ('v3f', (-cW*screenRatio, -cH/2, 0.0,
                                                 -cW*screenRatio, cH/2, 0.0,
                                                 cW*screenRatio, cH/2, 0.0,
                                                 cW*screenRatio, -cH/2, 0.0)),
                                    ('t2f', (0.0, 0.0,
                                            0.0, 1.0,
                                            1.0, 1.0,
                                            1.0, 0.0)),
                                        ('c3f', (1.0, 0.0, 1.0,
                                                1.0, 0.0, 1.0,
                                                1.0, 0.0, 1.0,
                                                1.0, 0.0, 1.0))
                                    )
                glPopMatrix()

                glDisable(GL_TEXTURE_2D)
                glDisable(GL_LIGHTING)

            # speeding car
            for p in traffic.fastCars:
                pz = (p.x / MINISCALE)
                px = p.z / MINISCALE

                glPushMatrix()
                glTranslatef(px, pz, 0.0)
                glRotatef(p.heading, 0.0, 0.0, 1.0)
                pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                        ('v3f', (-cW*screenRatio, -cH, 0.0,
                                                 -cW*screenRatio, cH, 0.0,
                                                 cW*screenRatio, cH, 0.0,
                                                 cW*screenRatio, -cH, 0.0)),
                                        ('c3f', (1.0, 0.0, 0.0,
                                                1.0, 0.0, 0.0,
                                                1.0, 0.0, 0.0,
                                                1.0, 0.0, 0.0))
                                    )
                glPopMatrix()

            glPopMatrix() # pop general map offset


            # own car
            glPushMatrix()
            glTranslatef(xOff-yP, (-car.modelOffset)/MINISCALE, 0.0)
            glRotatef(car.angleHeading, 0.0, 0.0, 1.0)
            pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
                                    ('v3f', (-cW*screenRatio, -cH, 0.0,
                                             -cW*screenRatio, cH, 0.0,
                                             cW*screenRatio, cH, 0.0,
                                             cW*screenRatio, -cH, 0.0)),
                                    ('c3f', (0.0, 1.0, 0.0,
                                            0.0, 1.0, 0.0,
                                            0.0, 1.0, 0.0,
                                            0.0, 1.0, 0.0))
                                )
            glPopMatrix()

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)

    def addTextScreen(self, name, content):
        self.textScreens[name] = TextScreen(content)

    # loads all the textures used in the simulator
    def loadTextures(self):
        textureSurface = image.load('img/road4.jpg')
        globals.texture.append(textureSurface.texture)
        textureSurface = image.load('img/steppe-ground3.jpg')
        globals.texture.append(textureSurface.texture)
        textureSurface = image.load('img/steppe.jpg')
        globals.texture.append(textureSurface.texture)
        textureSurface = image.load('img/circle.png')
        globals.texture.append(textureSurface.texture)

        textureSurface = image.load('img/cactus1.png')
        globals.scrubs.append(textureSurface.texture)
        textureSurface = image.load('img/cactus2.png')
        globals.scrubs.append(textureSurface.texture)
        textureSurface = image.load('img/cactus3.png')
        globals.scrubs.append(textureSurface.texture)
        textureSurface = image.load('img/speedsign.png')
        globals.scrubs.append(textureSurface.texture)

        textureSurface = image.load('img/speed-dial.png')
        self.dashboard.append(textureSurface.texture)
        textureSurface = image.load('img/blinker-off.png')
        self.dashboard.append(textureSurface.texture)
        textureSurface = image.load('img/blinker-on.png')
        self.dashboard.append(textureSurface.texture)
        textureSurface = image.load('img/speed-needle.png')
        self.dashboard.append(textureSurface.texture)

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        #glGenerateMipmap(GL_TEXTURE_2D)

        # allocate a texture and add to the frame buffer
        w = 512
        h = 256
        self.fbtex = image.Texture.create_for_size(gl.GL_TEXTURE_2D, w, h, gl.GL_RGBA)


    # set the screen size
    def setScreenSize(self, w, h):
        self.w = w
        self.h = h

    # setup the OpenGL environment
    def setup(self):

        # One-time GL setup
        glEnable(GL_TEXTURE_2D)

        # Uncomment this line for a wireframe view
        #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        glLightfv(GL_LIGHT0, GL_POSITION, helpers.vec(.5, .5, 1, 0))
        #glLightfv(GL_LIGHT0, GL_SPECULAR, vec(.5, .5, 1, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, helpers.vec(1, 1, 1, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, helpers.vec(1, 1, 1, 1))

        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

        fogColor = helpers.vec((137/255.0), (134/255.0), (141/255.0), 1.0)
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        glFogfv(GL_FOG_COLOR, fogColor)
        glFogf(GL_FOG_START,  0.0)
        glFogf(GL_FOG_END,    80.0)
        glHint(GL_FOG_HINT, GL_NICEST)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMatrixMode(GL_MODELVIEW)

    # set up the rendering target of the mirror view
    def mirrorSetup(self):

        glGenFramebuffersEXT(1, ctypes.byref(self.fbo))
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.fbo)

        # add a depth buffer for correct render order
        glGenRenderbuffersEXT(1, ctypes.byref(self.depthbuffer))
        glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, self.depthbuffer)
        glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT, GL_DEPTH_COMPONENT, 512, 256)
        glFramebufferRenderbufferEXT(GL_FRAMEBUFFER_EXT, GL_DEPTH_ATTACHMENT_EXT, GL_RENDERBUFFER_EXT, self.depthbuffer)

        glBindTexture(gl.GL_TEXTURE_2D, self.fbtex.id)
        glFramebufferTexture2DEXT(GL_FRAMEBUFFER_EXT, GL_COLOR_ATTACHMENT0_EXT, GL_TEXTURE_2D, self.fbtex.id, 0)

        status = glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT)
        assert status == GL_FRAMEBUFFER_COMPLETE_EXT

        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)

    # free some memory
    def cleanup(self):
        glDeleteFramebuffersEXT(1, ctypes.byref(self.fbo))

    # setup a 2D view for the dashboard
    def set_2d(self, w, h):
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-1, 1, -1, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    # setup a view for textscreens
    def set_text(self, w, h):
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(-w/2, w/2, -h/2, h/2, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    # setup a view for the interactive environment
    def set_3d(self, w, h, angle=90.0):
        glEnable(GL_DEPTH_TEST)
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(angle, w / float(h), 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
