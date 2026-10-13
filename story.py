# story.py — движок сюжетных квестов.

from quests_data import STORY_QUESTS


# Индексация для быстрого доступа по id
QUESTS_BY_ID = {q["id"]: q for q in STORY_QUESTS}


class ActiveQuest:
    """Копия квеста со текущим прогрессом."""

    def __init__(self, quest_id):
        self.quest_id = quest_id
        self.data = QUESTS_BY_ID[quest_id]
        self.state = "in_progress"   # in_progress | ready_to_turn_in
        # Для visit: отметка «побывал в секторе»
        self.visited_target = False
        # Для deliver: груз выдан игроку при взятии
        self.cargo_given = False

    @property
    def title(self):
        return self.data["title"]

    @property
    def objective(self):
        return self.data["objective"]

    @property
    def giver_name(self):
        return self.data["giver_name"]

    @property
    def reward_money(self):
        return self.data.get("reward_money", 0)

    @property
    def reward_part(self):
        return self.data.get("reward_part", None)

    def check_objective(self, current_sector, current_station,
                        ship_systems):
        """Проверяет, выполнено ли задание."""
        obj = self.objective
        t = obj["type"]

        if t == "deliver":
            # Нужно быть на целевой станции
            if (current_sector == obj["target_sector"]
                    and current_station is not None
                    and current_station == obj["target_station"]):
                # И груз должен быть у игрока
                # (проверку груза делает main при доставке)
                pass

        elif t == "visit":
            if current_sector == obj["target_sector"]:
                self.visited_target = True

        elif t == "arrive":
            if current_sector == obj["target_sector"]:
                self.state = "ready_to_turn_in"

        # Для deliver/visit — переходим в ready_to_turn_in только по завершении
        # В реальности это делает main.py, вызывая mark_objective_complete.

    def mark_complete(self):
        self.state = "ready_to_turn_in"


class StoryManager:
    def __init__(self):
        self.active = {}           # {quest_id: ActiveQuest}
        self.completed = set()     # завершённые id
        self.available = []        # доступные сейчас id

    # ---------- Доступность ----------

    def recompute_available(self):
        """Пересчитывает список доступных квестов."""
        self.available = []
        for q in STORY_QUESTS:
            qid = q["id"]
            if qid in self.completed:
                continue
            if qid in self.active:
                continue
            # Проверяем requirements
            reqs = q.get("requires", [])
            if all(r in self.completed for r in reqs):
                self.available.append(qid)

    def is_available_at(self, sector_idx, station_idx):
        """Возвращает квест, доступный в этой точке, или None."""
        self.recompute_available()
        for qid in self.available:
            q = QUESTS_BY_ID[qid]
            if (q["giver_sector"] == sector_idx
                    and q["giver_station"] == station_idx):
                return qid
        return None

    def get_active_in_progress(self):
        """Список активных квестов."""
        return list(self.active.values())

    def get_active_for_giver(self, sector_idx, station_idx):
        """Активные квесты, чей giver находится здесь."""
        result = []
        for aq in self.active.values():
            q = aq.data
            if (q["giver_sector"] == sector_idx
                    and q["giver_station"] == station_idx):
                result.append(aq)
        return result

    # ---------- Действия ----------

    def start_quest(self, quest_id):
        if quest_id in self.active or quest_id in self.completed:
            return None
        aq = ActiveQuest(quest_id)
        self.active[quest_id] = aq

        # Для deliver — сразу выдаём груз игроку
        if aq.objective["type"] == "deliver":
            aq.cargo_given = True

        self.recompute_available()
        return aq

    def complete_quest(self, quest_id, ship_systems):
        """Завершает квест, выдаёт награды."""
        if quest_id not in self.active:
            return None
        aq = self.active.pop(quest_id)
        self.completed.add(quest_id)

        # Деньги
        money = aq.reward_money
        if money:
            ship_systems.money += money

        # Деталь
        part_id = aq.reward_part
        part_added = False
        if part_id:
            part_added = ship_systems.add_new_part(part_id)

        self.recompute_available()

        return {
            "money": money,
            "part_id": part_id,
            "part_added": part_added,
            "next": aq.data.get("next", None),
        }

    # ---------- Сериализация ----------

    def to_dict(self):
        return {
            "active": {
                qid: {
                    "state": aq.state,
                    "visited_target": aq.visited_target,
                    "cargo_given": aq.cargo_given,
                }
                for qid, aq in self.active.items()
            },
            "completed": list(self.completed),
        }

    def apply_dict(self, d):
        self.active = {}
        self.completed = set(d.get("completed", []))

        for qid, aq_data in d.get("active", {}).items():
            if qid not in QUESTS_BY_ID:
                continue
            aq = ActiveQuest(qid)
            aq.state = aq_data.get("state", "in_progress")
            aq.visited_target = aq_data.get("visited_target", False)
            aq.cargo_given = aq_data.get("cargo_given", False)
            self.active[qid] = aq

        self.recompute_available()