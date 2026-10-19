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
FLIGHT_TOP = 85  # Keep actors below the HUD.
ENEMY_COUNT = 30
ARENA_LEFT = WORLD - WIDTH
BOSS_HP = 60


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
        self.cooldown = .65 if enemy else 0
        self.invincible = 0.0
        self.age = 0.0
        self.origin_y = y

    def physics(self, dt):
        """Free flight: constant commanded velocity, no gravity or platforms."""
        self.box.x += self.velocity.x * dt
        self.box.x = max(0, min(WORLD - self.box.w, self.box.x))
        self.box.y += self.velocity.y * dt
        self.box.y = max(FLIGHT_TOP, min(HEIGHT - self.box.h, self.box.y))
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


class Boss(Actor):
    """Three readable attack patterns, with a faster second phase."""
    PATTERNS = ("ABANICO DIRIGIDO", "ANILLO", "BARRIDO")

    def __init__(self):
        super().__init__(WORLD - 260, 270, True)
        self.box.size = (130, 120)
        self.hp = BOSS_HP
        self.active = False
        self.attack_time = 0.0
        self.pattern = 0
        self.warning = True
        self.cooldown = 0

    @property
    def phase(self):
        return 2 if self.hp <= BOSS_HP // 2 else 1

    def update(self, dt, player):
        if not self.active or self.hp <= 0:
            return []
        self.physics(dt)
        self.box.centery = 360 + math.sin(self.age * (1.4 if self.phase == 2 else 1)) * 175
        self.facing = 1 if player.box.centerx > self.box.centerx else -1
        previous_pattern = self.pattern
        self.attack_time += dt
        self.pattern = int(self.attack_time / 5) % 3
        cycle = self.attack_time % 5
        self.warning = cycle < 1.0 or cycle > 4.0
        if previous_pattern != self.pattern:
            self.cooldown = 0
        if self.warning or self.cooldown > 0:
            return []
        delta = pg.Vector2(player.box.center) - pg.Vector2(self.box.center)
        aim = delta.normalize() if delta.length_squared() else pg.Vector2(-1, 0)
        if self.pattern == 0:
            angles = (-24, -12, 0, 12, 24) if self.phase == 2 else (-18, 0, 18)
            directions = [aim.rotate(a) for a in angles]
            self.cooldown = .75 if self.phase == 2 else 1.0
        elif self.pattern == 1:
            count = 16 if self.phase == 2 else 12
            directions = [pg.Vector2(1, 0).rotate(i * 360 / count + cycle * 22)
                          for i in range(count)]
            self.cooldown = 1.0 if self.phase == 2 else 1.3
        else:
            sweep = math.sin(cycle * 3) * 65
            directions = [pg.Vector2(self.facing, 0).rotate(sweep)]
            if self.phase == 2:
                directions.append(pg.Vector2(self.facing, 0).rotate(-sweep))
            self.cooldown = .17 if self.phase == 2 else .25
        bullets = []
        for direction in directions:
            bullet = Bullet(self, direction)
            bullet.velocity = direction * (310 if self.phase == 2 else 255)
            bullet.life = 4.5
            bullets.append(bullet)
        return bullets


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
        self.player = Actor(90, 320)
        self.enemies = [Actor(720 + i * 150, 140 + (i * 137) % 390, True)
                        for i in range(ENEMY_COUNT)]
        for i, enemy in enumerate(self.enemies):
            enemy.cooldown = .8 + (i % 5) * .27
        self.bullets = []
        self.particles = []
        self.pickups = [pg.FRect(x, y, 22, 22) for x, y in
                        ((1570, 230), (2700, 460), (3900, 180), (5100, 380))]
        self.camera = 0
        self.kills = 0
        self.mode = "play"
        self.elapsed = 0.0
        self.boss = Boss()

    def shoot(self, actor, direction):
        if actor.cooldown > 0:
            return
        self.bullets.append(Bullet(actor, direction))
        actor.cooldown = 2.1 if actor.enemy else .18
        self.media.sound("enemy_shoot" if actor.enemy else "shoot")

    def hit(self, actor, damage):
        if actor.invincible > 0 or actor.hp <= 0:
            return
        actor.hp = max(0, actor.hp - damage)
        actor.invincible = .12 if actor.enemy else 1.0
        self.media.sound("hit")
        for _ in range(10):
            self.particles.append([pg.Vector2(actor.box.center),
                                   pg.Vector2(self.rng.uniform(-180, 180), self.rng.uniform(-200, 20)), .45])
        if actor is self.boss and actor.hp <= 0:
            # A defeated boss cannot leave a final, unavoidable volley behind.
            self.media.sound("boss_defeat")
        elif actor.enemy and actor.hp <= 0:
            self.kills += 1

    def update(self, dt, axis=0, firing=False, vertical=0):
        if self.mode != "play":
            return
        self.elapsed += dt
        p = self.player
        movement = pg.Vector2(axis, vertical)
        if movement.length_squared() > 1:
            movement.normalize_ip()  # Diagonal flight has the same speed.
        p.velocity = movement * 310
        if axis:
            p.facing = 1 if axis > 0 else -1
        p.physics(dt)
        if not self.boss.active and self.boss.hp > 0 and p.box.x >= ARENA_LEFT + 80:
            self.boss.active = True
            self.bullets.clear()
            p.hp = min(6, p.hp + 2)
        if self.boss.active and self.boss.hp > 0:
            p.box.x = max(ARENA_LEFT + 20, min(WORLD - 180 - p.box.w, p.box.x))
        if firing:
            self.shoot(p, pg.Vector2(p.facing, 0))
        for e in self.enemies:
            if e.hp <= 0 or self.boss.active:
                continue
            delta = pg.Vector2(p.box.center) - pg.Vector2(e.box.center)
            active = abs(delta.x) < 730
            if active:
                e.facing = 1 if delta.x >= 0 else -1
                e.velocity.x = e.facing * 80 if abs(delta.x) > 310 else 0
                # Follow the player's altitude, with a small weaving motion.
                target_y = p.box.centery + math.sin(e.age * 1.8 + e.origin_y) * 65
                e.velocity.y = max(-115, min(115, (target_y - e.box.centery) * 1.5))
            else:
                e.velocity.x = 0
                e.velocity.y = math.cos(e.age * 1.2 + e.origin_y) * 30
            e.physics(dt)
            if active and 30 < delta.length() < 700:
                self.shoot(e, delta.normalize())
            if p.box.colliderect(e.box):
                self.hit(p, 1)
        boss_bullets = self.boss.update(dt, p)
        self.bullets.extend(boss_bullets)
        if boss_bullets:
            self.media.sound("enemy_shoot")
        if self.boss.active and self.boss.hp > 0 and p.box.colliderect(self.boss.box):
            self.hit(p, 2)
        # Substeps stop fast bullets tunnelling through actors.
        remaining = []
        for b in self.bullets:
            b.life -= dt
            alive = b.life > 0
            steps = max(1, math.ceil(b.velocity.length() * dt / 4))
            for _ in range(steps):
                if not alive:
                    break
                b.box.move_ip(b.velocity.x * dt / steps, b.velocity.y * dt / steps)
                targets = [p] if b.enemy else self.enemies + ([self.boss] if self.boss.active else [])
                for target in targets:
                    if target.hp > 0 and b.box.colliderect(target.box):
                        self.hit(target, 1)
                        alive = False
                        break
            if alive and -50 < b.box.x < WORLD + 50 and -100 < b.box.y < HEIGHT + 100:
                remaining.append(b)
        self.bullets = [b for b in remaining if not (self.boss.active and self.boss.hp <= 0 and b.enemy)]
        for item in self.pickups[:]:
            if p.hp > 0 and p.hp < 6 and p.box.colliderect(item):
                p.hp = min(6, p.hp + 2)
                self.pickups.remove(item)
                self.media.sound("pickup")
        for particle in self.particles:
            particle[0] += particle[1] * dt
            particle[2] -= dt
        self.particles = [a for a in self.particles if a[2] > 0]
        target_camera = ARENA_LEFT if self.boss.active else max(0, min(WORLD - WIDTH, p.box.centerx - WIDTH * .37))
        self.camera += (target_camera - self.camera) * min(1, 7 * dt)
        if p.hp <= 0:
            self.mode = "dead"
        elif self.boss.hp <= 0 and p.box.centerx > WORLD - 150:
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
        # Optional flight frames; older manifests continue to use run/idle.
        moving = actor.velocity.length_squared() > 1
        cfg = self.media.config["sprites"]["enemy" if actor.enemy else "player"]
        state = "fly" if cfg.get("fly") else "run" if moving else "idle"
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
        if self.boss.active and self.boss.hp > 0:
            wall_x = int(ARENA_LEFT + 20 - self.camera)
            pg.draw.line(self.canvas, (255, 115, 140), (wall_x, FLIGHT_TOP), (wall_x, HEIGHT), 3)
        goal_x = WORLD - 120 - self.camera
        goal_color = (255, 115, 140) if self.boss.hp > 0 else (94, 239, 195)
        pg.draw.line(self.canvas, goal_color, (int(goal_x), FLIGHT_TOP), (int(goal_x), HEIGHT), 5)
        self.text("BLOQUEADA" if self.boss.hp > 0 else "META", (int(goal_x) - 115, 140), goal_color)
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
        self.draw_boss()
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
        self.text(f"ENEMIGOS  {self.kills:02d}/{len(self.enemies)}", (505, 17))
        self.text(f"AVANCE  {min(100, int(self.player.box.x / (WORLD - 165) * 100))}%", (770, 17))
        self.text("WASD o flechas: volar    J/Ctrl/Espacio: disparar    P/Esc: pausa    M: audio", (28, 49), font=self.small)
        if self.mode != "play":
            veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            veil.fill((5, 12, 27, 215))
            self.canvas.blit(veil, (0, 0))
            title, sub = {
                "title": ("NEON RUNNER", "Vuela, esquiva y derrota al jefe final para abrir la meta."),
                "pause": ("PAUSA", "P o Esc para continuar"),
                "dead": ("INTENTA OTRA VEZ", "R o Enter para reiniciar"),
                "win": ("MISIÓN COMPLETA", f"Enemigos derrotados: {self.kills}/{len(self.enemies)}  ·  Tiempo: {int(self.elapsed)} s"),
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

    def draw_boss(self):
        boss = self.boss
        if not boss.active or boss.hp <= 0:
            return
        box = pg.Rect(round(boss.box.x - self.camera), round(boss.box.y), 130, 120)
        image = None
        if "boss" in self.media.config["sprites"]:
            cfg = self.media.config["sprites"]["boss"]
            state = "fly" if cfg.get("fly") else "idle"
            image = self.media.actor("boss", state, box.size, boss.age, boss.facing)
        flashing = boss.invincible > 0 and int(boss.age * 24) % 2
        if not flashing:
            if image:
                self.canvas.blit(image, box)
            else:
                color = (255, 155, 75) if boss.phase == 1 else (255, 75, 150)
                pg.draw.rect(self.canvas, (41, 26, 57), box, border_radius=24)
                pg.draw.rect(self.canvas, color, box, 5, border_radius=24)
                pg.draw.circle(self.canvas, color, box.center, 26)
                pg.draw.circle(self.canvas, (255, 239, 190), box.center, 11)
                for offset in (22, 90):
                    pg.draw.rect(self.canvas, color, (box.x - 12, box.y + offset, box.w + 24, 9))
        pg.draw.rect(self.canvas, (20, 18, 38), (240, 84, 620, 46), border_radius=6)
        pg.draw.rect(self.canvas, (78, 36, 61), (250, 113, 600, 8))
        pg.draw.rect(self.canvas, (255, 110, 130), (250, 113, round(600 * boss.hp / BOSS_HP), 8))
        label = "PREPARANDO" if boss.warning else "ATAQUE"
        self.text(f"JEFE {boss.hp}/{BOSS_HP}  FASE {boss.phase}  {label}: {boss.PATTERNS[boss.pattern]}",
                  (250, 89), (255, 208, 175), self.small)


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
                game.update(STEP, 1, True, 1 if frame % 240 < 120 else -1)
                if frame % 30 == 0:
                    game.draw()
                if game.mode == "dead":
                    game.reset()
            print("OK: 600 physics frames, rendering, shooting and enemies")
            return
        clock = pg.time.Clock()
        accumulator = 0.0
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
                    elif event.key == pg.K_m:
                        game.muted = not game.muted
                        if pg.mixer.get_init():
                            pg.mixer.music.set_volume(0 if game.muted else .3)
                        for sound in game.media.sounds.values():
                            sound.set_volume(0 if game.muted else .35)
            keys = pg.key.get_pressed()
            axis = int(keys[pg.K_d] or keys[pg.K_RIGHT]) - int(keys[pg.K_a] or keys[pg.K_LEFT])
            vertical = int(keys[pg.K_s] or keys[pg.K_DOWN]) - int(keys[pg.K_w] or keys[pg.K_UP])
            while accumulator >= STEP:
                game.update(STEP, axis, keys[pg.K_j] or keys[pg.K_LCTRL] or keys[pg.K_SPACE], vertical)
                accumulator -= STEP
            game.draw()
    finally:
        pg.quit()


if __name__ == "__main__":
    main()
