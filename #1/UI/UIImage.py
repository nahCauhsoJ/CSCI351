import pygame
import numpy as np
from World.WorldCommon import ScreenSize, Server

class UIImage:

    def __init__(self, element=None):
        if element != None:
            self.id = element.get("id")
            self.group = None
            self.path = element.get("path")
            self.surf = pygame.image.load(self.path) if self.path != None else None
            self.x = int(element.get("x"))
            self.y = int(element.get("y"))
            self.orig_width = int(element.get("width", default="0"))
            self.width = self.orig_width # self.orig_width is specially for hp bars.
            self.height = int(element.get("height", default="0"))
            self.surf = pygame.transform.scale(self.surf, (self.width, self.height)) if self.surf != None else None
            self.rect = pygame.Rect((self.x, self.y), (self.width, self.height))
            self.justify = element.get("justify")
            self.vjustify = element.get("vjustify")
            anchor = element.find("Anchor")
            if anchor != None:
                self.anchorX = float(anchor.get("x"))
                self.anchorY = float(anchor.get("y"))
            else:
                self.anchorX = 0
                self.anchorY = 0
            self._CalcRect()

        self.visible = True if element.get("visible") == "True" else False

    def _CalcRect(self):
        self.rect.left = self.anchorX * ScreenSize[0] + self.x
        if self.justify == "right":
            self.rect.left -= self.width
        if self.justify == "center":
            self.rect.left -= self.width // 2

        self.rect.top = self.anchorY * ScreenSize[1] + self.y
        if self.vjustify == "bottom":
            self.rect.top -= self.height
        if self.vjustify == "center":
            self.rect.top -= self.height // 2
        
        self.surf = pygame.transform.scale(self.surf, (self.width, self.height)) if self.surf != None else None
        self.rect.width = self.width
        self.rect.height = self.height

    def ProcessEvent(self, event):
        return False

    def Update(self, deltaTime):
        pass

    def Render(self, screen):
        if self.surf and self.visible:
            screen.blit(self.surf, self.rect)