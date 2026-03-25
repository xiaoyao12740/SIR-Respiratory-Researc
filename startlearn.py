import math
import random
import sys
import time
from collections import deque

import pygame

pygame.init()

WINDOW_W = 1280
WINDOW_H = 820
PANEL_W = 300
FPS = 60
BG = (20, 24, 32)
PANEL_BG = (46, 52, 64)
CARD = (58, 66, 80)
CARD2 = (70, 78, 95)
TEXT = (240, 242, 245)
SUBTEXT = (190, 198, 210)
WALL = (93, 97, 107)
FLOOR = (224, 224, 226)
FLOOR2 = (214, 214, 216)
GOAL = (241, 193, 67)
PLAYER = (88, 153, 255)
BOX = (190, 129, 64)
BOX_ON_GOAL = (228, 165, 89)
GREEN = (88, 191, 122)
RED = (214, 99, 99)
YELLOW = (225, 180, 75)
GRID_LINE = (176, 176, 176)

DIRS = {
    "上": (0, -1),
    "下": (0, 1),
    "左": (-1, 0),
    "右": (1, 0),
}
DIR_LIST = list(DIRS.values())

DIFF_CFG = {
    "简单": {
        "boxes": (1, 3),
        "sizes": {"小": (8, 8), "中": (9, 9), "大": (10, 10)},
        "obstacles": 2,
        "scramble": (32, 48),
        "style_bonus": {"开阔": 0, "均衡": 1, "曲折": 2},
    },
    "普通": {
        "boxes": (2, 4),
        "sizes": {"小": (9, 9), "中": (10, 10), "大": (11, 11)},
        "obstacles": 3,
        "scramble": (52, 76),
        "style_bonus": {"开阔": 0, "均衡": 2, "曲折": 4},
    },
    "困难": {
        "boxes": (3, 5),
        "sizes": {"小": (10, 10), "中": (11, 11), "大": (12, 12)},
        "obstacles": 4,
        "scramble": (78, 110),
        "style_bonus": {"开阔": 1, "均衡": 3, "曲折": 6},
    },
}

TEMPLATES = [
    [(0, 0)],
    [(0, 0), (1, 0)],
    [(0, 0), (0, 1)],
    [(0, 0), (1, 0), (0, 1)],
    [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (0, 1), (0, 2)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 0), (0, 1), (1, 1)],
]


def load_font(size):
    names = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "WenQuanYi Zen Hei",
        "Arial Unicode MS",
    ]
    for name in names:
        font = pygame.font.SysFont(name, size)
        if font:
            return font
    return pygame.font.Font(None, size)


class Button:
    def __init__(self, rect, text, callback, font, color=CARD2, hover=(98, 108, 128)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = font
        self.color = color
        self.hover_color = hover
        self.is_hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def draw(self, screen):
        color = self.hover_color if self.is_hover else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (20, 20, 20), self.rect, 2, border_radius=8)
        txt = self.font.render(self.text, True, TEXT)
        txt_rect = txt.get_rect(center=self.rect.center)
        screen.blit(txt, txt_rect)


class ChoiceGroup:
    def __init__(self, x, y, title, choices, current, font, on_change):
        self.x = x
        self.y = y
        self.title = title
        self.choices = list(choices)
        self.current = current
        self.font = font
        self.on_change = on_change
        self.buttons = []
        self._make_buttons()

    def _make_buttons(self):
        self.buttons = []
        bx = self.x
        by = self.y + 36
        for idx, ch in enumerate(self.choices):
            rect = pygame.Rect(bx + idx * 112, by, 98, 36)
            self.buttons.append((ch, rect))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for ch, rect in self.buttons:
                if rect.collidepoint(event.pos):
                    self.current = ch
                    self.on_change(ch)

    def draw(self, screen, title_font):
        title = title_font.render(self.title, True, TEXT)
        screen.blit(title, (self.x, self.y))
        for ch, rect in self.buttons:
            active = ch == self.current
            color = (103, 134, 200) if active else CARD
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, (18, 18, 18), rect, 2, border_radius=8)
            txt = self.font.render(ch, True, TEXT)
            screen.blit(txt, txt.get_rect(center=rect.center))


class GeneratorError(Exception):
    pass


class Generator:
    def __init__(self, width, height, box_count, difficulty, style, progress_cb=None):
        self.width = width
        self.height = height
        self.box_count = box_count
        self.difficulty = difficulty
        self.style = style
        self.progress_cb = progress_cb
        self.cfg = DIFF_CFG[difficulty]

    def report(self, ratio, stage, msg):
        if self.progress_cb:
            self.progress_cb(ratio, stage, msg)

    def build(self):
        attempts = 28
        for attempt in range(1, attempts + 1):
            self.report((attempt - 1) / attempts, "尝试", f"正在生成第 {attempt}/{attempts} 次尝试")
            try:
                level = self._try_build_once()
                self.report(1.0, "完成", "地图生成完成")
                return level
            except GeneratorError:
                continue
        return self._template_fallback()

    def _try_build_once(self):
        walls = self._outer_walls()
        self.report(0.08, "布局", "正在构建边界与活动区")
        self._place_obstacles(walls)
        free = self._largest_component(walls)
        if len(free) < self.box_count * 8 + 12:
            raise GeneratorError()

        good_cells = [c for c in free if self._is_good_floor(c, walls)]
        if len(good_cells) < self.box_count + 3:
            raise GeneratorError()

        self.report(0.25, "目标", "正在布置目标点")
        goals = self._pick_spread_cells(good_cells, self.box_count, min_dist=2)
        if goals is None:
            raise GeneratorError()

        player = self._pick_player_start(free, goals, walls)
        boxes = [tuple(g) for g in goals]
        moved_count = [0] * self.box_count

        scramble_steps = random.randint(*self.cfg["scramble"]) + self.cfg["style_bonus"][self.style] * 4
        if self.box_count >= 4:
            scramble_steps += 8
        reverse_actions = []
        seen_states = set()
        stagnant = 0

        self.report(0.38, "打乱", "正在逆向打乱箱子")
        for step in range(scramble_steps):
            progress = 0.38 + 0.42 * (step / max(1, scramble_steps))
            self.report(progress, "打乱", f"正在逆向打乱：{step + 1}/{scramble_steps}")
            action = self._random_reverse_action(player, boxes, walls, goals, moved_count)
            if action is None:
                stagnant += 1
                if stagnant > 18:
                    raise GeneratorError()
                continue
            stagnant = 0
            kind, dx, dy, box_idx = action
            if kind == "move":
                player = (player[0] + dx, player[1] + dy)
            else:
                old_player = player
                player = (player[0] + dx, player[1] + dy)
                boxes[box_idx] = old_player
                moved_count[box_idx] += 1
            reverse_actions.append((kind, dx, dy))
            state_key = (player, tuple(sorted(boxes)))
            if state_key in seen_states and step > scramble_steps * 0.65:
                break
            seen_states.add(state_key)

        initial_boxes = set(boxes)
        goals_set = set(goals)
        if len(initial_boxes) != self.box_count:
            raise GeneratorError()
        if all(m > 0 for m in moved_count) is False:
            raise GeneratorError()
        if initial_boxes & goals_set:
            raise GeneratorError()
        if sum(self._min_goal_dist(b, goals_set) for b in initial_boxes) < self.box_count * 2:
            raise GeneratorError()
        if self._too_trivial(initial_boxes, goals_set):
            raise GeneratorError()

        self.report(0.85, "验证", "正在验证标准解")
        solution = self._invert_reverse_actions(reverse_actions)
        if not self._validate_solution(player, initial_boxes, goals_set, walls, solution):
            raise GeneratorError()

        return {
            "width": self.width,
            "height": self.height,
            "walls": walls,
            "goals": goals_set,
            "player": player,
            "boxes": initial_boxes,
            "solution": solution,
            "difficulty": self.difficulty,
            "style": self.style,
            "size_label": self._size_label(),
            "recommended": self._size_label(),
            "warning": "",
        }

    def _size_label(self):
        for label, wh in self.cfg["sizes"].items():
            if wh == (self.width, self.height):
                return label
        return f"{self.width}×{self.height}"

    def _outer_walls(self):
        walls = set()
        for x in range(self.width):
            walls.add((x, 0))
            walls.add((x, self.height - 1))
        for y in range(self.height):
            walls.add((0, y))
            walls.add((self.width - 1, y))
        return walls

    def _place_obstacles(self, walls):
        target = self.cfg["obstacles"] + self.cfg["style_bonus"][self.style]
        if self.width >= 11 and self.height >= 11:
            target += 1
        tries = 0
        placed = 0
        while placed < target and tries < target * 18:
            tries += 1
            tpl = random.choice(TEMPLATES)
            ox = random.randint(2, self.width - 4)
            oy = random.randint(2, self.height - 4)
            cells = {(ox + dx, oy + dy) for dx, dy in tpl}
            if any(c[0] <= 1 or c[1] <= 1 or c[0] >= self.width - 2 or c[1] >= self.height - 2 for c in cells):
                continue
            if any(c in walls for c in cells):
                continue
            if any(self._touch_count(c, walls | cells) > 3 for c in cells):
                continue
            test_walls = walls | cells
            comp = self._largest_component(test_walls)
            if len(comp) < (self.width - 2) * (self.height - 2) * 0.55:
                continue
            walls.update(cells)
            placed += 1

    def _touch_count(self, cell, walls):
        x, y = cell
        count = 0
        for dx, dy in DIR_LIST:
            if (x + dx, y + dy) in walls:
                count += 1
        return count

    def _largest_component(self, walls):
        free = {(x, y) for x in range(1, self.width - 1) for y in range(1, self.height - 1) if (x, y) not in walls}
        if not free:
            return set()
        seen = set()
        best = set()
        for cell in free:
            if cell in seen:
                continue
            comp = set()
            dq = deque([cell])
            seen.add(cell)
            while dq:
                cx, cy = dq.popleft()
                comp.add((cx, cy))
                for dx, dy in DIR_LIST:
                    nb = (cx + dx, cy + dy)
                    if nb in free and nb not in seen:
                        seen.add(nb)
                        dq.append(nb)
            if len(comp) > len(best):
                best = comp
        return best

    def _is_good_floor(self, cell, walls):
        x, y = cell
        open_neighbors = 0
        for dx, dy in DIR_LIST:
            if (x + dx, y + dy) not in walls:
                open_neighbors += 1
        if open_neighbors <= 1:
            return False
        up = (x, y - 1) in walls
        down = (x, y + 1) in walls
        left = (x - 1, y) in walls
        right = (x + 1, y) in walls
        if (up or down) and (left or right):
            return False
        return True

    def _pick_spread_cells(self, cells, count, min_dist=2):
        shuffled = cells[:]
        random.shuffle(shuffled)
        chosen = []
        for cell in shuffled:
            if all(abs(cell[0] - c[0]) + abs(cell[1] - c[1]) >= min_dist for c in chosen):
                chosen.append(cell)
                if len(chosen) == count:
                    return chosen
        return None

    def _pick_player_start(self, free, goals, walls):
        candidates = [c for c in free if c not in goals and self._is_good_floor(c, walls)]
        candidates.sort(key=lambda c: min(abs(c[0] - g[0]) + abs(c[1] - g[1]) for g in goals))
        return random.choice(candidates[: max(6, min(20, len(candidates)))])

    def _random_reverse_action(self, player, boxes, walls, goals, moved_count):
        box_set = set(boxes)
        options = []
        pushy = []
        for dx, dy in DIR_LIST:
            np = (player[0] + dx, player[1] + dy)
            if np not in walls and np not in box_set:
                options.append(("move", dx, dy, None))
            back = (player[0] - dx, player[1] - dy)
            if np not in walls and np not in box_set and back in box_set:
                idx = boxes.index(back)
                pushy.append(("pull", dx, dy, idx))
        if pushy:
            # 优先拉动尚未移动过的箱子
            candidates = sorted(pushy, key=lambda it: (moved_count[it[3]], random.random()))
            if random.random() < 0.72:
                return candidates[0]
            return random.choice(pushy + options)
        if options:
            return random.choice(options)
        return None

    def _invert_reverse_actions(self, reverse_actions):
        solution = []
        for _, dx, dy in reversed(reverse_actions):
            solution.append((-dx, -dy))
        return solution

    def _min_goal_dist(self, box, goals):
        return min(abs(box[0] - gx) + abs(box[1] - gy) for gx, gy in goals)

    def _too_trivial(self, boxes, goals):
        same_row = len({b[1] for b in boxes}) == 1 and len({g[1] for g in goals}) == 1
        same_col = len({b[0] for b in boxes}) == 1 and len({g[0] for g in goals}) == 1
        if same_row or same_col:
            # 严格阻止“排排站直接平推”
            if sorted(b[0] for b in boxes) == sorted(g[0] for g in goals) or sorted(b[1] for b in boxes) == sorted(g[1] for g in goals):
                return True
        return False

    def _validate_solution(self, player, boxes, goals, walls, solution):
        sim = LevelRuntime(self.width, self.height, walls, goals, player, boxes, solution)
        for dx, dy in solution:
            if not sim.try_move(dx, dy, record=False):
                return False
        return sim.is_win()

    def _template_fallback(self):
        # 预制“保底但不白给”的模板，避免假困难和无解。
        w = max(self.width, 9)
        h = max(self.height, 9)
        walls = self._outer_walls()
        midx = w // 2
        midy = h // 2
        # 加几面短墙形成绕位要求
        extras = {(midx - 2, midy - 1), (midx - 2, midy), (midx + 2, midy), (midx + 2, midy + 1)}
        if self.box_count >= 4:
            extras |= {(midx, midy - 2), (midx, midy + 2)}
        walls |= {c for c in extras if 1 < c[0] < w - 2 and 1 < c[1] < h - 2}
        goals = set()
        boxes = set()
        row_g = 2
        row_b = h - 3
        cols = list(range(2, 2 + self.box_count))
        for i, x in enumerate(cols):
            goals.add((x, row_g + (i % 2)))
            boxes.add((w - 3 - i, row_b - (i % 2)))
        player = (2, h - 2)
        # 用一个小范围 BFS 求标准解；保底图规模不大，这里可接受。
        solution = fallback_solve(w, h, walls, goals, player, boxes)
        if solution is None:
            raise RuntimeError("保底模板求解失败")
        return {
            "width": w,
            "height": h,
            "walls": walls,
            "goals": goals,
            "player": player,
            "boxes": boxes,
            "solution": solution,
            "difficulty": self.difficulty,
            "style": self.style,
            "size_label": self._size_label(),
            "recommended": self._size_label(),
            "warning": "已启用保底模板关卡。",
        }


class LevelRuntime:
    def __init__(self, width, height, walls, goals, player, boxes, standard_solution=None):
        self.width = width
        self.height = height
        self.walls = set(walls)
        self.goals = set(goals)
        self.player_start = tuple(player)
        self.boxes_start = set(boxes)
        self.standard_solution = list(standard_solution or [])
        self.reset_all()

    def reset_all(self):
        self.player = self.player_start
        self.boxes = set(self.boxes_start)
        self.history = []
        self.moves = 0
        self.status = "准备开始"
        self.auto_mode = False
        self.auto_step = False
        self.auto_from_start = True
        self.play_queue = []
        self.play_index = 0
        self.last_play_time = 0

    def start_demo(self, step_mode=False):
        self.reset_for_demo()
        self.play_queue = list(self.standard_solution)
        self.play_index = 0
        self.auto_mode = True
        self.auto_step = step_mode
        self.last_play_time = 0
        self.status = "正在演示标准解" if not step_mode else "逐步演示已准备"

    def reset_for_demo(self):
        self.player = self.player_start
        self.boxes = set(self.boxes_start)
        self.history.clear()
        self.moves = 0
        self.auto_mode = False
        self.auto_step = False
        self.play_queue = []
        self.play_index = 0

    def stop_demo(self):
        self.auto_mode = False
        self.auto_step = False
        self.status = "已停止自动演示"

    def next_demo_step(self):
        if not self.auto_mode or not self.auto_step:
            return
        self._play_one()

    def update_demo(self):
        if not self.auto_mode or self.auto_step:
            return
        if self.is_win():
            self.auto_mode = False
            self.status = "演示完成，已通关"
            return
        now = time.time()
        if now - self.last_play_time >= 0.10:
            self.last_play_time = now
            self._play_one()

    def _play_one(self):
        if self.play_index >= len(self.play_queue):
            self.auto_mode = False
            self.status = "演示完成"
            return
        dx, dy = self.play_queue[self.play_index]
        ok = self.try_move(dx, dy, record=True)
        self.play_index += 1
        if not ok:
            self.auto_mode = False
            self.status = "演示中断：标准解执行失败"
            return
        if self.is_win():
            self.auto_mode = False
            self.status = "演示完成，已通关"

    def try_move(self, dx, dy, record=True):
        px, py = self.player
        np = (px + dx, py + dy)
        if np in self.walls:
            return False
        if np in self.boxes:
            bp = (np[0] + dx, np[1] + dy)
            if bp in self.walls or bp in self.boxes:
                return False
            if record:
                self.history.append((self.player, set(self.boxes), self.moves))
            self.boxes.remove(np)
            self.boxes.add(bp)
            self.player = np
            self.moves += 1
            self.status = "推动成功"
            return True
        if record:
            self.history.append((self.player, set(self.boxes), self.moves))
        self.player = np
        self.moves += 1
        self.status = "移动成功"
        return True

    def undo(self):
        if not self.history:
            self.status = "没有可以撤销的步骤"
            return
        self.player, self.boxes, self.moves = self.history.pop()
        self.auto_mode = False
        self.status = "已撤销一步"

    def is_win(self):
        return self.boxes == self.goals


class GameUI:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("推箱子 - pygame版")
        self.clock = pygame.time.Clock()
        self.font = load_font(24)
        self.small_font = load_font(20)
        self.big_font = load_font(36)
        self.huge_font = load_font(52)
        self.running = True
        self.state = "菜单"
        self.progress_ratio = 0.0
        self.progress_stage = ""
        self.progress_msg = ""
        self.warning = ""
        self.buttons = []
        self.groups = []
        self.level = None

        self.difficulty = "普通"
        self.size_mode = "推荐"
        self.size_label = "中"
        self.style = "均衡"
        self.map_w, self.map_h = DIFF_CFG[self.difficulty]["sizes"][self.size_label]
        self.box_count = 3
        self._clamp_boxes()
        self.build_menu()

    def _clamp_boxes(self):
        lo, hi = DIFF_CFG[self.difficulty]["boxes"]
        self.box_count = max(lo, min(hi, self.box_count))

    def build_menu(self):
        self.state = "菜单"
        self.buttons = [
            Button((520, 290, 240, 56), "开始游戏", self.open_settings, self.font),
            Button((520, 370, 240, 56), "操作说明", self.show_help, self.font),
            Button((520, 450, 240, 56), "退出游戏", self.quit_game, self.font),
        ]

    def open_settings(self):
        self.state = "设置"
        self.warning = ""
        self._build_settings_widgets()

    def _build_settings_widgets(self):
        self.buttons = []
        self.groups = []
        self.groups.append(ChoiceGroup(120, 120, "难度", ["简单", "普通", "困难"], self.difficulty, self.small_font, self.set_difficulty))
        self.groups.append(ChoiceGroup(120, 220, "地图模式", ["推荐", "自定义"], self.size_mode, self.small_font, self.set_size_mode))
        self.groups.append(ChoiceGroup(120, 320, "推荐尺寸", ["小", "中", "大"], self.size_label, self.small_font, self.set_size_label))
        self.groups.append(ChoiceGroup(120, 420, "地图风格", ["开阔", "均衡", "曲折"], self.style, self.small_font, self.set_style))

        self.buttons.extend([
            Button((620, 168, 52, 44), "-", self.decrease_boxes, self.font),
            Button((810, 168, 52, 44), "+", self.increase_boxes, self.font),
            Button((620, 268, 52, 44), "-", self.decrease_w, self.font),
            Button((810, 268, 52, 44), "+", self.increase_w, self.font),
            Button((620, 328, 52, 44), "-", self.decrease_h, self.font),
            Button((810, 328, 52, 44), "+", self.increase_h, self.font),
            Button((120, 630, 210, 52), "恢复推荐参数", self.restore_recommended, self.small_font),
            Button((390, 630, 180, 52), "生成地图", self.start_generate, self.small_font, color=(80, 128, 94), hover=(95, 152, 112)),
            Button((620, 630, 180, 52), "返回菜单", self.build_menu, self.small_font),
        ])
        self.update_warning()

    def set_difficulty(self, d):
        self.difficulty = d
        self._clamp_boxes()
        if self.size_mode == "推荐":
            self.map_w, self.map_h = DIFF_CFG[d]["sizes"][self.size_label]
        self.update_warning()

    def set_size_mode(self, mode):
        self.size_mode = mode
        if mode == "推荐":
            self.map_w, self.map_h = DIFF_CFG[self.difficulty]["sizes"][self.size_label]
        self.update_warning()

    def set_size_label(self, label):
        self.size_label = label
        if self.size_mode == "推荐":
            self.map_w, self.map_h = DIFF_CFG[self.difficulty]["sizes"][label]
        self.update_warning()

    def set_style(self, style):
        self.style = style
        self.update_warning()

    def decrease_boxes(self):
        lo, _ = DIFF_CFG[self.difficulty]["boxes"]
        self.box_count = max(lo, self.box_count - 1)
        self.update_warning()

    def increase_boxes(self):
        _, hi = DIFF_CFG[self.difficulty]["boxes"]
        self.box_count = min(hi, self.box_count + 1)
        self.update_warning()

    def decrease_w(self):
        if self.size_mode == "自定义":
            self.map_w = max(8, self.map_w - 1)
            self.update_warning()

    def increase_w(self):
        if self.size_mode == "自定义":
            self.map_w = min(13, self.map_w + 1)
            self.update_warning()

    def decrease_h(self):
        if self.size_mode == "自定义":
            self.map_h = max(8, self.map_h - 1)
            self.update_warning()

    def increase_h(self):
        if self.size_mode == "自定义":
            self.map_h = min(13, self.map_h + 1)
            self.update_warning()

    def restore_recommended(self):
        self.size_mode = "推荐"
        self.size_label = "中"
        self.map_w, self.map_h = DIFF_CFG[self.difficulty]["sizes"][self.size_label]
        for g in self.groups:
            if g.title == "地图模式":
                g.current = self.size_mode
            elif g.title == "推荐尺寸":
                g.current = self.size_label
        self.update_warning()

    def update_warning(self):
        if self.size_mode == "推荐":
            self.warning = "当前使用推荐尺寸，生成速度与可玩性更稳定。"
            return
        rw, rh = DIFF_CFG[self.difficulty]["sizes"][self.size_label]
        msgs = []
        if self.map_w > rw or self.map_h > rh:
            msgs.append("当前尺寸大于推荐值，生成可能稍慢。")
        if self.map_w < 8 or self.map_h < 8:
            msgs.append("尺寸太小会减少操作空间。")
        if self.box_count >= 5 and (self.map_w < 11 or self.map_h < 11):
            msgs.append("5个箱子建议至少使用 11×11 地图。")
        self.warning = " ".join(msgs) if msgs else "当前自定义参数可正常尝试生成。"

    def start_generate(self):
        self.state = "生成中"
        self.progress_ratio = 0.0
        self.progress_stage = "准备"
        self.progress_msg = "正在准备生成器..."
        pygame.display.flip()
        width, height = (self.map_w, self.map_h)
        if self.size_mode == "推荐":
            width, height = DIFF_CFG[self.difficulty]["sizes"][self.size_label]
        gen = Generator(width, height, self.box_count, self.difficulty, self.style, self.on_progress)
        level_data = gen.build()
        self.level = LevelRuntime(level_data["width"], level_data["height"], level_data["walls"], level_data["goals"], level_data["player"], level_data["boxes"], level_data["solution"])
        self.warning = level_data.get("warning", "")
        self.build_game_buttons()
        self.state = "游戏"

    def on_progress(self, ratio, stage, msg):
        self.progress_ratio = max(0.0, min(1.0, ratio))
        self.progress_stage = stage
        self.progress_msg = msg
        self.handle_single_pump()
        self.draw()
        pygame.display.flip()

    def build_game_buttons(self):
        x = WINDOW_W - PANEL_W + 28
        y = 180
        w = 244
        h = 42
        gap = 10
        self.buttons = [
            Button((x, y, w, h), "重置本局", self.reset_level, self.small_font),
            Button((x, y + (h + gap), w, h), "撤销一步", self.undo, self.small_font),
            Button((x, y + 2 * (h + gap), w, h), "自动演示（从开局）", self.demo_auto, self.small_font),
            Button((x, y + 3 * (h + gap), w, h), "逐步演示（从开局）", self.demo_step, self.small_font),
            Button((x, y + 4 * (h + gap), w, h), "下一步", self.demo_next, self.small_font),
            Button((x, y + 5 * (h + gap), w, h), "停止播放", self.demo_stop, self.small_font),
            Button((x, y + 6 * (h + gap), w, h), "新游戏", self.open_settings, self.small_font),
            Button((x, y + 7 * (h + gap), w, h), "退出游戏", self.quit_game, self.small_font),
        ]

    def reset_level(self):
        if self.level:
            self.level.reset_all()
            self.level.status = "已恢复到开局"

    def undo(self):
        if self.level:
            self.level.undo()

    def demo_auto(self):
        if self.level:
            self.level.start_demo(step_mode=False)

    def demo_step(self):
        if self.level:
            self.level.start_demo(step_mode=True)

    def demo_next(self):
        if self.level:
            self.level.next_demo_step()

    def demo_stop(self):
        if self.level:
            self.level.stop_demo()

    def show_help(self):
        self.state = "说明"
        self.buttons = [Button((520, 700, 240, 52), "返回菜单", self.build_menu, self.font)]

    def quit_game(self):
        self.running = False

    def handle_single_pump(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if self.state in ("菜单", "说明", "游戏", "生成中"):
                for btn in self.buttons:
                    btn.handle_event(event)
            if self.state == "设置":
                for btn in self.buttons:
                    btn.handle_event(event)
                for g in self.groups:
                    g.handle_event(event)
            if self.state == "游戏" and self.level:
                self.handle_game_keys(event)

    def handle_game_keys(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.level.auto_mode and event.key not in (pygame.K_SPACE, pygame.K_ESCAPE):
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.level.try_move(0, -1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.level.try_move(0, 1)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.level.try_move(-1, 0)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.level.try_move(1, 0)
        elif event.key == pygame.K_z:
            self.level.undo()
        elif event.key == pygame.K_r:
            self.reset_level()
        elif event.key == pygame.K_f:
            self.demo_auto()
        elif event.key == pygame.K_g:
            self.demo_step()
        elif event.key == pygame.K_SPACE:
            self.demo_next()
        elif event.key == pygame.K_q:
            self.demo_auto()
        elif event.key == pygame.K_n:
            self.open_settings()
        elif event.key == pygame.K_ESCAPE:
            self.open_settings()

    def update(self):
        if self.state == "游戏" and self.level:
            self.level.update_demo()
            if self.level.is_win() and not self.level.auto_mode:
                self.level.status = "恭喜通关！"

    def draw(self):
        self.screen.fill(BG)
        if self.state == "菜单":
            self.draw_menu()
        elif self.state == "说明":
            self.draw_help()
        elif self.state == "设置":
            self.draw_settings()
        elif self.state == "生成中":
            self.draw_generating()
        elif self.state == "游戏":
            self.draw_game()

    def draw_menu(self):
        title = self.huge_font.render("推箱子（pygame版）", True, TEXT)
        sub = self.small_font.render("中文界面 · 保证可演示 · 适合作为 Python 兴趣小项目", True, SUBTEXT)
        self.screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 170)))
        self.screen.blit(sub, sub.get_rect(center=(WINDOW_W // 2, 230)))
        info_lines = [
            "本版本采用“从完成态逆向打乱”的关卡生成思路。",
            "每个箱子都必须参与打乱，避免随机到“白送箱子”。",
            "自动演示默认从开局播放标准解，稳定不犯傻。",
        ]
        for i, line in enumerate(info_lines):
            txt = self.small_font.render(line, True, SUBTEXT)
            self.screen.blit(txt, (350, 560 + i * 28))
        for btn in self.buttons:
            btn.draw(self.screen)

    def draw_help(self):
        title = self.big_font.render("操作说明", True, TEXT)
        self.screen.blit(title, (110, 80))
        lines = [
            "移动：方向键 或 WASD",
            "撤销：Z",
            "重置本局：R",
            "自动演示：F 或 Q（会从开局播放标准解）",
            "逐步演示：G，下一步：空格",
            "停止播放：点击按钮",
            "新游戏：N，返回设置：Esc",
            "说明：自动演示不是临时暴力求解，而是生成关卡时记录的标准解。",
        ]
        for i, line in enumerate(lines):
            txt = self.font.render(line, True, TEXT if i < 7 else YELLOW)
            self.screen.blit(txt, (110, 160 + i * 52))
        for btn in self.buttons:
            btn.draw(self.screen)

    def draw_settings(self):
        title = self.big_font.render("游戏设置", True, TEXT)
        self.screen.blit(title, (110, 40))
        for g in self.groups:
            g.draw(self.screen, self.small_font)

        box_txt = self.small_font.render(f"箱子数量：{self.box_count}", True, TEXT)
        self.screen.blit(box_txt, (700, 180))

        mode_txt = self.small_font.render("自定义宽度：" + str(self.map_w), True, TEXT if self.size_mode == "自定义" else SUBTEXT)
        self.screen.blit(mode_txt, (700, 280))
        mode_txt2 = self.small_font.render("自定义高度：" + str(self.map_h), True, TEXT if self.size_mode == "自定义" else SUBTEXT)
        self.screen.blit(mode_txt2, (700, 340))

        if self.size_mode == "推荐":
            rw, rh = DIFF_CFG[self.difficulty]["sizes"][self.size_label]
            rec = self.small_font.render(f"当前推荐尺寸：{rw} × {rh}", True, GREEN)
            self.screen.blit(rec, (620, 420))
        else:
            rec = self.small_font.render(f"当前自定义尺寸：{self.map_w} × {self.map_h}", True, YELLOW)
            self.screen.blit(rec, (620, 420))

        range_lo, range_hi = DIFF_CFG[self.difficulty]["boxes"]
        hint = self.small_font.render(f"推荐箱子范围：{range_lo} ~ {range_hi}    地图风格：{self.style}", True, SUBTEXT)
        self.screen.blit(hint, (120, 540))
        warn = self.small_font.render("提示：" + self.warning, True, YELLOW)
        self.screen.blit(warn, (120, 580))
        for btn in self.buttons:
            btn.draw(self.screen)

    def draw_generating(self):
        title = self.big_font.render("正在生成地图", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 180)))
        stage = self.font.render(f"阶段：{self.progress_stage}", True, SUBTEXT)
        msg = self.font.render(self.progress_msg, True, TEXT)
        self.screen.blit(stage, stage.get_rect(center=(WINDOW_W // 2, 280)))
        self.screen.blit(msg, msg.get_rect(center=(WINDOW_W // 2, 330)))
        bar_rect = pygame.Rect(260, 400, 760, 34)
        pygame.draw.rect(self.screen, CARD, bar_rect, border_radius=10)
        fill = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.w * self.progress_ratio), bar_rect.h)
        pygame.draw.rect(self.screen, GREEN, fill, border_radius=10)
        pygame.draw.rect(self.screen, (10, 10, 10), bar_rect, 2, border_radius=10)
        pct = self.font.render(f"{int(self.progress_ratio * 100)}%", True, TEXT)
        self.screen.blit(pct, pct.get_rect(center=(WINDOW_W // 2, 417)))
        tips = self.small_font.render("生成逻辑：先布置边界与结构墙，再从完成态逆向打乱并记录标准解。", True, SUBTEXT)
        self.screen.blit(tips, tips.get_rect(center=(WINDOW_W // 2, 500)))

    def draw_game(self):
        assert self.level is not None
        board_w = WINDOW_W - PANEL_W - 60
        board_h = WINDOW_H - 60
        grid = min(board_w // self.level.width, board_h // self.level.height)
        ox = 30 + (board_w - grid * self.level.width) // 2
        oy = 30 + (board_h - grid * self.level.height) // 2

        for y in range(self.level.height):
            for x in range(self.level.width):
                rect = pygame.Rect(ox + x * grid, oy + y * grid, grid, grid)
                color = WALL if (x, y) in self.level.walls else (FLOOR if (x + y) % 2 == 0 else FLOOR2)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, GRID_LINE, rect, 1)
                if (x, y) in self.level.goals:
                    pygame.draw.circle(self.screen, GOAL, rect.center, max(6, grid // 6))

        for bx, by in self.level.boxes:
            rect = pygame.Rect(ox + bx * grid + 5, oy + by * grid + 5, grid - 10, grid - 10)
            color = BOX_ON_GOAL if (bx, by) in self.level.goals else BOX
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, (70, 55, 35), rect, 2, border_radius=8)
            cx, cy = rect.center
            pygame.draw.line(self.screen, (80, 72, 60), (rect.left + 10, cy), (rect.right - 10, cy), 2)
            pygame.draw.line(self.screen, (80, 72, 60), (cx, rect.top + 10), (cx, rect.bottom - 10), 2)

        px, py = self.level.player
        center = (ox + px * grid + grid // 2, oy + py * grid + grid // 2)
        radius = max(10, grid // 2 - 6)
        pygame.draw.circle(self.screen, PLAYER, center, radius)
        eye_r = max(2, grid // 12)
        pygame.draw.circle(self.screen, (255, 255, 255), (center[0] - radius // 3, center[1] - radius // 6), eye_r)
        pygame.draw.circle(self.screen, (255, 255, 255), (center[0] + radius // 3, center[1] - radius // 6), eye_r)

        panel = pygame.Rect(WINDOW_W - PANEL_W, 0, PANEL_W, WINDOW_H)
        pygame.draw.rect(self.screen, PANEL_BG, panel)
        title = self.big_font.render("游戏中", True, TEXT)
        self.screen.blit(title, (WINDOW_W - PANEL_W + 26, 22))

        info_lines = [
            f"难度：{self.difficulty}",
            f"箱子：{len(self.level.boxes)}",
            f"尺寸：{self.level.width} × {self.level.height}",
            f"风格：{self.style}",
            f"步数：{self.level.moves}",
        ]
        for i, line in enumerate(info_lines):
            txt = self.font.render(line, True, TEXT)
            self.screen.blit(txt, (WINDOW_W - PANEL_W + 26, 84 + i * 32))

        for btn in self.buttons:
            btn.draw(self.screen)

        status_title = self.small_font.render("状态：", True, TEXT)
        self.screen.blit(status_title, (WINDOW_W - PANEL_W + 26, 650))
        status_color = GREEN if self.level.is_win() else (YELLOW if self.level.auto_mode else SUBTEXT)
        status = self.small_font.render(self.level.status, True, status_color)
        self.screen.blit(status, (WINDOW_W - PANEL_W + 26, 684))

        if self.warning:
            warn = self.small_font.render(self.warning, True, YELLOW)
            self.screen.blit(warn, (WINDOW_W - PANEL_W + 26, 720))

        ops = [
            "移动：方向键 或 WASD",
            "Z 撤销   R 重置   F 自动",
            "G 逐步   空格 下一步",
            "Q 放弃演示   N 新游戏",
        ]
        for i, line in enumerate(ops):
            txt = self.small_font.render(line, True, SUBTEXT)
            self.screen.blit(txt, (WINDOW_W - PANEL_W + 26, 760 + i * 24))

        if self.level.is_win():
            win = self.big_font.render("恭喜通关！", True, GREEN)
            self.screen.blit(win, (50, 18))

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


def reachable_area(width, height, walls, boxes, start):
    blocked = set(walls) | set(boxes)
    dq = deque([start])
    seen = {start}
    while dq:
        x, y = dq.popleft()
        for dx, dy in DIR_LIST:
            nb = (x + dx, y + dy)
            if 0 <= nb[0] < width and 0 <= nb[1] < height and nb not in blocked and nb not in seen:
                seen.add(nb)
                dq.append(nb)
    return seen


def reconstruct_path(prev, end):
    path = []
    cur = end
    while prev[cur] is not None:
        cur, move = prev[cur]
        path.append(move)
    path.reverse()
    return path


def shortest_path(width, height, walls, boxes, start, target):
    blocked = set(walls) | set(boxes)
    dq = deque([start])
    prev = {start: None}
    while dq:
        cur = dq.popleft()
        if cur == target:
            return reconstruct_path(prev, cur)
        for dx, dy in DIR_LIST:
            nb = (cur[0] + dx, cur[1] + dy)
            if 0 <= nb[0] < width and 0 <= nb[1] < height and nb not in blocked and nb not in prev:
                prev[nb] = (cur, (dx, dy))
                dq.append(nb)
    return None


def fallback_solve(width, height, walls, goals, player, boxes, max_states=70000):
    start = (player, tuple(sorted(boxes)))
    dq = deque([start])
    prev = {start: None}
    explored = 0
    while dq and explored < max_states:
        explored += 1
        ppos, box_tuple = dq.popleft()
        box_set = set(box_tuple)
        if box_set == set(goals):
            # 回溯推箱步，再补玩家路径
            return rebuild_moves(prev, (ppos, box_tuple), width, height, walls)
        reach = reachable_area(width, height, walls, box_set, ppos)
        for box in list(box_set):
            bx, by = box
            for dx, dy in DIR_LIST:
                stand = (bx - dx, by - dy)
                push_to = (bx + dx, by + dy)
                if stand not in reach:
                    continue
                if push_to in walls or push_to in box_set:
                    continue
                new_boxes = set(box_set)
                new_boxes.remove(box)
                new_boxes.add(push_to)
                state = (box, tuple(sorted(new_boxes)))
                if state in prev:
                    continue
                prev[state] = ((ppos, box_tuple), (stand, (dx, dy), box))
                dq.append(state)
    return None


def rebuild_moves(prev, end_state, width, height, walls):
    chain = []
    cur = end_state
    while prev[cur] is not None:
        cur, info = prev[cur]
        chain.append(info)
    chain.reverse()
    moves = []
    current_player = cur[0]
    current_boxes = set(cur[1])
    for stand, push_dir, box in chain:
        path = shortest_path(width, height, walls, current_boxes, current_player, stand)
        if path is None:
            return None
        moves.extend(path)
        moves.append(push_dir)
        current_boxes.remove(box)
        new_box = (box[0] + push_dir[0], box[1] + push_dir[1])
        current_boxes.add(new_box)
        current_player = box
    return moves


if __name__ == "__main__":
    GameUI().run()
