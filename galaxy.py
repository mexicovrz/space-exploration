# galaxy.py — процедурная генерация галактики и секторов.

import math
import random
from combat import NPCShip, npc_registry
from data import WORLD_SIZE


# --- Имена станций ---
STATION_NAMES = [
    "Керн", "Стелла", "Ньютон", "Вега", "Арктур", "Церера", "Тритон",
    "Гелиос", "Порт-Роял", "Дельта", "Сириус", "Орион", "Кассий",
    "Титан", "Миранда", "Каллисто", "Ганимед", "Европа", "Ио", "Фобос",
    "Деймос", "Плутон", "Харон", "Эрида", "Макемаке", "Седна",
    "Центавра", "Альфа", "Бета-2", "Гамма-7", "Кси", "Омикрон",
    "Лира", "Дракон", "Феникс", "Гидра", "Кентавр", "Персей", "Андромеда",
]

STATION_PREFIXES = ["Станция", "Форт", "Порт", "База", "Терминал", "Узел"]


# --- Имена секторов ---
SECTOR_NAMES = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta",
    "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu",
    "Nu", "Xi", "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon",
]


def _sector_label(index):
    if 0 <= index < len(SECTOR_NAMES):
        return SECTOR_NAMES[index]
    return f"S{index}"


# --- Граф секторов ---

def generate_galaxy(seed=42, total=20, max_neighbors=4):
    """Возвращает словарь {sector_index: [neighbor_indices]}.

    Каждый сектор имеет не более max_neighbors соседей. Граф связный.
    """
    rng = random.Random(seed)
    graph = {i: [] for i in range(total)}

    # 1) Остовное дерево: каждый новый сектор цепляется к 1-2 уже существующим
    for i in range(1, total):
        candidates = [j for j in range(i) if len(graph[j]) < max_neighbors]
        if not candidates:
            candidates = list(range(i))
        num_links = rng.randint(1, min(2, len(candidates)))
        chosen = rng.sample(candidates, num_links)
        for c in chosen:
            if len(graph[i]) < max_neighbors:
                graph[i].append(c)
                graph[c].append(i)

    # 2) Дополнительные рёбра — чтобы было интереснее
    for i in range(total):
        if len(graph[i]) >= max_neighbors:
            continue
        candidates = [j for j in range(total)
                      if j != i and j not in graph[i]
                      and len(graph[j]) < max_neighbors]
        rng.shuffle(candidates)
        for c in candidates:
            if len(graph[i]) >= max_neighbors:
                break
            graph[i].append(c)
            graph[c].append(i)

    return graph


# --- Утилиты генерации ---

def _random_station_name(rng, used_names):
    for _ in range(50):
        prefix = rng.choice(STATION_PREFIXES)
        base = rng.choice(STATION_NAMES)
        name = f"{prefix} {base}"
        if name not in used_names:
            used_names.add(name)
            return name
    return f"Станция-{rng.randint(100, 999)}"


def _place_stations(rng, count):
    """Случайные позиции станций с минимальной дистанцией друг от друга."""
    positions = []
    margin = 500
    min_dist = 700
    attempts = 0
    while len(positions) < count and attempts < 500:
        attempts += 1
        x = rng.randint(margin, WORLD_SIZE - margin)
        y = rng.randint(margin, WORLD_SIZE - margin)
        ok = True
        for px, py in positions:
            if math.hypot(px - x, py - y) < min_dist:
                ok = False
                break
        if ok:
            positions.append((x, y))
    return positions


def _place_gates():
    """Всегда 4 врата по углам сектора с отступом."""
    margin = 350
    return [
        (margin, margin),                                  # левый верх
        (WORLD_SIZE - margin, margin),                     # правый верх
        (margin, WORLD_SIZE - margin),                     # левый низ
        (WORLD_SIZE - margin, WORLD_SIZE - margin),        # правый низ
    ]


def generate_sector(index, name, seed, neighbors):
    """Создаёт объект Sector со станциями, вратами и астероидами."""
    from world import Station, Gate, Asteroid, Sector, QuestMarker

    rng = random.Random(seed + index * 1000)

    sector = Sector(index, name)
    sector.seed = seed

    # --- Станции: 2-4 штуки ---
    used_names = set()
    num_stations = rng.randint(2, 4)
    station_positions = _place_stations(rng, num_stations)
    for (sx, sy) in station_positions:
        st_name = _random_station_name(rng, used_names)
        sector.stations.append(Station(int(sx), int(sy), st_name))

    # --- Врата: всегда 4, по углам ---
    gate_positions = _place_gates()
    for i, (gx, gy) in enumerate(gate_positions):
        if i < len(neighbors):
            target = neighbors[i]
            gate_name = f"Врата -> {_sector_label(target)}"
        else:
            target = -1
            gate_name = "Пустые врата"
        sector.gates.append(
            Gate(int(gx), int(gy), gate_name, target_sector=target))

    # --- Астероиды ---
    num_ast = rng.randint(20, 45)
    for _ in range(num_ast):
        ax = rng.randint(200, WORLD_SIZE - 200)
        ay = rng.randint(200, WORLD_SIZE - 200)
        ar = rng.randint(20, 80)
        if any(math.hypot(ax - sx, ay - sy) < 300
               for sx, sy in station_positions):
            continue
        if any(math.hypot(ax - gx, ay - gy) < 300
               for gx, gy in gate_positions):
            continue
        sector.asteroids.append(Asteroid(ax, ay, ar))
    
        # --- Сюжетные маркеры ---
    if index == 1:   # Beta
        from world import QuestMarker
        cx = WORLD_SIZE // 2
        cy = WORLD_SIZE // 2
        sector.quest_markers.append(
            QuestMarker(cx, cy, "Обломки 'Аргентины'", "gustav_1"))
    
        # --- NPC ---
    _spawn_npcs_in_sector(sector, rng)
    
    return sector
    
def _spawn_npcs_in_sector(sector, rng):
    """Спавнит NPC в секторе: пираты, патрули, торговцы, доставщики."""
    from data import WORLD_SIZE
    from combat import NPCShip

    margin = 500
    sector.npcs = []

    def random_pos():
        return (rng.randint(margin, WORLD_SIZE - margin),
                rng.randint(margin, WORLD_SIZE - margin))

    # Пиратов — 1-2
    for _ in range(rng.randint(1, 2)):
        x, y = random_pos()
        sector.npcs.append(NPCShip("pirate", x, y))

    # Пиратов — 1
    for _ in range(1):
        x, y = random_pos()
        sector.npcs.append(NPCShip("pirate", x, y))

    # Патрулей — 1
    for _ in range(1):
        x, y = random_pos()
        sector.npcs.append(NPCShip("patrol", x, y))

    # Торговцев — 1-2
    for _ in range(rng.randint(1, 2)):
        x, y = random_pos()
        sector.npcs.append(NPCShip("trader", x, y))

    # Доставщиков — 0-1
    for _ in range(rng.randint(0, 1)):
        x, y = random_pos()
        sector.npcs.append(NPCShip("courier", x, y))