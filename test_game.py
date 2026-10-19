"""Deterministic gameplay checks. Run: python -m unittest -v."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import unittest
import pygame as pg
from main import Actor, Bullet, Game, STEP, WORLD


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

    def test_ground_jump_and_landing(self):
        self.advance()
        p = self.game.player
        self.assertEqual(p.box.bottom, 570)
        self.assertTrue(p.grounded)
        self.game.update(STEP, jump=True)
        self.assertLess(p.velocity.y, 0)
        self.advance()
        self.assertEqual(p.box.bottom, 570)

    def test_projectiles_damage_both_sides(self):
        g = self.game
        self.advance()
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

    def test_platform_blocks_bullet(self):
        g = self.game
        g.enemies.clear()
        g.player.box.topleft = (350, 420)
        g.solids.append(pg.FRect(405, 380, 12, 190))
        g.shoot(g.player, pg.Vector2(1, 0))
        self.advance(30)
        self.assertEqual(len(g.bullets), 0)

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
        g.player.box.topleft = (1570, 516)
        g.update(STEP)
        self.assertEqual(g.player.hp, 5)
        self.assertEqual(len(g.pickups), 2)
        g.player.box.x = WORLD - 140
        g.update(STEP)
        self.assertEqual(g.mode, "win")

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


if __name__ == "__main__":
    unittest.main()
