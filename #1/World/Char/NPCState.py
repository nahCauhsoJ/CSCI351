from World.WorldCommon import Players, ComputeDir, MoveDir, Server
from World.Char.Character import AnimType

class Action:
    def __init__(self, element):
        pass

    def Enter(self, char):
        pass

    def Exit(self, char):
        pass

    def Act(self, char, deltaTime):
        pass

class IdleAction(Action):
    def Enter(self, char):
        pass

class ChaseAction(Action):
    def __init__(self, element):
        self.speed = float(element.get("speed"))
        super().__init__(element)

    def Enter(self, char):
        char.speed = self.speed
        char.ShowHp()
        if char.target == None:
            self.Exit(char)
            return
        char.lastdir, len = ComputeDir(char.GetCenterPosition(), char.target.GetCenterPosition() )
        char.charmove = True
        char.charTarget = char.target.GetCenterPosition() # It needs one extra call. Otherwise charmove will be immediately set to False by MoveDir.
        super().Enter(char)

    def Act(self, char, deltaTime):
        if not Server[0] or char.target == None:
            return
        char.charTarget = char.target.GetCenterPosition()
        char.lastdir, len = ComputeDir(char.GetCenterPosition(), char.target.GetCenterPosition() )

    def Exit(self, char):
        char.HideHp()
        char.target = None
        char.charmove = False
        char.charTarget = char.GetCenterPosition() # target is an actual characterm charTarget is a position. When chasing a moving target, we use target.

class ReturnAction(Action):
    def Act(self, char, deltaTime):
        pass

def CreateAction(element):
    action = element.find("Action")
    if action == None:
        return
    atype = action.get("type")
    if atype == "Idle":
        return IdleAction(action)
    if atype == "Chase":
        return ChaseAction(action)
    if atype == "Return":
        return ReturnAction(action)




class Decision:
    def __init__(self, element, state):
        self.state = state
        self.trueState = element.get("trueState")
        self.falseState = element.get("falseState")

    def Decide(self, char):
        return False

class PlayerInRange(Decision):
    def __init__(self, element, state):
        super().__init__(element, state)
        self.dist = int(element.get("distance"))
        self.distSqr = self.dist * self.dist

    def Decide(self, char):
        for target in Players:
            if target.dead:
                continue

            playerBox = target.GetCollisionBox()
            aiBox = char.GetCollisionBox()

            xdiff = 0
            ydiff = 0

            if playerBox.x > aiBox.x + aiBox.width:
                xdiff = playerBox.x - (aiBox.x + aiBox.width)
            elif playerBox.x + playerBox.width < aiBox.x:
                xdiff = aiBox.x - (playerBox.x + playerBox.width)

            if playerBox.y > aiBox.y + aiBox.height:
                ydiff = playerBox.y - (aiBox.y + aiBox.height)
            elif playerBox.y + playerBox.height < aiBox.y:
                ydiff = aiBox.y - (playerBox.y + playerBox.height)
        
            leng = xdiff * xdiff + ydiff * ydiff
            if leng < self.distSqr:
                char.target = target
                return True
        else:
            return False

class ClosestTarget(Decision):
    def __init__(self, element, state):
        super().__init__(element, state)
        self.lowest_dist = 2147483647
        self.lowest_dist_name = None

    def Decide(self, char):
        self.lowest_dist = 2147483647
        self.lowest_dist_player = None
        for target in Players:
            if target.dead:
                continue

            playerBox = target.GetCollisionBox()
            aiBox = char.GetCollisionBox()

            xdiff = 0
            ydiff = 0

            if playerBox.x > aiBox.x + aiBox.width:
                xdiff = playerBox.x - (aiBox.x + aiBox.width)
            elif playerBox.x + playerBox.width < aiBox.x:
                xdiff = aiBox.x - (playerBox.x + playerBox.width)

            if playerBox.y > aiBox.y + aiBox.height:
                ydiff = playerBox.y - (aiBox.y + aiBox.height)
            elif playerBox.y + playerBox.height < aiBox.y:
                ydiff = aiBox.y - (playerBox.y + playerBox.height)
        
            leng = xdiff * xdiff + ydiff * ydiff
            if self.lowest_dist > leng:
                self.lowest_dist = leng
                self.lowest_dist_player = target
        if self.lowest_dist_player == None:
            return False
        if self.lowest_dist_player.server_name == char.target.server_name:
            return False
        char.target = self.lowest_dist_player
        return False        

class HomeInRange(Decision):
    pass

class WasAttacked(Decision):
    pass

class TimeIsUp(Decision):
    pass



def CreateDecision(element, state):
    type = element.get("decide")
    if type == "player_in_range":
        return PlayerInRange(element, state)
    if type == "home_in_range":
        return HomeInRange(element, state)
    if type == "was_attacked":
        return WasAttacked(element, state)
    if type == "time_is_up":
        return TimeIsUp(element, state)
    if type == "closest_target":
        return ClosestTarget(element, state)

class State:
    def __init__(self, element):
        self.name = element.get("name")
        self.action = CreateAction(element)
        self.decisions = []
        for decision in element.findall("Decision"):
            self.decisions.append(CreateDecision(decision, self))

    def Update(self, char, deltaTime):
        self.action.Act(char, deltaTime)
        # Decisions have priority. The first decision from top to bottom in WorldData.xml that returns True gets to choose.
        for decision in self.decisions:
            result = decision.Decide(char)
            if result:
                if decision.trueState != None and decision.trueState != char.curState:
                    char.curState = decision.trueState
                    self.action.Exit(char)
                    return True
            else:
                if decision.falseState != None and decision.falseState != char.curState:
                    char.curState = decision.falseState
                    self.action.Exit(char)
                    return True
        return False