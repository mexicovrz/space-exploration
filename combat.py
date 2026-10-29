# combat.py — боевая система: стрельба, урон, эффекты, абстрактный бой NPC.

import math
import random
from localization import translate
from data import (NPC_TYPES,
                  SCRAP_DEF, SCRAP_BY_ID,
                  VALUABLES_DEF, VALUABLES_BY_ID,
                  DEBRIS_LIFETIME, DEBRIS_RADIUS)


# ============================================================
#                    ВИЗУАЛЬНЫЕ ЭФФЕКТЫ
# ============================================================

class HitFlash:
    """Короткая линия от стрелка к цели. Живёт 0.1 сек."""

    def __init__(self, from_pos, to_pos, color=(255, 240, 100)):
        self.from_pos = list(from_pos)
        self.to_pos = list(to_pos)
        self.color = color
        self.life = 0.12
        self.max_life = 0.12

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surface, camera):
        if self.life <= 0:
            return
        alpha = max(0.0, self.life / self.max_life)
        # от носа стрелка к цели
        sx1, sy1 = camera.world_to_screen(self.from_pos)
        sx2, sy2 = camera.world_to_screen(self.to_pos)
        # Цвет с прозрачностью — эмулируем через затемнение
        col = tuple(int(c * alpha) for c in self.color)
        w = max(1, int(2 * alpha * camera.zoom))
        import pygame
        pygame.draw.line(surface, col, (sx1, sy1), (sx2, sy2), w)


# Глобальный список эффектов. Обновляется в main.
effects = []


def add_hit_flash(from_pos, to_pos, color=(255, 240, 100)):
    effects.append(HitFlash(from_pos, to_pos, color))


def update_effects(dt):
    global effects
    effects = [e for e in effects if e.update(dt)]


def draw_effects(surface, camera):
    for e in effects:
        e.draw(surface, camera)


# ============================================================
#                    ХИТСКАН-СТРЕЛЬБА
# ============================================================

def angle_to(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def angle_diff(a, b):
    return (b - a + math.pi) % (2 * math.pi) - math.pi


def can_hit(shooter_pos, shooter_heading, target_pos, radius, arc=None):
    """Проверяет, в радиусе ли цель. Угол больше не важен.

    arc оставлен для совместимости с другими вызовами, но игнорируется.
    """
    dx = target_pos[0] - shooter_pos[0]
    dy = target_pos[1] - shooter_pos[1]
    dist = math.hypot(dx, dy)
    if dist > radius:
        return False, dist
    return True, dist


# ============================================================
#                    NPC SHIP
# ============================================================

class NPCShip:
    """Корабль-NPC с состояниями и боевыми параметрами."""

    def __init__(self, npc_type, x, y):
        cfg = NPC_TYPES[npc_type]
        self.npc_type = npc_type
        self.name = f"{cfg['name']}-{random.randint(1, 99)}"
        self.color = cfg["color"]
        self.pos = [x, y]
        self.vel = [0.0, 0.0]
        self.heading = random.uniform(0, math.tau)
        self.target = None

        self.hull_hp = cfg["hull_hp"]
        self.hull_hp_max = cfg["hull_hp"]
        self.damage = cfg["damage"]
        self.fire_rate = cfg["fire_rate"]
        self.fire_radius = cfg["radius"]
        self.speed_base = cfg["speed"]

        self.fire_timer = 0.0
        self.target_ship = None      # текущая цель боя (NPC или None для игрока)

        # AI состояние
        self.state = "travel"        # travel / patrol / chase / attack / flee / scan
        self.state_time = 0.0
        self.waypoint = None

        # Для абстрактного боя NPC vs NPC
        self.in_combat_with = None   # другой NPCShip
        self.combat_timer = 0.0

        self.dead = False

    @property
    def is_hostile(self):
        return self.npc_type == "pirate"

    @property
    def is_patrol(self):
        return self.npc_type == "patrol"

    @property
    def is_peaceful(self):
        return self.npc_type in ("trader", "courier")

    @property
    def hp_pct(self):
        if self.hull_hp_max <= 0:
            return 0.0
        return max(0.0, self.hull_hp / self.hull_hp_max)

    # --- Урон ---

    def take_damage(self, amount):
        """Возвращает True, если корабль уничтожен."""
        self.hull_hp -= amount
        if self.hull_hp <= 0:
            self.hull_hp = 0
            self.dead = True
            return True
        return False

    # --- Движение ---

    def set_target(self, pos):
        self.target = [pos[0], pos[1]]

    def at_target(self, eps=30):
        if self.target is None:
            return True
        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        return math.hypot(dx, dy) < eps

    def update_motion(self, dt, speed_mult=1.0):
        if self.target is None:
            return
        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        desired = math.atan2(dy, dx)

        # Плавный доворот
        diff = angle_diff(self.heading, desired)
        turn_speed = 3.0
        if abs(diff) <= turn_speed * dt:
            self.heading = desired
        else:
            self.heading += math.copysign(turn_speed * dt, diff)

        # Движение вперёд
        speed = 180.0 * self.speed_base * speed_mult
        self.pos[0] += math.cos(self.heading) * speed * dt
        self.pos[1] += math.sin(self.heading) * speed * dt

    # --- Простой AI ---

    def update_ai(self, dt, player_pos, player_ship, sector, all_npcs):
        """Обновляет состояние и цель. Простой FSM."""
        self.state_time += dt
        self.fire_timer = max(0.0, self.fire_timer - dt)

        # Проверяем расстояние до игрока
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist_to_player = math.hypot(dx, dy)

        # --- Определяем поведение по типу ---

        if self.npc_type == "pirate":
            # Пират атакует игрока, если он в радиусе 800
            if dist_to_player < 800:
                self.state = "chase"
                self.set_target(player_pos)
                if dist_to_player < self.fire_radius:
                    # Огонь!
                    self.fire_at_player(player_pos, player_ship)
            else:
                # Патрулирование сектора
                self._patrol_random(sector)

        elif self.npc_type == "patrol":
            # Если игрок в розыске и близко — атакуем игрока
            if player_ship.is_wanted and dist_to_player < 1200:
                self.state = "chase"
                self.set_target(player_pos)
                if dist_to_player < self.fire_radius:
                    self.fire_at_player(player_pos, player_ship)
                return

            # Иначе ищем пиратов
            pirate = self._find_nearby_pirate(all_npcs, radius=1200)
            if pirate is not None:
                self.state = "attack"
                self.set_target(pirate.pos)
                self.in_combat_with = pirate
                pirate.in_combat_with = self
                simulate_npc_combat(self, pirate, dt)
            else:
                self._patrol_random(sector)

        elif self.npc_type in ("trader", "courier"):
            # Мирные летают между станциями
            self._travel_between_stations(sector)

    def _patrol_random(self, sector):
        """Летает между случайными точками в секторе."""
        from data import WORLD_SIZE
        if self.at_target():
            import random
            self.set_target((
                random.randint(400, WORLD_SIZE - 400),
                random.randint(400, WORLD_SIZE - 400),
            ))

    def _travel_between_stations(self, sector):
        """Летит к следующей станции."""
        if self.target is None or self.at_target():
            import random
            stations = sector.stations
            if stations:
                st = random.choice(stations)
                self.set_target(st.pos)

    def _find_nearby_pirate(self, all_npcs, radius=1200):
        """Ищет ближайшего пирата в радиусе."""
        best = None
        best_d = radius
        for other in all_npcs:
            if other is self or other.dead:
                continue
            if other.npc_type != "pirate":
                continue
            d = math.hypot(other.pos[0] - self.pos[0],
                           other.pos[1] - self.pos[1])
            if d < best_d:
                best = other
                best_d = d
        return best

    def fire_at_player(self, player_pos, player_ship):
        """Стреляет в игрока, если кулдаун готов."""
        if self.fire_timer > 0:
            return
        # Проверяем радиус
        d = math.hypot(player_pos[0] - self.pos[0],
                       player_pos[1] - self.pos[1])
        if d > self.fire_radius:
            return
        # Наносим урон
        player_ship.take_damage_hull(self.damage)
        self.fire_timer = self.fire_rate
        # Визуальный эффект
        add_hit_flash(self.pos, player_pos,
                      color=(255, 80, 80))

    def draw(self, surface, camera, is_target=False):
        import pygame
        sx, sy = camera.world_to_screen(self.pos)
        size = 14 * camera.zoom
        h = self.heading
        nose = (sx + math.cos(h) * size, sy + math.sin(h) * size)
        left = (sx + math.cos(h + 2.5) * size, sy + math.sin(h + 2.5) * size)
        right = (sx + math.cos(h - 2.5) * size, sy + math.sin(h - 2.5) * size)
        pygame.draw.polygon(surface, self.color, [nose, left, right])
        outline = (255, 255, 255) if is_target else (200, 200, 200)
        pygame.draw.polygon(surface, outline, [nose, left, right], 2)

        # Полоска HP над кораблём
        bar_w = size * 2
        bar_h = 4
        bar_x = sx - bar_w / 2
        bar_y = sy - size - 12
        pygame.draw.rect(surface, (40, 40, 60),
                         (bar_x, bar_y, bar_w, bar_h))
        fill = bar_w * self.hp_pct
        col = (90, 210, 120) if self.hp_pct > 0.5 else (
            (240, 180, 60) if self.hp_pct > 0.25 else (230, 80, 80))
        pygame.draw.rect(surface, col, (bar_x, bar_y, fill, bar_h))

        # Имя при наведении
        if is_target:
            import pygame.font
            font = pygame.font.SysFont(None, int(18 * camera.zoom))
            surf = font.render(translate(self.name), True, (240, 240, 240))
            rect = surf.get_rect(center=(sx, sy - size - 24))
            surface.blit(surf, rect)


# ============================================================
#                    СИМУЛЯЦИЯ БОЯ NPC vs NPC (абстрактно)
# ============================================================

def simulate_npc_combat(npc_a, npc_b, dt):
    """Раз в секунду — урон. Кто-то умирает."""
    if npc_a.dead or npc_b.dead:
        return

    npc_a.combat_timer += dt
    if npc_a.combat_timer < 1.0:
        return
    npc_a.combat_timer = 0.0

    # Случайный урон
    dmg_a = npc_a.damage if npc_a.damage > 0 else 4.0
    dmg_b = npc_b.damage if npc_b.damage > 0 else 4.0

    npc_b.take_damage(dmg_a)
    if npc_b.dead:
        return
    npc_a.take_damage(dmg_b)


# ============================================================
#                    РЕГИСТР NPC ПО СЕКТОРУ
# ============================================================

# {sector_index: [NPCShip, ...]}
npc_registry = {}


def get_npcs_for_sector(sector_index):
    return npc_registry.get(sector_index, [])


def clear_npcs(sector_index):
    npc_registry[sector_index] = []
    
# ============================================================
#                    DEBRIS (ОБЛОМКИ)
# ============================================================

class Debris:
    """Обломки корабля. Содержат хлам, трофеи и опционально детали."""

    def __init__(self, x, y, scrap_list, valuables_list, parts_list):
        self.pos = [x, y]
        self.radius = DEBRIS_RADIUS
        self.scrap = scrap_list
        self.valuables = valuables_list
        self.parts = parts_list
        self.life = DEBRIS_LIFETIME
        self.collected = False

    @property
    def is_empty(self):
        return (not self.scrap and not self.valuables and not self.parts)

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surface, camera):
        import pygame
        sx, sy = camera.world_to_screen(self.pos)
        r = int(self.radius * camera.zoom)
        col = (230, 180, 60)
        outline = (255, 230, 120)
        pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, outline, pts, max(1, int(2 * camera.zoom)))
        pygame.draw.circle(surface, (60, 40, 20),
                           (int(sx), int(sy)), max(2, int(4 * camera.zoom)))
        pct = max(0.0, self.life / DEBRIS_LIFETIME)
        bar_w = r * 2
        bar_h = max(2, int(3 * camera.zoom))
        bar_x = sx - r
        bar_y = sy + r + 4
        pygame.draw.rect(surface, (60, 40, 40),
                         (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, (230, 180, 60),
                         (bar_x, bar_y, bar_w * pct, bar_h))


debris_list = []


def drop_debris(npc):
    """Создаёт обломки на месте убитого NPC."""
    if npc is None:
        return

    scrap_list = []
    valuables_list = []
    parts_list = []

    if npc.npc_type == "pirate":
        n_scrap = random.randint(2, 5)
        for _ in range(n_scrap):
            sid = random.choice(SCRAP_DEF)[0]
            found = False
            for i, (s, c) in enumerate(scrap_list):
                if s == sid:
                    scrap_list[i] = (s, c + 1)
                    found = True
                    break
            if not found:
                scrap_list.append((sid, 1))

        if random.random() < 0.30:
            from data import PARTS_DEF
            base_parts = [r for r in PARTS_DEF if not r[0].endswith("_mk2")
                          and r[1] not in ("Оружие", "Щит")]
            if base_parts:
                p = random.choice(base_parts)
                parts_list.append(p[0])

        if random.random() < 0.10:
            vid = random.choice(VALUABLES_DEF)[0]
            valuables_list.append((vid, 1))

    elif npc.npc_type == "patrol":
        for _ in range(random.randint(1, 2)):
            sid = random.choice(SCRAP_DEF)[0]
            found = False
            for i, (s, c) in enumerate(scrap_list):
                if s == sid:
                    scrap_list[i] = (s, c + 1)
                    found = True
                    break
            if not found:
                scrap_list.append((sid, 1))

        from data import PARTS_DEF
        mk2_parts = [r for r in PARTS_DEF if r[0].endswith("_mk2")]
        if mk2_parts:
            p = random.choice(mk2_parts)
            parts_list.append(p[0])

        if random.random() < 0.30:
            vid = random.choice(VALUABLES_DEF)[0]
            valuables_list.append((vid, 1))

    else:
        for _ in range(random.randint(1, 2)):
            sid = random.choice(SCRAP_DEF)[0]
            found = False
            for i, (s, c) in enumerate(scrap_list):
                if s == sid:
                    scrap_list[i] = (s, c + 1)
                    found = True
                    break
            if not found:
                scrap_list.append((sid, 1))

    d = Debris(npc.pos[0], npc.pos[1], scrap_list, valuables_list, parts_list)
    debris_list.append(d)


def update_debris(dt):
    global debris_list
    debris_list = [d for d in debris_list if d.update(dt)]


def draw_debris(surface, camera):
    for d in debris_list:
        d.draw(surface, camera)


def clear_debris():
    global debris_list
    debris_list = []


# ============================================================
#                    DISTRESS SIGNAL
# ============================================================

class DistressSignal:
    """Сигнал бедствия. При тапе запускает случайное событие."""

    def __init__(self, x, y, signal_type):
        self.pos = [x, y]
        self.radius = 60
        self.signal_type = signal_type
        self.life = 300.0
        self.max_life = 300.0
        self.used = False
        self.pulse = 0.0

    def update(self, dt):
        self.life -= dt
        self.pulse += dt * 3.0
        return self.life > 0

    def draw(self, surface, camera):
        import pygame
        import math as _m
        sx, sy = camera.world_to_screen(self.pos)
        r = int(self.radius * camera.zoom)
        pulse_r = r + int(_m.sin(self.pulse) * max(3, int(8 * camera.zoom)))
        col = (255, 100, 100) if self.signal_type == "ambush" else (100, 180, 255)
        pygame.draw.circle(surface, col, (int(sx), int(sy)), pulse_r,
                           max(2, int(3 * camera.zoom)))
        pygame.draw.circle(surface, (255, 255, 255),
                           (int(sx), int(sy)), max(3, int(5 * camera.zoom)))
        font = pygame.font.SysFont(None, max(12, int(20 * camera.zoom)))
        text = font.render("SOS", True, (255, 200, 200))
        rect = text.get_rect(center=(sx, sy - pulse_r - 12))
        surface.blit(text, rect)


signal_list = []


def spawn_signal(x, y, signal_type):
    signal_list.append(DistressSignal(x, y, signal_type))


def update_signals(dt):
    global signal_list
    signal_list = [s for s in signal_list if s.update(dt)]


def draw_signals(surface, camera):
    for s in signal_list:
        s.draw(surface, camera)


def clear_signals():
    global signal_list
    signal_list = []


def has_scanner(ship_systems):
    """Возвращает 0/1/2 — тир сканера, или 0 если нет."""
    hull = ship_systems.systems.get("hull", None)
    if hull is None:
        return 0
    for slot in hull.slots:
        if slot.part is None or slot.part.is_broken():
            continue
        effects = slot.part.info.get("effects", {})
        tier = effects.get("signal_scanner", 0)
        if tier > 0:
            return tier
    return 0
    
# ============================================================
#                    MISSILE (РАКЕТА)
# ============================================================

class Missile:
    """Самонаводящаяся ракета."""

    def __init__(self, pos, target, damage, speed=400.0):
        self.pos = [pos[0], pos[1]]
        self.target = target
        self.damage = damage
        self.speed = speed
        self.life = 15.0
        self.direction = 0.0
        self.dead = False

    def update(self, dt):
        if self.target is None or getattr(self.target, "dead", False):
            self.dead = True
            return False

        dx = self.target.pos[0] - self.pos[0]
        dy = self.target.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist < 20:
            if hasattr(self.target, "take_damage"):
                self.target.take_damage(self.damage)
            self.dead = True
            return False

        desired = math.atan2(dy, dx)
        diff = (desired - self.direction + math.pi) % (2 * math.pi) - math.pi
        turn_speed = 3.0
        if abs(diff) <= turn_speed * dt:
            self.direction = desired
        else:
            self.direction += math.copysign(turn_speed * dt, diff)

        self.pos[0] += math.cos(self.direction) * self.speed * dt
        self.pos[1] += math.sin(self.direction) * self.speed * dt

        self.life -= dt
        if self.life <= 0:
            self.dead = True
            return False
        return True

    def draw(self, surface, camera):
        import pygame
        sx, sy = camera.world_to_screen(self.pos)
        r = max(6, int(10 * camera.zoom))
        pygame.draw.circle(surface, (255, 100, 60),
                           (int(sx), int(sy)), r)
        tail_x = sx - math.cos(self.direction) * r * 2
        tail_y = sy - math.sin(self.direction) * r * 2
        pygame.draw.line(surface, (255, 200, 100),
                         (tail_x, tail_y), (sx, sy),
                         max(1, int(2 * camera.zoom)))


# --- Реестр ракет ---
missile_list = []


def spawn_missile(pos, target, damage, speed=400.0):
    missile_list.append(Missile(pos, target, damage, speed))


def update_missiles(dt):
    global missile_list
    for m in missile_list:
        m.update(dt)
    missile_list = [m for m in missile_list if not m.dead]


def draw_missiles(surface, camera):
    for m in missile_list:
        m.draw(surface, camera)


def clear_missiles():
    global missile_list
    missile_list = []