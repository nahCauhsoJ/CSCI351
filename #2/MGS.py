import Database.database as db
import Network.rest as nw
import Network.mySocket as sck
import threading

Initialized = False

def MainThread():
    global Initialized

    while True:
        if not Initialized:
            continue

t = threading.Thread(target=MainThread)
t.start()

db.Init()
nw.Init()
sck.Init(True, 5006)
Initialized = True

nw.Run()
