import socket
import threading
import time
import queue

_Messages = {} # Used by both
_lock = threading.Lock() # Used by both
_goodConnection = False # Used by both
_bridgeConnection = {'me':None, 'you':None} # Used by server
_serverConnection = None # Used by server
_clientLoaded = False # Used by server
_clientConnection = None # Used by client
_clientRole = 'Unassigned' # Used by client



def isConnected(name='me'):
    global _bridgeConnection
    if name != None:
        return _bridgeConnection[name] != None
    else:
        # The only time when client runs this on the server, is when the server's down.
        # So it'll be False regardless.
        # i.e. This won't even run if the server connected is good.
        return False

def Disconnect(): # Used by client if they failed to load the world, and needs to reset the socket
    global _clientConnection
    global _clientRole
    if _clientConnection != None:
        _clientConnection.close()
    _clientConnection = None
    _clientRole = 'Unassigned'

def SendMessageToServer(name, mes):
    global _clientConnection
    try:
        _clientConnection.sendall(bytearray(name + "|" + mes + "\x01", "utf-8"))
    except:
        pass

def SendMessageToClient(name, mes):
    global _bridgeConnection
    try:
        _bridgeConnection[name].sendall(bytearray('System' + "|" + mes + "\x01", "utf-8"))
    except:
        pass

def GetMessage(name):
    global _Messages
    global _lock

    with _lock:
        if not name in _Messages:
            return None
        mesList = _Messages[name]
        if mesList.empty():
            return None
        mes = mesList.get()
    return mes

def _Process(conn,name=None):
    global _Messages
    global _lock
    global _clientLoaded
    global isConnected
    global _clientConnection
    global _goodConnection
    roleAssigned = False # This is for the server to send an initial message to the client, telling it whether it's a host or visitor

    data = ""
    with conn:
        tries = 3
        flood_msg_cd = 0 # This is in ticks, not irl seconds
        while True:
            _goodConnection = True
            foundconn = False
            d = None
            try:
                d = conn.recv(1024)
                data += d.decode("utf-8")
                foundconn = True
                if tries < 3:
                    print('Nvm. The "someone" reconnected.')
                    _goodConnection = True
                    tries = 3
            except:
                if tries == 3:
                    print('Mmm? Someone disconnected.')
                _goodConnection = False
                time.sleep(1)
                tries -= 1

                if tries <= 0:
                    print('> *snap* goes a connection <')
                    if name == None:
                        # name = None means the client's the one processing data.
                        _clientConnection = None
                    break

            if not d:
                continue

            if not roleAssigned and name != None:
                SendMessageToClient(name,f"role,{name}")
                roleAssigned = True
                _clientLoaded = True

            for i in range(3):
                index = data.find("\x01")
                if index == -1:
                    break
                wrd = data.find("|")
                ky = data[0:wrd]
                ms = data[wrd+1:index]

                with _lock:
                    if not ky in _Messages:
                        _Messages[ky] = queue.Queue()
                    _Messages[ky].put(ms)

                data = data[index+1:]
                if len(data) > 1000:
                    if flood_msg_cd <= 0:
                        flood_msg_cd = 20
                        print("WARNING WARNING! data in mySocket.py is being flooded!!!")
                        print("Previous flooding Message:",ky,ms,end="\n\n")
                    else:
                        flood_msg_cd -= 1

    if name=='me' and _bridgeConnection['you'] != None:
        # This is to automatically shut down the visitor when the host is down.
        _bridgeConnection['you'].close()
    if name in _bridgeConnection:
        _bridgeConnection[name] = None

def _Listener(port):
    global _serverConnection
    global _bridgeConnection
    _serverConnection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _serverConnection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    _serverConnection.bind(('127.0.0.1', 5006))
    _serverConnection.listen()
    while True:
        conn, addr = _serverConnection.accept() # The code stops here indefinitely until a connection comes in

        if _bridgeConnection['me'] == None:
            print('! The host connected !')
            _bridgeConnection['me'] = conn
            _bridgeConnection['me'].setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            t = threading.Thread(target=_Process,args=[_bridgeConnection['me'],'me'])
            t.start()
        elif _bridgeConnection['you'] == None:
            print('! A visitor connected !')
            _bridgeConnection['you'] = conn
            _bridgeConnection['you'].setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            t = threading.Thread(target=_Process,args=[_bridgeConnection['you'],'you'])
            t.start()
        else:
            conn.close()

def _Connector(address, port):
    # Note that address is a string and port MUST be an integer.  
    global _clientConnection

    attemptConnection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    attemptConnection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    connected = False
    tries = 5
    while not connected and tries > 0:
        try:
            attemptConnection.connect((address, port))
            connected = True
        except Exception as e:
            time.sleep(1)
            tries -= 1
    
    if connected:
        _clientConnection = attemptConnection
        _Process(_clientConnection)
        print('Disconnected')
    else:
        print('Unable to connect to server')

def Init(asListener, address=None, port=None):
    if asListener:
        t = threading.Thread(target=_Listener,args=[port])
    else:
        t = threading.Thread(target=_Connector, args=[address,port])
    t.daemon = True # Just so that sys.exit() actually works
    t.start()