# screens.py — экраны станции, магазина (купить/продать/верфь),
#              контрактов, ремонта, карты, сюжета.

import pygame
import math
import galaxy
from data import (UI_PANEL, UI_BORDER, UI_TEXT, UI_ACCENT, UI_OK,
                  UI_WARN, UI_DANGER, UI_DIM, S,
                  FUEL_MAX, O2_MAX, O2_RESERVE_MAX,
                  FUEL_PRICE_PER_UNIT, O2_RESERVE_REFILL_PRICE,
                  PARTS_DEF, PARTS_BY_ID, SYSTEM_SLOTS, SYSTEM_NAMES,
                  CARGO_BY_ID,
                  STATION_MENU_BUTTON_W, STATION_MENU_BUTTON_H,
                  CONTRACT_MAX_ACTIVE, CONTRACT_URGENT_DEADLINE)
from ships_data import SPACESHIPS, SHIPS_BY_ID
from ui import Button, draw_text, draw_panel, get_font
from localization import get_language, toggle_language, translate
from contracts import take_contract, generate_contracts_for_station


PAGE_MAIN = "main"
PAGE_SHOP = "shop"
PAGE_CONTRACTS = "contracts"
PAGE_ACTIVE = "active"
PAGE_DELIVER = "deliver"

UI_GREY_FALLBACK = (120, 120, 130)

# Колбэк для открытия StoryScreen
_story_screen_callback = None


def set_story_screen_callback(cb):
    global _story_screen_callback
    _story_screen_callback = cb


def format_time(sec):
    sec = int(sec)
    m = sec // 60
    s = sec % 60
    return f"{m}:{s:02d}"


# ============================================================
#                       STATION SCREEN
# ============================================================

class StationScreen:
    def __init__(self, station, systems, on_undock,
                 all_stations=None, state_ref=None,
                 current_sector_idx=0):
        self.station = station
        self.systems = systems
        self.on_undock = on_undock
        self.all_stations = all_stations or []
        self.state = state_ref
        self._current_sector_idx = current_sector_idx

        self.active = False
        self.page = PAGE_MAIN

        self.main_buttons = []
        self.shop_back_button = None
        self.shop_row_buttons = []
        self.shop_tab_buttons = []
        self.sell_row_buttons = []
        self.ship_buy_buttons = []
        self.ammo_buy_buttons = []
        self._build_ammo_buttons()

        self.contract_buttons = []
        self.active_contract_buttons = []
        self.deliver_buttons = []
        self.contracts_back_button = None
        self.contracts_deliver_button = None

        # Кнопки продажи хлама/трофеев
        self.sell_scrap_button = None
        self.sell_valuables_button = None
        self._build_sell_extra_buttons()

        self._build_main_buttons()
        self._build_shop_buttons()
        self._build_shop_tabs()
        self._build_contract_buttons()

        # Прокрутка магазина "buy"
        self.shop_scroll = 0.0
        self.shop_dragging = False
        self.shop_drag_last_y = 0
        self.shop_row_h = S(38)
        self.shop_row_gap = S(4)
        self.shop_content_height = len(PARTS_DEF) * (self.shop_row_h + self.shop_row_gap)
        self.shop_view_top = S(220)
        self.shop_view_bottom = S(700)

        # Вкладка магазина
        self.shop_tab = "buy"

        # Прокрутка магазина "sell"
        self.sell_scroll = 0.0
        self.sell_dragging = False
        self.sell_drag_last_y = 0

        self._ensure_contracts()

    def _ensure_contracts(self):
        now = self.state.game_time if self.state else 0
        need_gen = (
            not getattr(self.station, "contracts_ever_generated", False)
            or (now - getattr(self.station, "contracts_generated_time", 0) > 15 * 60)
        )
        active_taken = [c for c in self.station.contracts if c.taken]
        if self.station.contracts and len(active_taken) == len(self.station.contracts):
            need_gen = True

        if need_gen:
            import random
            rng = random.Random(hash(self.station.name) + int(now))
            generate_contracts_for_station(
                self.station, self.all_stations, rng, now)
            self.station.contracts_ever_generated = True
            self._rebuild_contract_buttons()

    def _build_main_buttons(self):
        w = S(STATION_MENU_BUTTON_W)
        h = S(STATION_MENU_BUTTON_H)
        x = S(60)
        y = S(160)
        gap = S(14)
        self.main_buttons = [
            Button((x, y, w, h), "Заправить бак",
                   self.buy_fuel, font_size=26),
            Button((x, y + (h + gap), w, h), "Пополнить аварийный O2",
                   self.refill_o2_reserve, font_size=22),
            Button((x, y + (h + gap) * 2, w, h), "Магазин деталей",
                   self.open_shop, font_size=26),
            Button((x, y + (h + gap) * 3, w, h), "Контракты",
                   self._open_contracts_or_deliver, font_size=26),
            Button((x, y + (h + gap) * 4, w, h), "СЮЖЕТ",
                   self._open_story, font_size=26),
            Button((x, y + (h + gap) * 5, w, h), "Отстыковаться",
                   self.undock, font_size=26),
        ]

    def _build_shop_buttons(self):
        self.shop_back_button = Button(
            (S(60), S(720), S(200), S(60)),
            "Назад", self.back_to_main, font_size=24)
        self.shop_row_buttons = []
        for row in PARTS_DEF:
            pid = row[0]
            cb = (lambda pid_=pid: self.buy_part(pid_))
            self.shop_row_buttons.append(
                Button((0, 0, S(120), S(30)), "Купить", cb, font_size=18))

    def _build_shop_tabs(self):
        w = S(180)
        h = S(50)
        x = S(60)
        y = S(120)
        gap = S(10)
        self.shop_tab_buttons = [
            Button((x, y, w, h), "Купить",
                   (lambda: self._set_shop_tab("buy")), font_size=22),
            Button((x + w + gap, y, w, h), "Продать",
                   (lambda: self._set_shop_tab("sell")), font_size=22),
            Button((x + (w + gap) * 2, y, w, h), "Верфь",
                   (lambda: self._set_shop_tab("shipyard")), font_size=22),
            Button((x + (w + gap) * 3, y, w, h), "Боеприпасы",
                   (lambda: self._set_shop_tab("ammo")), font_size=22),
        ]

    def _build_sell_extra_buttons(self):
        """Кнопки «Продать весь хлам» и «Продать все трофеи»."""
        # Y-координаты ниже списка деталей
        w = S(400)
        h = S(50)
        x = S(60)
        # Список деталей заканчивается на S(220) + N*(38+4), обычно N~5-15
        y = S(560)
        gap = S(12)

        self.sell_scrap_button = Button(
            (x, y, w, h), "Продать весь хлам",
            self._sell_all_scrap, font_size=22)
        self.sell_valuables_button = Button(
            (x, y + h + gap, w, h), "Продать все трофеи",
            self._sell_all_valuables, font_size=22)

    def _build_ammo_buttons(self):
        from data import AMMO_DEF
        self.ammo_buy_buttons = []
        w = S(120)
        h = S(30)
        x = S(1060)
        y_base = S(245)
        gap = S(70)
        for i, row in enumerate(AMMO_DEF):
            aid = row[0]
            cb = (lambda a=aid: self.buy_ammo_at(a))
            btn = Button((x, y_base + i * gap, w, h),
                         "Купить", cb, font_size=18)
            self.ammo_buy_buttons.append(btn)

    def buy_ammo_at(self, ammo_id):
        print(f"[AMMO] buy_ammo_at({ammo_id})")
        from data import AMMO_BY_ID
        info = AMMO_BY_ID.get(ammo_id)
        if info is None:
            print("[AMMO] info not found")
            return
        if self.systems.money < info["price"]:
            print(f"[AMMO] not enough money: {self.systems.money} < {info['price']}")
            return
        if self.systems.total_weight() + info["weight"] > self.systems.cargo_max:
            print("[AMMO] not enough cargo space")
            return
        self.systems.money -= info["price"]
        self.systems.add_ammo(ammo_id, 1)
        print(f"[AMMO] bought! now: {self.systems.ammo}")

    def _sell_all_scrap(self):
        total = self.systems.sell_all_scrap()
        if total > 0 and self.state:
            self.state.notify(f"Хлам продан: +{total} кр.")
        else:
            if self.state:
                self.state.notify("Хлама нет")

    def _sell_all_valuables(self):
        total = self.systems.sell_all_valuables()
        if total > 0 and self.state:
            self.state.notify(f"Трофеи проданы: +{total} кр.")
        else:
            if self.state:
                self.state.notify("Трофеев нет")

    def _set_shop_tab(self, tab):
        self.shop_tab = tab
        self.shop_scroll = 0.0
        self.sell_scroll = 0.0
        self.shop_dragging = False
        self.sell_dragging = False
        if tab == "sell":
            self._rebuild_sell_buttons()
        elif tab == "shipyard":
            self._rebuild_ship_buttons()
        elif tab == "ammo":
             self._build_ammo_buttons()

    def _build_contract_buttons(self):
        self.contracts_back_button = Button(
            (S(60), S(720), S(200), S(60)),
            "Назад", self.back_to_main, font_size=24)
        self._rebuild_contract_buttons()

    def _rebuild_contract_buttons(self):
        self.contract_buttons = []
        y = S(180)
        h = S(70)
        gap = S(8)
        x = S(60)
        w = S(1050)

        available = [c for c in self.station.contracts if not c.taken]
        for c in available:
            btn = Button((x, y, w, h), "", None, font_size=20)
            self.contract_buttons.append((c, btn))
            y += h + gap

        self.active_contract_buttons = []
        y = S(180)
        for c in self.systems.active_contracts:
            btn = Button((x, y, w, h), "", None, font_size=20)
            self.active_contract_buttons.append((c, btn))
            y += h + gap

        self.deliver_buttons = []
        y = S(180)
        for c in self.systems.active_contracts:
            if c.to_station is self.station:
                btn = Button((x, y, w, h), "", None, font_size=20)
                self.deliver_buttons.append((c, btn))
                y += h + gap

        self.contracts_deliver_button = Button(
            (S(60), S(640), S(400), S(60)),
            "Сдать все", self.deliver_contracts, font_size=24)

    # --- Услуги ---

    def buy_fuel(self):
        need = FUEL_MAX - self.systems.fuel
        if need <= 0.01:
            return
        cost = need * FUEL_PRICE_PER_UNIT
        if self.systems.money < cost:
            return
        self.systems.money -= cost
        self.systems.refuel()

    def refill_o2_reserve(self):
        need = O2_RESERVE_MAX - self.systems.o2_reserve
        if need <= 0.01:
            return
        cost = max(1, int(need * O2_RESERVE_REFILL_PRICE / O2_RESERVE_MAX))
        if self.systems.money < cost:
            return
        self.systems.money -= cost
        self.systems.refill_o2_reserve()

    def undock(self):
        self.active = False
        self.on_undock()

    # --- Навигация ---

    def open_shop(self):
        self.page = PAGE_SHOP
        self.shop_tab = "buy"
        self.shop_scroll = 0.0
        self.sell_scroll = 0.0
        self._rebuild_sell_buttons()
        self._rebuild_ship_buttons()
        self._build_ammo_buttons()

    def open_contracts(self):
        self.page = PAGE_CONTRACTS
        self._rebuild_contract_buttons()

    def open_active(self):
        self.page = PAGE_ACTIVE
        self._rebuild_contract_buttons()

    def open_deliver(self):
        self.page = PAGE_DELIVER
        self._rebuild_contract_buttons()

    def _open_contracts_or_deliver(self):
        can_deliver = len(self.systems.contracts_to_station(self.station))
        if can_deliver > 0:
            self.open_deliver()
        else:
            self.open_contracts()

    def back_to_main(self):
        self.page = PAGE_MAIN
        self.shop_dragging = False
        self.sell_dragging = False

    # --- Сюжет ---

    def _get_current_station_idx(self):
        if self.all_stations is None:
            return -1
        for i, st in enumerate(self.all_stations):
            if st is self.station:
                return i
        return -1

    def _open_story(self):
        from quests_data import STORY_QUESTS

        sector_idx = self._current_sector_idx
        station_idx = self._get_current_station_idx()
        if station_idx < 0:
            if self.state:
                self.state.notify("Ошибка: станция не найдена")
            return

        story = self.systems.story_manager

        for aq in story.active.values():
            q = aq.data
            if (q["giver_sector"] == sector_idx
                    and q["giver_station"] == station_idx):
                if aq.state == "ready_to_turn_in":
                    self._open_story_screen(aq.quest_id, mode="turn_in")
                    return

        story.recompute_available()
        for qid in story.available:
            for q in STORY_QUESTS:
                if q["id"] != qid:
                    continue
                if (q["giver_sector"] == sector_idx
                        and q["giver_station"] == station_idx):
                    self._open_story_screen(qid, mode="intro")
                    return

        if self.state:
            self.state.notify("Нет доступных сюжетных заданий")

    def _open_story_screen(self, quest_id, mode):
        global _story_screen_callback
        if _story_screen_callback is not None:
            _story_screen_callback(quest_id, mode)

    # --- Магазин: покупка ---

    def buy_part(self, pid):
        info = PARTS_BY_ID[pid]
        if self.systems.money < info["price"]:
            return
        if not self.systems.add_new_part(pid):
            return
        self.systems.money -= info["price"]

    def _max_scroll(self):
        view_h = self.shop_view_bottom - self.shop_view_top
        return max(0.0, self.shop_content_height - view_h)

    def _max_sell_scroll(self):
        # Секция деталей: от S(245) до S(540)
        view_h = S(540) - S(245)
        total_h = len(self.systems.inventory) * (self.shop_row_h + self.shop_row_gap)
        return max(0.0, total_h - view_h)

    # --- Магазин: продажа ---

    def _rebuild_sell_buttons(self):
        self.sell_row_buttons = []
        w = S(140)
        h = S(30)
        x = S(1060)
        y = self.shop_view_top
        for i, part in enumerate(self.systems.inventory):
            cb = (lambda idx=i: self._sell_part_at(idx))
            btn = Button((x, y, w, h), "Продать", cb, font_size=18)
            self.sell_row_buttons.append(btn)
            y += self.shop_row_h + self.shop_row_gap

    def _sell_part_at(self, index):
        price = self.systems.sell_part_at(index)
        if price > 0 and self.state:
            self.state.notify(f"Продано за {price} кр.")
        self._rebuild_sell_buttons()

    # --- Магазин: верфь ---

    def _rebuild_ship_buttons(self):
        self.ship_buy_buttons = []
        w = S(180)
        h = S(50)
        x = S(900)
        y = self.shop_view_top + S(20)
        gap = S(90)
        for i, ship in enumerate(SPACESHIPS):
            cb = (lambda sid=ship["id"]: self.buy_ship_at(sid))
            btn = Button((x, y, w, h), "Купить", cb, font_size=20)
            self.ship_buy_buttons.append(btn)
            y += gap

    def buy_ship_at(self, ship_id):
        ok = self.systems.buy_ship(ship_id)
        if ok:
            if self.state:
                name = SHIPS_BY_ID[ship_id]["name"]
                self.state.notify(f"Куплен корабль: {name}")
            self._rebuild_ship_buttons()
        else:
            if self.state:
                self.state.notify("Не хватает денег или трюм не влезет")

    # --- Контракты ---

    def take_contract_action(self, contract):
        now = self.state.game_time if self.state else 0
        if not self.systems.can_add_cargo(contract.cargo_weight):
            if self.state:
                self.state.notify("Трюм полон")
            return
        if len(self.systems.active_contracts) >= CONTRACT_MAX_ACTIVE:
            if self.state:
                self.state.notify("Слишком много активных контрактов")
            return
        take_contract(contract, now, self.systems.active_contracts)
        if self.state:
            self.state.notify(f"Взято: {contract.cargo_name} -> {contract.to_station.name}")
        self._rebuild_contract_buttons()

    def deliver_contracts(self):
        if not self.deliver_buttons:
            return
        now = self.state.game_time if self.state else 0
        total = self.systems.complete_contracts_to_station(self.station, now)
        if total > 0 and self.state:
            self.state.notify(f"Доставлено! +{total} кр.")
        self._rebuild_contract_buttons()
        self.page = PAGE_MAIN

    # --- События ---

    def handle_event(self, event):
        if self.page == PAGE_MAIN:
            for b in self.main_buttons:
                if b.handle_event(event):
                    return
            return

        if self.page == PAGE_SHOP:
            for b in self.shop_tab_buttons:
                if b.handle_event(event):
                    return
            if self.shop_tab == "shipyard":
                for b in self.ship_buy_buttons:
                    if b.handle_event(event):
                        return
                self.shop_back_button.handle_event(event)
                return
            if self.shop_tab == "ammo":
                for b in self.ammo_buy_buttons:
                    if b.handle_event(event):
                        return
                self.shop_back_button.handle_event(event)
                return
            # Вкладка "Продать": сначала кнопки хлама/трофеев
            if self.shop_tab == "sell":
                if self.sell_scrap_button.handle_event(event):
                    return
                if self.sell_valuables_button.handle_event(event):
                    return
            self._handle_shop_event(event)
            return
            # Вкладка "Купить": кнопки боеприпасов
            if self.shop_tab == "buy":
                for b in self.ammo_buy_buttons:
                    if b.handle_event(event):
                        return
            self._handle_shop_event(event)
            return

        if self.page == PAGE_CONTRACTS:
            if self.contracts_back_button.handle_event(event):
                return
            self._handle_contract_list_click(event, self.contract_buttons, take=True)
            return

        if self.page == PAGE_ACTIVE:
            if self.contracts_back_button.handle_event(event):
                return
            return

        if self.page == PAGE_DELIVER:
            if self.contracts_back_button.handle_event(event):
                return
            if self.contracts_deliver_button.handle_event(event):
                return
            return

    def _handle_contract_list_click(self, event, pairs, take=False):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for c, btn in pairs:
                if btn.rect.collidepoint(event.pos):
                    if take:
                        self.take_contract_action(c)
                    return

    def _handle_shop_event(self, event):
        # Кнопки "Продать" — только на вкладке sell
        if self.shop_tab == "sell":
            for b in self.sell_row_buttons:
                if b.handle_event(event):
                    return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.shop_view_top <= pos[1] <= self.shop_view_bottom:
                if self.shop_tab == "buy":
                    if not self._point_in_any_buy_button(pos):
                        self.shop_dragging = True
                        self.shop_drag_last_y = pos[1]
                        return
                else:  # sell
                    # Зона скролла деталей — S(245) до S(540)
                    if not (S(245) <= pos[1] <= S(540)):
                        return
                    hit = False
                    for b in self.sell_row_buttons:
                        if b.rect.collidepoint(pos):
                            hit = True
                            break
                    if not hit:
                        self.sell_dragging = True
                        self.sell_drag_last_y = pos[1]
                        return
        elif event.type == pygame.MOUSEMOTION:
            if self.shop_dragging:
                dy = event.pos[1] - self.shop_drag_last_y
                self.shop_drag_last_y = event.pos[1]
                self.shop_scroll -= dy
                self.shop_scroll = max(0.0, min(self._max_scroll(), self.shop_scroll))
                return
            if self.sell_dragging:
                dy = event.pos[1] - self.sell_drag_last_y
                self.sell_drag_last_y = event.pos[1]
                self.sell_scroll -= dy
                self.sell_scroll = max(0.0, min(self._max_sell_scroll(), self.sell_scroll))
                return
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.shop_dragging:
                self.shop_dragging = False
                return
            if self.sell_dragging:
                self.sell_dragging = False
                return

        if self.shop_back_button.handle_event(event):
            return

        if self.shop_tab == "buy":
            for b in self.shop_row_buttons:
                if b.handle_event(event):
                    return

    def _point_in_any_buy_button(self, pos):
        for b in self.shop_row_buttons:
            if b.rect.collidepoint(pos):
                return True
        return False

    def refresh_button_states(self):
        if self.page != PAGE_MAIN:
            return
        need_fuel = FUEL_MAX - self.systems.fuel
        cost_fuel = need_fuel * FUEL_PRICE_PER_UNIT if need_fuel > 0.01 else 0
        self.main_buttons[0].text = f"Заправить ({int(cost_fuel)} кр.)"
        need_res = O2_RESERVE_MAX - self.systems.o2_reserve
        if need_res > 0.01:
            cost_res = max(1, int(need_res * O2_RESERVE_REFILL_PRICE / O2_RESERVE_MAX))
            self.main_buttons[1].text = f"Аварийный O2 ({cost_res} кр.)"
        else:
            self.main_buttons[1].text = "Аварийный O2 (полный)"

        available = len([c for c in self.station.contracts if not c.taken])
        active = len(self.systems.active_contracts)
        can_deliver = len(self.systems.contracts_to_station(self.station))

        if can_deliver > 0:
            self.main_buttons[3].text = f"Сдать контракты ({can_deliver})"
        elif active > 0:
            self.main_buttons[3].text = f"Контракты (взято {active})"
        else:
            self.main_buttons[3].text = f"Контракты ({available})"

    # --- Отрисовка ---

    def draw(self, surface, screen_w, screen_h):
        overlay = pygame.Surface((screen_w, screen_h))
        overlay.set_alpha(180)
        overlay.fill((8, 10, 22))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(S(40), S(60), screen_w - S(80), screen_h - S(120))
        draw_panel(surface, panel)
        if self.page == PAGE_MAIN:
            self._draw_main(surface, panel)
        elif self.page == PAGE_SHOP:
            self._draw_shop(surface, panel)
        elif self.page == PAGE_CONTRACTS:
            self._draw_contracts(surface, panel)
        elif self.page == PAGE_ACTIVE:
            self._draw_active(surface, panel)
        elif self.page == PAGE_DELIVER:
            self._draw_deliver(surface, panel)

    def _draw_main(self, surface, panel):
        draw_text(surface, f"Станция: {self.station.name}",
                  (panel.x + S(20), panel.y + S(16)),
                  size=36, color=UI_ACCENT)
        draw_text(surface, f"Кредиты: {int(self.systems.money)}",
                  (panel.x + S(20), panel.y + S(70)),
                  size=28, color=UI_OK)

        info_x = panel.x + S(460)
        info_y = panel.y + S(160)
        draw_text(surface, f"Топливо: {self.systems.fuel:5.1f} / {FUEL_MAX}",
                  (info_x, info_y), size=24, color=UI_TEXT)
        gen_alive = self.systems.systems["o2gen"].is_functional
        o2_color = UI_OK if gen_alive else (
            UI_DANGER if self.systems.o2 < 30 else UI_WARN)
        draw_text(surface, f"O2 в кабине: {self.systems.o2:5.1f} / {O2_MAX}",
                  (info_x, info_y + S(30)), size=22, color=o2_color)
        res = self.systems.o2_reserve
        res_color = UI_OK if res > 50 else (UI_WARN if res > 20 else UI_DANGER)
        draw_text(surface, f"Авар. баллон: {res:5.1f} / {O2_RESERVE_MAX}",
                  (info_x, info_y + S(58)), size=22, color=res_color)

        y = info_y + S(110)
        draw_text(surface, "Состояние систем:", (info_x, y),
                  size=22, color=UI_TEXT)
        y += S(30)
        for sid in ("engine", "reactor", "o2gen", "hull"):
            s = self.systems.systems[sid]
            col = UI_OK if s.state == "ok" else (
                UI_WARN if s.state == "warn" else UI_DANGER)
            draw_text(surface,
                      f"{SYSTEM_NAMES[sid]}: {int(s.hp)} / {int(s.hp_max)}",
                      (info_x, y), size=22, color=col)
            y += S(26)

        w_parts = self.systems.inventory_weight_total()
        w_cargo = self.systems.cargo_weight()
        w_total = w_parts + w_cargo
        cargo_max = self.systems.cargo_max
        col_w = UI_OK if w_total < cargo_max * 0.9 else UI_WARN
        draw_text(surface,
                  f"Трюм: {w_total:.1f} / {cargo_max:.0f}",
                  (info_x, panel.bottom - S(50)), size=20, color=col_w)

        # Текущий корабль
        ship = SHIPS_BY_ID.get(self.systems.ship_type, None)
        if ship is not None:
            draw_text(surface, f"Корабль: {ship['name']}",
                      (panel.x + S(20), panel.y + S(120)),
                      size=22, color=UI_ACCENT)

        for b in self.main_buttons:
            b.draw(surface)

    def _draw_shop(self, surface, panel):
        draw_text(surface, f"Магазин — {self.station.name}",
                  (panel.x + S(20), panel.y + S(14)),
                  size=30, color=UI_ACCENT)
        draw_text(surface, f"Кредиты: {int(self.systems.money)}",
                  (panel.x + S(20), panel.y + S(60)),
                  size=24, color=UI_OK)
        weight = self.systems.total_weight()
        cargo_max = self.systems.cargo_max
        col_w = UI_OK if weight < cargo_max * 0.9 else UI_WARN
        draw_text(surface,
                  f"Трюм: {weight:.1f} / {cargo_max:.0f}",
                  (panel.x + S(320), panel.y + S(60)),
                  size=24, color=col_w)

        # Вкладки
        for i, b in enumerate(self.shop_tab_buttons):
            tab_name = ["buy", "sell", "shipyard", "ammo"][i]
            b.color = UI_ACCENT if self.shop_tab == tab_name else UI_PANEL
            b.draw(surface)

        if self.shop_tab == "buy":
            self._draw_shop_buy(surface, panel)
        elif self.shop_tab == "sell":
            self._draw_shop_sell(surface, panel)
        elif self.shop_tab == "shipyard":
            self._draw_shop_shipyard(surface, panel)
        elif self.shop_tab == "ammo":
            self._draw_shop_ammo(surface, panel)

        self.shop_back_button.draw(surface)

    def _draw_shop_buy(self, surface, panel):
        y = S(190)
        draw_text(surface, "Группа", (S(60), y), size=18, color=UI_WARN)
        draw_text(surface, "Название", (S(280), y), size=18, color=UI_WARN)
        draw_text(surface, "Цена", (S(600), y), size=18, color=UI_WARN)
        draw_text(surface, "Вес", (S(680), y), size=18, color=UI_WARN)
        draw_text(surface, "Трюм", (S(760), y), size=18, color=UI_WARN)
        pygame.draw.line(surface, UI_BORDER,
                         (S(60), S(212)), (S(1000), S(212)), max(1, S(1)))

        view_rect = pygame.Rect(0, S(220), surface.get_width(),
                                S(700) - S(220))
        prev_clip = surface.get_clip()
        surface.set_clip(view_rect)

        row_h = self.shop_row_h
        gap = self.shop_row_gap
        start_y = S(220) - self.shop_scroll
        weight = self.systems.total_weight()

        for i, row in enumerate(PARTS_DEF):
            pid = row[0]
            group = row[1]
            name = row[2]
            price = row[3]
            part_weight = row[4]

            ry = start_y + i * (row_h + gap)
            if ry + row_h < S(220) - row_h or ry > S(700) + row_h:
                continue

            in_inv = sum(1 for p in self.systems.inventory if p.part_id == pid)
            afford = self.systems.money >= price
            fits = weight + part_weight <= self.systems.cargo_max
            color = UI_TEXT if (afford and fits) else UI_GREY_FALLBACK

            draw_text(surface, group, (S(60), ry + S(8)), size=18, color=color)
            draw_text(surface, name, (S(280), ry + S(8)), size=18, color=color)
            draw_text(surface, f"{price}", (S(600), ry + S(8)), size=18, color=color)
            draw_text(surface, f"{part_weight:.1f}", (S(680), ry + S(8)),
                      size=18, color=color)
            draw_text(surface, f"{in_inv}", (S(760), ry + S(8)), size=18,
                      color=UI_ACCENT if in_inv else color)

            btn = self.shop_row_buttons[i]
            buy_w = S(120)
            buy_h = S(30)
            btn.rect = pygame.Rect(S(1060), int(ry + (row_h - buy_h) // 2),
                                   buy_w, buy_h)
            btn.draw(surface)

        surface.set_clip(prev_clip)

        max_scroll = self._max_scroll()
        if max_scroll > 0.5:
            track_x = S(1230)
            track_top = S(220)
            track_bottom = S(700)
            track_h = track_bottom - track_top
            pygame.draw.rect(surface, (40, 40, 60),
                             (track_x, track_top, S(6), track_h),
                             border_radius=S(3))
            thumb_h = max(S(30), int(track_h * (track_h / self.shop_content_height)))
            t = self.shop_scroll / max_scroll
            thumb_y = track_top + int((track_h - thumb_h) * t)
            pygame.draw.rect(surface, UI_ACCENT,
                             (track_x, thumb_y, S(6), thumb_h),
                             border_radius=S(3))

    def _draw_shop_sell(self, surface, panel):
        # ===== Секция 1: Детали =====
        draw_text(surface, "ДЕТАЛИ", (S(60), S(190)),
                  size=20, color=UI_ACCENT)

        y = S(220)
        draw_text(surface, "Название", (S(60), y), size=16, color=UI_WARN)
        draw_text(surface, "HP", (S(380), y), size=16, color=UI_WARN)
        draw_text(surface, "Цена", (S(500), y), size=16, color=UI_WARN)
        draw_text(surface, "Вес", (S(700), y), size=16, color=UI_WARN)
        pygame.draw.line(surface, UI_BORDER,
                         (S(60), y + S(20)), (S(1000), y + S(20)),
                         max(1, S(1)))

        view_rect = pygame.Rect(0, S(245), surface.get_width(), S(540) - S(245))
        prev_clip = surface.get_clip()
        surface.set_clip(view_rect)

        self._rebuild_sell_buttons()

        row_h = self.shop_row_h
        gap = self.shop_row_gap
        start_y = S(245) - self.sell_scroll

        if not self.systems.inventory:
            draw_text(surface, "Трюм пуст.",
                      (S(60), S(260)), size=18, color=UI_DIM)
        else:
            for i, part in enumerate(self.systems.inventory):
                ry = start_y + i * (row_h + gap)
                if ry + row_h < S(245) - row_h or ry > S(540) + row_h:
                    continue

                price = self.systems.part_sell_price(part)

                draw_text(surface, part.name, (S(60), ry + S(8)),
                          size=16, color=UI_TEXT)
                draw_text(surface, f"{int(part.hp)}/{int(part.hp_max)}",
                          (S(380), ry + S(8)), size=16, color=UI_TEXT)
                draw_text(surface, f"{price}", (S(500), ry + S(8)),
                          size=16, color=UI_OK)
                draw_text(surface, f"{part.weight:.1f}", (S(700), ry + S(8)),
                          size=16, color=UI_DIM)

                btn = self.sell_row_buttons[i]
                buy_w = S(120)
                buy_h = S(28)
                btn.rect = pygame.Rect(S(820), int(ry + (row_h - buy_h) // 2),
                                       buy_w, buy_h)
                btn.draw(surface)

        surface.set_clip(prev_clip)

        # ===== Секция 2: Хлам =====
        y = S(555)
        pygame.draw.line(surface, UI_BORDER,
                         (S(60), y), (S(1000), y), max(1, S(2)))

        scrap_w = self.systems.scrap_weight()
        scrap_v = self.systems.scrap_value()
        col = UI_TEXT if scrap_v > 0 else UI_DIM
        draw_text(surface, f"Хлам: {scrap_w:.1f} кг  /  {scrap_v} кр.",
                  (S(500), y + S(10)), size=20, color=col)

        # ===== Секция 3: Трофеи =====
        y2 = S(605)
        pygame.draw.line(surface, UI_BORDER,
                         (S(60), y2), (S(1000), y2), max(1, S(2)))

        val_w = self.systems.valuables_weight()
        val_v = self.systems.valuables_value()
        col2 = UI_WARN if val_v > 0 else UI_DIM
        draw_text(surface, f"Трофеи: {val_w:.1f} кг  /  {val_v} кр.",
                  (S(500), y2 + S(10)), size=20, color=col2)

        # Кнопки
        self.sell_scrap_button.draw(surface)
        self.sell_valuables_button.draw(surface)

        # Скролл-бар для секции деталей
        max_scroll = self._max_sell_scroll()
        if max_scroll > 0.5:
            track_x = S(1230)
            track_top = S(245)
            track_bottom = S(540)
            track_h = track_bottom - track_top
            pygame.draw.rect(surface, (40, 40, 60),
                             (track_x, track_top, S(6), track_h),
                             border_radius=S(3))
            total_h = len(self.systems.inventory) * (row_h + gap)
            thumb_h = max(S(30), int(track_h * (track_h / max(total_h, 1))))
            t = self.sell_scroll / max_scroll
            thumb_y = track_top + int((track_h - thumb_h) * t)
            pygame.draw.rect(surface, UI_ACCENT,
                             (track_x, thumb_y, S(6), thumb_h),
                             border_radius=S(3))

    def _draw_shop_shipyard(self, surface, panel):
        y = S(190)
        draw_text(surface, "Корабль", (S(60), y), size=18, color=UI_WARN)
        draw_text(surface, "Трюм", (S(320), y), size=18, color=UI_WARN)
        draw_text(surface, "Скорость", (S(420), y), size=18, color=UI_WARN)
        draw_text(surface, "Расход", (S(560), y), size=18, color=UI_WARN)
        draw_text(surface, "Цена", (S(680), y), size=18, color=UI_WARN)
        pygame.draw.line(surface, UI_BORDER,
                         (S(60), S(212)), (S(1000), S(212)), max(1, S(1)))

        self._rebuild_ship_buttons()

        current_type = self.systems.ship_type
        y = self.shop_view_top + S(20)
        row_h = S(90)

        for i, ship in enumerate(SPACESHIPS):
            sid = ship["id"]
            is_current = (sid == current_type)

            bg_col = (40, 80, 40) if is_current else UI_PANEL
            pygame.draw.rect(surface, bg_col,
                             (S(60), y - S(6), S(1080), S(70)),
                             border_radius=S(8))
            pygame.draw.rect(surface, UI_BORDER,
                             (S(60), y - S(6), S(1080), S(70)),
                             width=max(1, S(2)), border_radius=S(8))

            draw_text(surface, ship["name"], (S(80), y),
                      size=22, color=UI_ACCENT)
            draw_text(surface, f"{int(ship['cargo_max'])}",
                      (S(320), y), size=20, color=UI_TEXT)
            draw_text(surface, f"{int(ship['speed_mult']*100)}%",
                      (S(420), y), size=20, color=UI_TEXT)
            draw_text(surface, f"{int(ship['fuel_mult']*100)}%",
                      (S(560), y), size=20, color=UI_TEXT)

            price_text = "— стартовый —" if ship["price"] == 0 else f"{ship['price']} кр."
            price_col = UI_OK if ship["price"] == 0 else (
                UI_TEXT if self.systems.money >= ship["price"] else UI_DIM)
            draw_text(surface, price_text, (S(680), y), size=20, color=price_col)

            draw_text(surface, ship["description"], (S(80), y + S(28)),
                      size=16, color=UI_DIM)

            if is_current:
                draw_text(surface, "— ВЫ ЗДЕСЬ —",
                          (S(900), y + S(20)),
                          size=20, color=UI_OK)
            else:
                btn = self.ship_buy_buttons[i]
                btn.rect = pygame.Rect(S(900), y + S(6), S(180), S(50))
                btn.draw(surface)

            y += row_h

    def _draw_shop_ammo(self, surface, panel):
        from data import AMMO_DEF

        y = S(190)
        draw_text(surface, "Название", (S(60), y), size=18, color=UI_WARN)
        draw_text(surface, "Цена", (S(400), y), size=18, color=UI_WARN)
        draw_text(surface, "Вес", (S(550), y), size=18, color=UI_WARN)
        draw_text(surface, "В трюме", (S(700), y), size=18, color=UI_WARN)
        pygame.draw.line(surface, UI_BORDER,
                         (S(60), S(212)), (S(1200), S(212)), max(1, S(1)))

        y = S(230)
        for i, row in enumerate(AMMO_DEF):
            aid, name, price, weight = row
            afford = self.systems.money >= price
            fits = (self.systems.total_weight() + weight
                    <= self.systems.cargo_max)
            color = UI_TEXT if (afford and fits) else UI_GREY_FALLBACK
            have = self.systems.ammo.get(aid, 0)

            # Фон
            pygame.draw.rect(surface, (28, 34, 52),
                             (S(60), y, S(1150), S(60)),
                             border_radius=S(6))

            draw_text(surface, name, (S(80), y + S(18)),
                      size=20, color=color)
            draw_text(surface, f"{price} кр.", (S(400), y + S(18)),
                      size=20, color=color)
            draw_text(surface, f"{weight:.1f}", (S(550), y + S(18)),
                      size=20, color=color)
            draw_text(surface, f"x{have}", (S(700), y + S(18)),
                      size=20, color=UI_ACCENT if have else color)

            # Кнопка
            btn = self.ammo_buy_buttons[i]
            btn.rect = pygame.Rect(S(1060), y + S(15),
                                   S(120), S(30))
            btn.draw(surface)

            y += S(70)

        self.shop_back_button.draw(surface)

    def _draw_contract_row(self, surface, x, y, w, h, contract, now,
                           show_from=True, dim=False):
        col_bg = UI_PANEL if not contract.urgent else (60, 40, 40)
        if dim:
            col_bg = (col_bg[0] // 2, col_bg[1] // 2, col_bg[2] // 2)
        pygame.draw.rect(surface, col_bg, (x, y, w, h), border_radius=S(8))
        pygame.draw.rect(surface, UI_BORDER, (x, y, w, h),
                         width=max(1, S(2)), border_radius=S(8))

        pad = S(14)
        draw_text(surface, contract.cargo_name, (x + pad, y + S(10)),
                  size=22, color=UI_ACCENT)
        draw_text(surface, f"Вес: {contract.cargo_weight:.1f}",
                  (x + pad, y + S(38)), size=18, color=UI_DIM)

        mid_x = x + S(360)
        if show_from:
            draw_text(surface, f"Из: {contract.from_station.name}",
                      (mid_x, y + S(10)), size=20, color=UI_TEXT)
            draw_text(surface, f"В: {contract.to_station.name}",
                      (mid_x, y + S(36)), size=20, color=UI_OK)
        else:
            draw_text(surface, f"В: {contract.to_station.name}",
                      (mid_x, y + S(10)), size=20, color=UI_OK)
            if contract.urgent and contract.deadline_time is not None:
                left = contract.time_left(now)
                late = contract.is_late(now)
                col = UI_DANGER if late else UI_WARN
                label = "ПРОСРОЧЕН" if late else f"Осталось: {format_time(left)}"
                draw_text(surface, label, (mid_x, y + S(36)),
                          size=20, color=col)

        reward = contract.current_reward(now)
        right_x = x + w - S(300)
        draw_text(surface, f"{reward} кр.", (right_x, y + S(10)),
                  size=24, color=UI_OK)
        if contract.urgent:
            draw_text(surface, "СРОЧНЫЙ", (right_x, y + S(40)),
                      size=18, color=UI_WARN)

    def _draw_contracts(self, surface, panel):
        draw_text(surface, f"Контракты — {self.station.name}",
                  (panel.x + S(20), panel.y + S(14)),
                  size=30, color=UI_ACCENT)
        draw_text(surface,
                  f"Активных: {len(self.systems.active_contracts)} / {CONTRACT_MAX_ACTIVE}",
                  (panel.x + S(20), panel.y + S(60)),
                  size=22, color=UI_TEXT)
        draw_text(surface, f"Кредиты: {int(self.systems.money)}",
                  (panel.x + S(420), panel.y + S(60)),
                  size=22, color=UI_OK)

        now = self.state.game_time if self.state else 0
        if not self.contract_buttons:
            draw_text(surface, "Нет доступных контрактов.",
                      (S(60), S(200)), size=24, color=UI_DIM)
        else:
            for c, btn in self.contract_buttons:
                x, y, w, h = btn.rect
                self._draw_contract_row(surface, x, y, w, h, c, now,
                                        show_from=True)
                take_btn = Button(
                    (x + w - S(160), y + (h - S(40)) // 2, S(140), S(40)),
                    "Взять", (lambda c_=c: self.take_contract_action(c_)),
                    font_size=20)
                take_btn.draw(surface)

        self.contracts_back_button.draw(surface)

    def _draw_active(self, surface, panel):
        draw_text(surface, "Активные контракты",
                  (panel.x + S(20), panel.y + S(14)),
                  size=30, color=UI_ACCENT)
        now = self.state.game_time if self.state else 0

        if not self.active_contract_buttons:
            draw_text(surface, "Нет активных контрактов.",
                      (S(60), S(200)), size=24, color=UI_DIM)
        else:
            for c, btn in self.active_contract_buttons:
                x, y, w, h = btn.rect
                self._draw_contract_row(surface, x, y, w, h, c, now,
                                        show_from=False)

        self.contracts_back_button.draw(surface)

    def _draw_deliver(self, surface, panel):
        draw_text(surface, f"Сдать контракты — {self.station.name}",
                  (panel.x + S(20), panel.y + S(14)),
                  size=30, color=UI_ACCENT)
        draw_text(surface, f"Можно сдать: {len(self.deliver_buttons)}",
                  (panel.x + S(20), panel.y + S(60)),
                  size=22, color=UI_TEXT)
        now = self.state.game_time if self.state else 0

        total_reward = 0
        for c, btn in self.deliver_buttons:
            total_reward += c.current_reward(now)
            x, y, w, h = btn.rect
            self._draw_contract_row(surface, x, y, w, h, c, now,
                                    show_from=False)

        draw_text(surface, f"Итого: {total_reward} кр.",
                  (S(60), S(560)), size=28, color=UI_OK)

        if self.deliver_buttons:
            self.contracts_deliver_button.draw(surface)
        self.contracts_back_button.draw(surface)


# ============================================================
#                       REPAIR SCREEN
# ============================================================

class RepairScreen:
    def __init__(self, systems, on_close):
        self.systems = systems
        self.on_close = on_close
        self.active = False

        self.back_button = Button(
            (S(60), S(720), S(200), S(60)),
            "Закрыть", self.close, font_size=24)

        self.system_buttons = []
        ids = ["engine", "reactor", "o2gen", "hull", "weapon", "shield"]
        for i, sid in enumerate(ids):
            cb = (lambda sid_=sid: self.select_system(sid_))
            btn = Button((S(60), S(160) + i * S(70), S(420), S(60)),
                         "", cb, font_size=22)
            self.system_buttons.append((sid, btn))

        self.selected_system = None
        self.selected_slot = None

        self.slot_buttons = []
        self.action_buttons = []

    def open(self):
        self.active = True
        self.selected_system = None
        self.selected_slot = None
        self._rebuild_slots()

    def close(self):
        self.active = False
        self.on_close()

    def select_system(self, sid):
        self.selected_system = sid
        self.selected_slot = None
        self._rebuild_slots()
        self._rebuild_actions()

    def select_slot(self, index):
        if self.selected_system is None:
            return
        self.selected_slot = index
        self._rebuild_actions()

    def _rebuild_slots(self):
        self.slot_buttons = []
        if self.selected_system is None:
            return
        sys = self.systems.systems[self.selected_system]
        for i, slot in enumerate(sys.slots):
            cb = (lambda i_=i: self.select_slot(i_))
            btn = Button((S(560), S(160) + i * S(70), S(660), S(60)),
                         "", cb, font_size=20)
            self.slot_buttons.append((i, btn))

    def _rebuild_actions(self):
        self.action_buttons = []
        if self.selected_system is None or self.selected_slot is None:
            return
        sys = self.systems.systems[self.selected_system]
        slot = sys.slots[self.selected_slot]
        if slot.part is not None:
            self.action_buttons.append(
                Button((S(60), S(400), S(200), S(50)),
                       "Вынуть", self.action_remove, font_size=20))
        if self.systems.find_part_in_inventory(slot.required_part_id,
                                                by_tier=True) is not None:
            self.action_buttons.append(
                Button((S(60), S(460), S(300), S(50)),
                       "Поставить из трюма", self.action_install,
                       font_size=20))

    def action_remove(self):
        if self.selected_system is None or self.selected_slot is None:
            return
        ok = self.systems.remove_part_from_system(
            self.selected_system, self.selected_slot)
        if ok:
            self._rebuild_slots()
            self._rebuild_actions()

    def action_install(self):
        if self.selected_system is None or self.selected_slot is None:
            return
        ok = self.systems.install_part_into_system(
            self.selected_system, self.selected_slot)
        if ok:
            self._rebuild_slots()
            self._rebuild_actions()

    def handle_event(self, event):
        if not self.active:
            return
        if self.back_button.handle_event(event):
            return
        for sid, b in self.system_buttons:
            if b.handle_event(event):
                return
        for i, b in self.slot_buttons:
            if b.handle_event(event):
                return
        for b in self.action_buttons:
            if b.handle_event(event):
                return

    def draw(self, surface, screen_w, screen_h):
        overlay = pygame.Surface((screen_w, screen_h))
        overlay.set_alpha(190)
        overlay.fill((8, 10, 22))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(S(40), S(60), screen_w - S(80), screen_h - S(120))
        draw_panel(surface, panel)

        draw_text(surface, "Ремонт",
                  (panel.x + S(20), panel.y + S(14)),
                  size=34, color=UI_ACCENT)

        weight = self.systems.inventory_weight_total()
        cargo_max = self.systems.cargo_max
        col_w = UI_OK if weight < cargo_max * 0.9 else UI_WARN
        draw_text(surface,
                  f"Трюм: {weight:.1f} / {cargo_max:.0f}",
                  (panel.x + S(400), panel.y + S(20)),
                  size=22, color=col_w)

        draw_text(surface, "Системы:", (S(60), S(130)),
                  size=20, color=UI_WARN)
        for sid, btn in self.system_buttons:
            s = self.systems.systems[sid]
            btn.color = UI_ACCENT if sid == self.selected_system else UI_PANEL
            btn.text = f"{SYSTEM_NAMES[sid]}   {int(s.hp)} / {int(s.hp_max)}"
            col_state = UI_OK if s.state == "ok" else (
                UI_WARN if s.state == "warn" else UI_DANGER)
            btn.text_color = UI_TEXT
            btn.draw(surface)
            bar_y = btn.rect.bottom - S(6)
            bar_w = btn.rect.w
            bar_h = S(4)
            pygame.draw.rect(surface, (40, 40, 60),
                             (btn.rect.x, bar_y, bar_w, bar_h))
            fill = int(bar_w * s.hp_pct)
            pygame.draw.rect(surface, col_state,
                             (btn.rect.x, bar_y, fill, bar_h))

        if self.selected_system is None:
            draw_text(surface, "Выбери систему слева",
                      (S(560), S(200)), size=22, color=UI_DIM)
        else:
            draw_text(surface,
                      f"Слоты: {SYSTEM_NAMES[self.selected_system]}",
                      (S(560), S(130)), size=20, color=UI_WARN)
            for i, btn in self.slot_buttons:
                slot = self.systems.systems[self.selected_system].slots[i]
                btn.color = UI_ACCENT if i == self.selected_slot else UI_PANEL
                if slot.part is None:
                    btn.text = f"[Пусто]   нужна: {PARTS_BY_ID[slot.required_part_id]['name']}"
                    btn.text_color = UI_DIM
                else:
                    p = slot.part
                    broken = " (СЛОМАНО)" if p.is_broken() else ""
                    btn.text = f"{p.name}   {int(p.hp)}/{int(p.hp_max)}{broken}"
                    if p.is_broken():
                        btn.text_color = UI_DANGER
                    else:
                        btn.text_color = UI_TEXT
                btn.draw(surface)

            for b in self.action_buttons:
                b.draw(surface)

        draw_text(surface, "Тап по слоту -> действия",
                  (S(560), S(500)), size=18, color=UI_DIM)

        self.back_button.draw(surface)


# ============================================================
#              ACTIVE CONTRACTS SCREEN
# ============================================================

class ActiveContractsScreen:
    def __init__(self, systems, on_close, state_ref=None):
        self.systems = systems
        self.on_close = on_close
        self.state = state_ref
        self.active = False
        self.back_button = Button(
            (S(60), S(720), S(200), S(60)),
            "Закрыть", self.close, font_size=24)

    def open(self):
        self.active = True

    def close(self):
        self.active = False
        self.on_close()

    def handle_event(self, event):
        if not self.active:
            return
        self.back_button.handle_event(event)

    def draw(self, surface, screen_w, screen_h):
        overlay = pygame.Surface((screen_w, screen_h))
        overlay.set_alpha(190)
        overlay.fill((8, 10, 22))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(S(40), S(60), screen_w - S(80), screen_h - S(120))
        draw_panel(surface, panel)

        draw_text(surface, "Активные контракты",
                  (panel.x + S(20), panel.y + S(14)),
                  size=34, color=UI_ACCENT)

        now = self.state.game_time if self.state else 0
        contracts = self.systems.active_contracts

        if not contracts:
            draw_text(surface, "Нет активных контрактов.",
                      (S(60), S(200)), size=24, color=UI_DIM)
        else:
            y = S(140)
            h = S(90)
            gap = S(10)
            x = S(60)
            w = panel.w - S(40)

            for c in contracts:
                col_bg = (60, 40, 40) if c.urgent else UI_PANEL
                pygame.draw.rect(surface, col_bg, (x, y, w, h),
                                 border_radius=S(8))
                pygame.draw.rect(surface, UI_BORDER, (x, y, w, h),
                                 width=max(1, S(2)), border_radius=S(8))

                draw_text(surface, c.cargo_name,
                          (x + S(16), y + S(12)),
                          size=24, color=UI_ACCENT)
                draw_text(surface, f"Вес: {c.cargo_weight:.1f}",
                          (x + S(16), y + S(48)),
                          size=18, color=UI_DIM)

                mid_x = x + S(400)
                draw_text(surface, f"Из: {c.from_station.name}",
                          (mid_x, y + S(12)),
                          size=20, color=UI_TEXT)
                draw_text(surface, f"Куда: {c.to_station.name}",
                          (mid_x, y + S(42)),
                          size=22, color=UI_OK)

                right_x = x + w - S(320)
                reward = c.current_reward(now)
                draw_text(surface, f"{reward} кр.",
                          (right_x, y + S(12)),
                          size=24, color=UI_OK)

                if c.urgent and c.deadline_time is not None:
                    left = c.time_left(now)
                    late = c.is_late(now)
                    col = UI_DANGER if late else UI_WARN
                    label = "ПРОСРОЧЕН" if late else f"Осталось: {format_time(left)}"
                    draw_text(surface, label, (right_x, y + S(48)),
                              size=20, color=col)
                else:
                    draw_text(surface, "Без срока", (right_x, y + S(48)),
                              size=18, color=UI_DIM)

                y += h + gap

        self.back_button.draw(surface)


# ============================================================
#                    START MENU SCREEN
# ============================================================

class StartMenuScreen:
    def __init__(self, has_save, on_continue, on_new_game):
        self.active = True
        self.has_save = has_save
        self.on_continue = on_continue
        self.on_new_game = on_new_game
        self.buttons = []
        self.language_button = None

    def _toggle_language(self):
        language = toggle_language()
        self.language_button.text = (
            "Язык: English" if language == "ru" else "Language: Русский")

    def _build_buttons(self, screen_w, screen_h):
        w = S(400)
        h = S(80)
        x = screen_w // 2 - w // 2
        y = screen_h // 2 + S(20)
        gap = S(20)
        self.buttons = []
        if self.has_save:
            self.buttons.append(
                Button((x, y, w, h), "Продолжить",
                       self.continue_game, font_size=30))
            self.buttons.append(
                Button((x, y + h + gap, w, h), "Новая игра",
                       self.new_game, font_size=30))
        else:
            self.buttons.append(
                Button((x, y, w, h), "Начать игру",
                       self.new_game, font_size=30))
        self.language_button = Button(
            (screen_w - S(230), S(30), S(200), S(56)),
            "Язык: English" if get_language() == "ru"
            else "Language: Русский",
            self._toggle_language,
            font_size=20)
        self.buttons.append(self.language_button)

    def continue_game(self):
        self.active = False
        self.on_continue()

    def new_game(self):
        self.active = False
        self.on_new_game()

    def handle_event(self, event):
        for b in self.buttons:
            if b.handle_event(event):
                return

    def draw(self, surface, screen_w, screen_h):
        if not self.buttons:
            self._build_buttons(screen_w, screen_h)

        surface.fill((8, 10, 22))
        draw_text(surface, "SPACE EXPLORATION",
                  (screen_w // 2, screen_h // 3),
                  size=72, color=UI_ACCENT, center=True)
        draw_text(surface, "космические путешествия и торговля",
                  (screen_w // 2, screen_h // 3 + S(80)),
                  size=28, color=UI_DIM, center=True)

        for b in self.buttons:
            b.draw(surface)


# ============================================================
#                    GALAXY MAP SCREEN
# ============================================================

class GalaxyMapScreen:
    def __init__(self, galaxy_graph, visited_sectors,
                 current_sector_index, on_close, state_ref=None,
                 systems=None):
        self.galaxy_graph = galaxy_graph
        self.visited_sectors = visited_sectors
        self.current_sector_index = current_sector_index
        self.on_close = on_close
        self.state = state_ref
        self.systems = systems

        self.active = False
        self.close_button = Button(
            (S(60), S(720), S(200), S(60)),
            "Закрыть", self.close, font_size=24)

        self.positions = {}
        self.radius = {}
        self._compute_layout()

        self.cam_x = 0.0
        self.cam_y = 0.0
        self.dragging = False
        self.drag_last = (0, 0)
        self._pending_tap = None

        self.selected_sector = None

    def open(self):
        self.active = True
        self.selected_sector = None
        pos = self.positions.get(self.current_sector_index, (0, 0))
        self.cam_x = pos[0]
        self.cam_y = pos[1]
        self.dragging = False
        self._pending_tap = None

    def close(self):
        self.active = False
        self.on_close()

    def _compute_layout(self):
        import random as _r
        total = len(self.galaxy_graph)
        rng = _r.Random()
        pos = {}
        for i in range(total):
            angle = (i / total) * math.tau
            radius = 500 + rng.uniform(-100, 100)
            pos[i] = [math.cos(angle) * radius, math.sin(angle) * radius]

        K_REPEL = 150000.0
        K_SPRING = 0.08
        IDEAL_LEN = 260.0
        STEP = 0.1
        ITERATIONS = 300

        for _ in range(ITERATIONS):
            forces = {i: [0.0, 0.0] for i in range(total)}
            for i in range(total):
                for j in range(i + 1, total):
                    dx = pos[j][0] - pos[i][0]
                    dy = pos[j][1] - pos[i][1]
                    d2 = dx * dx + dy * dy + 0.01
                    d = math.sqrt(d2)
                    f = K_REPEL / d2
                    fx = (dx / d) * f
                    fy = (dy / d) * f
                    forces[i][0] -= fx
                    forces[i][1] -= fy
                    forces[j][0] += fx
                    forces[j][1] += fy
            for i, neighbors in self.galaxy_graph.items():
                for j in neighbors:
                    if j < i:
                        continue
                    dx = pos[j][0] - pos[i][0]
                    dy = pos[j][1] - pos[i][1]
                    d = math.sqrt(dx * dx + dy * dy) + 0.01
                    f = K_SPRING * (d - IDEAL_LEN)
                    fx = (dx / d) * f
                    fy = (dy / d) * f
                    forces[i][0] += fx
                    forces[i][1] += fy
                    forces[j][0] -= fx
                    forces[j][1] -= fy
            for i in range(total):
                pos[i][0] += forces[i][0] * STEP
                pos[i][1] += forces[i][1] * STEP

        self.positions = {i: (pos[i][0], pos[i][1]) for i in range(total)}
        for i in range(total):
            if i == self.current_sector_index:
                self.radius[i] = S(34)
            elif i in self.visited_sectors:
                self.radius[i] = S(24)
            else:
                self.radius[i] = S(18)

    def _world_to_screen(self, wx, wy, screen_w, screen_h):
        return (wx - self.cam_x) + screen_w / 2, \
               (wy - self.cam_y) + screen_h / 2

    def handle_event(self, event):
        if not self.active:
            return
        if self.close_button.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.rect.collidepoint(event.pos):
                return
            self.dragging = True
            self.drag_last = event.pos
            self._pending_tap = event.pos
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            dx = event.pos[0] - self.drag_last[0]
            dy = event.pos[1] - self.drag_last[1]
            self.cam_x -= dx
            self.cam_y -= dy
            self.drag_last = event.pos
            if abs(dx) > 3 or abs(dy) > 3:
                self._pending_tap = None
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging and self._pending_tap:
                self._on_tap(self._pending_tap)
            self.dragging = False
            self._pending_tap = None

    def _visible_sectors(self):
        visible = set(self.visited_sectors.keys())
        for idx in list(visible):
            for n in self.galaxy_graph.get(idx, []):
                visible.add(n)
        return visible

    def _on_tap(self, screen_pos):
        W, H = pygame.display.get_surface().get_size()
        mx = screen_pos[0] - W / 2 + self.cam_x
        my = screen_pos[1] - H / 2 + self.cam_y
        visible = self._visible_sectors()
        best = None
        best_d = None
        for idx, (wx, wy) in self.positions.items():
            if idx not in visible:
                continue
            d = math.hypot(wx - mx, wy - my)
            if d < self.radius.get(idx, S(20)) + S(15):
                if best_d is None or d < best_d:
                    best = idx
                    best_d = d
        if best is not None:
            self.selected_sector = best

    def draw(self, surface, screen_w, screen_h):
        surface.fill((8, 10, 22))
        visible = self._visible_sectors()

        drawn_edges = set()
        for i, neighbors in self.galaxy_graph.items():
            if i not in visible:
                continue
            for j in neighbors:
                if j not in visible:
                    continue
                edge = tuple(sorted((i, j)))
                if edge in drawn_edges:
                    continue
                drawn_edges.add(edge)
                if i not in self.positions or j not in self.positions:
                    continue
                x1, y1 = self.positions[i]
                x2, y2 = self.positions[j]
                sx1, sy1 = self._world_to_screen(x1, y1, screen_w, screen_h)
                sx2, sy2 = self._world_to_screen(x2, y2, screen_w, screen_h)
                if i in self.visited_sectors and j in self.visited_sectors:
                    col = (90, 170, 255)
                elif i in self.visited_sectors or j in self.visited_sectors:
                    col = (110, 110, 140)
                else:
                    col = (60, 60, 80)
                pygame.draw.line(surface, col, (sx1, sy1), (sx2, sy2),
                                 max(1, S(2)))

        for idx, (wx, wy) in self.positions.items():
            if idx not in visible:
                continue
            sx, sy = self._world_to_screen(wx, wy, screen_w, screen_h)
            if sx < -100 or sx > screen_w + 100 or sy < -100 or sy > screen_h + 100:
                continue
            r = self.radius[idx]
            is_visited = idx in self.visited_sectors
            is_current = idx == self.current_sector_index
            if is_current:
                col = (90, 170, 255)
                outline = (255, 255, 255)
            elif is_visited:
                col = (90, 210, 120)
                outline = (255, 255, 255)
            else:
                col = (90, 90, 110)
                outline = (140, 140, 160)
            pygame.draw.circle(surface, col, (int(sx), int(sy)), r)
            pygame.draw.circle(surface, outline, (int(sx), int(sy)), r,
                               max(2, S(2)))
            if is_visited or is_current:
                name = self._sector_name(idx)
                surf = get_font(S(20)).render(
                    translate(name), True, (240, 240, 240))
                rect = surf.get_rect(center=(sx, sy - r - S(14)))
                surface.blit(surf, rect)
            else:
                surf = get_font(S(24)).render("?", True, (240, 240, 240))
                rect = surf.get_rect(center=(sx, sy))
                surface.blit(surf, rect)

        if self.systems is not None:
            story = self.systems.story_manager
            sector_marks = {}
            story.recompute_available()
            from quests_data import STORY_QUESTS
            for qid in story.available:
                for q in STORY_QUESTS:
                    if q["id"] == qid:
                        sec = q["giver_sector"]
                        sector_marks.setdefault(sec, set()).add("!")
                        break
            for aq in story.active.values():
                obj = aq.objective
                if obj["type"] in ("deliver", "visit", "arrive"):
                    sec = obj["target_sector"]
                    if aq.state == "in_progress":
                        sector_marks.setdefault(sec, set()).add("*")
                if aq.state == "ready_to_turn_in":
                    q = aq.data
                    sec = q["giver_sector"]
                    sector_marks.setdefault(sec, set()).add("★")

            for idx, marks in sector_marks.items():
                if idx not in self.positions:
                    continue
                sx, sy = self._world_to_screen(
                    *self.positions[idx], screen_w, screen_h)
                r = self.radius.get(idx, S(20))
                if "!" in marks:
                    draw_text(surface, "!",
                              (int(sx) - S(8), int(sy) - r - S(38)),
                              size=38, color=(240, 180, 60))
                if "*" in marks:
                    draw_text(surface, "*",
                              (int(sx) + S(12), int(sy) - r - S(30)),
                              size=32, color=(240, 180, 60))
                if "★" in marks:
                    draw_text(surface, "★",
                              (int(sx) - S(12), int(sy) - r - S(30)),
                              size=32, color=(90, 210, 120))

        if self.selected_sector is not None:
            self._draw_info_panel(surface, screen_w, screen_h)

        self.close_button.draw(surface)

        hint = "Тащи пальцем чтобы сдвинуть. Тап по сектору — информация"
        surf = get_font(S(18)).render(
            translate(hint), True, (150, 150, 160))
        rect = surf.get_rect(midbottom=(screen_w // 2, screen_h - S(20)))
        surface.blit(surf, rect)

    def _sector_name(self, idx):
        return galaxy._sector_label(idx)

    def _draw_info_panel(self, surface, screen_w, screen_h):
        idx = self.selected_sector
        is_visited = idx in self.visited_sectors

        panel_w = S(420)
        panel_h = S(400)
        px = screen_w - panel_w - S(40)
        py = S(100)
        rect = pygame.Rect(px, py, panel_w, panel_h)
        draw_panel(surface, rect)

        name = self._sector_name(idx)
        title_col = UI_OK if is_visited else UI_DIM
        draw_text(surface, f"Сектор {name}",
                  (rect.x + S(16), rect.y + S(14)),
                  size=28, color=title_col)

        if not is_visited:
            draw_text(surface, "Не исследован.",
                      (rect.x + S(16), rect.y + S(70)),
                      size=22, color=UI_DIM)
            draw_text(surface, "Сначала нужно побывать здесь.",
                      (rect.x + S(16), rect.y + S(100)),
                      size=18, color=UI_DIM)
            return

        sec = self.visited_sectors[idx]
        draw_text(surface, f"Станций: {len(sec.stations)}",
                  (rect.x + S(16), rect.y + S(70)),
                  size=22, color=UI_TEXT)

        y = rect.y + S(110)
        for st in sec.stations:
            draw_text(surface, f"- {st.name}",
                      (rect.x + S(24), y), size=20, color=UI_ACCENT)
            y += S(28)

        y += S(20)
        draw_text(surface, "Соседние сектора:",
                  (rect.x + S(16), y), size=20, color=UI_WARN)
        y += S(30)
        neighbors = self.galaxy_graph.get(idx, [])
        if not neighbors:
            draw_text(surface, "— нет —",
                      (rect.x + S(24), y), size=18, color=UI_DIM)
        else:
            for n in neighbors:
                n_name = self._sector_name(n)
                n_visited = n in self.visited_sectors
                col = UI_OK if n_visited else UI_DIM
                mark = "" if n_visited else " (?)"
                draw_text(surface, f"> {n_name}{mark}",
                          (rect.x + S(24), y), size=18, color=col)
                y += S(24)


# ============================================================
#                    STORY SCREEN
# ============================================================

class StoryScreen:
    def __init__(self, quest_id, story_manager, systems, on_close,
                 mode="intro", state_ref=None, visited_sectors=None):
        self.quest_id = quest_id
        self.story_manager = story_manager
        self.systems = systems
        self.on_close = on_close
        self.mode = mode
        self.state = state_ref
        self.active = False
        self._visited_sectors = visited_sectors or {}

        from story import QUESTS_BY_ID
        self.quest_data = QUESTS_BY_ID[quest_id]

        self.buttons = []
        self._build_buttons()

    def _build_buttons(self):
        from pygame import display
        surf = display.get_surface()
        if surf is not None:
            sw, sh = surf.get_size()
        else:
            sw, sh = 1280, 800

        w = S(300)
        h = S(70)
        gap = S(20)
        total_w = w * 2 + gap
        cx = (sw // 2) - (total_w // 2) + S(200)
        y = sh - S(60) - h - S(40)

        if self.mode == "intro":
            self.buttons.append(
                Button((cx, y, w, h), "Принять задание",
                       self.accept_quest, font_size=24))
        elif self.mode == "turn_in":
            self.buttons.append(
                Button((cx, y, w, h), "Завершить",
                       self.turn_in_quest, font_size=24))

        self.buttons.append(
            Button((cx + w + gap, y, w, h), "Закрыть",
                   self.close, font_size=24))

    def open(self):
        self.active = True

    def close(self):
        self.active = False
        self.on_close()

    def accept_quest(self):
        self.story_manager.start_quest(self.quest_id)
        obj = self.quest_data.get("objective", {})
        if obj.get("type") == "deliver":
            cargo_name = obj.get("cargo_name", "Груз")
            cargo_weight = obj.get("cargo_weight", 1.0)
            self.systems.quest_cargo[self.quest_id] = {
                "cargo_name": cargo_name,
                "weight": cargo_weight,
                "collected": False,
                "auto_given": True,
            }
        if self.state:
            self.state.notify(f"Задание принято: {self.quest_data['title']}")
        self.close()

    def turn_in_quest(self):
        result = self.story_manager.complete_quest(self.quest_id, self.systems)
        if result and self.state:
            msg = f"Квест завершён! +{result['money']} кр."
            if result["part_id"]:
                msg += f", деталь: {result['part_id']}"
            self.state.notify(msg)
        self.close()

    def handle_event(self, event):
        if not self.active:
            return
        for b in self.buttons:
            if b.handle_event(event):
                return

    def draw(self, surface, screen_w, screen_h):
        overlay = pygame.Surface((screen_w, screen_h))
        overlay.set_alpha(200)
        overlay.fill((8, 10, 22))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(S(40), S(60), screen_w - S(80), screen_h - S(120))
        draw_panel(surface, panel)

        draw_text(surface, self.quest_data["title"],
                  (panel.x + S(20), panel.y + S(14)),
                  size=32, color=UI_ACCENT)

        portrait_w = S(220)
        portrait_h = S(280)
        portrait_x = panel.x + S(30)
        portrait_y = panel.y + S(90)
        pygame.draw.rect(surface, (100, 40, 140),
                         (portrait_x, portrait_y, portrait_w, portrait_h),
                         border_radius=S(10))
        pygame.draw.rect(surface, UI_BORDER,
                         (portrait_x, portrait_y, portrait_w, portrait_h),
                         width=max(1, S(2)), border_radius=S(10))

        giver = self.quest_data.get("giver_name", "???")
        draw_text(surface, giver,
                  (portrait_x + portrait_w // 2,
                   portrait_y + portrait_h + S(20)),
                  size=22, color=UI_ACCENT, center=True)

        if self.mode == "intro":
            lines = self.quest_data.get("dialogue_intro", [])
        else:
            lines = self.quest_data.get("dialogue_end", [])

        lines = [self._substitute(line) for line in lines]

        text_x = panel.x + S(300)
        text_y = panel.y + S(100)
        line_h = S(36)
        for line in lines:
            self._draw_wrapped(surface, line, text_x, text_y,
                               panel.w - S(340), line_h)
            text_y += line_h * self._estimate_lines(line, panel.w - S(340)) + S(10)

        if self.mode == "intro":
            obj = self.quest_data["objective"]
            info_y = panel.bottom - S(240)
            draw_text(surface, "Задание:",
                      (panel.x + S(30), info_y),
                      size=22, color=UI_WARN)
            info_y += S(34)

            obj_text = self._objective_text(obj)
            self._draw_wrapped(surface, obj_text,
                               panel.x + S(30), info_y,
                               panel.w - S(60), S(28))

            reward = self.quest_data.get("reward_money", 0)
            part_id = self.quest_data.get("reward_part", None)
            reward_y = panel.bottom - S(140)
            draw_text(surface, f"Награда: {reward} кр.",
                      (panel.x + S(30), reward_y),
                      size=22, color=UI_OK)
            if part_id:
                pname = PARTS_BY_ID.get(part_id, {}).get("name", part_id)
                draw_text(surface, f"Деталь: {pname}",
                          (panel.x + S(30), reward_y + S(30)),
                          size=22, color=UI_OK)

        for b in self.buttons:
            b.draw(surface)

    def _substitute(self, text):
        obj = self.quest_data.get("objective", {})
        giver_sector = self.quest_data.get("giver_sector", -1)
        giver_station = self.quest_data.get("giver_station", -1)
        target_sector = obj.get("target_sector", -1)
        target_station = obj.get("target_station", -1)

        next_id = self.quest_data.get("next", None)
        next_sector = -1
        next_station = -1
        if next_id:
            from quests_data import STORY_QUESTS
            for q in STORY_QUESTS:
                if q["id"] == next_id:
                    next_sector = q.get("giver_sector", -1)
                    next_station = q.get("giver_station", -1)
                    break

        return (text
                .replace("{giver_sector}", self._sector_label(giver_sector))
                .replace("{giver_station}", self._station_label(giver_sector, giver_station))
                .replace("{target_sector}", self._sector_label(target_sector))
                .replace("{target_station}", self._station_label(target_sector, target_station))
                .replace("{next_giver_sector}", self._sector_label(next_sector))
                .replace("{next_giver_station}", self._station_label(next_sector, next_station)))

    def _sector_label(self, idx):
        if idx < 0:
            return "???"
        return galaxy._sector_label(idx)

    def _station_label(self, sector_idx, station_idx):
        if sector_idx < 0 or station_idx < 0:
            return "???"
        sec = self._visited_sectors.get(sector_idx)
        if sec is None:
            return "неизвестная станция"
        if station_idx >= len(sec.stations):
            return "неизвестная станция"
        return sec.stations[station_idx].name

    def _objective_text(self, obj):
        t = obj["type"]
        if t == "deliver":
            target_name = self._station_label(obj.get("target_sector", -1),
                                              obj.get("target_station", -1))
            return (f"Доставить '{obj['cargo_name']}' "
                    f"({obj['cargo_weight']} ед.) на {target_name}.")
        elif t == "visit":
            sec_name = self._sector_label(obj.get("target_sector", -1))
            return (f"Слетать в сектор {sec_name}, "
                    f"найти объект '{obj.get('marker_name', '???')}' "
                    f"и вернуться.")
        elif t == "arrive":
            sec_name = self._sector_label(obj.get("target_sector", -1))
            return f"Прибыть в сектор {sec_name}."
        return "???"

    def _estimate_lines(self, text, max_w):
        text = translate(text)
        font = get_font(S(24))
        words = text.split()
        lines = 1
        cur = ""
        for w in words:
            test = cur + " " + w if cur else w
            if font.size(test)[0] > max_w:
                lines += 1
                cur = w
            else:
                cur = test
        return lines

    def _draw_wrapped(self, surface, text, x, y, max_w, line_h):
        text = translate(text)
        font = get_font(S(24))
        words = text.split()
        cur = ""
        cy = y
        for w in words:
            test = cur + " " + w if cur else w
            if font.size(test)[0] > max_w:
                surf = font.render(cur, True, UI_TEXT)
                surface.blit(surf, (x, cy))
                cy += line_h
                cur = w
            else:
                cur = test
        if cur:
            surf = font.render(cur, True, UI_TEXT)
            surface.blit(surf, (x, cy))

# ============================================================
#              CONFIRM ATTACK SCREEN
# ============================================================

class ConfirmAttackScreen:
    """Подтверждение атаки на мирный корабль или патруль."""

    def __init__(self, npc_name, on_confirm, on_cancel, state_ref=None):
        self.npc_name = npc_name
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.state = state_ref
        self.active = False
        self.buttons = []

    def open(self):
        self.active = True
        self._build_buttons()

    def close(self):
        self.active = False
        self.on_cancel()

    def _build_buttons(self):
        from pygame import display
        surf = display.get_surface()
        if surf is not None:
            sw, sh = surf.get_size()
        else:
            sw, sh = 1280, 800

        w = S(260)
        h = S(70)
        gap = S(30)
        total_w = w * 2 + gap
        cx = (sw // 2) - (total_w // 2)
        y = (sh // 2) + S(40)

        self.buttons = [
            Button((cx, y, w, h), "Атаковать",
                   self.confirm, font_size=24),
            Button((cx + w + gap, y, w, h), "Отмена",
                   self.cancel, font_size=24),
        ]

    def confirm(self):
        self.active = False
        self.on_confirm()

    def cancel(self):
        self.active = False
        self.on_cancel()

    def handle_event(self, event):
        if not self.active:
            return
        for b in self.buttons:
            if b.handle_event(event):
                return

    def draw(self, surface, screen_w, screen_h):
        # Полупрозрачный фон
        overlay = pygame.Surface((screen_w, screen_h))
        overlay.set_alpha(200)
        overlay.fill((8, 10, 22))
        surface.blit(overlay, (0, 0))

        # Панель
        panel_w = S(700)
        panel_h = S(280)
        px = (screen_w - panel_w) // 2
        py = (screen_h - panel_h) // 2
        rect = pygame.Rect(px, py, panel_w, panel_h)
        draw_panel(surface, rect)

        draw_text(surface, "ВНИМАНИЕ",
                  (rect.centerx, rect.y + S(30)),
                  size=34, color=UI_WARN, center=True)

        draw_text(surface,
                  f"Атаковать {self.npc_name}?",
                  (rect.centerx, rect.y + S(100)),
                  size=28, color=UI_TEXT, center=True)

        draw_text(surface,
                  "Это мирный корабль. Патрули объявят вас в розыск.",
                  (rect.centerx, rect.y + S(150)),
                  size=20, color=UI_DIM, center=True)

        for b in self.buttons:
            b.draw(surface)
            
# ============================================================
#                    INVENTORY SCREEN
# ============================================================

class InventoryScreen:
    """Экран инвентаря: детали, хлам, трофеи, грузы."""

    def __init__(self, systems, on_close, state_ref=None):
        self.systems = systems
        self.on_close = on_close
        self.state = state_ref
        self.active = False

        self.scroll = 0.0
        self.dragging = False
        self.drag_last_y = 0

        self.close_button = Button(
            (S(60), S(720), S(200), S(60)),
            "Закрыть", self.close, font_size=24)

        # Кэш строк для расчёта высоты и отрисовки
        self.rows = []          # список dict-строк
        self.row_h = S(52)
        self.row_gap = S(4)
        self.view_top = S(150)
        self.view_bottom = S(700)

    def open(self):
        self.active = True
        self.scroll = 0.0
        self.dragging = False
        self._rebuild_rows()

    def close(self):
        self.active = False
        self.on_close()

    def _rebuild_rows(self):
        """Строит плоский список строк для отрисовки."""
        rows = []
        systems = self.systems

        # === Детали ===
        if systems.inventory:
            rows.append({"kind": "header", "text": "ДЕТАЛИ", "color": UI_ACCENT})
            for i, part in enumerate(systems.inventory):
                sell_price = systems.part_sell_price(part)
                rows.append({
                    "kind": "part",
                    "part": part,
                    "name": part.name,
                    "hp": f"{int(part.hp)}/{int(part.hp_max)}",
                    "weight": f"{part.weight:.1f}",
                    "price": f"{sell_price} кр.",
                })

        # === Хлам ===
        if systems.scrap:
            rows.append({"kind": "header", "text": "ХЛАМ", "color": UI_WARN})
            from data import SCRAP_BY_ID
            for sid, cnt in systems.scrap.items():
                info = SCRAP_BY_ID.get(sid)
                if info is None:
                    continue
                total_w = info["weight"] * cnt
                total_p = info["price"] * cnt
                rows.append({
                    "kind": "item",
                    "name": info["name"],
                    "count": f"x{cnt}",
                    "weight": f"{total_w:.1f}",
                    "price": f"{total_p} кр.",
                })

        # === Трофеи ===
        if systems.valuables:
            rows.append({"kind": "header", "text": "ТРОФЕИ", "color": (240, 180, 60)})
            from data import VALUABLES_BY_ID
            for vid, cnt in systems.valuables.items():
                info = VALUABLES_BY_ID.get(vid)
                if info is None:
                    continue
                total_w = info["weight"] * cnt
                total_p = info["price"] * cnt
                rows.append({
                    "kind": "item",
                    "name": info["name"],
                    "count": f"x{cnt}",
                    "weight": f"{total_w:.1f}",
                    "price": f"{total_p} кр.",
                })

        # === Грузы контрактов ===
        if systems.active_contracts:
            rows.append({"kind": "header", "text": "ГРУЗЫ КОНТРАКТОВ", "color": UI_OK})
            for c in systems.active_contracts:
                rows.append({
                    "kind": "item",
                    "name": c.cargo_name,
                    "count": "x1",
                    "weight": f"{c.cargo_weight:.1f}",
                    "price": f"→ {c.to_station.name}",
                })

        # === Груз сюжетных квестов ===
        if systems.quest_cargo:
            rows.append({"kind": "header", "text": "СЮЖЕТНЫЙ ГРУЗ", "color": (240, 180, 60)})
            for qid, data in systems.quest_cargo.items():
                if data.get("collected"):
                    continue
                rows.append({
                    "kind": "item",
                    "name": data.get("cargo_name", qid),
                    "count": "x1",
                    "weight": f"{data.get('weight', 0):.1f}",
                    "price": "— квест —",
                })

        self.rows = rows

    def _max_scroll(self):
        view_h = self.view_bottom - self.view_top
        total_h = len(self.rows) * (self.row_h + self.row_gap)
        return max(0.0, total_h - view_h)

    def handle_event(self, event):
        if not self.active:
            return

        if self.close_button.handle_event(event):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.rect.collidepoint(event.pos):
                return
            if self.view_top <= event.pos[1] <= self.view_bottom:
                self.dragging = True
                self.drag_last_y = event.pos[1]
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            dy = event.pos[1] - self.drag_last_y
            self.drag_last_y = event.pos[1]
            self.scroll -= dy
            self.scroll = max(0.0, min(self._max_scroll(), self.scroll))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False

    def draw(self, surface, screen_w, screen_h):
        # Затемнение
        overlay = pygame.Surface((screen_w, screen_h))
        overlay.set_alpha(190)
        overlay.fill((8, 10, 22))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(S(40), S(60), screen_w - S(80), screen_h - S(120))
        draw_panel(surface, panel)

        # Заголовок
        draw_text(surface, "ИНВЕНТАРЬ",
                  (panel.x + S(20), panel.y + S(14)),
                  size=34, color=UI_ACCENT)

        # Вес
        w_cur = self.systems.total_weight()
        w_max = self.systems.cargo_max
        col_w = UI_OK if w_cur < w_max * 0.9 else UI_WARN
        draw_text(surface, f"Трюм: {w_cur:.1f} / {w_max:.0f}",
                  (panel.x + S(400), panel.y + S(20)),
                  size=26, color=col_w)

        # Деньги
        draw_text(surface, f"Кредиты: {int(self.systems.money)}",
                  (panel.x + S(800), panel.y + S(20)),
                  size=26, color=UI_OK)

        # Строки
        self._rebuild_rows()

        view_rect = pygame.Rect(0, self.view_top,
                                surface.get_width(),
                                self.view_bottom - self.view_top)
        prev_clip = surface.get_clip()
        surface.set_clip(view_rect)

        if not self.rows:
            draw_text(surface, "Трюм пуст.",
                      (S(80), self.view_top + S(40)),
                      size=24, color=UI_DIM)
        else:
            # Заголовки колонок (фиксированные)
            y_hdr = self.view_top - self.row_h - S(4) - self.scroll
            if -S(50) < y_hdr < self.view_bottom:
                if self.rows and any(r["kind"] != "header" for r in self.rows):
                    draw_text(surface, "Название", (S(80), y_hdr + S(14)),
                              size=18, color=UI_DIM)
                    draw_text(surface, "Кол-во", (S(560), y_hdr + S(14)),
                              size=18, color=UI_DIM)
                    draw_text(surface, "HP", (S(680), y_hdr + S(14)),
                              size=18, color=UI_DIM)
                    draw_text(surface, "Вес", (S(820), y_hdr + S(14)),
                              size=18, color=UI_DIM)
                    draw_text(surface, "Цена", (S(940), y_hdr + S(14)),
                              size=18, color=UI_DIM)

            start_y = self.view_top - self.scroll
            for i, row in enumerate(self.rows):
                ry = start_y + i * (self.row_h + self.row_gap)
                if ry + self.row_h < self.view_top - self.row_h:
                    continue
                if ry > self.view_bottom:
                    break

                if row["kind"] == "header":
                    # Заголовок секции
                    col = row.get("color", UI_WARN)
                    draw_text(surface, row["text"], (S(80), ry + S(12)),
                              size=22, color=col)
                    pygame.draw.line(surface, UI_BORDER,
                                     (S(80), ry + S(40)),
                                     (S(1200), ry + S(40)),
                                     max(1, S(1)))
                    continue

                # Обычная строка
                bg = (28, 34, 52)
                pygame.draw.rect(surface, bg,
                                 (S(70), ry, S(1150), self.row_h),
                                 border_radius=S(6))

                draw_text(surface, row["name"], (S(80), ry + S(14)),
                          size=20, color=UI_TEXT)
                draw_text(surface, row.get("count", ""),
                          (S(560), ry + S(14)), size=20, color=UI_TEXT)
                if "hp" in row:
                    draw_text(surface, row["hp"], (S(680), ry + S(14)),
                              size=20, color=UI_OK)
                draw_text(surface, row.get("weight", ""),
                          (S(820), ry + S(14)), size=20, color=UI_DIM)
                draw_text(surface, row.get("price", ""),
                          (S(940), ry + S(14)), size=20, color=UI_OK)

        surface.set_clip(prev_clip)

        # Скролл-бар
        max_scroll = self._max_scroll()
        if max_scroll > 0.5:
            track_x = S(1230)
            track_top = self.view_top
            track_bottom = self.view_bottom
            track_h = track_bottom - track_top
            pygame.draw.rect(surface, (40, 40, 60),
                             (track_x, track_top, S(6), track_h),
                             border_radius=S(3))
            total_h = len(self.rows) * (self.row_h + self.row_gap)
            thumb_h = max(S(30), int(track_h * (track_h / total_h)))
            t = self.scroll / max_scroll
            thumb_y = track_top + int((track_h - thumb_h) * t)
            pygame.draw.rect(surface, UI_ACCENT,
                             (track_x, thumb_y, S(6), thumb_h),
                             border_radius=S(3))

        self.close_button.draw(surface)
        
# ============================================================
#                    PROLOGUE SCREEN
# ============================================================

class PrologueScreen:
    """Пролог: 20 экранов с текстом и картинкой."""

    def __init__(self, on_finish):
        from data import PROLOGUE_PAGES
        self.pages = PROLOGUE_PAGES
        self.index = 0
        self.on_finish = on_finish
        self.active = False
        self._image_cache = {}

        # Кнопки
        self.next_button = Button(
            (0, 0, S(300), S(70)),
            "Далее →", self.next_page, font_size=26)
        self.skip_button = Button(
            (S(60), S(60), S(220), S(50)),
            "Пропустить", self.skip_all, font_size=20)
        self.start_button = Button(
            (0, 0, S(300), S(70)),
            "Начать игру", self.finish, font_size=26)
        self._layout_buttons()

    def _layout_buttons(self):
        from pygame import display
        surf = display.get_surface()
        if surf is not None:
            sw, sh = surf.get_size()
        else:
            sw, sh = 1280, 800
        bw, bh = S(300), S(70)
        # Кнопка «Далее» снизу справа
        self.next_button.rect = pygame.Rect(
            sw - bw - S(60), sh - bh - S(50), bw, bh)
        # Кнопка «Начать» — там же, но показывается на последней странице
        self.start_button.rect = self.next_button.rect

    def open(self):
        self.active = True
        self.index = 0

    def close(self):
        self.active = False

    def next_page(self):
        if self.index < len(self.pages) - 1:
            self.index += 1
        else:
            self.finish()

    def skip_all(self):
        self.finish()

    def finish(self):
        self.active = False
        self.on_finish()

    def _load_image(self, path):
        """Загружает картинку. Если нет — возвращает None."""
        if path in self._image_cache:
            return self._image_cache[path]
        try:
            img = pygame.image.load(path).convert()
            self._image_cache[path] = img
            return img
        except Exception:
            self._image_cache[path] = None
            return None

    def handle_event(self, event):
        if not self.active:
            return
        # Кнопки
        if self.next_button.handle_event(event):
            return
        if self.skip_button.handle_event(event):
            return
        # На последней — start_button
        if self.index == len(self.pages) - 1:
            if self.start_button.handle_event(event):
                return
        # Тап по экрану — тоже «Далее»
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Если попал в кнопки — уже обработано
            if self.next_button.rect.collidepoint(event.pos):
                return
            if self.skip_button.rect.collidepoint(event.pos):
                return
            if self.index == len(self.pages) - 1:
                if self.start_button.rect.collidepoint(event.pos):
                    return
            # Иначе — следующая страница
            self.next_page()

    def draw(self, surface, screen_w, screen_h):
        if not self.active:
            return

        page = self.pages[self.index]
        is_final = page.get("is_final", False)
        is_title = page.get("is_title", False)

        # === Фон ===
        img = self._load_image(page.get("image", ""))
        if img is not None:
            # Растягиваем под экран, сохраняя пропорции (заполняем)
            scaled = pygame.transform.smoothscale(img, (screen_w, screen_h))
            surface.blit(scaled, (0, 0))
        else:
            # Заглушка: тёмный градиент
            surface.fill((8, 10, 22))
            # Лёгкий градиент
            for i in range(0, screen_h, 4):
                alpha = int(30 * (i / screen_h))
                pygame.draw.rect(surface, (10 + alpha, 12 + alpha, 25 + alpha),
                                 (0, i, screen_w, 4))

        # === Прогресс: "N / 20" ===
        prog = get_font(S(22)).render(
            f"{self.index + 1} / {len(self.pages)}", True, (200, 200, 220))
        surface.blit(prog, (screen_w - prog.get_width() - S(30), S(30)))

        # === Текст ===
        title = page.get("title", "")
        text = page.get("text", "")

        if is_title:
            # Титул — крупно в центре
            font_title = get_font(S(72))
            surf = font_title.render(translate(title), True, (220, 230, 255))
            rect = surf.get_rect(center=(screen_w // 2, screen_h // 2 - S(40)))
            surface.blit(surf, rect)

            font_sub = get_font(S(36))
            surf2 = font_sub.render(translate(text), True, (160, 180, 220))
            rect2 = surf2.get_rect(center=(screen_w // 2, screen_h // 2 + S(50)))
            surface.blit(surf2, rect2)
            
        else:
            # Обычный экран — плашка с текстом снизу (в 2 раза ниже)
            pad = S(40)
            panel_h = S(140)   # было S(240) — уменьшили в 2 раза
            panel_y = screen_h - panel_h - S(140)
            panel_rect = pygame.Rect(pad, panel_y,
                                     screen_w - pad * 2, panel_h)

            # Полупрозрачная плашка
            overlay = pygame.Surface((panel_rect.w, panel_rect.h),
                                     pygame.SRCALPHA)
            overlay.fill((8, 10, 22, 200))
            surface.blit(overlay, panel_rect.topleft)
            pygame.draw.rect(surface, (70, 90, 130), panel_rect,
                             width=max(1, S(2)), border_radius=S(12))

            # Заголовок сцены
            draw_text(surface, title,
                      (panel_rect.x + S(20), panel_rect.y + S(14)),
                      size=28, color=(240, 180, 60))

            # Текст с переносом
            self._draw_wrapped(surface, text,
                               panel_rect.x + S(20),
                               panel_rect.y + S(70),
                               panel_rect.w - S(40),
                               S(36))

        # === Кнопки ===
        # «Пропустить» — всегда
        self.skip_button.draw(surface)

        # «Далее» или «Начать игру»
        if is_final:
            self.start_button.draw(surface)
        else:
            self.next_button.draw(surface)

    def _draw_wrapped(self, surface, text, x, y, max_w, line_h):
        text = translate(text)
        font = get_font(S(24))
        # Обрабатываем \n как принудительные переносы
        paragraphs = text.split("\n")
        cy = y
        for para in paragraphs:
            words = para.split()
            cur = ""
            for w in words:
                test = cur + " " + w if cur else w
                if font.size(test)[0] > max_w:
                    surf = font.render(cur, True, (220, 225, 235))
                    surface.blit(surf, (x, cy))
                    cy += line_h
                    cur = w
                else:
                    cur = test
            if cur:
                surf = font.render(cur, True, (220, 225, 235))
                surface.blit(surf, (x, cy))
                cy += line_h
                
# ============================================================
#                    LOAD MISSILE SCREEN
# ============================================================

class LoadMissileScreen:
    """Экран заряжания ракеты в пусковую установку."""

    def __init__(self, systems, on_close, state_ref=None):
        self.systems = systems
        self.on_close = on_close
        self.state = state_ref
        self.active = False

        from data import AMMO_DEF
        self.ammo_list = AMMO_DEF

        self.close_button = Button(
            (S(60), S(720), S(200), S(60)),
            "Закрыть", self.close, font_size=24)

        self.load_buttons = []
        self._build_buttons()

    def _build_buttons(self):
        from data import AMMO_BY_ID
        self.load_buttons = []
        w = S(240)
        h = S(60)
        x = S(900)
        y = S(250)
        gap = S(80)
        for i, row in enumerate(AMMO_DEF):
            aid = row[0]
            cb = (lambda a=aid: self.load_ammo(a))
            btn = Button((x, y + i * gap, w, h),
                         "Зарядить", cb, font_size=22)
            self.load_buttons.append(btn)

    def open(self):
        self.active = True

    def close(self):
        self.active = False
        self.on_close()

    def load_ammo(self, ammo_id):
        ok = self.systems.load_missile(ammo_id)
        if ok and self.state:
            from data import AMMO_BY_ID
            name = AMMO_BY_ID.get(ammo_id, {}).get("name", "Ракета")
            self.state.notify(f"Заряжено: {name}")
            self.close()

    def handle_event(self, event):
        if not self.active:
            return
        if self.close_button.handle_event(event):
            return
        for b in self.load_buttons:
            if b.handle_event(event):
                return

    def draw(self, surface, screen_w, screen_h):
        from data import AMMO_BY_ID
        overlay = pygame.Surface((screen_w, screen_h))
        overlay.set_alpha(200)
        overlay.fill((8, 10, 22))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(S(40), S(60), screen_w - S(80), screen_h - S(120))
        draw_panel(surface, panel)

        draw_text(surface, "ЗАРЯЖАНИЕ РАКЕТЫ",
                  (panel.x + S(20), panel.y + S(14)),
                  size=32, color=UI_ACCENT)

        # Текущая заряженная
        if self.systems.loaded_missile is not None:
            aid, dmg, spd = self.systems.loaded_missile
            name = AMMO_BY_ID.get(aid, {}).get("name", "Ракета")
            draw_text(surface, f"Заряжено: {name} (урон {int(dmg)})",
                      (panel.x + S(20), panel.y + S(60)),
                      size=24, color=UI_OK)
        else:
            draw_text(surface, "Пусковая пуста",
                      (panel.x + S(20), panel.y + S(60)),
                      size=24, color=UI_DIM)

        # Список ракет в трюме
        y = S(250)
        for i, row in enumerate(self.ammo_list):
            aid, name, price, weight = row
            have = self.systems.ammo.get(aid, 0)
            from data import MISSILE_PARAMS
            params = MISSILE_PARAMS.get(aid, {"damage": 40})
            dmg = int(params["damage"])

            color = UI_TEXT if have > 0 else UI_DIM

            draw_text(surface, name, (S(80), y + S(10)),
                      size=22, color=color)
            draw_text(surface, f"Урон: {dmg}", (S(450), y + S(10)),
                      size=20, color=color)
            draw_text(surface, f"В трюме: x{have}", (S(650), y + S(10)),
                      size=20, color=UI_ACCENT if have > 0 else color)

            # Кнопка — только если есть ракеты
            if have > 0:
                btn = self.load_buttons[i]
                btn.rect = pygame.Rect(S(900), y, S(240), S(60))
                btn.draw(surface)

            y += S(80)

        self.close_button.draw(surface)