import os
import subprocess
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from conftest import image_bytes
from test_player import manifest

from player.cache import Cache, atomic_json
from player.render import fit_image, font, render_slide, wrapped


def test_letterboxing_crop_and_notice_rendering(tmp_path):
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    picture = pygame.Surface((200, 100))
    picture.fill("red")
    contained = fit_image(picture, (200, 200))
    assert contained.get_at((100, 10))[:3] == (8, 13, 17)
    assert contained.get_at((100, 100))[:3] == (255, 0, 0)
    cropped = fit_image(picture, (200, 200), "cover")
    assert cropped.get_at((100, 10))[:3] == (255, 0, 0)
    cache = Cache(tmp_path)
    note = {
        "kind": "notice",
        "notice": {
            "title": "Willkommen, liebe Eltern!",
            "text": "Ein langer\nText für die Gruppe.",
            "theme": "ocean",
        },
    }
    for size in [(1280, 720), (720, 1280)]:
        frame = render_slide(note, size, cache, "Gruppe 1")
        assert frame.get_size() == size
    long_word = "zusammengeschrieben" * 10
    face = font(30)
    assert all(face.size(line)[0] <= 200 for line in wrapped(long_word, face, 200))
    pygame.quit()


def test_player_starts_from_offline_cache_without_display_server(tmp_path):
    data = image_bytes()
    cache = Cache(tmp_path / "cache")
    cache.install(manifest(data), lambda *args: data)
    config = tmp_path / "player.json"
    atomic_json(
        config, {"server_url": "http://127.0.0.1:1", "token": "local-test", "cache_dir": str(cache.root)}
    )
    result = subprocess.run(
        [sys.executable, "-m", "player", "--config", str(config), "--windowed", "--frames", "4"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
