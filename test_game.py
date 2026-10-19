"""Deterministic gameplay checks. Run: python -m unittest -v."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import unittest
import pygame as pg
from main import Actor, Boss, Bullet, Game, STEP, WORLD, HEIGHT, FLIGHT_TOP, ENEMY_COUNT, ARENA_LEFT, BOSS_HP


class GameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        cls.screen = pg.display.set_mode((1100, 650))

    @classmethod
    def tearDownClass(cls):
        pg.quit()

    def setUp(self):
        self.game = Game(self.screen)
        self.game.reset()

    def advance(self, frames=120, **controls):
        for _ in range(frames):
            self.game.update(STEP, **controls)

    def test_free_flight_without_gravity(self):
        self.game.enemies.clear()
        p = self.game.player
        initial_y = p.box.y
        self.advance()
        self.assertEqual(p.box.y, initial_y)
        self.advance(30, vertical=-1)
        self.assertLess(p.box.y, initial_y)
        previous_y = p.box.y
        self.advance(30, vertical=1)
        self.assertGreater(p.box.y, previous_y)
        previous_y = p.box.y
        self.advance()
        self.assertEqual(p.box.y, previous_y)

    def test_flight_bounds_and_diagonal_speed(self):
        g = self.game
        g.enemies.clear()
        self.advance(300, vertical=-1)
        self.assertEqual(g.player.box.top, FLIGHT_TOP)
        self.advance(300, vertical=1)
        self.assertEqual(g.player.box.bottom, HEIGHT)
        g.update(STEP, axis=1, vertical=-1)
        self.assertAlmostEqual(g.player.velocity.length(), 310)
        e = Actor(WORLD + 10, -500, True)
        e.physics(STEP)
        self.assertEqual(e.box.right, WORLD)
        self.assertEqual(e.box.top, FLIGHT_TOP)

    def test_more_enemies_and_vertical_ai(self):
        g = self.game
        self.assertEqual(len(g.enemies), ENEMY_COUNT)
        self.assertGreater(ENEMY_COUNT, 11)
        g.player.box.topleft = (300, 100)
        e = Actor(700, 500, True)
        g.enemies = [e]
        self.advance(60)
        self.assertLess(e.box.y, 500)

    def test_projectiles_damage_both_sides(self):
        g = self.game
        self.advance()
        g.player.box.y = 516
        e = Actor(260, 516, True)
        g.enemies = [e]
        g.shoot(g.player, pg.Vector2(1, 0))
        self.advance(35)
        self.assertEqual(e.hp, 2)
        g.bullets.clear()
        e.cooldown = 0
        g.shoot(e, pg.Vector2(-1, 0))
        self.advance(50)
        self.assertLess(g.player.hp, 6)

    def test_bullets_cross_former_platform_area(self):
        g = self.game
        g.enemies.clear()
        g.player.box.topleft = (350, 420)
        g.shoot(g.player, pg.Vector2(1, 0))
        self.advance(30)
        self.assertEqual(len(g.bullets), 1)
        self.assertGreater(g.bullets[0].box.x, 440)

    def test_pause_freezes_world(self):
        g = self.game
        g.mode = "pause"
        before = g.player.box.copy()
        self.advance(axis=1, firing=True)
        self.assertEqual(g.player.box, before)
        self.assertEqual(g.elapsed, 0)

    def test_damage_invulnerability_and_defeat(self):
        g = self.game
        g.hit(g.player, 1)
        g.hit(g.player, 1)
        self.assertEqual(g.player.hp, 5)
        g.player.invincible = 0
        g.hit(g.player, 5)
        g.update(STEP)
        self.assertEqual(g.mode, "dead")
        g.reset()
        self.assertEqual(g.player.hp, 6)
        self.assertEqual(g.mode, "play")

    def test_pickup_and_victory(self):
        g = self.game
        g.player.hp = 3
        g.player.box.topleft = (1570, 220)
        g.update(STEP)
        self.assertEqual(g.player.hp, 5)
        self.assertEqual(len(g.pickups), 3)
        g.player.box.x = WORLD - 140
        g.update(STEP)
        self.assertEqual(g.mode, "play")
        self.assertTrue(g.boss.active)
        g.hit(g.boss, BOSS_HP)
        g.player.box.x = WORLD - 140
        g.update(STEP)
        self.assertEqual(g.mode, "win")

    def test_boss_activation_arena_and_reset(self):
        g = self.game
        self.assertFalse(g.boss.active)
        self.assertGreater(g.boss.box.width, g.player.box.width)
        self.assertGreater(g.boss.hp, g.enemies[0].hp)
        g.player.box.x = ARENA_LEFT + 85
        g.update(STEP)
        self.assertTrue(g.boss.active)
        self.advance(100, axis=-1)
        self.assertGreaterEqual(g.player.box.left, ARENA_LEFT + 20)
        g.reset()
        self.assertFalse(g.boss.active)
        self.assertEqual(g.boss.hp, BOSS_HP)

    def test_boss_patterns_second_phase_and_pause(self):
        g = self.game
        b = g.boss
        b.active = True
        for phase in (1, 2):
            b.hp = BOSS_HP if phase == 1 else BOSS_HP // 2
            self.assertEqual(b.phase, phase)
            counts = []
            for pattern in range(3):
                b.attack_time = pattern * 5 + 1.1
                b.pattern = pattern
                b.cooldown = 0
                volley = b.update(STEP, g.player)
                counts.append(len(volley))
                self.assertTrue(all(bullet.enemy for bullet in volley))
                self.assertTrue(all(bullet.velocity.length() > 0 for bullet in volley))
            self.assertEqual(counts, [3, 12, 1] if phase == 1 else [5, 16, 2])
        b.attack_time = 0
        b.cooldown = 0
        self.assertEqual(b.update(STEP, g.player), [])
        before = b.attack_time
        g.mode = "pause"
        self.advance()
        self.assertEqual(b.attack_time, before)

    def test_boss_player_projectile_damage_and_defeat(self):
        g = self.game
        g.enemies.clear()
        g.boss.active = True
        g.player.box.topleft = (g.boss.box.left - 90, g.boss.box.centery - 27)
        g.shoot(g.player, pg.Vector2(1, 0))
        self.advance(15)
        self.assertLess(g.boss.hp, BOSS_HP)
        g.boss.invincible = 0
        g.bullets.append(Bullet(g.boss, pg.Vector2(-1, 0)))
        g.hit(g.boss, BOSS_HP)
        g.update(STEP)
        self.assertFalse(any(b.enemy for b in g.bullets))
        self.assertEqual(g.kills, 0)

    def test_boss_full_cycle_stays_in_bounds(self):
        b = Boss()
        b.active = True
        player = self.game.player
        patterns = set()
        for _ in range(2400):
            b.update(STEP, player)
            patterns.add(b.pattern)
            self.assertGreaterEqual(b.box.top, FLIGHT_TOP)
            self.assertLessEqual(b.box.bottom, HEIGHT)
        self.assertEqual(patterns, {0, 1, 2})

    def test_enemies_attack_and_projectiles_expire(self):
        g = self.game
        g.player.box.topleft = (300, 516)
        g.enemies = [Actor(700, 516, True)]
        self.advance(100)
        self.assertTrue(any(b.enemy for b in g.bullets))
        g.enemies.clear()
        self.advance(400)
        self.assertFalse(g.bullets)

    def test_render_all_modes_and_resize(self):
        for mode in ("title", "play", "pause", "dead", "win"):
            self.game.mode = mode
            self.game.draw()
        self.game.screen = pg.display.set_mode((640, 480))
        self.game.draw()
        self.game.screen = pg.display.set_mode((1100, 650))
        self.game.boss.active = True
        self.game.camera = ARENA_LEFT
        self.game.mode = "play"
        self.game.draw()


if __name__ == "__main__":
    unittest.main()
