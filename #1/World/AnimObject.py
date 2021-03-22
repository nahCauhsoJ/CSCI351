
import pygame
import numpy as np
import os
from World.WorldCommon import Server

class AnimObject:


    # Default values are defined in World/WorldObject/AnimInit
    # If a new frame size or coord is needed, do this __init__ manually.
    def __init__(self, path, scale, frame_size, frame_coord):
        self.path = path
        self.img = pygame.image.load(path)
        self.frame_coord = frame_coord
        self.frame_size = np.asfarray(frame_size)
        self.size = self.frame_size * scale
        self.animTime = 0
        self.animFrameLen = 0.1667

        self.LoadFrame(0)

    def LoadFrame(self,index):
        if len(self.frame_coord) == 0 or self.frame_size[0] <= 0 or self.frame_size[1] <= 0:
            self.surf = None
            return
        
        self.surf = pygame.Surface(self.frame_size, pygame.SRCALPHA)
        self.surf.blit(self.img, (0,0), (*self.frame_coord[index], *self.frame_size))
        self.surf = pygame.transform.scale(self.surf, self.size.astype(int))
        

    def Update(self, deltaTime):
        if not Server[0]:
            frame = int(self.animTime // self.animFrameLen)
            self.animTime += deltaTime
            if self.animTime >= self.animFrameLen * len(self.frame_coord):
                self.animTime = 0
        self.LoadFrame(frame)