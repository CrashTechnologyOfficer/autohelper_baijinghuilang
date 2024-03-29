import re

from typing_extensions import override

from autohelper.feature.Box import find_box_by_name, find_boxes_by_name, find_boxes_within_boundary
from task.BJTask import BJTask


class ManXunTask(BJTask):

    def __init__(self):
        super().__init__()
        self.name = "自动漫巡任务"
        self.description = """自动漫巡
    """
        self.click_no_brainer = ["直接胜利", "属性提升", "前进", "通过", "继续", "收下", "跳过", "开始强化",
                                 re.compile(r"^解锁技能："), re.compile(r"^精神负荷降低"), "漫巡推进"]
        self.stats_priority_list = ["终端", "生命", "专精", "攻击", "防御"]
        self.config = {"跳过战斗": ["鱼叉将军-日光浅滩E"],
                       "选项优先级": ["风险区", "暗礁", "烙痕唤醒", "获取刻印属性", "记忆强化", "研习区",
                                      "休整区"],
                       "无法直接胜利, 自动投降跳过": False
                       }
        self.destination = None
        self.skill_counter = {}
        self.stats_up_re = re.compile(r"([\u4e00-\u9fff]+)\+(\d+)(?:~(\d+))?")

    def end(self, message, result=False):
        self.logger.info(f"执行结束:{message}")
        return result

    @property
    def choice_zone(self):
        return self.box_of_screen(0.7, 0.25, 0.3, 0.5, "选项检测区域")

    @property
    def dialog_zone(self):
        return self.box_of_screen(0.25, 0.2, 0.5, 0.7, "弹窗检测区域")

    @property
    def stats_zone(self):
        return self.box_of_screen(0.3, 0.8, 0.4, 0.2, "属性测区域,PC端虚化效果无法检测")

    @override
    def run_frame(self):
        if not self.check_is_manxun_ui():
            self.logger.error("必须从漫巡选项界面开始, 并且开启路线追踪")
            self.set_done()
            return False

        try:
            while self.loop():
                pass
        except Exception as e:
            self.logger.error(f"运行异常:", e)
            pass

        self.logger.info("漫巡完成")
        return True

    def check_is_manxun_ui(self):
        choices = self.find_choices()

        if not choices:
            self.logger.debug("找不到选项")
            return False

        if self.find_depth() == 0:
            self.logger.debug("找不到深度")
            return False

        return choices

    def loop(self, choice=-1):
        choices, choice_clicked = self.click_choice(choice)
        if not choice_clicked:
            self.logger.error(f"没有选项可以点击")
            return False
        self.wait_until(lambda: self.do_handle_dialog(choice, choices, choice_clicked))
        if self.done:
            return False

    def do_handle_dialog(self, choice, choices, choice_clicked):
        boxes = self.ocr(self.dialog_zone)
        if self.find_depth(boxes) > 0:
            self.logger.info(f"没有弹窗, 进行下一步")
            return True
        self.logger.debug(f"检测对话框区域 {boxes} ")
        if find_box_by_name(boxes, "提升攻击"):
            box = self.find_highest_gaowei_number(boxes)
            self.click_box(box)
            self.logger.info(f"高位同调 点击最高 {box}")
        elif confirm := find_box_by_name(boxes, "完成漫巡"):
            self.click_box(confirm)
            self.wait_click_box(lambda: self.ocr(self.dialog_zone, match="确认"))
            self.wait_click_box(lambda: self.ocr(self.dialog_zone, match="跳过漫巡回顾"))
            self.wait_click_box(lambda: self.ocr(self.dialog_zone, match="点击屏幕确认结算"))
            self.set_done()
        elif confirm := find_box_by_name(boxes, "解锁技能和区域"):
            self.handle_skill_dialog(boxes, confirm)
        elif find_box_by_name(boxes, "获得了一些技能点"):
            self.logger.info(f"获取技能点成功")
            self.click_box(find_box_by_name(boxes, re.compile(r"^\+\d+")))
        elif find_box_by_name(boxes, "刻印技能上限"):
            confirm = find_box_by_name(boxes, re.compile(r"前进！解锁"))
            self.logger.info(f"区域技能,点击两次")
            self.click_box(confirm)
            self.sleep(0.5)
            self.click_box(confirm)
        elif stat_combat := find_box_by_name(boxes, "开始战斗"):
            skip_battle = find_box_by_name(boxes, self.config.get("跳过战斗"))
            self.logger.debug(
                f"开始战斗 跳过战斗查询结果:{skip_battle} abs(choice):{abs(choice)} len(choices) {len(choices)}")
            if skip_battle and abs(choice) < len(choices):
                self.logger.info(f"回避配置列表里的战斗 {skip_battle}")
                self.click_cancel()
                return self.loop(choice=choice - 1)
            elif self.config.get("无法直接胜利, 自动投降跳过"):
                self.logger.info(f"开始自动跳过战斗")
                self.click_box(stat_combat)
                self.auto_skip_combat()
            else:
                raise RuntimeError("未开启自动战斗, 无法继续漫巡, 结束")
        elif no_brain_box := self.click_box_if_name_match(boxes, self.click_no_brainer):
            self.logger.info(f"点击固定对话框: {no_brain_box.name}")
        elif stats_up_choices := self.find_stats_up(boxes):
            self.handle_stats_up(stats_up_choices)
        else:
            raise RuntimeError(f"未知弹窗 无法处理")
        return True

    def find_stats_up(self, boxes):
        for box in boxes:
            if re.search(r"^[\u4e00-\u9fa5]{2}$", box.name):
                closest = box.find_closest_box("right", boxes)
                distance = closest.closest_distance(box)
                if distance < box.width:
                    match = re.search(r"\+(\d+)(?:~(\d+))?", closest.name)
                    if match:
                        box.name += match.group(0)
                        self.logger.debug(f"合并较近属性和数值, {box} {closest.name}")
                        closest.name = ""

        return find_boxes_by_name(boxes, self.stats_up_re)

    def ignore_right_stats(self, box, boxes):
        closest = box.find_closest_box("right", boxes)
        if closest is not None and isinstance(closest.name, str):
            match = re.search(r"\+(\d+)(?:~(\d+))?", closest.name)
            if match:
                distance = closest.closest_distance(box)
                if distance < box.width:
                    start, end = match.groups()
                    # Calculate the value. If 'end' is None, use 'start'; otherwise, calculate the average.
                    self.logger.debug(f"忽略右边最近的属性值 {box} {closest} {distance}")
                    closest.name = 0

    def auto_skip_combat(self):
        start_combat = self.wait_until(lambda: self.ocr(self.star_combat_zone, "开始战斗"), time_out=50)
        if not start_combat:
            raise RuntimeError("无法找到开始战斗按钮")
        self.click_relative(0.04, 0.065)
        self.wait_click_box(lambda: self.ocr(self.dialog_zone, "离开战斗"))
        self.wait_click_box(lambda: self.ocr(self.dialog_zone, "离开战斗"))
        self.wait_click_box(lambda: self.ocr(self.dialog_zone, "继续"), time_out=30)
        self.wait_click_box(lambda: self.ocr(self.dialog_zone, match=re.compile(r"回避")))
        self.wait_click_box(lambda: self.ocr(self.dialog_zone, match=re.compile(r"确\s?认")))

    def handle_stats_up(self, stats_up_choices):
        stats_up_parsed = self.parse_stats_choices(stats_up_choices)
        stats_boxes = self.ocr(self.stats_zone)
        current_stats = {}
        for box in stats_boxes:
            if re.search(r"[\u4e00-\u9fa5]{2}", box.name):
                number = box.find_closest_box("down", stats_boxes)
                number = int(number.name)
                current_stats[box.name] = number
        target = self.find_highest_increase_for_lowest_stat(stats_up_parsed, current_stats)
        self.click_box(target)
        self.logger.info(
            f"选择升级属性 {stats_up_choices} stats_up_parsed:{stats_up_parsed} current_stats:{current_stats} target:{target.name}")

    def handle_skill_dialog(self, boxes, confirm):
        search_skill_name_box = confirm.copy(-confirm.width / 2, -confirm.height * 2, confirm.width,
                                             confirm.height * 0.7)
        self.draw_boxes("skill_search_area", search_skill_name_box)
        skills = find_boxes_within_boundary(boxes, search_skill_name_box)
        self.draw_boxes("skills", skills)
        self.logger.info(f"获取技能 {skills}")
        self.click_box(confirm)

    def click_choice(self, index=-1):
        choices = self.find_choices()
        if abs(index) > len(choices):
            raise ValueError(f"click_choice out of bonds")
        else:
            if choices[index].name == "深度等级提升":
                depth = self.find_depth()
                self.logger.info(f"提升深度, {depth} 目前是第{abs(index)}个选项, 共有{len(choices)}选项")
                if depth < 12 or abs(index) == len(choices):
                    self.logger.info(f"提升深度,当前深度{depth}")
                else:
                    self.logger.info(f"不提升深度,当前深度{depth}")
                    index -= - 1
            self.click_box(choices[index])
            self.sleep(3)  # 等待动画
        self.logger.info(f"点击选项:{choices[index]}")
        return choices, choices[index]

    def do_find_choices(self):
        boxes = self.ocr(self.choice_zone)
        choices = find_boxes_by_name(boxes, re.compile(r"^通往"))
        if len(choices) > 0:
            for i in range(len(choices) - 1, -1, -1):
                if self.destination is None:
                    self.logger.debug(f"检测到追踪目标: {choices[i].name}")
                    self.destination = choices[i].name
                choices[i].height *= 3
                if self.destination != choices[i].name:
                    self.logger.info("排除错误追踪目标")
                    del choices[i]
                    continue
                right_text_box = choices[i].find_closest_box("right", boxes)
                if right_text_box is not None:
                    choices[i].name = right_text_box.name
        else:
            choices = find_boxes_by_name(boxes, "风险区")
        self.logger.debug(f"检测选项区域结果: {choices}")
        return choices

    def find_choices(self):
        return self.wait_until(self.do_find_choices, time_out=10)

    def find_depth(self, boxes=None):
        if boxes is None:
            boxes = self.ocr(self.dialog_zone)
        depth_box = None
        depth = 0
        numbers = find_boxes_by_name(boxes, re.compile(r"^[01D][0-9]$"))
        for number in numbers:
            # 居中大字深度
            if self.box_in_horizontal_center(number, off_percent=0.1) and number.height / self.height > 0.07:
                depth_box = number
                break
        if depth_box is not None:
            depth_box.name = depth_box.name.replace("D", "2")
            depth = int(depth_box.name)
        return depth

    def click_cancel(self):
        self.click_relative(0.5, 0.1)

    def find_highest_gaowei_number(self, boxes):
        highest_gaowei_number = 0
        highest_gaowei_box = None
        for box in boxes:
            if isinstance(box.name, str) and box.name[0] == '+' and all(
                    char.isdigit() or char == '+' or char == ' ' for char in box.name):
                # Split the string by '+' and sum the numbers
                numbers = box.name.split('+')
                sum_gaowei = sum(int(number) for number in numbers if number)
                box.name = sum_gaowei
                self.ignore_right_stats(box, boxes)
                if box.name > highest_gaowei_number:
                    highest_gaowei_number = box.name
                    highest_gaowei_box = box

        return highest_gaowei_box

    def parse_stats_choices(self, boxes):
        attributes = {}
        for box in boxes:
            # Find all matches of the pattern in the input string
            for match in re.finditer(self.stats_up_re, box.name):
                attribute, start, end = match.groups()
                # Calculate the value. If 'end' is None, use 'start'; otherwise, calculate the average.
                value = int(start) if not end else (int(start) + int(end)) / 2
                a_list = attributes.get(attribute, [])
                a_list.append((value, box))
                attributes[attribute] = a_list

        return attributes

    def find_highest_increase_for_lowest_stat(self, stats_up_parsed, current_stats):
        current_list = sorted(current_stats, key=current_stats.get, reverse=True)
        merged_list = self.stats_priority_list[:]  # Start with a copy of the first list to maintain its order
        for item in current_list:
            if item not in merged_list:
                merged_list.append(item)
        self.logger.debug(f"查找最高优先级提升属性 {stats_up_parsed} {merged_list} {current_stats}")
        # Find the lowest stat(s) in current_stats
        for stat in reversed(merged_list):
            if stat in stats_up_parsed:
                # Assuming stats_up_parsed[stat] is a list of tuples (value, box)
                # and we want the one with the highest 'value'
                value, box = max(stats_up_parsed[stat], key=lambda x: x[0])
                self.logger.info(f"查找最高优先级提升属性结果 {box.name}")
                return box  # Return the box associated with the highest increase
