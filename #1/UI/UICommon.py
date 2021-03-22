uiObjects = []
groupDict = {}
hp_objs = {}
uiIds = {}

prev_engage_count = [0]
engage_objs = []



def TempCleanup():
    global uiObjects
    global groupDict
    global hp_objs
    global uiIds
    global prev_engage_count
    global engage_objs

    uiObjects.clear()
    groupDict = {}
    hp_objs = {}
    uiIds = {}
    prev_engage_count[0] = 0
    engage_objs.clear()