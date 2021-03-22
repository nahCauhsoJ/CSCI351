import pygame
import xml.etree.ElementTree as ET
from UI.UIImage import UIImage
from UI.UIText import UIText
from UI.UIButton import UIButton
from World.WorldCommon import Players, Started
from UI.UICommon import uiObjects, uiIds, groupDict, hp_objs, engage_objs, prev_engage_count, TempCleanup
import UI.Chat as Chat


# Available scenes: 'menu', 'game'
def Init(scene='menu'):
    if scene=='menu':
        Chat.Init()

    tree = ET.parse("Data/UI.xml")
    root = tree.getroot()
    groups = root.findall("Group")

    if groups != None:
        for group in groups:
            if scene=='game' and group.attrib['name'] in ["menu"]:
                continue
            elif scene=='menu' and group.attrib['name'] not in ["menu"]:
                continue

            gp_name = group.get("name", default="generic")
            if gp_name not in groupDict:
                groupDict[gp_name] = []

            for element in group.findall("*"):
                ele = None
                if element.tag == "Image":
                    ele = UIImage(element)

                    # Too lazy. Imma make it hard-coded
                    if gp_name in ["player_hp_1","player_hp_2"]:
                        MakeHpBar(gp_name, ele)

                elif element.tag == "Text":
                    ele = UIText(element)

                elif element.tag == "Button":
                    ele = UIButton(element)

                uiObjects.append(ele)
                if ele.id: uiIds[ele.id] = ele                
                if ele != None:
                    ele.group = gp_name
                    groupDict[gp_name].append(ele)

def ProcessEvent(event):

    for i in reversed(uiObjects):
        if i.ProcessEvent(event) == True:
            return True

    if Chat.ProcessEvent(event):
        return True

    return False

def Update(deltaTime):
    Chat.Update(deltaTime)

    for i in uiObjects:
        i.Update(deltaTime)

    if Started[0]:
        if len(Players) > 0:
            UpdateHpBar("player_hp_1",Players[0])
        if len(Players) > 1:
            UpdateHpBar("player_hp_2",Players[1])

    enemy_bar_move = False
    if prev_engage_count[0] != len(engage_objs):
        prev_engage_count[0] = len(engage_objs)
        enemy_bar_move = True
        for i in groupDict["enemy1_hp"]: i.visible = False
        for i in groupDict["enemy2_hp"]: i.visible = False
        for i in groupDict["enemy3_hp"]: i.visible = False

    for j,k in enumerate(engage_objs):
        enemy_bar = None
        if j == 0:
            enemy_bar = groupDict["enemy1_hp"]
            for i in groupDict["enemy1_hp"]: i.visible = True
        elif j == 1:
            enemy_bar = groupDict["enemy2_hp"]
            for i in groupDict["enemy2_hp"]: i.visible = True
        elif j == 2:
            enemy_bar = groupDict["enemy3_hp"]
            for i in groupDict["enemy3_hp"]: i.visible = True
        else:
            break

        if enemy_bar_move:
            # Since it's a list, the order is not random. Hence this simple indexing.
            k.ui_disp_obj = enemy_bar[1]
        enemy_bar[3].width = int(k.hp / k.max_hp * enemy_bar[3].orig_width)
        #print(k.enemy_id, k.hp, k.max_hp, j, enemy_bar[3].rect, enemy_bar[3].width, enemy_bar[3].height)
        enemy_bar[3]._CalcRect()

def MakeHpBar(gp, ele):
    if not ele.id:
        return

    # The mini player inside the hp bar is initialized in MAG.py, since they aren't here in the beginning.
    if gp not in hp_objs: hp_objs[gp] = {}
    
    if "hp1" in ele.id:
        hp_objs[gp][0] = ele
    elif "hp2" in ele.id:
        hp_objs[gp][1] = ele
    elif "hp3" in ele.id:
        hp_objs[gp][2] = ele

def UpdateHpBar(gp,p_obj):
    hp_dict = hp_objs[gp]
    for i in hp_dict.values():
        i.visible = True
    if p_obj.hp < 3:
        hp_dict[2].visible = False
    if p_obj.hp < 2:
        hp_dict[1].visible = False
    if p_obj.hp < 1:
        hp_dict[0].visible = False

def Render(screen):
    for i in uiObjects:
        if not Started[0] and i.group not in ["menu"]:
            continue

        i.Render(screen)

    Chat.Render(screen)

def Cleanup():
    TempCleanup()