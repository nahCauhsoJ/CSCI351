import math
import numpy as np
import queue

Camera = np.asfarray([0,0])
DamagedTimer = {'p':0.5}
DataRoot = [None]

Paused = [True]             # No real use. :p
Server = [False]            # False: A client is running it, True: The server is running it.
SocketModule = [None]       # This, as the name said, contains the whole socket module. This is for the client to access mySocket.py.
Started = [False]
PhysicsEngine = [None]
PymunkCallback = [None]
ChatOpen = [False]
ScreenSize = [0,0]
WorldObjects = []
Enemies = []                # Yeah... I decided to make this since there are many cases when I only need the enemies.
Players = []                # Note that it can have 2 objects.
DetectSurvivorDelay = [-6.9]  # -6.9 cuz why not. I won't expect a pygame tick to take 6.9 seconds and that's all it matters.

SaveData = {
    0:{},
    1:{},
    2:{}
    }
CurrentSave = [None]        # There's only 3 possible numbers.

def ComputeDir(src, tgt):
    dir = tgt - src
    dir2 = dir * dir
    len = math.sqrt(np.sum(dir2))

    if len != 0:
        dir /= len
    return dir, len

def MoveDir(char, originalDir, target, speed, deltaTime):
    myPos = char.GetCenterPosition()
    dir, len = ComputeDir(myPos, target)

    if len == 0:
        return False
    else:
        prod = dir * originalDir
        dotpr = np.sum(prod)
        if dotpr < 0:
            char.SetCenterPosition(target) # We need precise positioning, so if it went too far, pull it back to its target position.
            char.charLastPos = target # Also set this so the player won't face the opposite direction when being pulled back.
            return False
        else:
            char.SetCenterPosition(myPos + speed * deltaTime * dir)
    return True

# Due to those STUPID Race Condition, this is a class to put all useful Pymunk method calls
#   into self.q. All these will be run after .step() is run in Update().
# Available methods: .add(), .reindex(), .remove()
class PymunkCallbackClass:
    def __init__(self):
       self.q = queue.Queue()
    def add(self,*objs):
        self.q.put_nowait(['add',objs])
    def custom(self,func,*args):
        self.q.put_nowait(['custom',func,args])
    def reindex_shapes_for_body(self,oooooh_mah_boooady): # *cough*
         self.q.put_nowait(['reindex',oooooh_mah_boooady])
    def remove(self,*objs):
        self.q.put_nowait(['remove',objs])
    def exec(self):
        while not self.q.empty():
            cb = self.q.get()
            if cb[0] == 'add':
                PhysicsEngine[0].add(*cb[1])
            elif cb[0] == 'custom':
                cb[1](*cb[2])
            elif cb[0] == 'reindex':
                # Note that this thing gets spammed every tick
                PhysicsEngine[0].reindex_shapes_for_body(cb[1])
            elif cb[0] == 'remove':
                PhysicsEngine[0].remove(*cb[1])






def TempCleanup():
    global Camera
    global Paused
    global Server
    global Started
    global PhysicsEngine
    global PymunkCallback
    global ScreenSize
    global WorldObjects
    global Players
    global SaveData
    global CurrentSave

    Camera[0], Camera[1] = 0, 0
    Paused[0] = True
    Server[0] = False
    Started[0] = False
    PhysicsEngine[0] = None
    PymunkCallback[0] = None
    #ScreenSize[0], ScreenSize[1] = 0, 0 # Can't clean this up due to UI using it but it being updated only on startup
    WorldObjects.clear()
    Players.clear()
    Enemies.clear()
    SaveData[0] = {}
    SaveData[1] = {}
    SaveData[2] = {}
    CurrentSave[0] = None

    # The one below does a thorough cleanup. Use it when necessary.
    """
    Camera = np.asfarray([0,0])
    Paused = [True]
    Server = [False]
    Started = [False]
    PhysicsEngine = [None]
    PymunkCallback = [None]
    ScreenSize = [0,0]
    WorldObjects = []
    Players = []
    SaveData = {
        0:{},
        1:{},
        2:{}
        }
    CurrentSave = [None]
    """