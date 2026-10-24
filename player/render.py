"""Nur aktuelles und vorheriges Bild bleiben als Vollbild-Surfaces im RAM."""

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

THEMES = {"ocean": ("#102f3b", "#80d8cc"), "sun": ("#423021", "#ffcc76"), "berry": ("#35253e", "#dab1e5")}


def font(size, bold=False):
    return pygame.font.SysFont("DejaVu Sans,Arial", max(12, int(size)), bold=bold)


def wrapped(text, face, width):
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split(" "):
            candidate = (current + " " + word).strip()
            if face.size(candidate)[0] <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = ""
                for character in word:
                    if face.size(current + character)[0] > width and current:
                        lines.append(current)
                        current = ""
                    current += character
        lines.append(current)
    return lines


def text_block(surface, text, area, color, initial_size, bold=False):
    size = max(12, initial_size)
    while size >= 12:
        face = font(size, bold)
        lines = wrapped(text, face, area.width)
        line_height = face.get_linesize() * 1.18
        if len(lines) * line_height <= area.height:
            break
        size -= 2
    for i, line in enumerate(lines):
        if (i + 1) * line_height > area.height:
            break
        surface.blit(face.render(line, True, color), (area.x, area.y + i * line_height))


def fit_image(image, size, fit="contain"):
    w, h = size
    ratio = (
        max(w / image.get_width(), h / image.get_height())
        if fit == "cover"
        else min(w / image.get_width(), h / image.get_height())
    )
    scaled = pygame.transform.smoothscale(
        image, (max(1, round(image.get_width() * ratio)), max(1, round(image.get_height() * ratio)))
    )
    canvas = pygame.Surface(size)
    canvas.fill("#080d11")
    canvas.blit(scaled, ((w - scaled.get_width()) // 2, (h - scaled.get_height()) // 2))
    return canvas


def render_slide(slide, size, cache, group_name="Willkommen"):
    w, h = size
    if slide and slide["kind"] == "image":
        return fit_image(
            pygame.image.load(str(cache.path(slide["asset"]))).convert(), size, slide.get("fit", "contain")
        )
    canvas = pygame.Surface(size)
    notice = (
        slide["notice"]
        if slide and slide["kind"] == "notice"
        else {
            "title": "Schön, dass ihr da seid.",
            "text": "Hier ist Platz für unsere gemeinsamen Momente.",
            "theme": "ocean",
        }
    )
    bg, accent = THEMES[notice.get("theme", "ocean")]
    canvas.fill(bg)
    margin = round(min(w, h) * 0.09)
    pygame.draw.rect(canvas, accent, (margin, margin, 46, 5), border_radius=2)
    label = font(min(w, h) * 0.025, True).render(group_name.upper(), True, accent)
    canvas.blit(label, (margin, margin + 23))
    content_width = w - 2 * margin
    has_image = bool(notice.get("image"))
    landscape = w > h
    if has_image and landscape:
        content_width = int(content_width * 0.57)
    title_area = pygame.Rect(margin, int(h * 0.25), content_width, int(h * 0.23))
    body_area = pygame.Rect(
        margin, int(h * 0.52), content_width, int(h * (0.20 if has_image and not landscape else 0.35))
    )
    text_block(canvas, notice["title"], title_area, "#ffffff", min(w, h) * 0.074, True)
    text_block(canvas, notice.get("text", ""), body_area, "#e7eeef", min(w, h) * 0.038)
    if has_image:
        if landscape:
            rect = pygame.Rect(int(w * 0.65), margin * 2, int(w * 0.29), h - margin * 3)
        else:
            rect = pygame.Rect(margin, int(h * 0.75), w - margin * 2, int(h * 0.2))
        picture = pygame.image.load(str(cache.path(notice["image"]))).convert()
        canvas.blit(fit_image(picture, rect.size), rect)
    return canvas
