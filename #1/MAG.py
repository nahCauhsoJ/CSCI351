import pygame
from World.WorldCommon import ScreenSize, Paused, Started, WorldObjects, Players, Enemies, ComputeDir, CurrentSave, SocketModule
from UI.Chat import DispMessage
import threading
import requests
import json
import numpy as np
import time

import sys
sys.path.append("../#2")
import Network.mySocket as sck
sys.path.pop()



# A variable to interrupt while loops
ShutUp = False

pygame.init()
size = width, height = 640, 480
ScreenSize[0] = width
ScreenSize[1] = height
screen = pygame.display.set_mode(size, pygame.SCALED)

pygame.mixer.init(frequency=22050, size=16, channels=2, buffer=4069)
pygame.mixer.music.load("Data/bensound-epic.ogg")

import World.World as WW
# WW.Init() is moved to StartGame()

import UI.UI as UI
from UI.UICommon import uiObjects, uiIds, groupDict
from UI.UIButton import RegisterButtonAction
UI.Init(scene='menu')

try:
    with open("SettingsFile.txt","r") as f:
        for line in f:
            i = line.find("volume ", 0, 7)
            if i != -1:
                volume = float(line[7:])
                if volume > 1:
                    volume = 1
                elif volume < 0:
                    volume = 0
                pygame.mixer.music.set_volume(volume)
                continue

            i = line.find("END\n", 0, 4)
            if i != -1:
                break
except:
    pass
pygame.mixer.music.play()

SettingsFile = open("SettingsFile.txt", "w")
def SaveSettings():
    global SettingsFile
    volume = pygame.mixer.music.get_volume()
    SettingsFile.write("volume " + str(volume) + "\n")
    SettingsFile.write("END\n")
    SettingsFile.flush()
    SettingsFile.seek(0,0)
SaveSettings()

_IsHost = False # Mainly to inform the vistor that they lost the race
def CantLoadSaves(world_clean = False):
    global _IsHost
    _IsHost = False
    if world_clean:
        WW.Cleanup()
        sck.Disconnect()
        UI.Cleanup() # Yeah... Rmb to re-initiate UI if you're gonna wipe it...
        UI.Init(scene='menu')


    else:
        for i in uiObjects: # CantLoadSaves now officially clears game scene UIs, so this will include ALL uiObjects.
            i.visible = False
        uiIds["start_game"].visible = True
        uiIds["volume_up"].visible = True
        uiIds["volume_down"].visible = True

def LoadingSaves():
    uiIds["start_game"].visible = False
    uiIds["volume_up"].visible = False
    uiIds["volume_down"].visible = False

    uiIds["menutxt_status"].SetText("Loading saves...")
    uiIds["menutxt_status"].visible = True

    t = threading.Thread(target=LoadedSaves)
    t.start()

def LoadedSaves():
    global _IsHost
    saves = None
    try:
        # Remember, started will get 'yes', 'no' or 'full'
        started = requests.get(url="http://localhost:5005/games/started",timeout=5).text
        if started == 'full':
            print("<Error> Server is full. The assignment only asks for 2 slots, so don't complain.")
            CantLoadSaves()
            return
        if started == 'no':
            _IsHost = True
            saves = requests.get(url="http://localhost:5005/games/existlist",timeout=5).json()
    except:
        print("<Error> Loading failed. Guess the server's down.")
        CantLoadSaves()
        return

    uiIds["save1"].SetText("New World")
    uiIds["save2"].SetText("New World")
    uiIds["save3"].SetText("New World")

    uiIds["menutxt_status"].visible = False
    uiIds["menutxt_choose"].visible = True
    if saves == None:
        uiIds["save1"].visible = False
        uiIds["save1"].SetText("Join this world!")
        uiIds["save1"].visible = True
    else:
        if saves["0"]:
            # There's a VERY HARD TO REPRODUCE BUG involving locked Surface during blit.
            #   It's somehow fixed when .visible is set to False until the rect is done calculating.
            uiIds["save1"].visible = False
            uiIds["save1"].SetText("Save 1")
        if saves["1"]:
            uiIds["save2"].visible = False
            uiIds["save2"].SetText("Save 2")
        if saves["2"]:
            uiIds["save3"].visible = False
            uiIds["save3"].SetText("Save 3")
        uiIds["save1"].visible = True
        uiIds["save2"].visible = True
        uiIds["save3"].visible = True

def StartingGame(save):
    uiIds["menutxt_choose"].visible = False
    uiIds["save1"].visible = False
    uiIds["save2"].visible = False
    uiIds["save3"].visible = False
    uiIds["menutxt_status"].SetText("Preparing connection...")
    uiIds["menutxt_status"].visible = True

    t = threading.Thread(target=StartGame,args=(save,))
    t.start()

def StartGame(save=0):
    save = int(save) # Just in case
    global size
    global screen
    global ShutUp
    global _IsHost

    uiIds["menutxt_status"].SetText("Connecting to server...")
    sck.Init(False,'127.0.0.1',5006)
    SocketModule[0] = sck
    tries = 5
    client_socket_got = False
    while tries > 0 and not ShutUp:
        if sck._clientConnection != None:
            # When this runs, it means _Process already started
            client_socket_got = True
            break
        time.sleep(1)
        tries -= 1

    if client_socket_got:
        # 'gimmerole' won't be interpreted. It's merely a placeholder for sending a dud message to the server,
        #   so that the server can set roleAssigned in _Process.
        sck.SendMessageToServer('','gimmerole')
        uiIds["menutxt_status"].SetText("Awaiting player role assignment...",size=48)
        tries = 50 # This means 50 times within 5 seconds
        role_got = False
        while tries > 0 and not ShutUp:
            if sck._clientRole != 'Unassigned': # This is handled in the message system in Update() below
                role_got = True

                # This is where the winner of the host-race is decided.
                if sck._clientRole == "you":
                    if _IsHost:
                        _IsHost = False
                        print("Someone was faster than you to be the host, so you're joining the save he decided instead.")
                    # CurrentSave[0] is set by WW.Init(), which depends on this save.
                    try:
                        s = requests.get(url=f"http://localhost:5005/games/getsave", timeout=5).json()
                        save = int(s)
                    except:
                        print('<Error> Server disconnected when retrieving data somehow...')
                        CantLoadSaves(True)
                        return
                break
            time.sleep(0.1)
            tries -= 1

        if not role_got:
            print('<Error> Server is unable to identify you...')
            CantLoadSaves()
            return
        
    else:
        print('<Error> Server is unable to maintain connection with you...')
        CantLoadSaves()
        return

    # When the code reaches here, the client should have the socket AND know its role.
    #   However, both server and client aren't ready to receive messages yet (unless manually set, like above)
    uiIds["menutxt_status"].SetText("Retrieving player data...")

    # Note that at this point, the world isn't even set up on the server-side
    # The server will do it when player's looking for playerdata
    player_data = None
    p = 1 if sck._clientRole == 'you' else 0
    try:
        # 10 seconds becuz the server needs more time to fully initate the world. Player data must be
        #   sent after the world is completely loaded to prevent race condition.
        player_data = requests.get(url=f"http://localhost:5005/games/{save}/player/{p}", timeout=10).json()
    except:
        print('<Error> Server is unable to give you player data...')
        CantLoadSaves(True)
        return

    if player_data == None:
        print('<Error> Player data is lost somehow.')
        CantLoadSaves(True)
        return

    WW.Init(size, screen, save)
    WW.LoadPlayer(p=0,server=False) # If it's player 2, the 2nd player will be added via 'join' message
    Players[0].SetCenterPosition(np.asfarray([player_data["x"],player_data["y"]]), safeMove=True)
    Players[0].hp = player_data["hp"]
    Players[0].server_name = sck._clientRole
    UI.Init(scene='game') # This MUST go before the request below. The race condition sucks.
    try:
        requests.post(url=f"http://localhost:5005/games/{sck._clientRole}/ready", timeout=20) # 20 because had a time when 5s is not enough time.
    except:
        print('<Error> Your connection went wrong. Disconnected for safety reasons.')
        CantLoadSaves(True) # This contains sck.Disconnect, which does all the disconnections
        return

    uiIds["menutxt_status"].visible = False
    for i in groupDict["player_hp_1"]:
        i.visible = True
    Players[0].ui_disp_obj = uiIds["player_now_1"]
    for i in WorldObjects:
        i.visible = True
    Paused[0] = False
    Started[0] = True
    

def VolUp():
    volume = pygame.mixer.music.get_volume()
    if volume < 1:
        volume += 0.05
        if volume > 1:
            volume = 1.0
        pygame.mixer.music.set_volume(volume)
        SaveSettings()

def VolDown():
    volume = pygame.mixer.music.get_volume()
    if volume > 0:
        volume -= 0.05
        if volume < 0:
            volume = 0.0
        pygame.mixer.music.set_volume(volume)
        SaveSettings()

RegisterButtonAction("LoadingSaves", LoadingSaves)
RegisterButtonAction("StartingGame", StartingGame)
RegisterButtonAction("VolUp", VolUp)
RegisterButtonAction("VolDown", VolDown)

def Update(deltaTime):
    paused = Paused[0]
    started = Started[0]
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if UI.ProcessEvent(event) == True:
            continue
        if not started and paused:
            continue
        if WW.ProcessEvent(event) == True:
            continue

    msg_got = sck.GetMessage('System')
    if msg_got != None:
        msg = msg_got.split(',')

        if msg[0] == 'moveenemy':
            for i in Enemies:
                if i.enemy_id == int(msg[3]):
                    oldpos = i.GetCenterPosition()
                    i.SetCenterPosition(np.asfarray(( float(msg[1]),float(msg[2]) )), True)
                    if i.curState == "Chase":
                        target = Players[0] if len(Players) > 0 else None
                        if target:
                            i.charTarget = target.GetCenterPosition()
                            i.lastdir, leng = ComputeDir(oldpos, target.GetCenterPosition())                    
                            if leng != 0:
                                i.charmove = True
                            else:
                                i.charmove = False
                    else:
                        i.charmove = False
                    break
        elif msg[0] == 'moveother':
            if len(Players) > 1:
                p_obj = Players[1]
                p_obj.charTarget[0], p_obj.charTarget[1] = float(msg[1]), float(msg[2])
                p_obj.lastdir, leng = ComputeDir(p_obj.charLastPos, p_obj.charTarget)
                if leng >= 1: # Small tolerance cuz frickin floats
                    p_obj.charmove = True
                    if leng > 48: # This is hardcoded to sync up the position when they're 48+ pixels apart.
                        p_obj.SetCenterPosition(p_obj.charTarget, True)
                else:
                    # This means when the player's not moving, sync up the position
                    p_obj.SetCenterPosition(p_obj.charTarget, True)
                if p_obj.dead: # Well... Cuz players can push corpses. Too lazy to patch that.
                    p_obj.SetCenterPosition(p_obj.charTarget, True)
        elif msg[0] == 'throwother':
            if len(Players) > 1:
                Players[1].Attack(with_anim=True)
        elif msg[0] == 'role':
            SocketModule[0]._clientRole = msg[1]
        elif msg[0] == 'chat':
            DispMessage( msg[1], ",".join(msg[2:]))
        elif msg[0] == 'join':
            # Remember, on client side, 'me' doesn't necessarily have to be Players[0].
            #   If the client is 'you', 'me' will be Players[1].
            WW.LoadPlayer(p=1,server=False)
            for i in groupDict["player_hp_2"]:
                i.visible = True
            Players[1].SetCenterPosition(np.asfarray( [float(msg[1]), float(msg[2])] ), safeMove=True)
            Players[1].hp = int(msg[3])
            Players[1].ui_disp_obj = uiIds["player_now_2"]
            Players[1].server_name = 'you' if SocketModule[0]._clientRole == 'me' else 'me'
        elif msg[0] == 'leave':
            WW.DelPlayer2()
            for i in groupDict["player_hp_2"]:
                i.visible = False
        elif msg[0] == 'hit':
            # 1: target type <p/e> 2: target's id (e.g. p,1 = 2nd player) 3&4: source's center position 5: New HP
            if msg[1] == "p":
                player_num = int(msg[2])
                if player_num != 1 or len(Players) > 1:
                    pos = np.asfarray(( float(msg[3]), float(msg[4]) ))
                    Players[player_num].hp = int(msg[5])
                    Players[player_num].Knockback(pos, 300) # Hardcoded force.
            elif msg[1] == "e":
                enemy_id = int(msg[2])
                for i in Enemies:
                    if i.enemy_id == enemy_id:
                        i.hp = int(msg[5])
                        break


    if started and not paused:
        WW.Update(deltaTime)
        
    UI.Update(deltaTime)

    if started and sck._clientConnection == None:
        CantLoadSaves(True)

    return True


def Render(screen):
    screen.fill((255,255,255))
    if Started[0]:
        WW.Render(screen)
    UI.Render(screen)
    pygame.display.flip()

def Cleanup():
    print("I'm leaving.")

    global ShutUp
    ShutUp = True
    
    WW.Cleanup()
    UI.Cleanup()
    sck.Disconnect()
    SettingsFile.close()

    sys.exit(0)



_gTickLastFrame = pygame.time.get_ticks()
_gDeltaTime = 0.0
while Update(_gDeltaTime):
    Render(screen)
    t = pygame.time.get_ticks()
    _gDeltaTime = ( t - _gTickLastFrame ) / 1000.0
    _gTickLastFrame = t
Cleanup()
