import re


_LANGUAGE = "ru"

_TRANSLATIONS = {}
_PAIRS = """
Продолжить	Continue
Новая игра	New Game
Начать игру	Start Game
Язык:	Language:
Русский	Russian
Английский	English
космические путешествия и торговля	Space travel and trade
Далее →	Next →
Пропустить	Skip
Закрыть	Close
Отмена	Cancel
Назад	Back
Принять задание	Accept Quest
Завершить	Complete
Взять	Accept
Сдать все	Turn In All
Вынуть	Remove
Поставить из трюма	Install from Cargo
Зарядить	Load
Атаковать	Attack
Стоп	Stop
Заправить бак	Refuel
Пополнить аварийный O2	Refill Emergency O2
Магазин деталей	Parts Shop
Контракты	Contracts
СЮЖЕТ	STORY
Отстыковаться	Undock
Купить	Buy
Продать	Sell
Верфь	Shipyard
Боеприпасы	Ammunition
Продать весь хлам	Sell All Scrap
Продать все трофеи	Sell All Valuables
РЕМОНТ	REPAIR
КОНТР.	CONTR.
КАРТА	MAP
ИНВ.	INV.
ЗАРЯД	LOAD
СОХР.	SAVE
ПАУЗА	PAUSED
ЦЕЛЬ:	TARGET:
Цель:	Target:
Курс:	Course:
Топливо	Fuel
Топливо:	Fuel:
O2 каб.	O2 cabin
O2 КАБ.!	O2 CABIN!
Баллон	Tank
Щит	Shield
Ракета	Missile
ЗАРЯЖЕНО:	LOADED:
Ракет в трюме:	Missiles in cargo:
Хлам:	Scrap:
Трофеи:	Valuables:
Трюм:	Cargo:
Кредиты:	Credits:
Станция:	Station:
Двигатель 2	Engine 2
Корабль:	Ship:
Состояние систем:	System Status:
Системы:	Systems:
Слоты:	Slots:
Выбери систему слева	Select a system on the left
[Пусто]   нужна:	[Empty]   required:
(СЛОМАНО)	(BROKEN)
Тап по слоту -> действия	Tap a slot -> actions
Трюм пуст.	Cargo is empty.
Название	Name
Группа	Category
Цена	Price
Вес	Weight
Кол-во	Qty
Трюм	Cargo
В трюме	In Cargo
ДЕТАЛИ	PARTS
ХЛАМ	SCRAP
ТРОФЕИ	VALUABLES
ГРУЗЫ КОНТРАКТОВ	CONTRACT CARGO
СЮЖЕТНЫЙ ГРУЗ	STORY CARGO
— квест —	— quest —
ИНВЕНТАРЬ	INVENTORY
Корабль	Ship
Скорость	Speed
Расход	Consumption
— стартовый —	— starting ship —
— ВЫ ЗДЕСЬ —	— YOU ARE HERE —
Из:	From:
В:	To:
Осталось:	Time left:
ПРОСРОЧЕН	OVERDUE
СРОЧНЫЙ	URGENT
Без срока	No deadline
Активных:	Active:
Нет доступных контрактов.	No contracts available.
Нет активных контрактов.	No active contracts.
Контракты —	Contracts —
Сдать контракты —	Turn In Contracts —
Можно сдать:	Ready to turn in:
Итого:	Total:
Вес:	Weight:
Куда:	To:
Экипировка:	Equipment:
Слишком много активных контрактов	Too many active contracts
Трюм полон	Cargo hold is full
Не хватает денег или трюм не влезет	Not enough credits or cargo space
Нет доступных сюжетных заданий	No story quests available
Ремонт	Repair
Продолжить	Continue
Доставить	Deliver
Закрыть	Close
Купить корабль:	Ship purchased:
Продано за	Sold for
Продано:	Sold:
Заправить (	Refuel (
Аварийный O2 (	Emergency O2 (
Аварийный O2 (полный)	Emergency O2 (full)
Сдать контракты (	Turn in contracts (
Контракты (взято	Contracts (accepted
Станция:	Station:
Магазин —	Shop —
Быстрый доступ:	Quick access:
Нет топлива или двигатель мёртв	No fuel or the engine is offline
Топливо кончилось	Out of fuel
Двигатель не работает	Engine is offline
Тапните, чтобы начать заново	Tap to start over
ВАШ КОРАБЛЬ УНИЧТОЖЕН	YOUR SHIP WAS DESTROYED
Игра сохранена	Game saved
Ошибка сохранения	Save failed
Ошибка:	Error:
Ошибка: станция не найдена	Error: station not found
Тапните по экрану, чтобы продолжить	Tap the screen to continue
СЮЖЕТНЫЙ ГРУЗ	STORY CARGO
Задания:	Quests:
контр.	contracts
сюжет	story
Задание:	Quest:
Задание принято:	Quest accepted:
Квест завершён!	Quest complete!
Награда:	Reward:
Деталь:	Part:
Принять	Accept
Нет активных контрактов.	No active contracts.
Контракт	Contract
Доставлено!	Delivered!
Взято:	Accepted:
Забрано:	Collected:
Пусто	Empty
Здесь ничего интересного	Nothing interesting here
Уже собрано	Already collected
Собрано! Вернись к	Collected! Return to
Собрано:	Collected:
Отстыковка выполнена	Undocking complete
Эти врата никуда не ведут	These gates lead nowhere
Не хватает денег (нужно	Not enough credits (need
Не хватает топлива (нужно	Not enough fuel (need
Прибытие: сектор	Arrived in sector
Вы атаковали мирного! Патрули в ярости!	You attacked a civilian! The patrols are furious!
Цель достигнута:	Destination reached:
Цель:	Target:
ОПОЗДАЛ	LATE
ЗАСАДА!	AMBUSH!
пиратов атакуют!	pirates are attacking!
Тайник найден! Трофей в трюме	Cache found! Valuables added to cargo
Пустой сигнал. Ничего нет.	Empty signal. Nothing here.
Заброшенный корабль! Забрано: хлам + трофей	Derelict ship! Collected: scrap + valuables
Заброшенный корабль! Забрано: хлам	Derelict ship! Collected: scrap
Торговец: продал редкий товар, +500 кр.	Trader sold rare goods, +500 cr.
Заряжаение ракеты	Loading missile
ЗАРЯЖАНИЕ РАКЕТЫ	LOADING MISSILE
Пусковая пуста	Launcher is empty
Урон:	Damage:
В трюме: x	In cargo: x
Ракета пущена!	Missile launched!
уничтожен	destroyed
Сигнал бедствия	Distress signal
Сектор	Sector
Соседние сектора:	Adjacent sectors:
— нет —	— none —
Не исследован.	Unexplored.
Сначала нужно побывать здесь.	You must visit this location first.
Станций:	Stations:
Тащи пальцем чтобы сдвинуть. Тап по сектору — информация	Drag to move. Tap a sector for information
Подтверждение атаки на мирный корабль или патруль.	Confirm attack on a civilian ship or patrol.
Это мирный корабль. Патрули объявят вас в розыск.	This is a civilian ship. Patrols will put you on their wanted list.
Медикаменты	Medicine
Продукты	Food
Запчасти для шахт	Mining parts
Электроника	Electronics
Руда	Ore
Ремонтный набор	Repair kit
Топливные ячейки	Fuel cells
Механика	Mechanics
Топливная магистраль	Fuel line
Редуктор	Gearbox
Подшипники	Bearings
Электрика	Electronics
Кабели	Cables
Предохранители	Fuses
Платы	Circuit boards
Энергия	Power
Ячейки	Cells
Стержни	Rods
Свечи зажигания	Spark plugs
Плиты	Plates
Герметик	Sealant
Жизнеобеспечение	Life support
Фильтры	Filters
Баллоны	Cylinders
Лазер	Laser
Импульсная автопушка	Pulse Autocannon
Ионная пушка	Ion Cannon
Дуговая пушка	Arc Cannon
Частые выстрелы, небольшой урон	Fast shots, low damage
Отключает оружие цели на 1,8 сек.	Disables the target's weapons for 1.8 sec.
Цепляет ближайшего пирата: +5 урона	Chains to a nearby pirate: +5 damage
Оружие	Weapons
Пусковая установка	Launcher
Генератор щита	Shield generator
Сканер сигналов	Distress scanner
Лёгкая ракета	Light missile
Тяжёлая ракета	Heavy missile
Двигатель	Engine
Реактор	Reactor
O2-генератор	O2 generator
Корпус	Hull
Торговец	Trader
Доставщик	Courier
Патруль	Patrol
Пират	Pirate
Металлолом	Scrap metal
Осколки проводов	Wire fragments
Сгоревшие чипы	Burnt chips
Погнутые пластины	Bent plates
Битое стекло	Broken glass
Золото	Gold
Драгоценные камни	Gemstones
Редкий сплав	Rare alloy
Контрабандный чип	Smuggled chip
Артефакт	Artifact
Скиталец	Wanderer
Стандартный корабль. Сбалансированные характеристики.	Standard ship with balanced stats.
Тягач	Hauler
Два двигателя: второй сохраняет ход при поломке первого. Большой трюм.	Twin engines: the second keeps you moving if the first fails. Large cargo hold.
Курьер	Courier
Два лазерных модуля. Быстрый, но с маленьким трюмом.	Dual laser modules. Fast, but with a small cargo hold.
Эхо аномалии	Anomaly Echo
Пролог	Prologue
Эпоха Врат	The Gate Age
Когда-то галактику связывала сеть Врат — гигантских колец из неизвестного металла.	Once, a network of Gates connected the galaxy—giant rings made of an unknown metal.
Древние	The Ancients
Никто не знал, кто их построил. Одни называли их Древними, другие — Пилигримами, третьи — Те, Кто Ушёл.	No one knew who built them. Some called them the Ancients, others the Pilgrims, and others the Ones Who Left.
Эпоха Согласия	The Age of Concord
Врата позволяли кораблям мгновенно перемещаться между системами. Торговля, наука, культура — всё росло и цвело. Это была Эпоха Согласия.	The Gates let ships travel instantly between systems. Trade, science, and culture flourished. This was the Age of Concord.
Цена Врат	The Price of the Gates
Но у всего есть цена. Врата требовали Ключ — устройство, синхронизирующее корабль с энергией кольца. Ключи были редки, и их распределение стало причиной первых конфликтов.	But everything has a price. The Gates required a Key, a device that synchronized a ship with the ring's energy. Keys were rare, and their distribution sparked the first conflicts.
Катастрофа	The Catastrophe
Никто точно не знает, что произошло.	No one knows exactly what happened.
Три версии	Three Theories
Одни говорят — Древние ушли, забрав свои технологии. Другие — что они погибли. Третьи — что это была война, в которой проиграли все.	Some say the Ancients left, taking their technology with them. Others say they died. Still others say it was a war in which everyone lost.
Эпоха Разлома	The Age of Rupture
Сеть Врат рухнула. Часть колец погасла навсегда, часть — законсервировалась. Сектора оказались отрезаны друг от друга. Началась Эпоха Разлома.	The Gate network collapsed. Some rings went dark forever; others were sealed. Sectors were cut off from one another. The Age of Rupture began.
Последствия	The Aftermath
Колонии, оставшиеся без поставок, вымирали. Станции, отрезанные от торговых путей, превращались в призраков.	Colonies without supplies died out. Stations cut off from trade routes became ghost towns.
Рождение фракций	The Rise of Factions
А те, кто сумел выжить, начали бороться за ресурсы. Так родились фракции.	Those who survived began fighting over resources. The factions were born.
Корпорация «Гелиос»	The Helios Corporation
Потомки корпоративных колонистов. Контролируют добычу и производство. Считают, что порядок важнее свободы.	Descendants of corporate colonists. They control mining and production, believing order matters more than freedom.
Повстанцы	The Rebels
Бывшие рабочие, беглые пилоты, дезертиры «Гелиоса». Борются за независимость станций и равный доступ к Вратам.	Former workers, fugitive pilots, and Helios deserters. They fight for station independence and equal access to the Gates.
Пираты	Pirates
Те, кто решил, что законы — для тех, у кого есть дом. Контролируют астероидные базы и чёрные рынки.	Those who decided laws are for people with homes. They control asteroid bases and black markets.
Одиночки	Loners
Механики, торговцы, наёмники, исследователи. Те, кто не примкнул ни к кому. Живут на станциях вроде «Ржавого причала».	Mechanics, traders, mercenaries, and explorers who joined no faction. They live at stations like Rusty Pier.
Легенда о МГД	The IGT Legend
Есть слух, который передают шёпотом. Говорят, Древние строили не только Врата — они строили Межгалактический двигатель.	A rumor is passed in whispers: the Ancients built more than the Gates—they built an Intergalactic Drive.
Что такое МГД	What Is the IGT?
Устройство, способное разорвать саму ткань пространства и перенести корабль между галактиками. Туда, откуда можно вернуться домой.	A device that can tear the fabric of space and carry a ship between galaxies—to a place from which it can return home.
Компоненты МГД	IGT Components
МГД состоит из четырёх компонентов: Ядро питания, Навигационный модуль, Стабилизатор прыжка, Ключ-код.	The IGT consists of four components: a power core, a navigation module, a jump stabilizer, and a key code.
Разбросанные компоненты	Scattered Components
Компоненты разбросаны по сектору. Одни — у фракций. Другие — в аномалиях. Третьи — там, куда лучше не летать.	The components are scattered across the sector. Some are held by factions, others are in anomalies, and some are in places best avoided.
Никто не собрал	No One Has Built It
Никто не собрал МГД целиком. Но многие пытались. И многие не вернулись.	No one has assembled the IGT. Many have tried, and many never returned.
Ты	You
Ты — один из тех, кто попробует.\\nДорога домой начинается сейчас.	You are one of those who will try.\\nThe journey home begins now.
Медикаменты для Форта	Medicine for the Fort
Инженер Ханна	Engineer Hannah
Ты тоже выжил? После крушения? Я — Ханна, инженер.	You survived too? The crash? I'm Hannah, an engineer.
Мой корабль разбился, как и твой.	My ship crashed, just like yours.
Слушай. У меня есть идея, как починить прыжковое ядро.	Listen. I have an idea for fixing the jump core.
Но сначала — помоги. На {target_station} нужны медикаменты.	But first, help me. {target_station} needs medicine.
Там вспышка лихорадки. Возьми 5 единиц и доставь.	There's a fever outbreak there. Take 5 units and deliver them.
Потом поговорим.	We'll talk afterward.
Спасибо. Ты честный пилот. Слушай сюда.	Thank you. You're an honest pilot. Listen.
Старый механик по имени Густав живёт на станции {next_giver_station},	An old mechanic named Gustav lives at {next_giver_station},
в секторе {next_giver_sector}.	in sector {next_giver_sector}.
Он единственный, кто разбирается в прыжковых ядрах.	He's the only one who understands jump cores.
Скажи ему, что от меня. Удачи, пилот.	Tell him I sent you. Good luck, pilot.
Чертежи Аргентины	The Argentina Blueprints
Механик Густав	Mechanic Gustav
Ханна прислала? Хм. Ладно, слушай.	Hannah sent you? Hmm. All right, listen.
У меня есть прыжковое ядро, но оно не работает. Нужны чертежи.	I have a jump core, but it doesn't work. I need the blueprints.
Они были на корабле 'Аргентина', который пропал в секторе {target_sector}.	They were aboard the ship 'Argentina', which vanished in sector {target_sector}.
Слетай туда. Найди обломки 'Аргентины' — они в центре сектора.	Fly there. Find the wreck of the 'Argentina' in the center of the sector.
Тапни по ним, забери картридж с данными.	Tap it and retrieve the data cartridge.
Принеси мне.	Bring it to me.
Хм. Настоящий картридж. Не ожидал. Слушай...	Hmm. A real cartridge. I didn't expect that. Listen...
Я стар. Мои руки уже не те. Но есть один человек —	I'm old. My hands aren't what they used to be. But there's someone—
Академик Лина. Она в секторе {next_giver_sector},	Academician Lina. She's in sector {next_giver_sector},
на станции {next_giver_station}.	at {next_giver_station}.
Она умеет собирать прыжковые ядра с нуля.	She can build jump cores from scratch.
Передай ей привет от старика Густава.	Give her my regards.
И вот, держи — пригодится.	Here, take this. It'll come in handy.
Катализатор Мёбиуса	The Mobius Catalyst
Академик Лина	Academician Lina
Густав? Жив ещё, старик. Что ж, помогу.	Gustav? The old man is still alive. All right, I'll help.
Для прыжкового ядра мне нужен катализатор Мёбиуса.	I need a Mobius catalyst for the jump core.
Он есть у торговца Марка в секторе {target_sector}.	Trader Mark has one in sector {target_sector}.
Марк — на станции {target_station}.	Mark is at {target_station}.
Слетай туда, сделай что попросит — потом возвращайся.	Fly there, do what he asks, then come back.
Катализатор. Хорошо.	The catalyst. Good.
Теперь слушай внимательно.	Now listen carefully.
Прыжковое ядро я соберу — но врата домой не здесь.	I'll build the jump core, but the gate home isn't here.
Они в секторе {next_giver_sector}, на дальней стороне.	It's in sector {next_giver_sector}, on the far side.
Через Delta. Лети туда. Ядро будет готово к твоему прибытию.	Through Delta. Go there. The core will be ready when you arrive.
Удачи, пилот. Возвращайся домой.	Good luck, pilot. Go home.
Возвращение домой	The Journey Home
Ты входишь в систему Epsilon.	You enter the Epsilon system.
Здесь тихо. Вдалеке — голубая планета. Твой дом.	It's quiet here. A blue planet hangs in the distance. Your home.
Ты проверяешь прыжковое ядро. Оно работает.	You check the jump core. It works.
Навигационный компьютер предлагает курс домой.	The navigation computer plots a course home.
Ты сделал это.	You did it.
кр.	cr.
кг	kg
сектор	sector
сектора	sector
секторе	sector
Сектор	Sector
станция	station
станции	station
Станция	Station
Обломки	Wreck
обломки	wreck
контракт	contract
Контракт	Contract
задание	quest
Задание	Quest
Задача	Objective
Собрано	Collected
ПРОСРОЧЕН	OVERDUE
Доставить	Deliver
Курс	Course
СЮЖЕТ	STORY
Станция-	Station-
Форт	Fort
Порт	Port
База	Base
Терминал	Terminal
Узел	Hub
Керн	Kern
Стелла	Stella
Ньютон	Newton
Вега	Vega
Арктур	Arcturus
Церера	Ceres
Тритон	Triton
Гелиос	Helios
Порт-Роял	Port Royal
Дельта	Delta
Сириус	Sirius
Орион	Orion
Кассий	Cassius
Титан	Titan
Миранда	Miranda
Каллисто	Callisto
Ганимед	Ganymede
Европа	Europa
Ио	Io
Фобос	Phobos
Деймос	Deimos
Плутон	Pluto
Харон	Charon
Эрида	Eris
Макемаке	Makemake
Седна	Sedna
Центавра	Centauri
Альфа	Alpha
Бета	Beta
Гамма	Gamma
Кси	Xi
Омикрон	Omicron
Лира	Lyra
Дракон	Draco
Феникс	Phoenix
Гидра	Hydra
Кентавр	Centaurus
Персей	Perseus
Андромеда	Andromeda
Кредиты	Credits
Скорость	Speed
Осталось	Time left
Здоровье	Health
Прибыть	Arrive
найти объект	find the object
и вернуться.	and return.
Топливо:	Fuel:
Двигатель не работает	Engine is offline
Нет топлива	Out of fuel
Ракета пущена!	Missile launched!
ВНИМАНИЕ	WARNING
Генератор MK2	Generator MK2
Сканер MK2	Scanner MK2
Курс: сигнал бедствия	Course: distress signal
КОНТР	CONTR.
время:	time:
(нажми ЗАРЯД)	(tap LOAD)
завершение	completion
визит	visit
финал	final
Хлам продан: +	Scrap sold: +
Хлама нет	No scrap to sell
Трофеи проданы: +	Valuables sold: +
Трофеев нет	No valuables to sell
Куплен корабль:	Ship purchased:
O2 в кабине:	Cabin O2:
Авар. баллон:	Emergency tank:
Активные контракты	Active Contracts
Груз	Cargo
, деталь:	, part:
неизвестная станция	unknown station
ед.) на	units) to
Слетать в сектор	Fly to sector
Прибыть в сектор	Arrive in sector
Обломки 'Аргентины'	Wreck of the 'Argentina'
Заказ Лины	Lina's Order
Заряжено:	Loaded:
(урон	(damage
Авария:	Emergency:
Наведи курсор	Tap
Продажа	Sale
Предмет	Item
Квест завершён!	Quest complete!
Врата	Gates
Пустые врата	Empty Gates
Врата ->	Gates ->
Сюжетные задания	Story Quests
Сюжетное задание	Story Quest
Аварийный баллон	Emergency tank
Полный	Full
Нет	None
"""

for _line in _PAIRS.splitlines():
    if _line.strip():
        _source, _target = _line.split("\t", 1)
        _source = _source.replace("\\n", "\n")
        _target = _target.replace("\\n", "\n")
        _TRANSLATIONS[_source] = _target

_TRANSLATION_PATTERN = re.compile(
    "|".join(re.escape(text) for text in
             sorted(_TRANSLATIONS, key=len, reverse=True))
)
_TEMPLATED_TRANSLATIONS = []
for _source, _target in sorted(
        _TRANSLATIONS.items(), key=lambda pair: len(pair[0]), reverse=True):
    if "{" not in _source:
        continue
    _parts = re.split(r"(\{\w+\})", _source)
    _groups = {}
    _pattern_parts = []
    for _part in _parts:
        _placeholder = re.fullmatch(r"\{(\w+)\}", _part)
        if _placeholder:
            _group = f"value{len(_groups)}"
            _groups[_placeholder.group(1)] = _group
            _pattern_parts.append(f"(?P<{_group}>.+?)")
        else:
            _pattern_parts.append(re.escape(_part))
    _TEMPLATED_TRANSLATIONS.append(
        (re.compile("".join(_pattern_parts)), _target, _groups))


def get_language():
    return _LANGUAGE


def set_language(language):
    global _LANGUAGE
    if language not in ("ru", "en"):
        raise ValueError(f"Unsupported language: {language}")
    _LANGUAGE = language


def toggle_language():
    set_language("en" if _LANGUAGE == "ru" else "ru")
    return _LANGUAGE


def translate(text):
    if _LANGUAGE == "ru" or not isinstance(text, str):
        return text
    for _pattern, _target, _groups in _TEMPLATED_TRANSLATIONS:
        text = _pattern.sub(
            lambda match: re.sub(
                r"\{(\w+)\}",
                lambda placeholder: match.group(
                    _groups[placeholder.group(1)]),
                _target),
            text)
    return _TRANSLATION_PATTERN.sub(
        lambda match: _TRANSLATIONS[match.group(0)], text)
