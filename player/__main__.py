import argparse
import getpass
import json
import os
import signal
import sys
import time
from pathlib import Path

from player.cache import atomic_json
from player.client import API, SyncWorker
from player.display_power import DisplayPower
from player.motion import MotionGate
from shared.schedule import resolve


def main():
    parser = argparse.ArgumentParser(description="KitaFenster Player")
    parser.add_argument("--config", default=str(Path.home() / ".config/kita-frame/player.json"))
    parser.add_argument("--pair", metavar="SERVER_URL", help="Gerät mit einem einmaligen Code koppeln")
    parser.add_argument("--ca-file", help="Optionales Zertifikat der lokalen CA")
    parser.add_argument("--windowed", action="store_true", help="Fenster für den Test am PC")
    parser.add_argument("--frames", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    config_path = Path(args.config).expanduser().resolve()
    if args.pair:
        api = API(args.pair, ca_file=args.ca_file)
        code = getpass.getpass("Kopplungscode aus der Verwaltung: ")
        try:
            result = json.loads(api.request("/api/device/pair", {"code": code}))
        except Exception:
            parser.exit(1, "Kopplung fehlgeschlagen. Serveradresse, Zertifikat und Code prüfen.\n")
        config = {
            "server_url": args.pair.rstrip("/"),
            **result,
            "cache_dir": str(config_path.parent / "cache"),
            "poll_seconds": 15,
            "cache_limit_mb": 1024,
        }
        if args.ca_file:
            config["ca_file"] = str(Path(args.ca_file).resolve())
        atomic_json(config_path, config)
        print("Gerät gekoppelt. Auf dem eingerichteten Pi: sudo reboot. Am PC: Player erneut starten.")
        return
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        parser.exit(1, "Konfiguration fehlt. Zuerst 'python -m player --pair http://NAS:8088' ausführen.\n")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    from player.presentation import Presentation

    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode(
        (1280, 720) if args.windowed else (0, 0), 0 if args.windowed else pygame.FULLSCREEN
    )
    pygame.display.set_caption("KitaFenster · Digitaler Bilderrahmen")
    pygame.mouse.set_visible(False)
    worker = SyncWorker(config)
    worker.start()
    gate, power = MotionGate(), DisplayPower()
    last_power, last_status = "on", None
    previous_term = signal.signal(signal.SIGTERM, lambda *_: worker.stop.set())
    clock = pygame.time.Clock()
    presentation = Presentation()
    running, frame = True, 0
    try:
        while running and not worker.restart.is_set() and not worker.stop.is_set():
            frame += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    args.windowed and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    running = False
            now = time.monotonic()
            manifest = worker.snapshot()
            decision = (
                resolve(manifest)
                if manifest
                else {"mode": "empty", "reason": "Noch keine Inhalte", "notices": []}
            )
            motion = (manifest or {}).get("settings", {}).get("motion", {})
            urgent = decision["reason"] == "Sofortmeldung"
            sensed = gate.update(motion, now, urgent=urgent)
            sleeping = not urgent and (
                decision["mode"] == "black" or (motion.get("enabled", False) and sensed.idle)
            )
            power_state = power.apply(sleeping, motion.get("power_mode", "hdmi"))
            mode, reason = decision["mode"], decision["reason"]
            if sleeping:
                cause = reason if mode == "black" else sensed.reason
                reason = cause + (" · HDMI aus" if power_state == "standby" else " · Schwarzbild")
                mode = "sleep"
            elif sensed.reason and not urgent:
                reason += " · " + sensed.reason
            error = "; ".join(filter(None, (sensed.error, power.error)))[:160]
            worker.report(
                mode,
                reason[:160],
                error,
                {
                    **sensed.diagnostics,
                    "display": power_state,
                    "display_error": power.error,
                },
            )
            status = (mode, reason, error)
            if status != last_status:
                print("Anzeige: " + reason + (" | " + error if error else ""), flush=True)
                last_status = status
            if sleeping:
                # No rendering/page flips on a disabled HDMI CRTC.
                if power_state == "black" and last_power != "black":
                    screen.fill("black")
                    pygame.display.flip()
                last_power = power_state
                presentation.reset()
                clock.tick(5)
                if args.frames and frame >= args.frames:
                    running = False
                continue
            last_power = "on"
            rendered, transitioning = presentation.frame(
                manifest, decision, screen.get_size(), now, worker.cache
            )
            screen.blit(rendered, (0, 0))
            pygame.display.flip()
            clock.tick(25 if transitioning else 2)
            if args.frames and frame >= args.frames:
                running = False
    finally:
        worker.stop.set()
        gate.close()
        power.close()
        pygame.quit()
        signal.signal(signal.SIGTERM, previous_term)
    if worker.restart.is_set():
        # Supervisor restarts the process; local development also restarts the player.
        os.execv(sys.executable, [sys.executable, "-m", "player", *sys.argv[1:]])


if __name__ == "__main__":
    main()
