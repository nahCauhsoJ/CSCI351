import pygame
from World.WorldCommon import ScreenSize, SocketModule, ChatOpen

_chatHistory = []
_chatHistMax = 5
_curMessage = ""
_chatSurf = None

_userColor = {'me':(0,165,255), 'you':(231,84,128)}

def Init():
    global _font

    _font = pygame.font.SysFont("arial", 24)

def _OpenChat():
    global _chatSurf
    global _font
    global _userColor

    if SocketModule[0] != None and SocketModule[0]._clientConnection != None:
        ChatOpen[0] =  True
        _chatSurf = _font.render("Message: ", True, _userColor[SocketModule[0]._clientRole])
    else:
        print("Chat unavailable until a connection is made with the server.")

def _CloseChat():
    global _chatSurf
    ChatOpen[0] =  False
    del _chatSurf
    

def _PostMessage():
    global _curMessage
    if _curMessage == "":
        return
    if SocketModule[0] != None and SocketModule[0]._clientConnection != None:
        SocketModule[0].SendMessageToServer(SocketModule[0]._clientRole,f'chat,{_curMessage}')
    _curMessage = ""

def DispMessage(name,msg):
    global _chatHistory
    global _chatHistMax
    global _userColor

    if len(_chatHistory) > _chatHistMax:
        _chatHistory = _chatHistory[len(_chatHistory) - _chatHistMax : ]
    _chatHistory.append(_font.render(name + ": " + msg, True, _userColor[name]))

def _AddChat(c):
    global _curMessage
    global _chatSurf
    global _font
    global _userColor

    if not c:
        return False

    success = False
    if c == '\b':
        if _curMessage != "":
            _curMessage = _curMessage[:-1]
        success = True
    elif ord(c) >= 32 and ord(c) <= 128:
        _curMessage += c
        success = True

    if success:
        del _chatSurf
        _chatSurf = _font.render("Message: " + _curMessage, True, _userColor[SocketModule[0]._clientRole])

def ProcessEvent(event):
    global _curMessage

    if event.type == pygame.KEYDOWN:
        c = event.unicode
        if event.key == pygame.K_RETURN:
            if ChatOpen[0]:
                _PostMessage()
                _CloseChat()
            else:
                _OpenChat()
            return True
        elif ChatOpen[0]:
            if event.key == pygame.K_BACKSPACE:
                c = '\b'
            _AddChat(c)
            return True

    return False

def Update(deltaTime):
    pass

def Render(screen):
    global _chatSurf

    y = ScreenSize[1]
    rect = pygame.Rect((0,y),(0,0))
    if ChatOpen[0]:
        size = _chatSurf.get_rect().size
        y -= size[1]
        rect.top = y
        screen.blit(_chatSurf, rect)

    for surf in reversed(_chatHistory):
        size = surf.get_rect().size
        y -= size[1]
        rect.top = y
        screen.blit(surf, rect)