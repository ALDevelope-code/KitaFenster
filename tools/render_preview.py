"""Bilder der tatsächlichen Player-Darstellung für die lokale Sichtprüfung."""

import os
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from player.cache import Cache
from player.render import render_slide

pygame.display.init()
pygame.font.init()
pygame.display.set_mode((1280, 720))
output = Path("test-results")
output.mkdir(exist_ok=True)
cache = Cache(output / "render-cache")
notice = {
    "kind": "notice",
    "notice": {
        "title": "Wir gehen auf Entdeckungstour.",
        "text": "Liebe Eltern,\nbitte denkt morgen an wetterfeste Kleidung, einen kleinen Rucksack und eine Trinkflasche.\n\nWir freuen uns auf einen Tag voller Entdeckungen!",
        "theme": "ocean",
    },
}
for label, size in [("landscape", (1920, 1080)), ("portrait", (1080, 1920))]:
    surface = render_slide(notice, size, cache, "Gruppe 1")
    pygame.image.save(surface, output / ("player-" + label + ".png"))
pygame.quit()
print("Player-Vorschauen unter test-results erzeugt.")
