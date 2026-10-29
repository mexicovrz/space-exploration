# ui.py — базовые элементы интерфейса с автомасштабированием

import pygame
from data import (UI_PANEL, UI_BORDER, UI_TEXT, UI_ACCENT, WHITE, S)
from localization import translate


_font_cache = {}

def get_font(size):
    size = max(8, int(size))
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont(None, size)
    return _font_cache[size]


class Button:
    def __init__(self, rect, text, callback=None, font_size=26,
                 color=UI_PANEL, text_color=UI_TEXT):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font_size = S(font_size)
        self.color = color
        self.text_color = text_color
        self.pressed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.pressed = False
                if self.callback:
                    self.callback()
                return True
            self.pressed = False
        return False

    def draw(self, surface):
        col = UI_ACCENT if self.pressed else self.color
        radius = S(8)
        pygame.draw.rect(surface, col, self.rect, border_radius=radius)
        pygame.draw.rect(surface, UI_BORDER, self.rect,
                         width=max(1, S(2)), border_radius=radius)
        font = get_font(self.font_size)
        surf = font.render(translate(self.text), True, self.text_color)
        r = surf.get_rect(center=self.rect.center)
        surface.blit(surf, r)


def draw_text(surface, text, pos, size=24, color=UI_TEXT, center=False):
    font = get_font(S(size))
    surf = font.render(translate(text), True, color)
    r = surf.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    surface.blit(surf, r)
    return r


def draw_panel(surface, rect, color=UI_PANEL, border=UI_BORDER):
    radius = S(10)
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=max(1, S(2)),
                     border_radius=radius)