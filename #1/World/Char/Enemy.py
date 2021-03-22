import pygame
import numpy as np
from World.Char.Character import Character, AnimType
from World.Char.NPCState import State
from UI.UICommon import engage_objs, groupDict
from World.WorldCommon import Server, SocketModule, WorldObjects, CurrentSave, Players, Enemies
import requests

class Enemy(Character):

    # Remember to put this method in a thread...
    @classmethod
    def LoadEnemies(cls):
        try:
            return requests.get(url=f"http://localhost:5005/games/{CurrentSave[0]}/enemyload").json()
        except:
            print("Loading failed. Guess the server's down.")
            return {}

    _ReadyToRender = 0 # 0: Not yet, -1: Asking World.Update to make them visible, 1: rendered        

    _EnemyIdIncrement = 0

    @classmethod
    def GenId(cls):
        # id() exists, but it gens inconsistent ID every game, so I had to make a generator myself.
        # Also, with this generator, it's easy to link Enemy objects via matching self.enemy_id.
        Enemy._EnemyIdIncrement += 1
        return Enemy._EnemyIdIncrement

    def __init__(self, element=None, path=None, name=None, size=None):
        self.enemy_id = Enemy.GenId()
        self.curState = None
        self.stateList = {}
        self._SendEnemyPosCooldown = 0

        # Kinda like a global variable for the states, since idle and chase share different attributes.
        # Don't change it, NPCState will overwrite it anyways.
        self.target = None

        if element != None:
            ai = element.find("AI")
            if ai != None:
                for state in ai.findall("State"):
                    s = State(state)
                    self.stateList[s.name] = s
                    if self.curState == None:
                        self.curState = s.name

        self.engage_timer = -1

        super().__init__(element=element, path=path, name=name, size=size)

    def LoadEnemyData(self,enemy_id,enemy_data):
        for i in Enemies:
            if isinstance(i, Enemy) and i.enemy_id == int(enemy_id):
                break
        else:
            # Remember, dead enemies exists as 0 hp.
            print("<Database> Can't find this Enemy object in the world.")
            return False

        if "x" not in enemy_data or "y" not in enemy_data or "hp" not in enemy_data:
            print("<Database> Loading invalid data into Enemy object")
            return False

        self.SetCenterPosition(np.asfarray([enemy_data["x"], enemy_data["y"]]))
        self.hp = enemy_data["hp"]

    def ProcessCollision(self):
        if len(self.collided_objs) < 1:
            return False

        for i in self.collided_objs:
            if i.name in ["rock"]:
                if Server[0]:
                    if self.hp > 0:
                        src_pos = i.GetCenterPosition()
                        if i.name == "rock":
                            i.timeToDestruction = 0
                            self.hp -= 1
                        if SocketModule[0]._serverConnection != None:
                            if SocketModule[0]._bridgeConnection['me'] != None:
                                SocketModule[0].SendMessageToClient('me',f'hit,e,{self.enemy_id},{src_pos[0]},{src_pos[1]},{self.hp}')
                            if SocketModule[0]._bridgeConnection['you'] != None:
                                SocketModule[0].SendMessageToClient('you',f'hit,e,{self.enemy_id},{src_pos[0]},{src_pos[1]},{self.hp}')
                else:
                    if self.hp > 0:
                        self.ShowHp()
                        self.engage_timer = 100
    
    def ShowHp(self):
        if self in engage_objs:
            return

        engage_objs.append(self)

    def HideHp(self):
        if self not in engage_objs:
            return
        
        engage_objs.remove(self)
        self.ui_disp_obj = None # engage_objs lost reference to this, so we have to do it here.

    def Update(self, deltaTime):
        if not Server[0] and not SocketModule[0]._goodConnection:
            self.charmove = False # This is to stop enemies from moving if the connection is cut.

        if self.curState != None and not self.dead:
            result = self.stateList[self.curState].Update(self,deltaTime)
            if result:                
                self.stateList[self.curState].action.Enter(self)

        if self.engage_timer > -1:
            if self.engage_timer == 0 and self.curState == "Idle":
                self.HideHp()
            self.engage_timer -= 1

        super().Update(deltaTime)

    # Read the parent method in WorldObject.py to see why this is a thing.
    def SendPosData(self,deltaTime,force_upd=False):
        if Server[0]:
            if self._SendEnemyPosCooldown <= 0:
                pos = self.GetCenterPosition()
                if abs(self.saved_pos[0] - pos[0]) > 0.1 or abs(self.saved_pos[1] - pos[1]) > 0.1:
                    self.saved_pos = pos
                    self._SendEnemyPosCooldown = 0.02
                    self.dirty = True
                    if SocketModule[0]._serverConnection != None:
                        if SocketModule[0]._bridgeConnection['me'] != None:
                            SocketModule[0].SendMessageToClient('me','moveenemy,{0},{1},{2}'.format(*self.GetCenterPosition(), self.enemy_id))
                        if SocketModule[0]._bridgeConnection['you'] != None:
                            SocketModule[0].SendMessageToClient('you','moveenemy,{0},{1},{2}'.format(*self.GetCenterPosition(), self.enemy_id))
            else:
                self._SendEnemyPosCooldown -= deltaTime

    def Revive(self):
        super().Revive()
        self.SetCollisionBox()
        self.visible = True

    def Death(self):
        if not self.dead:
            self.RemoveCollisionBox()
            self.visible = False
            self.engage_timer = -1
            self.HideHp()
        super().Death()
        self.stateList[self.curState].action.Exit(self)
        self.curState = "Idle"

    def Cleanup():
        Enemy._EnemyIdIncrement = 0
        Enemy._ReadyToRender = 0