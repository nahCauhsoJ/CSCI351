import pygame
import numpy as np
from World.WorldCommon import ScreenSize
from UI.UIText import UIText

_ButtonActions = {}

def RegisterButtonAction(name, callback):
    _ButtonActions[name] = callback

class UIButton(UIText):

    def __init__(self, element=None):
        if element != None:
            super().__init__(element=element)

            btn_el = element.find("Action")
            self.action = btn_el.get("onClick", default="")
            self.args = btn_el.get("args")
            self.pressed = btn_el.get("pressed")
            self.normal_surf = self.surf

            if self.args != None:
                self.args = self.args.split(",")
            else:
                self.args = []

            if self.pressed == None:
                self.pressed_surf = None
            else:
                self.pressed_surf = pygame.image.load(self.pressed)
                if self.pressed_surf != None:
                    self.pressed_surf = pygame.transform.scale(self.pressed_surf, (self.width, self.height))

        self.pressed = False
        self.disabled = False

    def ProcessEvent(self, event):
        if self.disabled or not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            left, middle, right = pygame.mouse.get_pressed()
            pos = pygame.mouse.get_pos()
            if left == True and self.rect.collidepoint(pos):
                self.pressed = True
                return True
        elif self.pressed and event.type == pygame.MOUSEBUTTONUP:
            left, middle, right = pygame.mouse.get_pressed()
            if left == False:
                self.pressed = False
                pos = pygame.mouse.get_pos()
                if self.rect.collidepoint(pos) and self.action in _ButtonActions:
                    _ButtonActions[self.action](*self.args)
        return False

    def Update(self, deltaTime):
        pass

    def Render(self, screen):
        self.surf = self.pressed_surf if self.pressed else self.normal_surf
        super().Render(screen)