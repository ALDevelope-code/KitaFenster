"""Independent slide clocks and transitions for each display region."""

import json
import random

import pygame

from player.render import render_slide
from shared.layout import region_rects
from shared.schedule import slides


class Region:
    def __init__(self):
        self.signature = None
        self.items = []
        self.index = 0
        self.next_slide = 0
        self.current = self.previous = None
        self.item = None
        self.size = None
        self.changed_at = 0

    def update(self, items, size, now, cache, group, shuffle=False):
        signature = json.dumps([items, group, shuffle], sort_keys=True)
        if signature != self.signature:
            self.signature = signature
            self.items = list(items)
            if shuffle:
                random.shuffle(self.items)
            self.index, self.next_slide = 0, 0
        due = now >= self.next_slide
        resized = size != self.size
        if not due and not resized:
            return
        if due:
            self.item = self.items[self.index % len(self.items)] if self.items else None
            self.index += 1
            self.next_slide = now + (self.item["seconds"] if self.item else 30)
        try:
            rendered = render_slide(self.item, size, cache, group)
        except Exception:
            rendered = render_slide(None, size, cache, "Willkommen")
        self.previous = self.current if not resized else None
        self.current, self.size, self.changed_at = rendered, size, now

    def draw(self, target, rect, now, settings):
        duration = settings.get("transition_seconds", 0)
        progress = min(1, (now - self.changed_at) / duration) if duration else 1
        transition = settings.get("transition", "none")
        surface = target.subsurface(rect)
        if self.previous is None or progress >= 1 or transition == "none":
            self.previous = None
            surface.blit(self.current, (0, 0))
            return False
        surface.blit(self.previous, (0, 0))
        if transition == "fade":
            self.current.set_alpha(round(progress * 255))
            surface.blit(self.current, (0, 0))
            self.current.set_alpha(None)
        else:
            width = rect[2]
            surface.blit(self.previous, (-int(progress * width), 0))
            surface.blit(self.current, (width - int(progress * width), 0))
        return True


class Presentation:
    def __init__(self):
        self.regions = {}
        self.surface = None

    def reset(self):
        self.regions.clear()
        self.surface = None

    def frame(self, manifest, decision, physical_size, now, cache):
        settings = manifest["settings"] if manifest else {}
        rotation = settings.get("rotation", 0)
        size = physical_size[::-1] if rotation in (90, 270) else physical_size
        if self.surface is None or self.surface.get_size() != size:
            self.surface = pygame.Surface(size)
        self.surface.fill("black")
        if decision["mode"] == "black":
            self.regions.clear()
            return pygame.transform.rotate(self.surface, -rotation) if rotation else self.surface, False
        main = slides(manifest, decision) if manifest else []
        secondary = slides(manifest, decision["secondary"]) if decision.get("secondary") else []
        rectangles = region_rects(size, settings.get("split", {}), bool(secondary))
        active = False
        for area, rect in rectangles.items():
            region = self.regions.setdefault(area, Region())
            choice = decision if area == "main" else decision["secondary"]
            region.update(
                main if area == "main" else secondary,
                rect[2:],
                now,
                cache,
                manifest["group_name"] if manifest else "Willkommen",
                settings.get("order") == "shuffle" and choice["mode"] == "photos",
            )
            active |= region.draw(self.surface, rect, now, settings)
        for area in list(self.regions):
            if area not in rectangles:
                del self.regions[area]
        return pygame.transform.rotate(self.surface, -rotation) if rotation else self.surface, active
