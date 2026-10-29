# data.py — константы, цвета, настройки

# --- Окно и время ---
FPS = 60
FULLSCREEN = True
TITLE = "Space Exploration"

BASE_WIDTH = 1280
BASE_HEIGHT = 800

UI_SCALE = 1.0

def set_ui_scale(width, height):
    global UI_SCALE
    UI_SCALE = min(width / BASE_WIDTH, height / BASE_HEIGHT)

def S(v):
    return int(round(v * UI_SCALE))


# --- Цвета ---
BLACK        = (0, 0, 0)
DARK_SPACE   = (8, 10, 22)
WHITE        = (240, 240, 240)
GREY         = (120, 120, 130)
DARK_GREY    = (60, 60, 70)
LIGHT_GREY   = (180, 180, 190)

UI_BG        = (18, 22, 34)
UI_PANEL     = (28, 34, 52)
UI_BORDER    = (70, 90, 130)
UI_TEXT      = (220, 225, 235)
UI_ACCENT    = (90, 170, 255)
UI_WARN      = (240, 180, 60)
UI_DANGER    = (230, 80, 80)
UI_OK        = (90, 210, 120)
UI_DIM = (150, 150, 160)

SHIP_COLOR   = (120, 220, 255)
STATION_COLOR= (140, 200, 140)
GATE_COLOR   = (220, 180, 90)
ASTEROID_COL = (90, 90, 100)
STAR_COLOR   = (200, 200, 220)

# --- Игровые константы ---
TIME_SCALES = [1, 2, 5]
START_MONEY = 50000000
START_FUEL  = 100.0
START_O2    = 100.0

# --- Мир ---
WORLD_SIZE = 4000
DOCK_DISTANCE = 90
GATE_DISTANCE = 90

# --- Корабль ---
SHIP_SIZE = 18
SHIP_MAX_SPEED = 320.0
SHIP_ACCEL = 260.0
SHIP_ARRIVE_EPS = 12
SHIP_BRAKE_RADIUS = 320.0

SHIP_TURN_SPEED = 8.0
SHIP_TURN_SPEED_MOVING = 5.0
SHIP_MIN_SPEED_FOR_TURN = 10.0

SHIP_SNAP_ON_TAP = True

# --- Ресурсы ---
FUEL_MAX = 100.0
FUEL_BURN_PER_SEC = 1.2

O2_MAX = 100.0
O2_BURN_PER_SEC = 0.25

O2_RESERVE_MAX = 100.0
O2_RESERVE_BURN_PER_SEC = 0.5
O2_RESERVE_REFILL_PRICE = 60

# Пороги для цвета
SYSTEM_CRITICAL = 30.0
SYSTEM_WARNING = 60.0

# --- Экономика станций ---
FUEL_PRICE_PER_UNIT = 2.0
O2_REFILL_PRICE = 30

# --- Экран станции ---
STATION_MENU_BUTTON_W = 340
STATION_MENU_BUTTON_H = 70

# --- Параметры обломков ---
DEBRIS_LIFETIME = 60.0
DEBRIS_RADIUS = 40

# --- Детали (запчасти) ---
# Формат: (id, группа, имя, цена, вес, hp_max, wear_rate, tier_for, effects)
# tier_for: id базовой детали, к которой относится эта (для совместимости слота).
#           Для базовых — совпадает с собственным id.
# effects: словарь бонусов:
#   speed_bonus   — множитель макс. скорости (например, 0.15 = +15%)
#   accel_bonus   — множитель ускорения
#   fuel_save     — уменьшение расхода топлива (0.25 = −25%)
#   o2_save       — уменьшение расхода O2
#   wear_reduction_<sid>  — уменьшение износа системы (0.30 = −30%)
#   hp_bonus_<sid>        — прибавка к HP системы
#
# Система: engine / reactor / o2gen / hull

PARTS_DEF = [
    # ============ МЕХАНИКА (двигатель) ============
    ("pipe_m",    "Механика", "Топливная магистраль",    25, 1.5, 100.0, 0.30,
     "pipe_m", {}),
    ("pipe_m_mk2", "Механика", "Топливная магистраль MK2", 250, 1.8, 100.0, 0.30,
     "pipe_m", {"fuel_save": 0.25}),

    ("gear_m",    "Механика", "Редуктор",                40, 2.0, 100.0, 0.15,
     "gear_m", {}),
    ("gear_m_mk2", "Механика", "Редуктор MK2",          500, 2.3, 100.0, 0.15,
     "gear_m", {"speed_bonus": 0.15}),

    ("bearing_m", "Механика", "Подшипники",              30, 1.0, 100.0, 0.20,
     "bearing_m", {}),
    ("bearing_m_mk2", "Механика", "Подшипники MK2",     400, 1.3, 100.0, 0.20,
     "bearing_m", {"accel_bonus": 0.20}),

    # ============ ЭЛЕКТРИКА (реактор, o2gen) ============
    ("cable_e",   "Электрика", "Кабели",                 20, 1.0, 100.0, 0.10,
     "cable_e", {}),
    ("cable_e_mk2", "Электрика", "Кабели MK2",          250, 1.2, 100.0, 0.10,
     "cable_e", {"wear_reduction_reactor": 0.30}),

    ("fuse_e",    "Электрика", "Предохранители",         35, 0.5, 100.0, 0.12,
     "fuse_e", {}),
    ("fuse_e_mk2", "Электрика", "Предохранители MK2",   350, 0.7, 100.0, 0.12,
     "fuse_e", {"hp_bonus_reactor": 20.0}),

    ("board_e",   "Электрика", "Платы",                  60, 1.5, 100.0, 0.08,
     "board_e", {}),
    ("board_e_mk2", "Электрика", "Платы MK2",           450, 1.8, 100.0, 0.08,
     "board_e", {"wear_reduction_o2gen": 0.25}),

    # ============ ЭНЕРГИЯ (реактор, o2gen) ============
    ("cell_n",    "Энергия", "Ячейки",                   80, 2.5, 100.0, 0.05,
     "cell_n", {}),
    ("cell_n_mk2", "Энергия", "Ячейки MK2",             800, 2.8, 100.0, 0.05,
     "cell_n", {"hp_bonus_reactor": 25.0}),

    ("rod_n",     "Энергия", "Стержни",                 120, 3.0, 100.0, 0.04,
     "rod_n", {}),
    ("rod_n_mk2", "Энергия", "Стержни MK2",            1000, 3.4, 100.0, 0.04,
     "rod_n", {"wear_reduction_reactor": 0.40}),

    ("spark_n",   "Энергия", "Свечи зажигания",          45, 0.8, 100.0, 0.10,
     "spark_n", {}),
    ("spark_n_mk2", "Энергия", "Свечи зажигания MK2",   450, 1.0, 100.0, 0.10,
     "spark_n", {"accel_bonus": 0.15}),

    # ============ КОРПУС ============
    ("plate_h", "Корпус", "Плиты", 50, 4.0, 100.0, 0.0,
     "scanner_h", {}),
    ("plate_h_mk2", "Корпус", "Плиты MK2", 500, 4.5, 100.0, 0.0,
     "scanner_h", {"hp_bonus_hull": 50.0}),

    ("sealant_h", "Корпус", "Герметик",                  25, 1.0, 100.0, 0.0,
     "sealant_h", {}),
    ("sealant_h_mk2", "Корпус", "Герметик MK2",         300, 1.2, 100.0, 0.0,
     "sealant_h", {"hp_bonus_hull": 30.0}),

    # ============ ЖИЗНЕОБЕСПЕЧЕНИЕ ============
    ("filter_l",  "Жизнеобеспечение", "Фильтры",         30, 1.2, 100.0, 0.06,
     "filter_l", {}),
    ("filter_l_mk2", "Жизнеобеспечение", "Фильтры MK2", 300, 1.4, 100.0, 0.06,
     "filter_l", {"o2_save": 0.30}),

    ("bottle_l",  "Жизнеобеспечение", "Баллоны",         70, 3.0, 100.0, 0.03,
     "bottle_l", {}),
    ("bottle_l_mk2", "Жизнеобеспечение", "Баллоны MK2", 700, 3.4, 100.0, 0.03,
     "bottle_l", {"hp_bonus_o2gen": 25.0}),
     
         # ============ ОРУЖИЕ ============
    ("laser_w", "Оружие", "Лазер", 1200, 2.0, 100.0, 0.05,
     "laser_w", {"weapon_damage": 8.0, "weapon_rate": 0.5}),
    ("laser_w_mk2", "Оружие", "Лазер MK2", 3500, 2.5, 100.0, 0.05,
     "laser_w", {"weapon_damage": 14.0, "weapon_rate": 0.4}),
    ("autocannon_w", "Оружие", "Импульсная автопушка", 2600, 3.2, 100.0, 0.07,
     "laser_w", {"weapon_damage": 5.0, "weapon_rate": 0.22}),
    ("ion_w", "Оружие", "Ионная пушка", 4200, 2.8, 100.0, 0.06,
     "laser_w", {"weapon_damage": 6.0, "weapon_rate": 0.65,
                 "weapon_emp_duration": 1.8}),
    ("arc_w", "Оружие", "Дуговая пушка", 6200, 4.0, 100.0, 0.08,
     "laser_w", {"weapon_damage": 10.0, "weapon_rate": 0.85,
                 "weapon_chain_damage": 5.0, "weapon_chain_range": 240.0}),

    # ============ ЩИТ ============
    ("shield_gen", "Щит", "Генератор щита", 2000, 3.0, 100.0, 0.05,
     "shield_gen", {"shield_max": 50.0, "shield_regen": 2.0}),
    ("shield_gen_mk2", "Щит", "Генератор MK2", 5000, 3.5, 100.0, 0.05,
     "shield_gen", {"shield_max": 80.0, "shield_regen": 3.0}),
     
     # =========== СКАНЕР =========
    ("scanner_h", "Корпус", "Сканер сигналов", 1800, 1.5, 100.0, 0.03,
     "scanner_h", {"signal_scanner": 1}),
    ("scanner_h_mk2", "Корпус", "Сканер MK2", 4500, 1.8, 100.0, 0.03,
     "scanner_h", {"signal_scanner": 2}),
     
    # ============ ПУСКОВАЯ УСТАНОВКА ============
    ("launcher_w", "Оружие", "Пусковая установка", 3000, 3.0, 100.0, 0.05,
     "launcher_w", {"is_launcher": 1}),
    ("launcher_w_mk2", "Оружие", "Пусковая установка MK2", 7000, 3.5, 100.0, 0.05,
     "launcher_w", {"is_launcher": 1, "missile_rate_bonus": 0.5}),
]

WEAPON_QUIRKS = {
    "autocannon_w": "Частые выстрелы, небольшой урон",
    "ion_w": "Отключает оружие цели на 1,8 сек.",
    "arc_w": "Цепляет ближайшего пирата: +5 урона",
}

# Быстрый доступ
PARTS_BY_ID = {row[0]: {
    "id": row[0],
    "group": row[1],
    "name": row[2],
    "price": row[3],
    "weight": row[4],
    "hp_max": row[5],
    "wear_rate": row[6],
    "tier_for": row[7],
    "effects": row[8],
} for row in PARTS_DEF}

# Карта: какой id (слот) какие детали принимает.
# Ключ — базовый id слота (например "pipe_m"), значение — список всех id,
# которые можно поставить в этот слот.
SLOT_COMPATIBLE = {}
for row in PARTS_DEF:
    pid = row[0]
    tier = row[7]
    SLOT_COMPATIBLE.setdefault(tier, []).append(pid)

AMMO_DEF = [
    ("missile_light", "Лёгкая ракета", 300, 0.3),
    ("missile_ammo", "Ракета", 800, 0.8),
    ("missile_heavy", "Тяжёлая ракета", 1500, 2.0),
]

# Параметры ракет: урон и скорость
MISSILE_PARAMS = {
    "missile_light": {"damage": 20.0, "speed": 500.0},
    "missile_ammo":  {"damage": 40.0, "speed": 400.0},
    "missile_heavy": {"damage": 80.0, "speed": 250.0},
}

# --- Слоты систем ---
SYSTEM_SLOTS = {
    "engine":  ["pipe_m", "gear_m", "bearing_m"],
    "reactor": ["cell_n", "rod_n", "cable_e"],
    "o2gen":   ["board_e", "spark_n", "filter_l"],
    "hull":    ["scanner_h", "sealant_h", "bottle_l"],
    "weapon":  ["laser_w", "launcher_w"],
    "shield":  ["shield_gen"],
    "engine2": ["pipe_m", "gear_m", "bearing_m"],
}

# Имена систем (для отображения)
SYSTEM_NAMES = {
    "engine":  "Двигатель",
    "reactor": "Реактор",
    "o2gen":   "O2-генератор",
    "hull":    "Корпус",
    "weapon":  "Оружие",
    "shield":  "Щит",
    "engine2": "Двигатель 2",
}

# --- Инвентарь ---
INVENTORY_MAX_WEIGHT = 80.0

# --- Аварии ---
ACCIDENT_DAMAGE_MIN = 10.0
ACCIDENT_DAMAGE_MAX = 30.0
ACCIDENT_COOLDOWN_MIN = 60.0
ACCIDENT_COOLDOWN_MAX = 140.0
# --- Трюм ---
INVENTORY_MAX_WEIGHT = 80.0     # подняли с 50 до 80 (общий вес: детали + груз)

# --- Грузы (для контрактов) ---
# (id, имя, вес, базовая цена за единицу веса)
CARGO_DEF = [
    ("meds",     "Медикаменты",         6.0,  22),
    ("food",     "Продукты",            8.0,  15),
    ("parts",    "Запчасти для шахт",  10.0,  20),
    ("electronics", "Электроника",      4.0,  28),
    ("ore",      "Руда",               14.0,  12),
    ("repair",   "Ремонтный набор",     7.0,  24),
    ("fuelcell", "Топливные ячейки",   12.0,  18),
]

CARGO_BY_ID = {row[0]: {
    "id": row[0],
    "name": row[1],
    "weight": row[2],
    "price_per_weight": row[3],
} for row in CARGO_DEF}

# --- Контракты ---
STATION_CONTRACTS_COUNT = 3            # сколько контрактов на станции
CONTRACT_GEN_TIME = 15 * 60            # 15 игровых минут (в секундах) — обновление
CONTRACT_URGENT_DEADLINE = 10 * 60     # 10 игровых минут — срок срочного
CONTRACT_REWARD_MULT_URGENT = 1.5      # множитель награды для срочного
CONTRACT_REWARD_MULT_LATE = 0.5        # если опоздал — награда падает вдвое
CONTRACT_MAX_ACTIVE = 3                # максимум активных контрактов у игрока
CONTRACT_DISTANCE_DIVISOR = 2000.0     # чем больше — тем меньше влияние расстояния

# --- Характеристики NPC ---
# Формат: {тип: {поле: значение}}
NPC_TYPES = {
    "trader": {
        "name": "Торговец",
        "color": (240, 200, 60),
        "hull_hp": 40.0,
        "damage": 0.0,
        "fire_rate": 0.0,
        "radius": 400,
        "speed": 0.7,
    },
    "courier": {
        "name": "Доставщик",
        "color": (100, 200, 140),
        "hull_hp": 40.0,
        "damage": 0.0,
        "fire_rate": 0.0,
        "radius": 400,
        "speed": 1.2,
    },
    "patrol": {
        "name": "Патруль",
        "color": (90, 140, 240),
        "hull_hp": 250.0,
        "damage": 18.0,
        "fire_rate": 0.6,
        "radius": 900,
        "speed": 0.9,
    },
    "pirate": {
        "name": "Пират",
        "color": (230, 60, 60),
        "hull_hp": 60.0,
        "damage": 6.0,
        "fire_rate": 1.0,
        "radius": 500,
        "speed": 1.0,
    },
}

# --- Хлам (лут с пиратов) ---
# (id, имя, цена за единицу, вес за единицу)
SCRAP_DEF = [
    ("scrap_metal", "Металлолом",        8,  0.5),
    ("scrap_wire",  "Осколки проводов",  12, 0.3),
    ("scrap_chip",  "Сгоревшие чипы",    15, 0.2),
    ("scrap_plate", "Погнутые пластины", 10, 0.6),
    ("scrap_glass", "Битое стекло",      6,  0.4),
]

SCRAP_BY_ID = {row[0]: {
    "id": row[0],
    "name": row[1],
    "price": row[2],
    "weight": row[3],
} for row in SCRAP_DEF}


# --- Ценный лут (трофеи) ---
# (id, имя, цена, вес)
VALUABLES_DEF = [
    ("gold",     "Золото",             500,  3.0),
    ("gems",     "Драгоценные камни",  800,  1.0),
    ("alloy",    "Редкий сплав",       1200, 5.0),
    ("chip",     "Контрабандный чип",  2000, 0.5),
    ("artifact", "Артефакт",           3000, 2.0),
]

VALUABLES_BY_ID = {row[0]: {
    "id": row[0],
    "name": row[1],
    "price": row[2],
    "weight": row[3],
} for row in VALUABLES_DEF}


# --- Параметры обломков ---
DEBRIS_LIFETIME = 60.0            # секунд до исчезновения
DEBRIS_RADIUS = 40                # радиус тапа по обломкам

def clamp(v, lo, hi):
    return max(lo, min(hi, v))
    
# --- Пролог: 20 экранов ---
# image: путь к файлу. Если файла нет — рисуется заглушка.
PROLOGUE_PAGES = [
    {
        "title": "Эхо аномалии",
        "text": "Пролог",
        "image": "images/prologue/01_title.jpeg",
        "is_title": True,
    },
    {
        "title": "Эпоха Врат",
        "text": "Когда-то галактику связывала сеть Врат — гигантских колец из неизвестного металла.",
        "image": "images/prologue/02_gate.jpeg",
    },
    {
        "title": "Древние",
        "text": "Никто не знал, кто их построил. Одни называли их Древними, другие — Пилигримами, третьи — Те, Кто Ушёл.",
        "image": "images/prologue/03_ancients.jpeg",
    },
    {
        "title": "Эпоха Согласия",
        "text": "Врата позволяли кораблям мгновенно перемещаться между системами. Торговля, наука, культура — всё росло и цвело. Это была Эпоха Согласия.",
        "image": "images/prologue/04_concord.jpeg",
    },
    {
        "title": "Цена Врат",
        "text": "Но у всего есть цена. Врата требовали Ключ — устройство, синхронизирующее корабль с энергией кольца. Ключи были редки, и их распределение стало причиной первых конфликтов.",
        "image": "images/prologue/05_key.jpeg",
    },
    {
        "title": "Катастрофа",
        "text": "Никто точно не знает, что произошло.",
        "image": "images/prologue/06_catastrophe.jpeg",
    },
    {
        "title": "Три версии",
        "text": "Одни говорят — Древние ушли, забрав свои технологии. Другие — что они погибли. Третьи — что это была война, в которой проиграли все.",
        "image": "images/prologue/07_versions.jpeg",
    },
    {
        "title": "Эпоха Разлома",
        "text": "Сеть Врат рухнула. Часть колец погасла навсегда, часть — законсервировалась. Сектора оказались отрезаны друг от друга. Началась Эпоха Разлома.",
        "image": "images/prologue/08_rupture.jpeg",
    },
    {
        "title": "Последствия",
        "text": "Колонии, оставшиеся без поставок, вымирали. Станции, отрезанные от торговых путей, превращались в призраков.",
        "image": "images/prologue/09_decline.jpeg",
    },
    {
        "title": "Рождение фракций",
        "text": "А те, кто сумел выжить, начали бороться за ресурсы. Так родились фракции.",
        "image": "images/prologue/10_factions.jpeg",
    },
    {
        "title": "Корпорация «Гелиос»",
        "text": "Потомки корпоративных колонистов. Контролируют добычу и производство. Считают, что порядок важнее свободы.",
        "image": "images/prologue/11_helios.jpeg",
    },
    {
        "title": "Повстанцы",
        "text": "Бывшие рабочие, беглые пилоты, дезертиры «Гелиоса». Борются за независимость станций и равный доступ к Вратам.",
        "image": "images/prologue/12_rebels.jpeg",
    },
    {
        "title": "Пираты",
        "text": "Те, кто решил, что законы — для тех, у кого есть дом. Контролируют астероидные базы и чёрные рынки.",
        "image": "images/prologue/13_pirates.jpeg",
    },
    {
        "title": "Одиночки",
        "text": "Механики, торговцы, наёмники, исследователи. Те, кто не примкнул ни к кому. Живут на станциях вроде «Ржавого причала».",
        "image": "images/prologue/14_loners.jpeg",
    },
    {
        "title": "Легенда о МГД",
        "text": "Есть слух, который передают шёпотом. Говорят, Древние строили не только Врата — они строили Межгалактический двигатель.",
        "image": "images/prologue/15_legend.jpeg",
    },
    {
        "title": "Что такое МГД",
        "text": "Устройство, способное разорвать саму ткань пространства и перенести корабль между галактиками. Туда, откуда можно вернуться домой.",
        "image": "images/prologue/16_engine.jpeg",
    },
    {
        "title": "Компоненты МГД",
        "text": "МГД состоит из четырёх компонентов: Ядро питания, Навигационный модуль, Стабилизатор прыжка, Ключ-код.",
        "image": "images/prologue/17_components.jpeg",
    },
    {
        "title": "Разбросанные компоненты",
        "text": "Компоненты разбросаны по сектору. Одни — у фракций. Другие — в аномалиях. Третьи — там, куда лучше не летать.",
        "image": "images/prologue/18_scattered.jpeg",
    },
    {
        "title": "Никто не собрал",
        "text": "Никто не собрал МГД целиком. Но многие пытались. И многие не вернулись.",
        "image": "images/prologue/19_failed.jpeg",
    },
    {
        "title": "Ты",
        "text": "Ты — один из тех, кто попробует.\nДорога домой начинается сейчас.",
        "image": "images/prologue/20_you.jpeg",
        "is_final": True,
    },
]

AMMO_BY_ID = {row[0]: {
    "id": row[0],
    "name": row[1],
    "price": row[2],
    "weight": row[3],
} for row in AMMO_DEF}