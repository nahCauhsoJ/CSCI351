import pygame
import numpy as np
from World.WorldCommon import ScreenSize
from UI.UIImage import UIImage

class UIText(UIImage):

    _LoadedFonts = {}

    def __init__(self, element=None):
        if element != None:
            super().__init__(element=element)

            txt_el = element.find("Font")
            if txt_el != None:
                self.text = txt_el.get("text")
                self.orig_size = int(txt_el.get("size"))
                self.size = self.orig_size
                self.font_style = txt_el.get("font", default="arial")
                self.txt_justify = txt_el.get("justify")
                self.txt_vjustify = txt_el.get("vjustify")
                self.color = txt_el.get("color")           

                self._CalcTextSurf()
            else:
                self.txt_surf = None
                self.txt_width = 0
                self.txt_height = 0

            self.txt_rect = pygame.Rect((self.x, self.y), (0, 0))
            self._CalcTextRect()

    # A lazy function to set text and refresh both surf and rect
    def SetText(self,txt,size=None):
        self.text = txt
        self.size = size if size != None else self.orig_size
        self._CalcTextSurf()
        self._CalcTextRect()

    def _CalcTextSurf(self):
        if self.color != None and "," in self.color:
            temp1 = self.color.split(",")
            self.color = [int(temp1[0]), int(temp1[1]), int(temp1[2])]
        else:
            self.color = "black"
        if not isinstance(self.color, pygame.Color):
            self.color = pygame.Color(self.color)

        self.font = pygame.font.SysFont(self.font_style, self.size)
        self.txt_surf = self.font.render(self.text, True, self.color)
        
    def _CalcTextRect(self):
        self._CalcRect()
        self.txt_rect.width = self.txt_width = self.txt_surf.get_width()
        self.txt_rect.height = self.txt_height = self.txt_surf.get_height()

        self.txt_rect.left = self.rect.left
        if self.txt_justify == "right":
            self.txt_rect.left += self.width - self.txt_width
        if self.txt_justify == "center":
            self.txt_rect.left += (self.width - self.txt_width) // 2

        self.txt_rect.top = self.rect.top
        if self.txt_vjustify == "bottom":
            self.txt_rect.top += self.height - self.txt_height
        if self.txt_vjustify == "center":
            self.txt_rect.top += (self.height - self.txt_height) // 2

    def ProcessEvent(self, event):
        return False

    def Update(self, deltaTime):
        pass

    def Render(self, screen):
        if self.visible and self.txt_surf != None:
            screen.blit(self.txt_surf, self.txt_rect)
        super().Render(screen)