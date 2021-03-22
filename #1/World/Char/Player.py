import pygame
import pymunk
from pymunk.vec2d import Vec2d
import numpy as np
import math
import os
from World.Char.Character import Character, AnimType
from World.WorldObject import WorldObject
from World.WorldCommon import WorldObjects, ComputeDir, MoveDir, Camera, Server, CurrentSave, SocketModule, ChatOpen, DetectSurvivorDelay, Players, DamagedTimer

class Player(Character):

    _speed = 200.0

    _key_pressed = {
        pygame.K_w: False,
        pygame.K_a: False,
        pygame.K_s: False,
        pygame.K_d: False}

    def __init__(self, element = None, path = None, name = None, size = None, body_type = pymunk.Body.KINEMATIC):
        
        self.moveType = 'mouse' # Use to see if player's previously moved by mouse/key. Available value: 'mouse', 'key'
        self.server_name = None

        super().__init__(element=element,path=path,name=name,size=size,body_type=body_type)
        self.speed = Player._speed
        self._SendPlayerPosCooldown = 0

    def ProcessEvent(self,event):
        if self.server_name != SocketModule[0]._clientRole:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            left, middle, right = pygame.mouse.get_pressed()

            if left and not self.nic:
                self.moveType = 'mouse'
                self.charTarget = np.asfarray(pygame.mouse.get_pos()) - Camera
                self.lastdir, leng = ComputeDir(self.GetCenterPosition(), self.charTarget)
                if leng != 0:
                    self.charmove = True
            return True

        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE and not self.nic and not ChatOpen[0]:
            self.Attack(with_anim=True)
            if SocketModule[0]._clientConnection != None and SocketModule[0]._clientRole != None:
                SocketModule[0].SendMessageToServer(SocketModule[0]._clientRole,f'throw')
            return True

        if event.type == pygame.KEYDOWN:
            if event.key in Player._key_pressed:
                Player._key_pressed[event.key] = True
                return True

        elif event.type == pygame.KEYUP:
            if event.key in Player._key_pressed:
                Player._key_pressed[event.key] = False
                return True

        return False

    def Attack(self,with_anim=False):
        if with_anim:
            self.attacking = True
            self.animType = AnimType.ATTACK

            # This is here so that players won't stare at the same direction when spamming attacks.
            # And yes, for visual satisfaction, players won't change direction until they finished the attack animation.
            # Quite subtle when the animFrameLen is that low tho...
            self.ReloadAnimSurf()
            self.anim_obj.animTime = 0.001
            self.anim_obj.animFrameLen = 0.0417

        rock = WorldObject(path=os.path.dirname(__file__) + "/../../../#1/TinyAdventurePack/Other/Rock.png", name="rock", size=(15,15), body_type=pymunk.Body.DYNAMIC)
        rock.shape[0].friction = 0
        rock_dir = Vec2d(self.lastdir[0], self.lastdir[1])        
        rock_pos = self.GetCenterPosition() + rock_dir * (self.col_rect.width + self.col_rect.height) / 2 # + np.asfarray((0,-10))
        rock.SetCenterPosition(rock_pos)
        rock.visible = True
        rock_dir[1] = -rock_dir[1]
        rock.body.apply_impulse_at_world_point(rock_dir * 7500.0, rock.body.position)
        rock.timeToDestruction = 0.2
        WorldObjects.append(rock)

    def Knockback(self, src_pos, force):
         super().Knockback(src_pos, force)

    def Update(self, deltaTime):
        if not Server[0]:
            
            if self.attacking and self.anim_obj != None and self.anim_obj.animTime == 0:
                self.attacking = False
                self.anim_obj.animFrameLen = 0.1667
            
            if self.dead and self.animType != AnimType.DEAD and self.anim_obj != None and self.anim_obj.animTime == 0:
                self.animType = AnimType.DEAD
                self.ReloadAnimSurf()
                self.anim_obj.__init__(self.anim_obj.path, self.scale, frame_size=(30,25), frame_coord=[(0,0)])
                self.anim_obj.animFrameLen = 0.1667

            if self.server_name == SocketModule[0]._clientRole:
                moved = False
                key_dir = np.asfarray([0,0])
                if Player._key_pressed[pygame.K_w]:
                    key_dir[1] -= 1
                    moved = True
                if Player._key_pressed[pygame.K_a]:
                    key_dir[0] -= 1
                    moved = True
                if Player._key_pressed[pygame.K_s]:
                    key_dir[1] += 1
                    moved = True
                if Player._key_pressed[pygame.K_d]:
                    key_dir[0] += 1
                    moved = True

                if ChatOpen[0]:
                    moved = False

                if moved and not self.nic:
                    if key_dir[0] != 0 or key_dir[1] != 0:
                        self.moveType = 'key'
                        if 0 not in key_dir:
                            key_dir *= math.sqrt(0.5)
                        self.lastdir = key_dir
                        self.charTarget = self.GetCenterPosition() + key_dir * self.speed
                        self.charmove = True
                    else:
                        self.charmove = False
                        self.charTarget = self.GetCenterPosition()
                elif self.charmove and self.moveType == 'key':
                    self.charmove = False
                    self.charTarget = self.GetCenterPosition()
        
        super().Update(deltaTime)

    # Read the parent method in WorldObject.py to see why this is a thing.
    def SendPosData(self, deltaTime, force_upd=False):
        if not Server[0]:
            if self.server_name != SocketModule[0]._clientRole:
                return
            if self._SendPlayerPosCooldown <= 0 or force_upd:
                pos = self.GetCenterPosition()
                if abs(self.saved_pos[0] - pos[0]) > 0.1 or abs(self.saved_pos[1] - pos[1]) > 0.1:
                    self.saved_pos = pos
                    self._SendPlayerPosCooldown = 0.1
                    if SocketModule[0]._clientConnection != None and SocketModule[0]._clientRole != None:
                        SocketModule[0].SendMessageToServer(SocketModule[0]._clientRole,'move,{0},{1},{2},{3}'.format(*self.GetCenterPosition(), *self.lastdir))
            else:
                self._SendPlayerPosCooldown -= deltaTime

    def DetectCol(self):
        if Server[0]: # Player position is decided by the client via a solid SetCenterPosition. Server shouldn't modify it during collisions.
            super().DetectCol(False)
        else:
            super().DetectCol()
                
    def ProcessCollision(self):
        if len(self.collided_objs) < 1:
            return False

        for i in self.collided_objs:
            if Server[0] and i.name in ["Skel","Death"]:
                if self.hp > 0 and self.damaged_timer <= -1:
                    self.damaged_timer = DamagedTimer['p']
                    src_pos = i.GetCenterPosition()
                    if i.name == "Skel":
                        self.hp -= 1
                    elif i.name == "Death":
                        self.hp -= 3
                        print("What. You thought red hearts have to give you positive hp?")
                    if SocketModule[0]._serverConnection != None:
                        if SocketModule[0]._bridgeConnection['me'] != None:
                            player_num = 0 if self.name == 'Player1' else 1
                            SocketModule[0].SendMessageToClient('me',f'hit,p,{player_num},{src_pos[0]},{src_pos[1]},{self.hp}')
                        if SocketModule[0]._bridgeConnection['you'] != None:
                            player_num = 0 if self.name == 'Player2' else 1
                            SocketModule[0].SendMessageToClient('you',f'hit,p,{player_num},{src_pos[0]},{src_pos[1]},{self.hp}')
    def Revive(self):
        super().Revive()
        if not Server[0] and self.anim_obj != None:
            self.anim_obj.__init__(self.anim_obj.path, self.scale, frame_size=(30,25), frame_coord=[(0,0),(30,0),(60,0),(90,0),(120,0),(150,0)])

    def Death(self):
        if not self.dead:
            if not Server[0]:
                self.animType = AnimType.FALL
                self.ReloadAnimSurf()
                self.anim_obj.__init__(self.anim_obj.path, self.scale / (300 / 30), frame_size=(300,250), frame_coord=[(0,0),(300,0),(600,0),(900,0),(1200,0),(1500,0)])

                self.anim_obj.animTime = 0.001
                self.anim_obj.animFrameLen = 0.1667
            DetectSurvivorDelay[0] = 3.0

        super().Death()
        

    def Render(self,screen):
        super().Render(screen)