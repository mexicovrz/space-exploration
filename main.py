# main.py — точка входа.

# --- ЛОГ В ФАЙЛ (для отладки) ---
import os as _os
import os
_LOG_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "startup_log.txt")

def _log(msg):
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
            f.flush()
    except Exception:
        pass

try:
    if _os.path.exists(_LOG_PATH):
        _os.remove(_LOG_PATH)
except Exception:
    pass

_log("### START main.py")

# --- Импорты ---
_log("### before imports")
import sys
import random
import math
_log("### stdlib OK")

import pygame
_log("### pygame OK")

from data import (FPS, FULLSCREEN, TITLE, DARK_SPACE, UI_TEXT, TIME_SCALES,
                  set_ui_scale, S,
                  DOCK_DISTANCE, GATE_DISTANCE,
                  FUEL_MAX, O2_MAX, O2_RESERVE_MAX,
                  WORLD_SIZE,
                  UI_ACCENT, UI_OK, UI_WARN, UI_DANGER, UI_BORDER, UI_DIM,
                  SCRAP_BY_ID, VALUABLES_BY_ID, PARTS_BY_ID)
_log("### data OK")

from ui import Button, draw_text, draw_panel, get_font
_log("### ui OK")

import combat
_log("### combat OK")

from ship import ShipSystems
_log("### ship OK")

from screens import (StationScreen, RepairScreen,
                     ActiveContractsScreen, StartMenuScreen,
                     StoryScreen, ConfirmAttackScreen,
                     InventoryScreen, PrologueScreen,LoadMissileScreen)
from screens import set_story_screen_callback
_log("### screens OK")

from story import QUESTS_BY_ID as STORY_QUESTS_BY_ID
_log("### story OK")

import world as W
_log("### world OK")

import galaxy
_log("### galaxy OK")

import save as SAVE
_log("### save OK")


# --- pygame init ---
_log("### before pygame.init")
pygame.init()
_log("### pygame.init OK")

if FULLSCREEN:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((1280, 800))
_log("### display mode OK")

WIDTH, HEIGHT = screen.get_size()
set_ui_scale(WIDTH, HEIGHT)
_log(f"### ui scale OK, {WIDTH}x{HEIGHT}")

pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()
pygame.mouse.set_visible(False)
_log("### display setup OK")

W.bind_pygame(pygame.draw.circle, pygame.draw.polygon)
_log("### bind_pygame OK")


# ---------- Утилиты ----------
def format_time(sec):
    sec = int(sec)
    m = sec // 60
    s = sec % 60
    return f"{m}:{s:02d}"


# ---------- Камера ----------
class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0

    def follow(self, target, dt, smoothing=6.0):
        k = min(1.0, smoothing * dt)
        self.x += (target[0] - self.x) * k
        self.y += (target[1] - self.y) * k

    def world_to_screen(self, pos):
        return ((pos[0] - self.x) * self.zoom + WIDTH / 2,
                (pos[1] - self.y) * self.zoom + HEIGHT / 2)

    def screen_to_world(self, pos):
        return ((pos[0] - WIDTH / 2) / self.zoom + self.x,
                (pos[1] - HEIGHT / 2) / self.zoom + self.y)


# ---------- Состояние игры ----------
class GameState:
    def __init__(self):
        self.paused = False
        self.time_scale_index = 0
        self.game_time = 0.0
        self.notification = ""
        self.notification_t = 0.0

    @property
    def time_scale(self):
        return 0 if self.paused else TIME_SCALES[self.time_scale_index]

    def notify(self, text, seconds=2.5):
        self.notification = text
        self.notification_t = seconds


_log("### before state init")
state = GameState()
camera = Camera()
_log("### state OK")

# Галактика
GALAXY_SEED = 12345
GALAXY_TOTAL = 20
_log("### before galaxy graph")
galaxy_graph = galaxy.generate_galaxy(seed=GALAXY_SEED,
                                      total=GALAXY_TOTAL,
                                      max_neighbors=4)
_log("### galaxy graph OK")

current_sector_index = 0

# Кэш посещённых секторов
visited_sectors = {}


def get_or_create_sector(idx):
    if idx in visited_sectors:
        return visited_sectors[idx]
    name = galaxy._sector_label(idx)
    neighbors = galaxy_graph.get(idx, [])
    new_sector = galaxy.generate_sector(idx, name, GALAXY_SEED, neighbors)
    visited_sectors[idx] = new_sector
    return new_sector

_log("### before load sector")
sector = get_or_create_sector(current_sector_index)
_log("### sector loaded")

_log("### before ship/systems")
ship = W.Ship(1200, 800)
systems = ShipSystems()
camera.x, camera.y = ship.pos
_log("### ship/systems OK")

def maybe_spawn_signal_for_sector():
    import random as _r
    import combat as _c
    tier = _c.has_scanner(systems)
    _log(f"### signal spawn check: tier={tier}, "
         f"existing={len(_c.signal_list)}")
    if tier <= 0:
        _log("### no scanner")
        return
    chance = 0.30 if tier == 1 else 0.60
    roll = _r.random()
    _log(f"### signal roll: {roll:.2f} vs chance {chance}")
    if roll > chance:
        _log("### unlucky, no signal")
        return
    if len(_c.signal_list) > 0:
        _log("### signal already exists")
        return

    signal_types = ["wreck", "ambush", "trader", "cache", "empty"]
    weights = [30, 25, 15, 20, 10]
    stype = _r.choices(signal_types, weights=weights, k=1)[0]

    from data import WORLD_SIZE
    for _ in range(20):
        sx = _r.randint(500, WORLD_SIZE - 500)
        sy = _r.randint(500, WORLD_SIZE - 500)
        d = math.hypot(sx - ship.pos[0], sy - ship.pos[1])
        if d > 800:
            _c.spawn_signal(sx, sy, stype)
            return

# Экраны
station_screen = None
repair_screen = None
contracts_screen = None
galaxy_map_screen = None
story_screen = None
confirm_attack_screen = None
inventory_screen = None
prologue_screen = None
load_missile_screen = None

# Цель игрока (NPC)
player_target = None
player_fire_timer = 0.0
missile_timer = 0.0

# Прыжок
JUMP_COST_MONEY = 50
JUMP_COST_FUEL = 5.0

def open_load_missile():
    global load_missile_screen
    load_missile_screen = LoadMissileScreen(
        systems, on_close=close_load_missile, state_ref=state)
    load_missile_screen.open()
    state.paused = True


def close_load_missile():
    global load_missile_screen
    load_missile_screen = None
    state.paused = False

# ---------- Функции управления ----------
def toggle_pause():
    state.paused = not state.paused


def cycle_speed():
    state.time_scale_index = (state.time_scale_index + 1) % len(TIME_SCALES)


def stop_ship():
    ship.stop()
    state.notify("Стоп")


def _check_quest_objectives_at_station(station):
    station_idx = -1
    for i, st in enumerate(sector.stations):
        if st is station:
            station_idx = i
            break
    if station_idx < 0:
        return

    for aq in systems.story_manager.active.values():
        obj = aq.objective
        t = obj["type"]

        if t == "deliver":
            if (obj["target_sector"] == current_sector_index
                    and obj["target_station"] == station_idx
                    and aq.state == "in_progress"):
                qc = systems.quest_cargo.get(aq.quest_id, {})
                if qc.get("collected", False) or qc.get("auto_given", False):
                    systems.quest_cargo.pop(aq.quest_id, None)
                    aq.state = "ready_to_turn_in"
                    state.notify(f"Цель достигнута: {aq.title}")

        elif t == "visit":
            if obj.get("return_to_giver", False) and aq.visited_target:
                giver_sector = aq.data["giver_sector"]
                giver_station = aq.data["giver_station"]
                if (giver_sector == current_sector_index
                        and giver_station == station_idx
                        and aq.state == "in_progress"):
                    aq.state = "ready_to_turn_in"
                    state.notify(f"Цель достигнута: {aq.title}")


def open_station(station):
    global station_screen
    ship.stop()

    _check_quest_objectives_at_station(station)

    station_screen = StationScreen(
        station, systems, on_undock=close_station,
        all_stations=sector.stations, state_ref=state,
        current_sector_idx=current_sector_index)
    station_screen.active = True
    state.paused = True


def close_station():
    global station_screen
    station_screen = None
    state.paused = False
    state.notify("Отстыковка выполнена")
    try:
        save_now()
    except Exception:
        pass


def open_repair():
    global repair_screen
    repair_screen = RepairScreen(systems, on_close=close_repair)
    repair_screen.open()
    state.paused = True


def close_repair():
    global repair_screen
    repair_screen = None
    state.paused = False
    maybe_spawn_signal_for_sector()


def open_contracts_screen():
    global contracts_screen
    contracts_screen = ActiveContractsScreen(
        systems, on_close=close_contracts_screen, state_ref=state)
    contracts_screen.open()
    state.paused = True


def close_contracts_screen():
    global contracts_screen
    contracts_screen = None
    state.paused = False


def open_galaxy_map():
    global galaxy_map_screen
    try:
        from screens import GalaxyMapScreen
        galaxy_map_screen = GalaxyMapScreen(
            galaxy_graph=galaxy_graph,
            visited_sectors=visited_sectors,
            current_sector_index=current_sector_index,
            on_close=close_galaxy_map,
            state_ref=state,
            systems=systems,
        )
        galaxy_map_screen.open()
        state.paused = True
    except Exception:
        import traceback
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise


def close_galaxy_map():
    global galaxy_map_screen
    galaxy_map_screen = None
    state.paused = False


def open_story_screen(quest_id, mode):
    global story_screen
    story_screen = StoryScreen(
        quest_id=quest_id,
        story_manager=systems.story_manager,
        systems=systems,
        on_close=close_story_screen,
        mode=mode,
        state_ref=state,
        visited_sectors=visited_sectors,
    )
    story_screen.open()


def close_story_screen():
    global story_screen
    story_screen = None


set_story_screen_callback(open_story_screen)


def _show_final_scene(quest_id):
    global story_screen
    story_screen = StoryScreen(
        quest_id=quest_id,
        story_manager=systems.story_manager,
        systems=systems,
        on_close=close_story_screen,
        mode="turn_in",
        state_ref=state,
        visited_sectors=visited_sectors,
    )
    story_screen.open()
    state.paused = True


# --- Атака с подтверждением ---

def open_confirm_attack(npc):
    global confirm_attack_screen
    confirm_attack_screen = ConfirmAttackScreen(
        npc_name=npc.name,
        on_confirm=lambda: do_attack(npc),
        on_cancel=close_confirm_attack,
        state_ref=state,
    )
    confirm_attack_screen.open()
    state.paused = True


def close_confirm_attack():
    global confirm_attack_screen
    confirm_attack_screen = None
    state.paused = False

def open_inventory():
    global inventory_screen
    inventory_screen = InventoryScreen(
        systems, on_close=close_inventory, state_ref=state)
    inventory_screen.open()
    state.paused = True


def close_inventory():
    global inventory_screen
    inventory_screen = None
    state.paused = False

def open_prologue():
    global prologue_screen
    prologue_screen = PrologueScreen(on_finish=close_prologue)
    prologue_screen.open()
    state.paused = True


def close_prologue():
    global prologue_screen
    prologue_screen = None
    state.paused = False

def do_attack(npc):
    global player_target, confirm_attack_screen
    player_target = npc

    if npc.npc_type in ("trader", "courier", "patrol"):
        systems.is_wanted = True
        state.notify("Вы атаковали мирного! Патрули в ярости!")
    else:
        state.notify(f"Цель: {npc.name}")

    confirm_attack_screen = None
    state.paused = False


def start_jump(target_sector_index):
    if target_sector_index < 0:
        state.notify("Эти врата никуда не ведут")
        return
    if systems.money < JUMP_COST_MONEY:
        state.notify(f"Не хватает денег (нужно {JUMP_COST_MONEY})")
        return
    if systems.fuel < JUMP_COST_FUEL:
        state.notify(f"Не хватает топлива (нужно {JUMP_COST_FUEL})")
        return
    systems.money -= JUMP_COST_MONEY
    systems.fuel -= JUMP_COST_FUEL
    finish_jump(target_sector_index)


def finish_jump(target_idx):
    global sector, current_sector_index
    global player_target
    combat.clear_debris()
    combat.clear_signals()

    prev_idx = current_sector_index
    sector = get_or_create_sector(target_idx)
    current_sector_index = target_idx
    player_target = None

    return_gate = None
    for g in sector.gates:
        if g.target_sector == prev_idx:
            return_gate = g
            break
    if return_gate is None and sector.gates:
        return_gate = sector.gates[0]

    if return_gate is not None:
        g = return_gate
        cx = WORLD_SIZE / 2
        cy = WORLD_SIZE / 2
        dx = cx - g.pos[0]
        dy = cy - g.pos[1]
        L = math.hypot(dx, dy) or 1.0
        ship.pos[0] = g.pos[0] + (dx / L) * 220
        ship.pos[1] = g.pos[1] + (dy / L) * 220
    else:
        ship.pos[0] = WORLD_SIZE / 2
        ship.pos[1] = WORLD_SIZE / 2

    ship.vel = [0.0, 0.0]
    ship.target = None
    camera.x, camera.y = ship.pos
    state.paused = False
    state.notify(f"Прибытие: сектор {sector.name}")

    for aq in list(systems.story_manager.active.values()):
        obj = aq.objective
        if obj["type"] == "arrive":
            if obj["target_sector"] == current_sector_index:
                if aq.state == "in_progress":
                    aq.state = "ready_to_turn_in"
                    _show_final_scene(aq.quest_id)
        elif obj["type"] == "visit":
            if obj["target_sector"] == current_sector_index:
                aq.visited_target = True

    try:
        save_now()
    except Exception:
        pass
        
    maybe_spawn_signal_for_sector()


# ---------- Сохранение / загрузка ----------

def _collect_state():
    from contracts import register_station

    for sec_idx, sec in visited_sectors.items():
        for i, st in enumerate(sec.stations):
            register_station(st, sec_idx, i)

    stations_by_sector = {}
    for sec_idx, sec in visited_sectors.items():
        stations_by_sector[str(sec_idx)] = {
            "stations": [st.to_dict() for st in sec.stations],
        }

    return {
        "version": 1,
        "galaxy_seed": GALAXY_SEED,
        "galaxy_total": GALAXY_TOTAL,
        "current_sector": current_sector_index,
        "visited_sector_indices": list(visited_sectors.keys()),
        "game_time": state.game_time,
        "time_scale_index": state.time_scale_index,
        "ship_pos": list(ship.pos),
        "ship_heading": ship.heading,
        "systems": systems.to_dict(),
        "stations_by_sector": stations_by_sector,
    }


def save_now():
    try:
        data = _collect_state()
        ok = SAVE.save_game(data)
        if ok:
            state.notify("Игра сохранена")
        else:
            state.notify("Ошибка сохранения")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.notify(f"Ошибка: {e}")


def load_from_save():
    data = SAVE.load_game()
    if data is None:
        return False

    global sector, current_sector_index
    global systems, visited_sectors, galaxy_graph

    try:
        seed = data.get("galaxy_seed", GALAXY_SEED)
        total = data.get("galaxy_total", GALAXY_TOTAL)
        galaxy_graph = galaxy.generate_galaxy(seed=seed, total=total,
                                              max_neighbors=4)

        visited_sectors = {}
        visited_indices = data.get("visited_sector_indices", [])
        stations_by_sector = data.get("stations_by_sector", {})

        for sec_idx in visited_indices:
            sec = get_or_create_sector(sec_idx)
            key = str(sec_idx)
            stations_data = stations_by_sector.get(key, {})
            st_list = stations_data.get("stations", [])
            from contracts import register_station
            for i, st_data in enumerate(st_list):
                if i < len(sec.stations):
                    register_station(sec.stations[i], sec_idx, i)

        def station_lookup(from_ref, to_ref):
            def get_station(ref):
                sec_idx, st_idx = ref[0], ref[1]
                if sec_idx not in visited_sectors:
                    return None
                if 0 <= st_idx < len(visited_sectors[sec_idx].stations):
                    return visited_sectors[sec_idx].stations[st_idx]
                return None
            return get_station(from_ref), get_station(to_ref)

        for sec_idx in visited_indices:
            sec = visited_sectors[sec_idx]
            key = str(sec_idx)
            stations_data = stations_by_sector.get(key, {})
            st_list = stations_data.get("stations", [])
            for i, st_data in enumerate(st_list):
                if i < len(sec.stations):
                    sec.stations[i].apply_dict(st_data, station_lookup)

        current_sector_index = data.get("current_sector", 0)
        if current_sector_index not in visited_sectors:
            get_or_create_sector(current_sector_index)
        sector = visited_sectors[current_sector_index]

        ship.pos = list(data.get("ship_pos", [WORLD_SIZE / 2, WORLD_SIZE / 2]))
        ship.heading = data.get("ship_heading", 0.0)
        ship.vel = [0.0, 0.0]
        ship.target = None

        camera.x, camera.y = ship.pos

        systems.apply_dict(data.get("systems", {}), station_lookup)

        state.game_time = data.get("game_time", 0.0)
        state.time_scale_index = data.get("time_scale_index", 0)

        try:
            apply_ship_effects()
        except Exception:
            pass

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("load error:", e)
        return False


# ---------- Кнопки HUD ----------
_log("### before buttons")
btn_w, btn_h = S(140), S(70)
margin = S(20)
bottom = HEIGHT - btn_h - margin

buttons = [
    Button((margin, bottom, btn_w, btn_h), "II", toggle_pause, font_size=32),
    Button((margin * 2 + btn_w, bottom, btn_w, btn_h), "x1",
           cycle_speed, font_size=28),
    Button((margin * 3 + btn_w * 2, bottom, btn_w, btn_h), "STOP",
           stop_ship, font_size=26),
    Button((margin * 4 + btn_w * 3, bottom, btn_w, btn_h), "РЕМОНТ",
           open_repair, font_size=24),
    Button((margin * 5 + btn_w * 4, bottom, btn_w, btn_h), "КОНТР.",
           open_contracts_screen, font_size=24),
    Button((margin * 6 + btn_w * 5, bottom, btn_w, btn_h), "КАРТА",
           open_galaxy_map, font_size=24),
    Button((margin * 7 + btn_w * 6, bottom, btn_w, btn_h), "ИНВ.",
           open_inventory, font_size=24),
    Button((margin * 8 + btn_w * 7, bottom, btn_w, btn_h), "ЗАРЯД",
           open_load_missile, font_size=22),
]

save_btn_w, save_btn_h = S(120), S(36)
save_button = Button(
    (WIDTH - save_btn_w - S(16), S(4), save_btn_w, save_btn_h),
    "СОХР.", save_now, font_size=20,
)
_log("### buttons OK")


# ---------- Фон ----------
_stars = [(random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1),
           random.randint(80, 200)) for _ in range(260)]


def draw_background():
    screen.fill(DARK_SPACE)
    for x, y, b in _stars:
        pygame.draw.circle(screen, (b, b, b + 20), (x, y), 1)


# ---------- Обработка тапа ----------
def handle_tap(pos):
    global player_target

    if not systems.can_thrust:
        state.notify("Нет топлива или двигатель мёртв")
        return

    wx, wy = camera.screen_to_world(pos)

    # Тап по сигналу
    for s in combat.signal_list:
        if s.used:
            continue
        dd = math.hypot(s.pos[0] - wx, s.pos[1] - wy)
        if dd < s.radius + 20:
            dist_to_ship = math.hypot(s.pos[0] - ship.pos[0],
                                      s.pos[1] - ship.pos[1])
            if dist_to_ship > s.radius + 60:
                ship.set_target(s.pos[0], s.pos[1])
                state.notify("Курс: сигнал бедствия")
                return
            _activate_signal(s)
            return
    
    # Тап по обломкам
    for d in combat.debris_list:
        if d.collected:
            continue
        dd = math.hypot(d.pos[0] - wx, d.pos[1] - wy)
        if dd < d.radius + 20:
            # Проверяем расстояние до корабля
            dist_to_ship = math.hypot(d.pos[0] - ship.pos[0],
                                      d.pos[1] - ship.pos[1])
            if dist_to_ship > d.radius + 60:
                ship.set_target(d.pos[0], d.pos[1])
                state.notify("Курс: обломки")
                return
            # Собираем лут
            collected_msg = []
            for sid, cnt in d.scrap:
                systems.add_scrap(sid, cnt)
                info = SCRAP_BY_ID.get(sid, {})
                collected_msg.append(f"{info.get('name', sid)} x{cnt}")
            for vid, cnt in d.valuables:
                systems.add_valuable(vid, cnt)
                info = VALUABLES_BY_ID.get(vid, {})
                collected_msg.append(f"{info.get('name', vid)} x{cnt}")
            for pid in d.parts:
                systems.add_new_part(pid)
                info = PARTS_BY_ID.get(pid, {})
                collected_msg.append(info.get("name", pid))
            d.collected = True
            if collected_msg:
                state.notify("Забрано: " + ", ".join(collected_msg[:3]),
                             seconds=3.0)
            else:
                state.notify("Пусто")
            # Удаляем обломки из списка
            try:
                combat.debris_list.remove(d)
            except ValueError:
                pass
            try:
                save_now()
            except Exception:
                pass
            return

    # Сюжетные маркеры:
    for m in getattr(sector, "quest_markers", []):
        d = math.hypot(m.pos[0] - wx, m.pos[1] - wy)
        if d < m.radius + 20:
            dist_to_ship = math.hypot(m.pos[0] - ship.pos[0],
                                      m.pos[1] - ship.pos[1])
            if dist_to_ship > m.radius + 40:
                ship.set_target(m.pos[0], m.pos[1])
                state.notify(f"Курс: {m.name}")
                return
            aq = systems.story_manager.active.get(m.quest_id, None)
            if aq is None:
                state.notify("Здесь ничего интересного")
                return
            if aq.state != "in_progress":
                state.notify("Уже собрано")
                return
            m.collected = True
            aq.visited_target = True
            obj = aq.objective
            if not obj.get("return_to_giver", False):
                aq.state = "ready_to_turn_in"
            if obj.get("return_to_giver", False):
                giver_name = aq.data.get("giver_name", "NPC")
                state.notify(f"Собрано! Вернись к {giver_name}", seconds=4.0)
            else:
                state.notify(f"Собрано: {m.name}")
            try:
                save_now()
            except Exception:
                pass
            return

    # Тап по NPC
    for npc in sector.npcs:
        if npc.dead:
            continue
        d = math.hypot(npc.pos[0] - wx, npc.pos[1] - wy)
        if d < 40:
            # Пират ИЛИ игрок уже в розыске — без подтверждения
            if npc.npc_type == "pirate" or systems.is_wanted:
                player_target = npc
                state.notify(f"Цель: {npc.name}")
            else:
                open_confirm_attack(npc)
            return

    for st in sector.stations:
        d = math.hypot(st.pos[0] - wx, st.pos[1] - wy)
        if d < st.radius + 20:
            dist_to_ship = math.hypot(st.pos[0] - ship.pos[0],
                                      st.pos[1] - ship.pos[1])
            if dist_to_ship < DOCK_DISTANCE:
                open_station(st)
            else:
                ship.set_target(st.pos[0], st.pos[1])
                state.notify(f"Курс: {st.name}")
            return

    for g in sector.gates:
        d = math.hypot(g.pos[0] - wx, g.pos[1] - wy)
        if d < g.radius + 20:
            dist_to_ship = math.hypot(g.pos[0] - ship.pos[0],
                                      g.pos[1] - ship.pos[1])
            if dist_to_ship < GATE_DISTANCE:
                start_jump(g.target_sector)
            else:
                ship.set_target(g.pos[0], g.pos[1])
                state.notify(f"Курс: {g.name}")
            return

    ship.set_target(wx, wy)

def _activate_signal(s):
    """Запускает событие сигнала бедствия."""
    import random as _r
    s.used = True

    if s.signal_type == "wreck":
        from data import SCRAP_DEF, VALUABLES_DEF
        n = _r.randint(2, 4)
        for _ in range(n):
            sid = _r.choice(SCRAP_DEF)[0]
            systems.add_scrap(sid, 1)
        if _r.random() < 0.5:
            vid = _r.choice(VALUABLES_DEF)[0]
            systems.add_valuable(vid, 1)
            state.notify("Заброшенный корабль! Забрано: хлам + трофей",
                         seconds=3.5)
        else:
            state.notify("Заброшенный корабль! Забрано: хлам", seconds=3.5)

    elif s.signal_type == "ambush":
        from combat import NPCShip
        n = _r.randint(2, 3)
        for _ in range(n):
            px = s.pos[0] + _r.randint(-200, 200)
            py = s.pos[1] + _r.randint(-200, 200)
            sector.npcs.append(NPCShip("pirate", px, py))
        state.notify(f"ЗАСАДА! {n} пиратов атакуют!", seconds=4.0)

    elif s.signal_type == "trader":
        state.notify("Торговец: продал редкий товар, +500 кр.", seconds=3.5)
        systems.money += 500

    elif s.signal_type == "cache":
        from data import VALUABLES_DEF
        vid = _r.choice(VALUABLES_DEF)[0]
        systems.add_valuable(vid, _r.randint(1, 2))
        state.notify("Тайник найден! Трофей в трюме", seconds=3.5)

    elif s.signal_type == "empty":
        state.notify("Пустой сигнал. Ничего нет.", seconds=2.5)

    try:
        combat.signal_list.remove(s)
    except ValueError:
        pass
    try:
        save_now()
    except Exception:
        pass

# ---------- Отрисовка мира ----------
def draw_world():
    step = 400
    x0 = int(camera.x // step) * step
    y0 = int(camera.y // step) * step
    for gx in range(x0 - step * 3, x0 + step * 3 + 1, step):
        for gy in range(y0 - step * 3, y0 + step * 3 + 1, step):
            sx, sy = camera.world_to_screen((gx, gy))
            if -50 < sx < WIDTH + 50 and -50 < sy < HEIGHT + 50:
                pygame.draw.circle(screen, (30, 35, 55), (int(sx), int(sy)), 2)

    for a in sector.asteroids:
        a.draw(screen, camera)

    story = systems.story_manager
    story.recompute_available()

    for st_idx, st in enumerate(sector.stations):
        st.draw(screen, camera)

        has_available = False
        for qid in story.available:
            q = STORY_QUESTS_BY_ID[qid]
            if (q["giver_sector"] == current_sector_index
                    and q["giver_station"] == st_idx):
                has_available = True
                break

        has_turn_in = False
        for aq in story.active.values():
            q = aq.data
            if (q["giver_sector"] != current_sector_index
                    or q["giver_station"] != st_idx):
                continue
            if aq.state == "ready_to_turn_in":
                has_turn_in = True
                break
            obj = aq.objective
            if (obj["type"] == "visit"
                    and obj.get("return_to_giver", False)
                    and aq.visited_target):
                has_turn_in = True
                break

        is_contract_target = any(c.to_station is st
                                 for c in systems.active_contracts)

        is_quest_deliver = False
        for aq in story.active.values():
            obj = aq.objective
            if (obj["type"] == "deliver"
                    and obj["target_sector"] == current_sector_index
                    and obj["target_station"] == st_idx
                    and aq.state == "in_progress"):
                is_quest_deliver = True
                break

        sx, sy = camera.world_to_screen(st.pos)
        r = int(st.radius * camera.zoom)

        if has_available or has_turn_in:
            pygame.draw.circle(screen, (240, 180, 60),
                               (int(sx), int(sy)), r + 16, max(2, S(3)))
            draw_text(screen, "!",
                      (int(sx) - S(10), int(sy) - r - S(50)),
                      size=54, color=(240, 180, 60))

        if is_contract_target:
            pygame.draw.circle(screen, (90, 210, 120),
                               (int(sx), int(sy)), r + 8, max(2, S(3)))
            draw_text(screen, "КОНТР",
                      (int(sx) - S(38), int(sy) - r - S(30)),
                      size=20, color=(90, 210, 120))

        if is_quest_deliver:
            pygame.draw.circle(screen, (240, 180, 60),
                               (int(sx), int(sy)), r + 12, max(2, S(3)))
            draw_text(screen, "СЮЖЕТ",
                      (int(sx) - S(38), int(sy) - r - S(30)),
                      size=20, color=(240, 180, 60))

    for g in sector.gates:
        g.draw(screen, camera)

    # NPC
    for npc in sector.npcs:
        is_target = (npc is player_target)
        npc.draw(screen, camera, is_target=is_target)

    # Сигналы
    combat.draw_signals(screen, camera)

    # Ракеты
    combat.draw_missiles(screen, camera)

    # Обломки
    combat.draw_debris(screen, camera)

    # Боевые эффекты
    combat.draw_effects(screen, camera)

    if ship.target is not None:
        tx, ty = ship.target
        sx, sy = camera.world_to_screen((tx, ty))
        pygame.draw.circle(screen, (90, 170, 255), (int(sx), int(sy)),
                           max(3, int(6 * camera.zoom)), 2)

    ship.draw(screen, camera)


# ---------- HUD ----------
def draw_top_bar():
    top = pygame.Rect(0, 0, WIDTH, S(44))
    draw_panel(screen, top)
    speed_label = "ПАУЗА" if state.paused else f"x{TIME_SCALES[state.time_scale_index]}"
    draw_text(screen,
              f"Space Exploration - сектор {sector.name}  |  время: {state.game_time:6.1f} c  |  {speed_label}",
              (S(16), S(10)), size=24, color=UI_TEXT)
    buttons[1].text = f"x{TIME_SCALES[state.time_scale_index]}"
    save_button.draw(screen)


def draw_ship_panel():
    panel_w = S(320)
    panel_h = S(360)
    rect = pygame.Rect(S(16), S(60), panel_w, panel_h)
    draw_panel(screen, rect)
    x = rect.x + S(14)
    y = rect.y + S(12)

    draw_text(screen, f"Топливо {systems.fuel:5.1f}", (x, y),
              size=22, color=UI_TEXT)
    bar = pygame.Rect(x, y + S(28), panel_w - S(28), S(14))
    pygame.draw.rect(screen, (40, 40, 60), bar, border_radius=S(4))
    fill = int(bar.w * systems.fuel / FUEL_MAX)
    col = (240, 180, 60) if systems.fuel > 20 else (230, 80, 80)
    pygame.draw.rect(screen, col,
                     (bar.x, bar.y, fill, bar.h), border_radius=S(4))
    y += S(56)

    gen_alive = systems.systems["o2gen"].is_functional
    o2_label = "O2 каб." if gen_alive else "O2 КАБ.!"
    draw_text(screen, f"{o2_label:8s} {systems.o2:5.1f}", (x, y),
              size=22, color=UI_TEXT if gen_alive else (230, 80, 80))
    bar = pygame.Rect(x, y + S(26), panel_w - S(28), S(12))
    pygame.draw.rect(screen, (40, 40, 60), bar, border_radius=S(4))
    fill = int(bar.w * systems.o2 / O2_MAX)
    col = (90, 210, 120) if gen_alive else (230, 80, 80)
    pygame.draw.rect(screen, col,
                     (bar.x, bar.y, fill, bar.h), border_radius=S(4))
    y += S(48)

    draw_text(screen, f"Баллон   {systems.o2_reserve:5.1f}", (x, y),
              size=22, color=UI_TEXT)
    bar = pygame.Rect(x, y + S(26), panel_w - S(28), S(12))
    pygame.draw.rect(screen, (40, 40, 60), bar, border_radius=S(4))
    fill = int(bar.w * systems.o2_reserve / O2_RESERVE_MAX)
    col = (90, 170, 220) if systems.o2_reserve > 30 else (230, 80, 80)
    pygame.draw.rect(screen, col,
                     (bar.x, bar.y, fill, bar.h), border_radius=S(4))
    y += S(56)

    # Щит
    s_max = systems.shield_max
    if s_max > 0:
        s_cur = systems.current_shield
        draw_text(screen, f"Щит      {s_cur:5.1f} / {s_max:.0f}", (x, y),
                  size=22, color=UI_ACCENT)
        bar = pygame.Rect(x, y + S(26), panel_w - S(28), S(12))
        pygame.draw.rect(screen, (40, 40, 60), bar, border_radius=S(4))
        fill = int(bar.w * (s_cur / s_max))
        pygame.draw.rect(screen, UI_ACCENT,
                         (bar.x, bar.y, fill, bar.h), border_radius=S(4))
        y += S(48)

    # Ракета заряжена?
    if systems.has_launcher:
        if systems.loaded_missile is not None:
            aid, dmg, spd = systems.loaded_missile
            from data import AMMO_BY_ID
            name = AMMO_BY_ID.get(aid, {}).get("name", "Ракета")
            y_rocket = rect.bottom + S(8)
            if player_target is not None and not player_target.dead:
                y_rocket += S(90)
            draw_text(screen, f"ЗАРЯЖЕНО: {name}",
                      (rect.x + S(14), y_rocket),
                      size=20, color=UI_OK)
        else:
            # Показать количество ракет в трюме
            total = sum(systems.ammo.values())
            if total > 0:
                y_rocket = rect.bottom + S(8)
                if player_target is not None and not player_target.dead:
                    y_rocket += S(90)
                draw_text(screen, f"Ракет в трюме: {total} (нажми ЗАРЯД)",
                          (rect.x + S(14), y_rocket),
                          size=18, color=UI_WARN)

    from data import SYSTEM_NAMES
    for sid in ("engine", "reactor", "o2gen", "hull"):
        sys = systems.systems[sid]
        pct = sys.hp_pct
        if sys.state == "dead":
            col = (80, 80, 90)
        elif sys.state == "crit":
            col = (230, 80, 80)
        elif sys.state == "warn":
            col = (240, 180, 60)
        else:
            col = (90, 210, 120)

        draw_text(screen, f"{SYSTEM_NAMES[sid][:11]:11s} {int(sys.hp):3d}",
                  (x, y), size=20, color=UI_TEXT)
        bar = pygame.Rect(x + S(180), y + S(4),
                          panel_w - S(200), S(12))
        pygame.draw.rect(screen, (40, 40, 60), bar, border_radius=S(3))
        fill = int(bar.w * pct)
        pygame.draw.rect(screen, col,
                         (bar.x, bar.y, fill, bar.h), border_radius=S(3))
        y += S(26)

    # Хлам и трофеи (если есть)
    scrap_w = systems.scrap_weight()
    val_w = systems.valuables_weight()
    if scrap_w > 0 or val_w > 0:
        y += S(6)
        if scrap_w > 0:
            scrap_val = systems.scrap_value()
            draw_text(screen, f"Хлам: {scrap_w:.1f} кг ({scrap_val} кр.)",
                      (x, y), size=18, color=UI_DIM)
            y += S(20)
        if val_w > 0:
            val_val = systems.valuables_value()
            draw_text(screen, f"Трофеи: {val_w:.1f} кг ({val_val} кр.)",
                      (x, y), size=18, color=UI_WARN)
            y += S(20)

    # Цель
    if player_target is not None and not player_target.dead:
        ty = rect.bottom + S(8)
        rect2 = pygame.Rect(S(16), ty, panel_w, S(90))
        draw_panel(screen, rect2)
        draw_text(screen, "ЦЕЛЬ:", (rect2.x + S(12), rect2.y + S(8)),
                  size=20, color=UI_WARN)
        draw_text(screen, player_target.name,
                  (rect2.x + S(12), rect2.y + S(32)),
                  size=22, color=UI_TEXT)
        # HP цели
        hp_pct = player_target.hp_pct
        bar = pygame.Rect(rect2.x + S(12), rect2.y + S(60),
                          rect2.w - S(24), S(12))
        pygame.draw.rect(screen, (40, 40, 60), bar, border_radius=S(3))
        fill = int(bar.w * hp_pct)
        col = (90, 210, 120) if hp_pct > 0.5 else (
            (240, 180, 60) if hp_pct > 0.25 else (230, 80, 80))
        pygame.draw.rect(screen, col,
                         (bar.x, bar.y, fill, bar.h), border_radius=S(3))


def draw_contracts_panel():
    contracts = systems.active_contracts
    active_quests = list(systems.story_manager.active.values())

    if not contracts and not active_quests:
        return

    from data import CONTRACT_MAX_ACTIVE

    rows = []
    for aq in active_quests:
        obj = aq.objective
        if obj["type"] == "deliver":
            target = f"Сектор {obj['target_sector']}, станция #{obj['target_station']}"
            title = f"[СЮЖЕТ] {aq.title}"
            reward_text = "завершение"
        elif obj["type"] == "visit":
            target = f"Сектор {obj['target_sector']}"
            title = f"[СЮЖЕТ] {aq.title}"
            reward_text = "визит"
        elif obj["type"] == "arrive":
            target = f"Сектор {obj['target_sector']}"
            title = f"[СЮЖЕТ] {aq.title}"
            reward_text = "финал"
        else:
            target = "???"
            title = aq.title
            reward_text = ""
        rows.append((title, target, reward_text, (240, 180, 60)))

    now = state.game_time
    for c in contracts:
        target = c.to_station.name
        title = c.cargo_name
        reward = c.current_reward(now)
        r_text = f"{reward} кр."
        if c.urgent and c.deadline_time is not None:
            left = c.time_left(now)
            late = c.is_late(now)
            r_text = f"{reward} кр. / {'ОПОЗДАЛ' if late else format_time(left)}"
        rows.append((title, target, r_text, UI_OK))

    panel_w = S(480)
    row_h = S(56)
    header_h = S(38)
    panel_h = header_h + row_h * len(rows) + S(12)
    panel_x = WIDTH - panel_w - S(16)
    panel_y = S(60)
    rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    draw_panel(screen, rect)

    header = f"Задания: {len(active_quests)} сюжет / {len(contracts)} контр."
    draw_text(screen, header,
              (rect.x + S(12), rect.y + S(8)),
              size=20, color=UI_ACCENT)

    y = rect.y + header_h
    for title, target, reward_text, col in rows:
        draw_text(screen, title, (rect.x + S(12), y + S(4)),
                  size=18, color=col)
        draw_text(screen, f"-> {target}", (rect.x + S(12), y + S(26)),
                  size=18, color=UI_TEXT)

        surf = get_font(S(18)).render(reward_text, True, col)
        screen.blit(surf, (rect.right - surf.get_width() - S(12), y + S(14)))

        y += row_h
        if (title, target, reward_text, col) is not rows[-1]:
            pygame.draw.line(screen, UI_BORDER,
                             (rect.x + S(12), y - S(4)),
                             (rect.right - S(12), y - S(4)),
                             max(1, S(1)))


def draw_minimap():
    map_size = S(280)
    margin = S(20)
    pad = S(8)
    rect = pygame.Rect(
        WIDTH - map_size - margin,
        HEIGHT - map_size - margin - S(90),
        map_size, map_size
    )
    draw_panel(screen, rect)
    inner = rect.inflate(-pad * 2, -pad * 2)

    scale = inner.w / WORLD_SIZE

    def w2m(pos):
        x = inner.x + int(pos[0] * scale)
        y = inner.y + int(pos[1] * scale)
        return x, y

    for a in sector.asteroids:
        mx, my = w2m(a.pos)
        if inner.collidepoint(mx, my):
            pygame.draw.circle(screen, (55, 55, 70), (mx, my), 1)

    for g in sector.gates:
        mx, my = w2m(g.pos)
        r = max(3, S(5))
        pts = [(mx, my - r), (mx + r, my), (mx, my + r), (mx - r, my)]
        col = (220, 180, 90) if g.target_sector >= 0 else (100, 100, 110)
        pygame.draw.polygon(screen, col, pts)

    for m in getattr(sector, "quest_markers", []):
        aq = systems.story_manager.active.get(m.quest_id, None)
        if aq is None:
            continue
        mx, my = w2m(m.pos)
        r = max(4, S(7))
        col = (240, 180, 60) if (aq.state == "in_progress"
                                 and not m.collected) else (80, 80, 90)
        pts = [(mx, my - r), (mx + r, my), (mx, my + r), (mx - r, my)]
        pygame.draw.polygon(screen, col, pts)

    # Сигналы
    for s in combat.signal_list:
        mx, my = w2m(s.pos)
        col = (255, 100, 100) if s.signal_type == "ambush" else (100, 180, 255)
        pygame.draw.circle(screen, col, (mx, my), max(4, S(5)))

    # Обломки
    for d in combat.debris_list:
        mx, my = w2m(d.pos)
        pygame.draw.circle(screen, (230, 180, 60),
                           (mx, my), max(3, S(4)))

    # NPC на мини-карте
    for npc in sector.npcs:
        mx, my = w2m(npc.pos)
        col = npc.color
        pygame.draw.circle(screen, col, (mx, my), max(2, S(3)))

    for st in sector.stations:
        mx, my = w2m(st.pos)
        r = max(3, S(5))
        is_target = any(c.to_station is st for c in systems.active_contracts)
        if is_target:
            pygame.draw.circle(screen, (90, 210, 120),
                               (mx, my), r + S(3), max(1, S(2)))
        pygame.draw.circle(screen, (140, 200, 140), (mx, my), r)
        pygame.draw.circle(screen, (255, 255, 255), (mx, my), r, 1)

    half_w_world = (WIDTH / 2) / camera.zoom
    half_h_world = (HEIGHT / 2) / camera.zoom
    cam_x0 = camera.x - half_w_world
    cam_y0 = camera.y - half_h_world
    cam_x1 = camera.x + half_w_world
    cam_y1 = camera.y + half_h_world
    mx0, my0 = w2m((cam_x0, cam_y0))
    mx1, my1 = w2m((cam_x1, cam_y1))
    cam_rect = pygame.Rect(mx0, my0, mx1 - mx0, my1 - my0)
    cam_rect = cam_rect.clip(inner)
    pygame.draw.rect(screen, (255, 255, 255), cam_rect, max(1, S(1)))

    mx, my = w2m(ship.pos)
    h = ship.heading
    size = S(7)
    nose = (mx + math.cos(h) * size, my + math.sin(h) * size)
    left = (mx + math.cos(h + 2.4) * size, my + math.sin(h + 2.4) * size)
    right = (mx + math.cos(h - 2.4) * size, my + math.sin(h - 2.4) * size)
    pygame.draw.polygon(screen, (120, 220, 255), [nose, left, right])
    pygame.draw.polygon(screen, (255, 255, 255), [nose, left, right], 1)

    label = f"Сектор {sector.name}"
    surf = get_font(S(16)).render(label, True, UI_TEXT)
    screen.blit(surf, (rect.x + S(8), rect.y + S(6)))


def draw_notification():
    if state.notification_t <= 0:
        return
    surf = get_font(S(28)).render(state.notification, True, (255, 255, 255))
    r = surf.get_rect(midbottom=(WIDTH // 2, HEIGHT - S(120)))
    pad = S(12)
    bg = pygame.Rect(r.x - pad, r.y - pad, r.w + pad * 2, r.h + pad * 2)
    draw_panel(screen, bg)
    screen.blit(surf, r)


def draw_hud():
    draw_top_bar()
    draw_ship_panel()
    draw_contracts_panel()
    draw_minimap()
    draw_notification()


# ---------- apply_ship_effects ----------
def apply_ship_effects():
    from data import SHIP_MAX_SPEED, SHIP_ACCEL
    speed_mult = (systems.effects.get("speed_mult", 1.0)
                  * systems.get_ship_speed_mult())
    accel_mult = (systems.effects.get("accel_mult", 1.0)
                  * systems.get_ship_accel_mult())
    ship.max_speed = SHIP_MAX_SPEED * speed_mult
    ship.accel = SHIP_ACCEL * accel_mult


# ---------- game_over ----------
def game_over():
    import save as _SAVE
    try:
        _SAVE.delete_save()
    except Exception:
        pass

    font_big = get_font(S(72))
    font_small = get_font(S(28))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                running = False

        screen.fill((8, 0, 0))
        surf = font_big.render("ВАШ КОРАБЛЬ УНИЧТОЖЕН",
                               True, (230, 80, 80))
        rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - S(60)))
        screen.blit(surf, rect)

        surf2 = font_small.render("Тапните, чтобы начать заново",
                                  True, (240, 240, 240))
        rect2 = surf2.get_rect(center=(WIDTH // 2, HEIGHT // 2 + S(40)))
        screen.blit(surf2, rect2)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ---------- Основной цикл ----------
def main():
    global station_screen, repair_screen, contracts_screen, galaxy_map_screen
    global story_screen
    global player_target, player_fire_timer, missile_timer
    global confirm_attack_screen
    global inventory_screen
    global prologue_screen
    global load_missile_screen

    _log("### main() entered")
    running = True

    # --- Стартовое меню ---
    _log("### before start menu")
    has_save = SAVE.has_save()
    _log(f"### has_save = {has_save}")

    menu = StartMenuScreen(
        has_save=has_save,
        on_continue=lambda: load_from_save(),
        on_new_game=lambda: open_prologue(),
    )

    _log("### start menu created")

    while menu.active and running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                menu.handle_event(event)
        menu.draw(screen, WIDTH, HEIGHT)
        pygame.display.flip()
        clock.tick(FPS)

    _log("### start menu exited")

    if not running:
        pygame.quit()
        sys.exit()

    # --- Основной цикл ---
    _log("### entering main loop")
    maybe_spawn_signal_for_sector()
    while running:

        dt = clock.tick(FPS) / 1000.0

        # === СЮЖЕТ ===
        if story_screen is not None and story_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    story_screen.close()
                    break
                else:
                    story_screen.handle_event(event)
                    if story_screen is None or not story_screen.active:
                        break
            if story_screen is not None and story_screen.active:
                if station_screen is not None:
                    draw_background()
                    draw_world()
                    for b in buttons:
                        b.draw(screen)
                    draw_hud()
                    station_screen.draw(screen, WIDTH, HEIGHT)
                else:
                    draw_background()
                    draw_world()
                    for b in buttons:
                        b.draw(screen)
                    draw_hud()
                story_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === РЕМОНТ ===
        if repair_screen is not None and repair_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    repair_screen.close()
                    break
                else:
                    repair_screen.handle_event(event)
                    if repair_screen is None or not repair_screen.active:
                        break
            if repair_screen is not None and repair_screen.active:
                draw_background()
                draw_world()
                for b in buttons:
                    b.draw(screen)
                draw_hud()
                repair_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === КОНТРАКТЫ ===
        if contracts_screen is not None and contracts_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    contracts_screen.close()
                    break
                else:
                    contracts_screen.handle_event(event)
                    if contracts_screen is None or not contracts_screen.active:
                        break
            if contracts_screen is not None and contracts_screen.active:
                draw_background()
                draw_world()
                for b in buttons:
                    b.draw(screen)
                draw_hud()
                contracts_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === КАРТА ===
        if galaxy_map_screen is not None and galaxy_map_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    galaxy_map_screen.close()
                    break
                else:
                    galaxy_map_screen.handle_event(event)
                    if galaxy_map_screen is None or not galaxy_map_screen.active:
                        break
            if galaxy_map_screen is not None and galaxy_map_screen.active:
                galaxy_map_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === ПОДТВЕРЖДЕНИЕ АТАКИ ===
        if confirm_attack_screen is not None and confirm_attack_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    confirm_attack_screen.cancel()
                    break
                else:
                    confirm_attack_screen.handle_event(event)
                    if confirm_attack_screen is None or not confirm_attack_screen.active:
                        break
            if confirm_attack_screen is not None and confirm_attack_screen.active:
                draw_background()
                draw_world()
                for b in buttons:
                    b.draw(screen)
                draw_hud()
                confirm_attack_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === ПРОЛОГ ===
        if prologue_screen is not None and prologue_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    prologue_screen.skip_all()
                    break
                else:
                    prologue_screen.handle_event(event)
                    if prologue_screen is None or not prologue_screen.active:
                        break
            if prologue_screen is not None and prologue_screen.active:
                prologue_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === ИНВЕНТАРЬ ===
        if inventory_screen is not None and inventory_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    inventory_screen.close()
                    break
                else:
                    inventory_screen.handle_event(event)
                    if inventory_screen is None or not inventory_screen.active:
                        break
            if inventory_screen is not None and inventory_screen.active:
                draw_background()
                draw_world()
                for b in buttons:
                    b.draw(screen)
                draw_hud()
                inventory_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === ЗАРЯЖАНИЕ РАКЕТЫ ===
        if load_missile_screen is not None and load_missile_screen.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    load_missile_screen.close()
                    break
                else:
                    load_missile_screen.handle_event(event)
                    if load_missile_screen is None or not load_missile_screen.active:
                        break
            if load_missile_screen is not None and load_missile_screen.active:
                draw_background()
                draw_world()
                for b in buttons:
                    b.draw(screen)
                draw_hud()
                load_missile_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === СТАНЦИЯ ===
        if station_screen is not None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    close_station()
                    break
                else:
                    station_screen.handle_event(event)
                    if station_screen is None:
                        break
            if station_screen is not None:
                station_screen.refresh_button_states()
                draw_background()
                draw_world()
                for b in buttons:
                    b.draw(screen)
                draw_hud()
                station_screen.draw(screen, WIDTH, HEIGHT)
                pygame.display.flip()
                continue

        # === ОБЫЧНЫЙ РЕЖИМ ===
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                consumed = False
                if save_button.rect.collidepoint(event.pos):
                    save_button.handle_event(event)
                    consumed = True
                else:
                    for b in buttons:
                        if b.rect.collidepoint(event.pos):
                            b.handle_event(event)
                            consumed = True
                            break
                if not consumed and not state.paused:
                    handle_tap(event.pos)
            else:
                for b in buttons:
                    b.handle_event(event)

        scaled_dt = dt * state.time_scale
        if scaled_dt > 0:
            engines_ok = systems.can_thrust
            has_target = ship.target is not None
            thrust_scale = 1.0 if (engines_ok and has_target) else 0.0

            if not engines_ok and has_target:
                ship.stop()
                if systems.fuel <= 0.01:
                    state.notify("Топливо кончилось")
                elif not systems.engine_alive:
                    state.notify("Двигатель не работает")

            apply_ship_effects()
            ship.update(scaled_dt)

            # Автострельба по цели
            if player_target is not None and not player_target.dead:
                # --- Лазер ---
                if systems.weapon_damage > 0:
                    ok, dist = combat.can_hit(
                        ship.pos, ship.heading, player_target.pos,
                        systems.weapon_radius)
                    if ok:
                        player_fire_timer -= scaled_dt
                        if player_fire_timer <= 0:
                            player_target.take_damage(systems.weapon_damage)
                            combat.add_hit_flash(
                                ship.pos, player_target.pos,
                                color=(120, 220, 255))
                            player_fire_timer = systems.weapon_rate

                # --- Ракеты ---
                if systems.has_launcher and systems.loaded_missile is not None:
                    ok_r, dist_r = combat.can_hit(
                        ship.pos, ship.heading, player_target.pos,
                        1500.0)
                    if ok_r:
                        # Стреляем сразу, без кулдауна
                        result = systems.fire_loaded_missile()
                        if result is not None:
                            aid, dmg, spd = result
                            combat.spawn_missile(
                            ship.pos, player_target, dmg, spd)
                            state.notify("Ракета пущена!")

                if player_target.dead:
                    state.notify(f"{player_target.name} уничтожен")
                    combat.drop_debris(player_target)
                    player_target = None
            else:
                if player_target is not None and player_target.dead:
                    player_target = None

            camera.follow(ship.pos, scaled_dt)

            systems.update(scaled_dt, thrust_scale)
            combat.update_effects(scaled_dt)
            combat.update_debris(scaled_dt)
            combat.update_missiles(scaled_dt)
            combat.update_signals(scaled_dt)

            if getattr(systems, "last_accident", None):
                state.notify(systems.last_accident)
                systems.last_accident = None

            # --- NPC ---
            for npc in sector.npcs:
                if npc.dead:
                    continue
                npc.update_ai(scaled_dt, ship.pos, systems, sector,
                              sector.npcs)
                npc.update_motion(scaled_dt)

            sector.npcs = [n for n in sector.npcs if not n.dead]

            # Проверка смерти игрока
            hull = systems.systems["hull"]
            any_broken = any(
                slot.part is None or slot.part.is_broken()
                for slot in hull.slots
            )
            if any_broken:
                game_over()

        if state.notification_t > 0:
            state.notification_t -= dt
            if state.notification_t < 0:
                state.notification_t = 0

        state.game_time += scaled_dt

        draw_background()
        draw_world()
        for b in buttons:
            b.draw(screen)
        draw_hud()
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    _log("### calling main()")
    try:
        main()
    except Exception:
        import traceback
        _log("### EXCEPTION in main()")
        try:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise
    _log("### main() exited normally")