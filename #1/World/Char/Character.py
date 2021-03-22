import pygame
import pymunk
import math
import numpy as np
from World.WorldObject import WorldObject
from World.WorldCommon import PhysicsEngine, WorldObjects, MoveDir
from enum import IntEnum

class AnimType(IntEnum):
    IDLE = 0
    WALK = 1
    ATTACK = 2
    FALL = 3
    DEAD = 4

class AnimDir(IntEnum):
    DOWN = 0
    LEFT = 1
    UP = 2
    RIGHT = 3

class Character(WorldObject):

    _LoadedImages = {}

    _Enum2Path_Type = {
        AnimType.IDLE: "Idle",
        AnimType.WALK: "Walk",
        AnimType.ATTACK: "Attack",
        AnimType.FALL: "Fall",
        AnimType.DEAD: "Dead"
        }
    _Enum2Path_Dir = {
        AnimDir.DOWN: "down",
        AnimDir.LEFT: "left",
        AnimDir.UP: "up",
        AnimDir.RIGHT: "right"
        }

    def __init__(self, element = None, path = None, name = None, size = None, body_type = pymunk.Body.KINEMATIC):
        super().__init__(element=element,path=path,name=name,size=size,body_type=body_type)
        self.animDir = AnimDir.DOWN
        self.animType = AnimType.IDLE
        self.lastdir = np.asfarray([0.0, 1.0])
        self.nic = False    # Stands for Not In Control.
        self.lastAnimDir = self.animDir
        self.lastAnimType = self.animType
        self.charmove = False
        self.speed = 0
        self.charLastPos = self.GetCenterPosition()
        self.charTarget = self.charLastPos
        self.attacking = False

        self.ui_disp_obj = None
        self.max_hp = int(element.get("hp", default=10))
        self.hp = self.max_hp
        self.dead = False

    def ReloadAnimSurf(self):
        if self.anim_obj == None:
            return

        self.lastAnimDir = self.animDir
        self.lastAnimType = self.animType

        state_path = Character._Enum2Path_Type[self.animType]
        dir_path = Character._Enum2Path_Dir[self.animDir]

        if "Skeleton" in self.path:
            char_path = "Skeleton"
        elif "Character" in self.path:
            char_path = "Character/"
            if self.name == "Player1":
                char_path += "Char_one"
            elif self.name == "Player2":
                char_path += "Char_two"
            else:
                char_path = None

        if char_path:
            whole_path = "TinyAdventurePack/{0}/{1}/Char_{2}_{3}.png".format(char_path, state_path, state_path.lower(), dir_path)
            if whole_path in Character._LoadedImages.keys():
                self.anim_obj.path = whole_path
                self.anim_obj.img = Character._LoadedImages[whole_path]
            else:
                self.anim_obj.path = whole_path
                self.anim_obj.img = pygame.image.load(whole_path)
                Character._LoadedImages[whole_path] = self.anim_obj.img

    def SetCenterPosition(self, pos, safeMove = False):
        super().SetCenterPosition(pos, safeMove)
        if safeMove:
            self.charLastPos = self.GetCenterPosition()

    def Update(self, deltaTime):
        if self.hp <= 0:
            self.Death()
        # Note that Enemy's damaged_timer is always -1, so it gets nic only when it's dead.
        self.nic = False if self.damaged_timer <= -1 and not self.dead else True

        if not self.nic:
            if self.charmove:
                self.charmove = MoveDir(self, self.lastdir, self.charTarget, self.speed, deltaTime)
                self.animType = AnimType.WALK if not self.attacking else AnimType.ATTACK
            else: # self.attacking will never be True for those that don't attack. Donut worry.
                self.animType = AnimType.IDLE if not self.attacking else AnimType.ATTACK

            if self.anim_obj != None:
                curPos = self.GetCenterPosition()
                curDir = curPos - self.charLastPos
                self.charLastPos = curPos
                

                if curDir[0] != 0 or curDir[1] != 0:
                    # Inconsistency happens when player goes exactly 45 degrees, hence the rounding
                    if math.fabs(round(curDir[0],5)) > math.fabs(round(curDir[1],5)):
                        if curDir[0] > 0:
                            self.animDir = AnimDir.RIGHT
                        else:
                            self.animDir = AnimDir.LEFT

                    else:
                        if curDir[1] > 0:
                            self.animDir = AnimDir.DOWN
                        else:
                            self.animDir = AnimDir.UP

            if self.lastAnimDir != self.animDir and not self.attacking:
                self.ReloadAnimSurf()
            elif self.lastAnimType != self.animType:
                self.ReloadAnimSurf()

        if self.ui_disp_obj != None:
            self.ui_disp_obj.surf = pygame.transform.scale(self.surf, (self.ui_disp_obj.width, self.ui_disp_obj.height))

        super().Update(deltaTime)

    def GetData(self):
        pos = self.GetCenterPosition()
        return {
            'x': float(pos[0]),
            'y': float(pos[1]),
            'hp': self.hp
        }

    def DetectCol(self,push=True):
        if len(self.collided_objs) > 0:
            self.collided_objs = []
        bodies = []

        for i in self.shape:
            result = PhysicsEngine[0].shape_query(i)
            direction_taken = [False, False]

            for r in result:
                # Well, if I don't do this, the chars' shape will collide itself if it has multiple. Then the char will become a bullet itself.
                if r.shape in self.shape:
                    continue
                bodies.append(r.shape._get_body())

                if push:
                    points = r.contact_point_set.points
                    if len(points) > 0:
                        n = r.contact_point_set.normal * points[0].distance
                        p = self.GetCenterPosition()

                        # If char collides with 2+ shapes, and both shapes push it in the same direction,
                        #   the char gets pushed further than expected.
                        # These 4 conditions below fixes that, along with direction_taken.
                        if direction_taken[0]:
                            n.x = 0
                        if direction_taken[1]:
                            n.y = 0
                        if abs(n.x) > 0.0:
                            direction_taken[0] = True
                        if abs(n.y) > 0.0:
                            direction_taken[1] = True

                        # The ultimate fix exclusively for Circles. Otherwise the chars will get stuck inside the circle. Stupid circles with their weird normals.
                        if isinstance(r.shape, pymunk.Circle):
                            n.x = -n.x
                            if isinstance(i, pymunk.Circle):
                                n.x = -n.x
                                n.y = -n.y
                        else:
                            n.y = -n.y

                        p += n
                        self.SetCenterPosition(p, safeMove=True)

            if True in direction_taken:
                break

        for i in WorldObjects:
            if i.body in bodies:
                self.collided_objs.append(i)

    # Remember Revive is NOT spammed and is only run in World.py.
    def Revive(self):
        orig_pos = self.orig_pos if self.element != None else np.asfarray([0,0])
        self.SetCenterPosition(orig_pos)
        self.charLastPos = self.GetCenterPosition()
        self.animDir = AnimDir.DOWN # This plus above ensure everyone always spawns facing downward.
        self.hp = self.max_hp
        self.dead = False

    # Remember Death is spammed when hp = 0.
    def Death(self):
        if not self.dead:
            self.dead = True

    def Render(self,screen):
        super().Render(screen)