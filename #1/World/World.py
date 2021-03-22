
import pygame
import pymunk
import pymunk.pygame_util
import numpy as np
import requests
import threading
import os

from World.WorldObject import WorldObject, objectWidth, objectHeight
from World.Char.Player import Player
from World.Char.Enemy import Enemy
import xml.etree.ElementTree as ET
from World.WorldCommon import DataRoot, PhysicsEngine, PymunkCallback, PymunkCallbackClass, WorldObjects, Players, Enemies, ComputeDir, Paused, Camera, ScreenSize, CurrentSave, Server, TempCleanup, SocketModule, DetectSurvivorDelay
# ComputeDir is used in GameMain.py in MGS project. Don't ignore it!

def Init(size, screen, save=None):
    global _width
    global _height
    global _grass
    global _objectRect
    
    global physics
    global _draw_options

    if size == None or screen == None:
        Server[0] = True
    if save != None:
        CurrentSave[0] = save

    PhysicsEngine[0] = pymunk.Space()
    PhysicsEngine[0].gravity = 0,0
    PymunkCallback[0] = PymunkCallbackClass()

    if not Server[0]:
        _draw_options = pymunk.pygame_util.DrawOptions(screen)
        _width, _height = size
        _grass = pygame.image.load("TinyAdventurePack/Other/grass.png")
        _grass = pygame.transform.scale(_grass, (objectWidth, objectHeight))
        _objectRect = pygame.Rect(0, 0, objectWidth, objectHeight)

    tree = ET.parse(os.path.dirname(__file__) + "/../Data/WorldData.xml")
    root = tree.getroot()
    DataRoot[0] = root

    objects = root.find("Objects")
    if objects != None:
        for object in objects.findall("Object"):
            wo = WorldObject(element=object)
            WorldObjects.append(wo)

    # Unlike players, Enemies won't join or leave the game, so it's fine for clients to pre-load them.
    enemies = root.find("Enemies")
    if enemies != None:
        if Server[0]:
            import Database.database as db # The system doesn't know whether it's client or server until Init() is run, so had to put it here
            enemy_list = db.GetEnemyData(save)
            # Remember that only the server's side can run this
            for enemy in enemies.findall("Enemy"):
                wo = Enemy(element=enemy)
                WorldObjects.append(wo)
                Enemies.append(wo)
                center_pos = wo.GetCenterPosition()
                wo.size[0] /= 6 # Similar to AnimInit, this one is hard-coded. Rmb that size is calculated by self.surf.get_rect, so we have to divide width by number of frames.
                wo.SetCenterPosition(center_pos) # Note that SetCenterPosition is influenced by self.size.
                for i in enemy_list:
                    if 'enemy_id' in i and wo.enemy_id == int(i['enemy_id']):
                        if 'enemy_data' in i:
                            wo.LoadEnemyData(i['enemy_id'],i['enemy_data'])
                        else:
                            wo.RemoveCollisionBox()
                            del wo
                        break
                else:
                    db.NewEnemyData(save, wo.enemy_id, wo.GetData())
                
        else:
            # It'll be weird if the player is allow a few seconds to run away while enemies are loading,
            #   so I won't bother making a thread for this.
            LoadAllEnemyData(enemies)

    PymunkCallback[0].exec()



def ProcessEvent(event):
    for i in WorldObjects:
        if i.ProcessEvent(event) == True:
            return True

def _SortWorldObjects(worldObject):
    box = worldObject.GetCollisionBox()
    return box.y + box.height

_timeStep = 1.0/60.0
_timeSinceLastFrame = 0
_timeSinceLastSave = 0
# WARNING: In the server, this runs even before Players are added
def Update(deltaTime):
    global _timeStep
    global _timeSinceLastFrame
    global _timeSinceLastSave

    _timeSinceLastFrame += deltaTime
    while (_timeSinceLastFrame >= _timeStep):
        PhysicsEngine[0].step(_timeStep)
        _timeSinceLastFrame -= _timeStep
    PymunkCallback[0].exec()

    if not Server[0]:
        camera_aim_num = 0 if Players[0].dead == False or len(Players) < 2 else 1
        c = -(Players[camera_aim_num].GetCenterPosition() - (ScreenSize[0]//2.0, ScreenSize[1]//2.0))
        Camera[0] = c[0]
        Camera[1] = c[1]

        if Enemy._ReadyToRender == -1:
            for i in WorldObjects:
                if isinstance(i, Enemy):
                    i.visible = True
            Enemy._ReadyToRender = 1

    for i in WorldObjects:
        i.Update(deltaTime)
        if i.anim_obj != None: # Objects from server won't have anim_obj anyways.
            i.anim_obj.Update(deltaTime)

    i = len(WorldObjects) - 1
    while i >= 0:
        # Players and Enemies dying won't get them removed. They have a spcial way to die.
        if WorldObjects[i].timeToDestruction == 0:
            WorldObjects[i].RemoveCollisionBox()
            temp = WorldObjects[i]
            WorldObjects.remove(temp)
        i -= 1

    for i in WorldObjects:
        i.DetectCol()

    for i in WorldObjects:
        i.ProcessCollision()

    for i in WorldObjects:
        i.SendPosData(deltaTime)

    if not Server[0]:
        WorldObjects.sort(key=_SortWorldObjects)

    DetectSurvivors(deltaTime)

def LoadAllEnemyData(enemies):
    enemy_data_all = Enemy.LoadEnemies()
    if len(enemy_data_all) > 0:
        for enemy in enemies.findall("Enemy"):
            wo = Enemy(element=enemy)
            for i in enemy_data_all:
                if wo.enemy_id == int(i['enemy_id']):
                    WorldObjects.append(wo)
                    Enemies.append(wo)
                    wo.LoadEnemyData(i['enemy_id'],i['enemy_data'])
                    wo.AnimInit(frame_size=(30,25), frame_coord=[(0,0),(30,0),(60,0),(90,0),(120,0),(150,0)])
                    wo.anim_obj.LoadFrame(0)
    Enemy._ReadyToRender = -1

def LoadPlayer(p=0,server=True):
    if p == 0:
        players = DataRoot[0].find("Player")
        if players != None:
            player = Player(element=players)
            if server: player.server_name = 'me'
    else:
        player = Player(element=Players[0].element)
        if server: player.server_name = 'you'
        if server:
            player.path = "TinyAdventurePack/Character/Char_two/Idle/Char_idle_down.png"
            player.name = "Player2"
        else:
            if SocketModule[0]._clientRole == "me":
                # Bear in mind that objects that use AnimObject does not use .path for rendering, but .path inside the AnimObject class.
                player.path = "TinyAdventurePack/Character/Char_two/Idle/Char_idle_down.png"
                player.name = "Player2"
                player.visible = True # Remember this was only set for Player 1 when the world first loaded. Hence you need to set manually here.
                player.ReloadAnimSurf()
            else:
                player.path = "TinyAdventurePack/Character/Char_one/Idle/Char_idle_down.png"
                player.name = "Player1"
                player.visible = True
                player.ReloadAnimSurf()
                Players[0].name = "Player2"
                Players[0].ReloadAnimSurf()

    WorldObjects.append(player)
    Players.append(player)

    # When AnimInit is used, self.size will be overwritten, and hence need not to pre-define.
    # If a different size is needed, just use scale.
    if server:
        import Database.database as db # The system doesn't know whether it's client or server until Init() is run, so had to put it here
        import json # Well, might as well. This is the only place that needs json.
        data = db.GetCharData(CurrentSave[0],p=p) # By the time this runs, 'you' should be initiated in database since it runs MAG.py first.
        if len(data) > 0:
            data = json.loads(data)
            # Similar to AnimInit, this one is hard-coded. Rmb that size is calculated by self.surf.get_rect, so we have to divide width by number of frames.
            # Also rmb to set the size BEFORE .SetCenterPosition. Cuz this function relies on the size as well.
            player.size[0] /= 6
            player.SetCenterPosition(np.asfarray([data["x"],data["y"]]), safeMove=True)
            player.charTarget = np.asfarray([data["x"],data["y"]])
            player.hp = data["hp"]
        else:
            raise ValueError("We're unable to get player data and we cannot let this slip by. Get slapped by a Value Error.")

    else:
        player.AnimInit(frame_size=(30,25), frame_coord=[(0,0),(30,0),(60,0),(90,0),(120,0),(150,0)])
        player.anim_obj.LoadFrame(0)

def DelPlayer2():
    if len(Players) > 1:
        # We can easily find the player object, so let's not bother timeToDestruction.
        temp = Players.pop()
        WorldObjects.remove(temp)
        temp.RemoveCollisionBox()
        for i in Enemies:
            if i.target != None and i.target.name == temp.name:
                i.target = None

def DetectSurvivors(deltaTime):
    if DetectSurvivorDelay[0] == -6.9:
        return

    if DetectSurvivorDelay[0] > 0:
        DetectSurvivorDelay[0] -= deltaTime
        return

    if DetectSurvivorDelay[0] <= 0:
        all_dead = True
        if len(Players) >= 2:
            if Players[1].dead == False:
                all_dead = False
        if Players[0].dead == False:
            all_dead = False

        if all_dead == False:
            return

    # The below stuff only runs if none of the above detections do a return.
    DetectSurvivorDelay[0] = -6.9 # Bear in mind that the stuff below only runs once due to this line.
    for i in [*Players, *Enemies]:
        i.Revive()
        if Server[0]:
            i.dirty = True
    # Player 2 can be offline. So a manual revival is done directly on the database. 
    # The game can't run anyways if the database is offline, so I won't bother making a thread.
    if Server[0]: # Again, remember this is an exclusive revival for Player 2 if he's offline.
        import Database.database as db # The system doesn't know whether it's client or server until Init() is run, so had to initialize it here.
        if len(Players) < 2 and len( db.GetCharData(CurrentSave[0], 1) ) > 0:
            player_data = {'x':Players[0].orig_pos[0],'y':Players[0].orig_pos[1],'hp':Players[0].max_hp}
            db.SavePlayerData(player_data, CurrentSave[0], 1)

def Render(screen):

    global _width
    global _height
    global _grass
    global _objectRect
    global _draw_options

    _objectRect.x = 0
    _objectRect.y = 0
    for i in range(_width // objectWidth):
        _objectRect.x = i * objectWidth
        for j in range(1 + _height // objectHeight):
            _objectRect.y = j * objectHeight
            screen.blit(_grass, _objectRect)

    for i in WorldObjects:
        i.Render(screen)

    #PhysicsEngine[0].debug_draw(_draw_options)

def Cleanup():
    TempCleanup()
    Enemy.Cleanup()