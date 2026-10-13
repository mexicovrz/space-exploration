# world.py — сектор, станции, врата, астероиды, корабль

import math
import random
from data import (WORLD_SIZE, STATION_COLOR, GATE_COLOR, ASTEROID_COL,
                  SHIP_COLOR, SHIP_SIZE, SHIP_MAX_SPEED, SHIP_ACCEL,
                  SHIP_ARRIVE_EPS, SHIP_BRAKE_RADIUS,
                  SHIP_TURN_SPEED, SHIP_TURN_SPEED_MOVING,
                  SHIP_MIN_SPEED_FOR_TURN, SHIP_SNAP_ON_TAP, clamp)


def angle_to(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def angle_diff(a, b):
    return (b - a + math.pi) % (2 * math.pi) - math.pi


def turn_towards(current, target, max_step):
    d = angle_diff(current, target)
    if abs(d) <= max_step:
        return target
    return current + math.copysign(max_step, d)


# Заглушки для рисования — привязываются из main.py
pygame_draw_circle = None
pygame_draw_polygon = None

def bind_pygame(draw_circle, draw_polygon):
    global pygame_draw_circle, pygame_draw_polygon
    pygame_draw_circle = draw_circle
    pygame_draw_polygon = draw_polygon


class Station:
    def __init__(self, x, y, name):
        self.pos = [x, y]
        self.name = name
        self.radius = 40
        # Контракты
        self.contracts = []                # список Contract
        self.contracts_generated_time = 0.0
        self.contracts_ever_generated = False

    def draw(self, surface, cam):
        sx, sy = cam.world_to_screen(self.pos)
        r = int(self.radius * cam.zoom)
        pygame_draw_circle(surface, STATION_COLOR, (int(sx), int(sy)), r)
        pygame_draw_circle(surface, (255, 255, 255), (int(sx), int(sy)), r, 2)
        
    def to_dict(self):
        from contracts import contract_to_dict
        return {
            "pos": list(self.pos),
            "name": self.name,
            "radius": self.radius,
            "contracts": [contract_to_dict(c) for c in self.contracts],
            "contracts_generated_time": self.contracts_generated_time,
            "contracts_ever_generated": self.contracts_ever_generated,
        }

    def apply_dict(self, d, station_lookup):
        from contracts import contract_from_dict
        self.pos = list(d["pos"])
        self.name = d["name"]
        self.radius = d.get("radius", 40)
        self.contracts = []
        for c_data in d.get("contracts", []):
            c = contract_from_dict(c_data, station_lookup)
            if c is not None:
                self.contracts.append(c)
        self.contracts_generated_time = d.get("contracts_generated_time", 0.0)
        self.contracts_ever_generated = d.get("contracts_ever_generated", False)


class Gate:
    def __init__(self, x, y, name, target_sector):
        self.pos = [x, y]
        self.name = name
        self.target_sector = target_sector
        self.radius = 30

    def draw(self, surface, cam):
        sx, sy = cam.world_to_screen(self.pos)
        r = int(self.radius * cam.zoom)
        pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        pygame_draw_polygon(surface, GATE_COLOR, pts)
        pygame_draw_polygon(surface, (255, 255, 255), pts, 2)


class Asteroid:
    def __init__(self, x, y, r):
        self.pos = [x, y]
        self.radius = r
        self.shape = self._make_shape()

    def _make_shape(self):
        pts = []
        n = random.randint(6, 9)
        for i in range(n):
            a = (i / n) * math.tau
            rr = self.radius * random.uniform(0.7, 1.1)
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
        return pts

    def draw(self, surface, cam):
        sx, sy = cam.world_to_screen(self.pos)
        z = cam.zoom
        pts = [(sx + px * z, sy + py * z) for px, py in self.shape]
        pygame_draw_polygon(surface, ASTEROID_COL, pts)

class QuestMarker:
    """Объект на карте, связанный с сюжетным квестом (обломки, сигнал)."""

    def __init__(self, x, y, name, quest_id):
        self.pos = [x, y]
        self.name = name
        self.quest_id = quest_id
        self.radius = 50
        self.collected = False

    def draw(self, surface, cam, active=True):
        sx, sy = cam.world_to_screen(self.pos)
        r = int(self.radius * cam.zoom)
        col = (240, 180, 60) if active else (100, 100, 110)
        outline = (255, 255, 255) if active else (140, 140, 160)
        pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        pygame_draw_polygon(surface, col, pts)
        pygame_draw_polygon(surface, outline, pts, max(1, int(2 * cam.zoom)))

class Ship:
    def __init__(self, x, y):
        self.pos = [x, y]
        self.vel = [0.0, 0.0]
        self.heading = 0.0
        self.target = None

    def set_target(self, x, y):
        self.target = [x, y]
        if SHIP_SNAP_ON_TAP:
            self.heading = angle_to(self.pos, self.target)

    def stop(self):
        self.target = None
        self.vel = [0.0, 0.0]

    def update(self, dt):
        if self.target is None:
            return

        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        dist = math.hypot(dx, dy)

        if dist < SHIP_ARRIVE_EPS:
            self.vel[0] *= 0.85
            self.vel[1] *= 0.85
            if math.hypot(*self.vel) < 8:
                self.stop()
            return

        desired = math.atan2(dy, dx)

        if dist < SHIP_BRAKE_RADIUS:
            thrust_scale = dist / SHIP_BRAKE_RADIUS
        else:
            thrust_scale = 1.0
        thrust_scale = clamp(thrust_scale, 0.0, 1.0)

        speed = math.hypot(*self.vel)
        turn_speed = (SHIP_TURN_SPEED if speed < SHIP_MIN_SPEED_FOR_TURN
                      else SHIP_TURN_SPEED_MOVING)

        if speed < SHIP_MIN_SPEED_FOR_TURN:
            aim = desired
        else:
            aim = math.atan2(self.vel[1], self.vel[0])

        self.heading = turn_towards(self.heading, aim, turn_speed * dt)

        ax = math.cos(desired) * SHIP_ACCEL * thrust_scale
        ay = math.sin(desired) * SHIP_ACCEL * thrust_scale
        self.vel[0] += ax * dt
        self.vel[1] += ay * dt

        speed = math.hypot(*self.vel)
        if speed > SHIP_MAX_SPEED:
            k = SHIP_MAX_SPEED / speed
            self.vel[0] *= k
            self.vel[1] *= k

        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

        self.pos[0] = clamp(self.pos[0], 0, WORLD_SIZE)
        self.pos[1] = clamp(self.pos[1], 0, WORLD_SIZE)

    def draw(self, surface, cam):
        sx, sy = cam.world_to_screen(self.pos)
        size = SHIP_SIZE * cam.zoom
        h = self.heading
        nose = (sx + math.cos(h) * size, sy + math.sin(h) * size)
        left = (sx + math.cos(h + 2.5) * size, sy + math.sin(h + 2.5) * size)
        right = (sx + math.cos(h - 2.5) * size, sy + math.sin(h - 2.5) * size)
        pygame_draw_polygon(surface, SHIP_COLOR, [nose, left, right])
        pygame_draw_polygon(surface, (255, 255, 255), [nose, left, right], 2)


class Sector:
    def __init__(self, index, name):
        self.index = index
        self.name = name
        self.seed = 0
        self.stations = []
        self.gates = []
        self.asteroids = []
        self.quest_markers = []
        self.npcs = []


def make_test_sector():
    sec = Sector(0, "Alpha")
    sec.stations.append(Station(600, 500, "Станция Керн"))
    sec.stations.append(Station(3200, 1100, "Форт Ньютон"))
    sec.stations.append(Station(1800, 2800, "Порт Стелла"))
    sec.gates.append(Gate(2000, 3600, "Врата - Beta", target_sector=1))

    random.seed(7)
    for _ in range(28):
        x = random.randint(200, WORLD_SIZE - 200)
        y = random.randint(200, WORLD_SIZE - 200)
        r = random.randint(25, 80)
        sec.asteroids.append(Asteroid(x, y, r))
    return sec