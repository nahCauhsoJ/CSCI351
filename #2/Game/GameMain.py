import pygame
import sys
import threading
import time
import Network.mySocket as sck
import Database.database as db
import numpy as np
from pymunk.vec2d import Vec2d

sys.path.append('../#1')
import World.World as WW
sys.path.pop()

pygame.init()

_disconnect = True
Started = False
Multiplayer = False
def GameLoop(save=0):
    global Started
    global _disconnect
    global Multiplayer
    _gTickLastFrame = pygame.time.get_ticks()
    while True:
        t = pygame.time.get_ticks()
        # Somehow, if you initiate _gDeltaTime outside the while loop, _gDeltaTime does not update.
        #   Did some tests and realize it's another side effect of threading.
        #   And since I can't define it outside, I had to put this process to the top of the while loop.
        _gDeltaTime = (t - _gTickLastFrame) / 1000.0
        _gTickLastFrame = t

        if sck._clientLoaded: # This means that if any client is loaded, the world will start updating
            WW.Update(_gDeltaTime)
        if not sck.isConnected('me'):
            sck.SendMessageToClient('you','leave')
            _disconnect = True
            Started = False
            WW.Cleanup()
            print("The host is offline. World closed.")
            break
        if Multiplayer and not sck.isConnected('you'):
            WW.DelPlayer2()
            sck.SendMessageToClient('me','leave') # This tells the visitor player to quit, not the host
            Multiplayer = False
        

        for i in [*WW.Players, *WW.Enemies]:
            # timeSinceLastSave doesn't fit what I'm doing here, so I changed the name completely.
            if i.save_cd > 0.0:
                i.save_cd -= _gDeltaTime
            if i.dirty and i.save_cd <= 0.0:
                i.save_cd += 3.0
                print(f"<Autosave> Saving position of {i.name}...")
                if isinstance(i, WW.Enemy):
                    i.dirty = False
                    db.SaveEnemyData(i.GetData(), save, i.enemy_id)
                elif isinstance(i, WW.Player):
                    i.dirty = False
                    p = 0 if i.name == "Player1" else 1 # This Player1 is set in the xml file, equal to "me" in database
                    db.SavePlayerData(i.GetData(), WW.CurrentSave[0], p=p)
            
        # Somehow, the 'gimmerole' message can't reach here. Another race issue with threading, perhaps...
        #   So don't bother detecting it.
        for i in ['me','you']:
            player_num = 0 if i == 'me' else 1

            msg_got = sck.GetMessage(i)
            if msg_got != None:
                msg = msg_got.split(',')

                if msg[0] == 'move':
                    msg[0] = 'moveother'
                    if i == 'you' and sck._bridgeConnection['me'] != None:
                        sck.SendMessageToClient('me', ",".join(msg))
                    elif i == 'me' and sck._bridgeConnection['you'] != None:
                        sck.SendMessageToClient('you',",".join(msg))
                    # In WW.Players, logically, 0 is always the host.
                    p_obj = WW.Players[player_num]
                    oldpos = p_obj.GetCenterPosition()
                    p_obj.SetCenterPosition(np.asfarray(( float(msg[1]),float(msg[2]) )), True)
                    p_obj.charTarget[0], p_obj.charTarget[1] = float(msg[1]), float(msg[2])
                    p_obj.lastdir[0], p_obj.lastdir[1] = float(msg[3]), float(msg[4])
                    p_obj.dirty = True
                        
                elif msg[0] == 'chat':
                    if sck._bridgeConnection['me'] != None:
                        sck.SendMessageToClient('me',f'chat,{i},{",".join(msg[1:])}')
                    if sck._bridgeConnection['you'] != None:
                        sck.SendMessageToClient('you',f'chat,{i},{",".join(msg[1:])}')
                elif msg[0] == 'updatehp': # Currently has nothing using it.
                    # 1: entity type <p/e> 2: index of entity list. <0/1 for players> <enemy_id for enemies> 3: New HP value
                    if msg[1] == "p":
                        WW.Players[int(msg[2])].hp = int(msg[3])
                    elif msg[1] == "e":
                        for i in WW.Enemies:
                            if i.enemy_id == int(msg[2]):
                                i.hp = int(msg[3])
                elif msg[0] == 'throw':
                    WW.Players[player_num].Attack()
                    if i == 'you' and sck._bridgeConnection['me'] != None:
                        sck.SendMessageToClient('me','throwother')
                    elif i == 'me' and sck._bridgeConnection['you'] != None:
                        sck.SendMessageToClient('you','throwother')

def LoadPlayer(p=0):
    WW.LoadPlayer(p=p,server=True)

def NewGame(id, remote_addr, remote_port, save):
    global _disconnect
    if not _disconnect:
        return

    if id == 0:
        argslist = []
        argslist.append(remote_addr)
        argslist.append(remote_port)
        argslist.append(save)
        t = threading.Thread(target=NewGameThread, args=argslist)
        t.start()
    else:
        argslist = []
        argslist.append(remote_addr)
        argslist.append(remote_port)
        argslist.append(save)
        t = threading.Thread(target=JoinGameThread, args=argslist)
        t.start()

def JoinGameThread(remote_addr, remove_port, save):
    print("Someone's joining a Game Thread...")

def NewGameThread(remote_addr, remote_port, save):
    print("Creating a new Game Thread...")
    WW.Init(None, None, save=save)
    
    tries = 10
    while not sck.isConnected() and tries > 0:
        time.sleep(1)
        tries -= 1

    if sck.isConnected():
        global Started
        Started = True
        WW.SocketModule[0] = sck
        GameLoop(save)
    else:
        print('Game cannot start somehow...')
        WW.Cleanup()