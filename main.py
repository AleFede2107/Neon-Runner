"""Neon Runner — Python 3.11.9. Run: python main.py.

World coordinates never depend on the camera. Physics runs at a fixed 120 Hz.
Missing media are replaced automatically; see assets/manifest.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame as pg

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1100, 650
WORLD = 6400
STEP = 1 / 120
GRAVITY = 1750


class Media:
    def __init__(self):
        self.config = json.loads((ROOT / "assets/manifest.json").read_text("utf-8"))
        self.cache = {}
        self.sounds = {}
        if pg.mixer.get_init():
            for name, path in self.config["sounds"].items():
                try:
                    self.sounds[name] = pg.mixer.Sound(str(ROOT / "assets" / path))
                    self.sounds[name].set_volume(.35)
                except (pg.error, FileNotFoundError):
                    pass
            try:
                pg.mixer.music.load(str(ROOT / "assets" / self.config["music"]))
                pg.mixer.music.set_volume(.3)
                pg.mixer.music.play(-1)
            except (pg.error, FileNotFoundError):
                pass

    def image(self, path, size=None):
        key = (path, size)
        if key not in self.cache:
            try:
                img = pg.image.load(str(ROOT / "assets" / path)).convert_alpha()
                if size:
                    img = pg.transform.scale(img, size)
                self.cache[key] = img
            except (pg.error, FileNotFoundError):
                self.cache[key] = None
        return self.cache[key]

    def sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def actor(self, kind, state, size, age, facing):
        cfg = self.config["sprites"][kind]
        frames = cfg.get(state) or cfg.get("idle", [])
        if not frames:
            return None
        img = self.image(frames[int(age * cfg.get("fps", 8)) % len(frames)], size)
        return pg.transform.flip(img, True, False) if img and facing < 0 else img


class Actor:
    def __init__(self, x, y, enemy=False):
        self.box = pg.FRect(x, y, 36, 54)
        self.velocity = pg.Vector2()
        self.enemy = enemy
        self.hp = 3 if enemy else 6
        self.facing = -1 if enemy else 1
        self.grounded = False
        self.cooldown = .65 if enemy else 0
        self.invincible = 0.0
        self.age = 0.0
        self.origin = x

    def physics(self, dt, solids):
        self.velocity.y = min(1050, self.velocity.y + GRAVITY * dt)
        self.box.x += self.velocity.x * dt
        for solid in solids:
            if self.box.colliderect(solid):
                if self.velocity.x > 0:
                    self.box.right = solid.left
                elif self.velocity.x < 0:
                    self.box.left = solid.right
        self.box.x = max(0, min(WORLD - self.box.w, self.box.x))
        self.box.y += self.velocity.y * dt
        self.grounded = False
        for solid in solids:
            if self.box.colliderect(solid):
                if self.velocity.y > 0:
                    self.box.bottom = solid.top
                    self.grounded = True
                elif self.velocity.y < 0:
                    self.box.top = solid.bottom
                self.velocity.y = 0
        self.cooldown = max(0, self.cooldown - dt)
        self.invincible = max(0, self.invincible - dt)
        self.age += dt


class Bullet:
    def __init__(self, owner, direction):
        self.enemy = owner.enemy
        self.box = pg.FRect(0, 0, 16, 7)
        self.box.center = (owner.box.centerx + direction.x * 29,
                           owner.box.centery + direction.y * 29)
        self.velocity = direction * (430 if self.enemy else 790)
        self.life = 2.5


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.canvas = pg.Surface((WIDTH, HEIGHT))
        self.media = Media()
        self.font = pg.font.Font(None, 26)
        self.big = pg.font.Font(None, 76)
        self.small = pg.font.Font(None, 21)
        self.rng = random.Random(17)
        self.muted = False
        self.reset()
        self.mode = "title"

    def reset(self):
        self.player = Actor(90, 420)
        self.solids = [pg.FRect(0, 570, WORLD, 100)]
        self.solids += [pg.FRect(x, y, w, 22) for x, y, w in [
            (440, 455, 180), (820, 360, 200), (1220, 455, 170),
            (1650, 420, 220), (2070, 330, 200), (2480, 450, 220),
            (2950, 410, 220), (3400, 320, 190), (3850, 445, 250),
            (4350, 360, 220), (4820, 445, 250), (5330, 350, 220)]]
        self.enemies = [Actor(x, 516, True) for x in
                        (720, 1450, 1950, 2390, 2850, 3310, 3760, 4260, 4740, 5250, 5740)]
        self.bullets = []
        self.particles = []
        self.pickups = [pg.FRect(x, 539, 22, 22) for x in (1570, 3100, 4620)]
        self.camera = 0
        self.kills = 0
        self.mode = "play"
        self.coyote = self.jump_buffer = 0.0
        self.elapsed = 0.0

    def shoot(self, actor, direction):
        if actor.cooldown > 0:
            return
        self.bullets.append(Bullet(actor, direction))
        actor.cooldown = 1.45 if actor.enemy else .18
        self.media.sound("enemy_shoot" if actor.enemy else "shoot")

    def hit(self, actor, damage):
        if actor.invincible > 0 or actor.hp <= 0:
            return
        actor.hp -= damage
        actor.invincible = .12 if actor.enemy else 1.0
        self.media.sound("hit")
        for _ in range(10):
            self.particles.append([pg.Vector2(actor.box.center),
                                   pg.Vector2(self.rng.uniform(-180, 180), self.rng.uniform(-200, 20)), .45])
        if actor.enemy and actor.hp <= 0:
            self.kills += 1

    def update(self, dt, axis=0, firing=False, jump=False):
        if self.mode != "play":
            return
        self.elapsed += dt
        p = self.player
        self.jump_buffer = .12 if jump else max(0, self.jump_buffer - dt)
        self.coyote = .10 if p.grounded else max(0, self.coyote - dt)
        if self.jump_buffer and self.coyote:
            p.velocity.y = -660
            p.grounded = False
            self.coyote = self.jump_buffer = 0
            self.media.sound("jump")
        p.velocity.x = axis * 310
        if axis:
            p.facing = 1 if axis > 0 else -1
        p.physics(dt, self.solids)
        if firing:
            self.shoot(p, pg.Vector2(p.facing, 0))
        for e in self.enemies:
            if e.hp <= 0:
                continue
            delta = pg.Vector2(p.box.center) - pg.Vector2(e.box.center)
            active = abs(delta.x) < 730
            if active:
                e.facing = 1 if delta.x >= 0 else -1
                e.velocity.x = e.facing * 58 if abs(delta.x) > 270 else 0
            else:
                e.velocity.x = 0
            e.physics(dt, self.solids)
            if active and 30 < delta.length() < 700:
                # Walls and platforms block both sight and projectiles.
                if not any(s.clipline(e.box.center, p.box.center) for s in self.solids):
                    self.shoot(e, delta.normalize())
            if p.box.colliderect(e.box):
                self.hit(p, 1)
        # Substeps stop fast bullets tunnelling through thin walls or actors.
        remaining = []
        for b in self.bullets:
            b.life -= dt
            alive = b.life > 0
            steps = max(1, math.ceil(b.velocity.length() * dt / 4))
            for _ in range(steps):
                if not alive:
                    break
                b.box.move_ip(b.velocity.x * dt / steps, b.velocity.y * dt / steps)
                if any(b.box.colliderect(s) for s in self.solids):
                    alive = False
                    break
                for target in ([p] if b.enemy else self.enemies):
                    if target.hp > 0 and b.box.colliderect(target.box):
                        self.hit(target, 1)
                        alive = False
                        break
            if alive and -50 < b.box.x < WORLD + 50 and -100 < b.box.y < HEIGHT + 100:
                remaining.append(b)
        self.bullets = remaining
        for item in self.pickups[:]:
            if p.hp > 0 and p.hp < 6 and p.box.colliderect(item):
                p.hp = min(6, p.hp + 2)
                self.pickups.remove(item)
                self.media.sound("pickup")
        for particle in self.particles:
            particle[0] += particle[1] * dt
            particle[1].y += 450 * dt
            particle[2] -= dt
        self.particles = [a for a in self.particles if a[2] > 0]
        target_camera = max(0, min(WORLD - WIDTH, p.box.centerx - WIDTH * .37))
        self.camera += (target_camera - self.camera) * min(1, 7 * dt)
        if p.hp <= 0 or p.box.top > HEIGHT + 100:
            self.mode = "dead"
        elif p.box.centerx > WORLD - 150:
            self.mode = "win"

    def text(self, text, pos, color=(224, 239, 255), font=None):
        self.canvas.blit((font or self.font).render(text, True, color), pos)

    def background(self):
        self.canvas.fill((10, 16, 35))
        for i, layer in enumerate(self.media.config["background"]):
            image = self.media.image(layer["file"])
            factor = layer["speed"]
            if image:
                # Preserve aspect ratio, repeat horizontally at canvas height.
                size = (max(1, round(image.get_width() * HEIGHT / image.get_height())), HEIGHT)
                scaled = self.media.image(layer["file"], size)
                offset = -(self.camera * factor) % size[0]
                x = offset - size[0]
                while x < WIDTH:
                    self.canvas.blit(scaled, (int(x), 0))
                    x += size[0]
            elif i == 0:
                for n in range(55):
                    x = int(n * 139 - self.camera * factor) % (WIDTH + 30)
                    pg.draw.circle(self.canvas, (71, 104, 145), (x, (n * 83) % 360), 1)
                pg.draw.circle(self.canvas, (49, 73, 110), (870, 125), 42)
            else:
                spacing = 160 if i == 1 else 105
                for n in range(-1, WIDTH // spacing + 2):
                    world_n = n + math.floor(self.camera * factor / spacing)
                    x = n * spacing - (self.camera * factor) % spacing
                    h = 80 + (world_n * 73 % 180)
                    color = (20, 36, 59) if i == 1 else (26, 51, 71)
                    pg.draw.rect(self.canvas, color, (int(x), 570 - h, spacing - 15, h))
                    for yy in range(590 - h, 540, 35):
                        pg.draw.rect(self.canvas, (35, 73, 91), (int(x) + 15, yy, 5, 9))

    def draw_actor(self, actor):
        if actor.hp <= 0:
            return
        if actor.invincible > 0 and int(actor.age * 18) % 2:
            return
        box = pg.Rect(round(actor.box.x - self.camera), round(actor.box.y), 36, 54)
        state = "jump" if not actor.grounded else "run" if actor.velocity.x else "idle"
        kind = "enemy" if actor.enemy else "player"
        image = self.media.actor(kind, state, box.size, actor.age, actor.facing)
        if image:
            self.canvas.blit(image, box)
        else:
            color = (255, 105, 125) if actor.enemy else (80, 235, 217)
            pg.draw.rect(self.canvas, (8, 24, 40), box.inflate(6, 6), border_radius=7)
            pg.draw.rect(self.canvas, color, box, border_radius=6)
            eye_x = box.centerx + actor.facing * 8
            pg.draw.rect(self.canvas, (14, 32, 50), (eye_x - 5, box.y + 10, 11, 8))
            pg.draw.rect(self.canvas, (222, 239, 251),
                         (box.centerx + actor.facing * 15 - 7, box.centery - 2, 17, 7))
        if actor.enemy:
            pg.draw.rect(self.canvas, (77, 39, 58), (box.x, box.y - 12, 36, 4))
            pg.draw.rect(self.canvas, (255, 125, 142), (box.x, box.y - 12, 12 * actor.hp, 4))

    def draw(self):
        self.background()
        for solid in self.solids:
            box = pg.Rect(round(solid.x - self.camera), round(solid.y), round(solid.w), round(solid.h))
            if box.right < 0 or box.left > WIDTH:
                continue
            texture = self.media.image(self.media.config["terrain"], (64, int(solid.h)))
            if texture:
                for x in range(box.left, box.right, 64):
                    self.canvas.blit(texture, (x, box.y), (0, 0, min(64, box.right - x), box.h))
            else:
                pg.draw.rect(self.canvas, (28, 48, 67), box)
                pg.draw.line(self.canvas, (65, 194, 190), box.topleft, box.topright, 3)
        goal_x = WORLD - 120 - self.camera
        pg.draw.rect(self.canvas, (94, 239, 195), (int(goal_x), 465, 8, 105))
        pg.draw.polygon(self.canvas, (94, 239, 195), [(int(goal_x), 465), (int(goal_x) + 65, 485), (int(goal_x), 505)])
        for item in self.pickups:
            box = pg.Rect(round(item.x - self.camera), round(item.y), 22, 22)
            image = self.media.image(self.media.config["pickup"], box.size)
            if image:
                self.canvas.blit(image, box)
            else:
                pg.draw.rect(self.canvas, (100, 245, 180), box, border_radius=4)
                self.text("+", (box.x + 4, box.y - 1), (15, 58, 50))
        self.draw_actor(self.player)
        for e in self.enemies:
            self.draw_actor(e)
        for b in self.bullets:
            box = pg.Rect(round(b.box.x - self.camera), round(b.box.y), 16, 7)
            image = self.media.image(self.media.config["bullets"]["enemy" if b.enemy else "player"], box.size)
            if image:
                self.canvas.blit(image, box)
            else:
                pg.draw.rect(self.canvas, (255, 133, 133) if b.enemy else (255, 237, 158), box, border_radius=3)
        for pos, _, life in self.particles:
            pg.draw.circle(self.canvas, (255, 211, 135), (round(pos.x - self.camera), round(pos.y)), max(1, round(life * 8)))
        pg.draw.rect(self.canvas, (12, 23, 40), (0, 0, WIDTH, 75))
        self.text("NEON / RUNNER", (28, 17), (91, 234, 215))
        self.text("SALUD", (270, 18), font=self.small)
        for n in range(6):
            pg.draw.rect(self.canvas, (85, 231, 193) if n < self.player.hp else (42, 58, 77), (330 + n * 20, 20, 14, 18), border_radius=3)
        self.text(f"ENEMIGOS  {self.kills:02d}/11", (505, 17))
        self.text(f"AVANCE  {min(100, int(self.player.box.x / (WORLD - 165) * 100))}%", (770, 17))
        self.text("A/D o flechas: mover    Espacio: saltar    J: disparar    P/Esc: pausa    M: audio", (28, 49), font=self.small)
        if self.mode != "play":
            veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            veil.fill((5, 12, 27, 215))
            self.canvas.blit(veil, (0, 0))
            title, sub = {
                "title": ("NEON RUNNER", "Llega a la bandera. Esquiva los disparos y busca botiquines."),
                "pause": ("PAUSA", "P o Esc para continuar"),
                "dead": ("INTENTA OTRA VEZ", "R o Enter para reiniciar"),
                "win": ("MISIÓN COMPLETA", f"Enemigos derrotados: {self.kills}/11  ·  Tiempo: {int(self.elapsed)} s"),
            }[self.mode]
            self.text(title, (75, 230), (104, 241, 217), self.big)
            self.text(sub, (80, 320))
            self.text("Enter: jugar  |  R: reiniciar  |  Cierra la ventana para salir", (80, 375), font=self.small)
        dest = self.screen.get_rect()
        ratio = min(dest.w / WIDTH, dest.h / HEIGHT)
        size = (max(1, int(WIDTH * ratio)), max(1, int(HEIGHT * ratio)))
        self.screen.fill((4, 9, 18))
        self.screen.blit(pg.transform.scale(self.canvas, size), ((dest.w - size[0]) // 2, (dest.h - size[1]) // 2))
        pg.display.flip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true", help="Run 600 simulated frames without opening a window")
    args = parser.parse_args()
    if args.smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    pg.mixer.pre_init(44100, -16, 2, 512)
    pg.init()
    try:
        screen = pg.display.set_mode((WIDTH, HEIGHT), pg.RESIZABLE)
        pg.display.set_caption("Neon Runner — Python side scroller")
        game = Game(screen)
        if args.smoke_test:
            game.reset()
            for frame in range(600):
                game.update(STEP, 1, True, frame % 95 == 0)
                if frame % 30 == 0:
                    game.draw()
                if game.mode == "dead":
                    game.reset()
            print("OK: 600 physics frames, rendering, shooting and enemies")
            return
        clock = pg.time.Clock()
        accumulator = 0.0
        jump_pending = False
        running = True
        while running:
            accumulator += min(clock.tick(120) / 1000, .1)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                elif event.type == pg.WINDOWFOCUSLOST and game.mode == "play":
                    game.mode = "pause"
                elif event.type == pg.KEYDOWN:
                    if event.key in (pg.K_ESCAPE, pg.K_p) and game.mode in ("play", "pause"):
                        game.mode = "pause" if game.mode == "play" else "play"
                    elif event.key == pg.K_r or (event.key == pg.K_RETURN and game.mode in ("title", "dead", "win")):
                        game.reset()
                    elif event.key in (pg.K_SPACE, pg.K_w, pg.K_UP) and game.mode == "play":
                        jump_pending = True
                    elif event.key == pg.K_m:
                        game.muted = not game.muted
                        if pg.mixer.get_init():
                            pg.mixer.music.set_volume(0 if game.muted else .3)
                        for sound in game.media.sounds.values():
                            sound.set_volume(0 if game.muted else .35)
            keys = pg.key.get_pressed()
            axis = int(keys[pg.K_d] or keys[pg.K_RIGHT]) - int(keys[pg.K_a] or keys[pg.K_LEFT])
            while accumulator >= STEP:
                game.update(STEP, axis, keys[pg.K_j] or keys[pg.K_LCTRL], jump_pending)
                jump_pending = False
                accumulator -= STEP
            game.draw()
    finally:
        pg.quit()


if __name__ == "__main__":
    main()
