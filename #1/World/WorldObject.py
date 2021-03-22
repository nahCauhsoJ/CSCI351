import pygame
import pymunk
import math
import numpy as np
from World.AnimObject import AnimObject
from World.WorldCommon import PymunkCallback, ScreenSize, ComputeDir, Camera, Server, DamagedTimer
import os

objectWidth = 32
objectHeight = 32

class WorldObject:

    def __init__(self,
                 element = None,
                 path = None,
                 name= None,
                 size = None,
                 body_type = pymunk.Body.STATIC,
                 mass = 10,
                 moment = 10):
        self.body = None
        self.body_type = body_type
        self.element = None
        self.group = None
        
        if element != None:
            if path == None:
                self.path = element.get("path")
                if self.path != None:
                    self.path = os.path.dirname(__file__) + "/../" + self.path
            else:
                self.path = path
            self.name = element.get("name")
            s = element.get("scale")
            self.element = element
        else:
            self.path = path
            self.name = name
            s = None

        self.surf = pygame.image.load(self.path) if self.path != None else None

        self.scale = 4 if s == None else float(s)
        if size == None:
            self.size = np.asfarray(self.surf.get_rect().size) * self.scale
        else:
            self.size = np.asfarray(size)
        self.surf = pygame.transform.scale(self.surf, (int(self.size[0]), int(self.size[1]))) if self.surf else None
        self.pos = np.asfarray([0,0]) # Remember self.pos repr. top-left, but most code use GetCenterPosition. Try not to reference self.pos.
        self.orig_pos = self.pos if element == None else np.asfarray(( float(element.get("x")), float(element.get("y")) )) # Mainly used for resetting. Note that, unlike self.pos, self.orig_pos repr. center, NOT top-left

        if element != None:
            self.SetCenterPosition(self.orig_pos)
        self.rect = pygame.Rect(self.pos, self.size)

        self.col_type = "box"
        self.col_rect = None
        self.ghost = True # When True, it means self.body isn't registered to the Physics Engine.
        self.collided_objs = []
        self.timeToDestruction = -1
        self.SetCollisionBox(mass=mass, moment=moment)

        self.damaged_timer = -1
        self.anim_obj = None
        self.visible = False

        # ! For server use ONLY !
        # If the character moved or took damage, it'll be set to True.
        # Will be set to False once its data is stored in database.
        # Those that won't be in database will be forever dirty, well but that matters not.
        self.dirty = False # Originally planned that WorldObjects can also be moved, but I guess we're not going that far...
        self.save_cd = 0.0

        # There are too much uncertainties of how an object is moved. So if any difference from this exceeds the tolerance, the position is updated.
        self.saved_pos = self.orig_pos # Tolerance is hard-coded as 0.1.
        # Even if movable objects don't exist in this game, it feels right to put it here.

    def AnimInit(self, frame_size = (0,0), frame_coord = [(0,0)]):
        self.anim_obj = AnimObject(self.path,self.scale,frame_size,frame_coord)
        center_pos = self.GetCenterPosition()
        self.size = self.anim_obj.size
        self.SetCenterPosition(center_pos) # Note that SetCenterPosition is influenced by self.size.
        self.rect = pygame.Rect(self.pos, self.size)
        self.SetCollisionBox()

    def SetCenterPosition(self, pos, safeMove = False):
        self.pos = pos - (self.size / 2)

        # self.body_type is the preset type, self.body.body_type is what changes
        if self.body != None:
            center = self.GetCenterPosition()
            self.body.position = center[0], ScreenSize[1] - center[1]
            PymunkCallback[0].reindex_shapes_for_body(self.body)

    def GetCenterPosition(self):
        return self.pos + (self.size / 2)

    def ChangeBodyType(self,t):
        new_body = pymunk.Body(1,4294967296,t)
        center = self.GetCenterPosition()
        new_body.position = center[0], ScreenSize[1] - center[1]
        self.RemoveCollisionBox()
        # Basically, any code that needs to run between 2 Pymunk methods can be wrapped with a function
        #   and put it in the same queue as those Pymunk functions, and run them after .step() is executed.
        # Race condition SUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUCKs
        def f1(self,new_body):
            for i in self.shape:
                i._set_body(new_body)

            self.body = new_body
        PymunkCallback[0].custom(f1,self,new_body)
        PymunkCallback[0].add(new_body, *self.shape)
        self.ghost = False

    # Never use Knockback on the server side.
    def Knockback(self, src_pos, force):
        if self.body_type != pymunk.Body.DYNAMIC:
            self.ChangeBodyType(pymunk.Body.DYNAMIC)
        self.damaged_timer = DamagedTimer['p']
        dir = ComputeDir(src_pos, self.GetCenterPosition())
        dir[0][1] = -dir[0][1]
        def f1(self):
            self.body.apply_impulse_at_local_point(dir[0] * force, self.body.position)
        PymunkCallback[0].custom(f1,self)

    def RemoveCollisionBox(self):
        if not self.ghost:
            PymunkCallback[0].remove(*self.shape, self.body)
            self.ghost = True

    # I probably have to draw a ton of vertices to make the pymunk.Poly
    #   look round. So here's round_edges indicating how many vertices will be used.
    #   The more it uses, the slower the game. Ofc, rectangles don't use it.
    def SetCollisionBox(self, round_edges = 64, mass = 10, moment = 10):
        self.RemoveCollisionBox()
        self.col_rect = pygame.Rect((0,0), self.size)
        
        self.body = pymunk.Body(mass, moment, self.body_type)
        # Again, we don't want self.body.position to be an integer, which is what
        #   GetCollisionBoxCenter() gives.
        center = self.GetCenterPosition()
        self.body.position = center[0], ScreenSize[1] - center[1]
        PymunkCallback[0].reindex_shapes_for_body(self.body)
        
        self.shape = []
        self.ghost = False
        box = self.GetCollisionBox()
        offset = np.asfarray((0,0))
        if self.element != None:
            col_elem = self.element.find("Col")
            if col_elem != None:
                self.col_rect = pygame.Rect((int(col_elem.get("xoff")),
                                            int(col_elem.get("yoff"))), 
                                            (int(col_elem.get("w")), 
                                             int(col_elem.get("h"))))
                self.col_type = col_elem.get("type")
                offset += self.col_rect.topleft
                offset[1] *= -1

                if self.col_type == 'oval':
                    # quadrant_coords contain round_edges / 4 + 1 elements.
                    #   The last one is the first pair of coords in the next quadrant.
                    # Vertices are obtained anti-clockwised, starting at (box.w, 0).
                    poly = []
                    quadrant_coords = []
                    r_major = self.col_rect.w / 2
                    r_minor = self.col_rect.h / 2

                    for i in range(round_edges // 4 + 1):
                        ix = r_major * math.sin(math.radians(90 * i / (round_edges // 4)))
                        iy = math.sqrt( (1 - ix**2 / r_major**2) * r_minor**2 )
                        quadrant_coords.append((ix,iy))
                    
                    for i in quadrant_coords[:-1]:
                        poly.append( np.asfarray((i[0], i[1])) + offset)
                    for i in quadrant_coords[:0:-1]:
                        poly.append( np.asfarray((-i[0], i[1])) + offset)
                    for i in quadrant_coords[:-1]:
                        poly.append( np.asfarray((-i[0], -i[1])) + offset)
                    for i in quadrant_coords[:0:-1]:
                        poly.append( np.asfarray((i[0], -i[1])) + offset)
                    self.shape.append( pymunk.Poly(self.body, poly) )
                    PymunkCallback[0].add(self.body, *self.shape)

                elif self.col_type == "capsule":
                    if self.col_rect.w > self.col_rect.h:
                        off = (self.col_rect.w - self.col_rect.h) / 2
                        dim = (np.asfarray((-off, -self.col_rect.h/2)) + offset,
                               np.asfarray((off, -self.col_rect.h/2)) + offset,
                               np.asfarray((off, self.col_rect.h/2)) + offset,
                               np.asfarray((-off, self.col_rect.h/2)) + offset)
                        self.shape.append( pymunk.Circle(self.body, self.col_rect.h/2, np.asfarray((off, 0)) + offset) )
                        self.shape.append( pymunk.Poly(self.body, dim) )
                        self.shape.append( pymunk.Circle(self.body, self.col_rect.h/2, np.asfarray((-off, 0)) + offset) )
                    elif self.col_rect.w < self.col_rect.h:
                        off = (self.col_rect.h - self.col_rect.w) / 2
                        dim = (np.asfarray((-self.col_rect.w/2, -off)) + offset,
                               np.asfarray((-self.col_rect.w/2, off)) + offset,
                               np.asfarray((self.col_rect.w/2, off)) + offset,
                               np.asfarray((self.col_rect.w/2, -off)) + offset)
                        self.shape.append( pymunk.Circle(self.body, self.col_rect.w/2, np.asfarray((0, off)) + offset) )
                        self.shape.append( pymunk.Poly(self.body, dim) )
                        self.shape.append( pymunk.Circle(self.body, self.col_rect.w/2, np.asfarray((0, -off)) + offset) )
                    else:
                        self.shape.append( pymunk.Circle(self.body, self.col_rect.w/2, offset) )

                    PymunkCallback[0].add(self.body, *self.shape)
                    
                else:
                    dim = (np.asfarray((-self.col_rect.w/2, -self.col_rect.h/2)) + offset,
                               np.asfarray((-self.col_rect.w/2, self.col_rect.h/2)) + offset,
                               np.asfarray((self.col_rect.w/2, self.col_rect.h/2)) + offset,
                               np.asfarray((self.col_rect.w/2, -self.col_rect.h/2)) + offset)
                    self.shape = [ pymunk.Poly(self.body, dim) ]
                    PymunkCallback[0].add(self.body, *self.shape)

                return

        # Remember this will not run if col_elem is not None.
        self.shape.append( pymunk.Poly.create_box(self.body, box.size) )
        PymunkCallback[0].add(self.body, *self.shape)

    def GetCollisionBox(self):
        return pygame.Rect(self.pos + np.asfarray(self.col_rect.topleft), self.col_rect.size)

    def GetCollisionBoxCenter(self):
        box = self.GetCollisionBox()
        return np.asfarray([box.x + (box.w / 2), box.y + (box.h / 2)])

    def ProcessEvent(self,event):
        return False

    def Update(self, deltaTime):
        if self.damaged_timer > 0: # Note that damaged_timer is measured in seconds.
            if Server[0]:
                self.dirty = True # Being knocked means it moves, right?
            self.damaged_timer -= deltaTime

        elif self.damaged_timer != -1:
            self.damaged_timer = -1

        if self.body.body_type == pymunk.Body.DYNAMIC:
            # MUST NOT USE GetCollisionBoxCenter! It causes inconsistency in position due to its nature
            #   of rounding off floats
            center = self.GetCenterPosition()
            self.pos[0] = self.body.position[0] - (center[0] - self.pos[0])
            self.pos[1] = (ScreenSize[1] - self.body.position[1]) - (center[1] - self.pos[1])
            if self.body_type == pymunk.Body.KINEMATIC and self.damaged_timer == -1:
                self.ChangeBodyType(self.body_type)
                # Due to how direction is calculated by curPos - lastCharPos, knocking back will always put them in opposite direction.
                #   So here's a manual fix to make the player maintain same direction.
                self.charLastPos = self.GetCenterPosition()
                if not Server[0]:
                    self.SendPosData(deltaTime,force_upd=True)

        self.rect.x = self.pos[0]
        self.rect.y = self.pos[1]

        if self.timeToDestruction != -1:
            self.timeToDestruction -= deltaTime
            if self.timeToDestruction < 0:
                self.timeToDestruction = 0

    def DetectCol(self):
        pass

    def ProcessCollision(self):
        pass

    # All movable characters send its position data to server/client. But inconsistency happens due to local collision updating position.
    #   Hence, this method is created to specifically send data AFTER the collision is processed.
    # Also, since all data sending has a cooldown, a deltaTime here is a must.
    def SendPosData(self, deltaTime, force_upd=False):
        pass

    def Render(self, screen):
        rect = self.rect.copy()
        rect.x += int(Camera[0])
        rect.y += int(Camera[1])

        if self.anim_obj != None:
            self.surf = self.anim_obj.surf

        if self.visible:
            screen.blit(self.surf, rect)