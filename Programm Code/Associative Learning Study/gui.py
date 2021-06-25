# Gui elements

# Last update: 

import pygame

RED = (255, 0, 0)

class PopUp():

    def __init__(self, width=100, height=50, pos_x=100, pos_y=100):
        self.image = pygame.Surface([width, height])
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.center = [pos_x, pos_y]

    def draw(self, surface):
        surface.blit(self.image, self.rect)
