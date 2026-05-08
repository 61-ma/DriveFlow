from __future__ import annotations

import re
from typing import Iterable
from uuid import uuid4

from .models import (
    AssistantResponse,
    ConversationState,
    ConversationTurn,
    ItineraryDay,
    QuickAction,
    SceneHint,
    Stage,
    TravelPlan,
    TravelRequest,
)

SLOT_LABELS = {
    "destination": "目的地",
    "days": "天数",
    "departure_city": "出发地",
    "date_range": "出行时间",
    "budget": "预算",
}

REQUIRED_SLOTS = ["destination", "days", "departure_city", "date_range", "budget"]


class UserMessageParser:
    destinations = [
        "云南",
        "大理",
        "丽江",
        "香格里拉",
        "西双版纳",
        "北京",
        "上海",
        "成都",
        "重庆",
        "三亚",
        "厦门",
        "西安",
        "新疆",
        "杭州",
    ]
    cities = [
        "北京",
        "上海",
        "广州",
        "深圳",
        "杭州",
        "南京",
        "武汉",
        "西安",
        "成都",
        "重庆",
        "昆明",
        "苏州",
        "长沙",
    ]
    date_keywords = [
        "五一",
        "端午",
        "中秋",
        "国庆",
        "十一",
        "元旦",
        "春节",
        "暑假",
        "寒假",
        "下周",
        "下个月",
        "本月底",
        "周末",
        "六月",
        "七月",
        "八月",
        "九月",
        "十月",
        "11月",
        "12月",
    ]
    preference_keywords = {
        "自然风光": "自然风光",
        "山水": "自然风光",
        "风景": "自然风光",
        "慢节奏": "慢节奏",
        "轻松": "慢节奏",
        "古城": "古城漫游",
        "人文": "人文体验",
        "美食": "美食体验",
        "拍照": "摄影出片",
        "摄影": "摄影出片",
        "亲子": "亲子友好",
        "小众": "小众体验",
        "网红打卡": "网红打卡",
        "徒步": "户外轻徒步",
    }
    focus_cities = ["大理", "丽江", "香格里拉", "西双版纳", "昆明"]

    def apply_message(self, request: TravelRequest, text: str) -> list[str]:
        updated_fields: list[str] = []

        destination = self.extract_destination(text)
        if destination and destination != request.destination:
            request.destination = destination
            updated_fields.append("destination")

        days = self.extract_days(text)
        if days and days != request.days:
            request.days = days
            updated_fields.append("days")

        departure_city = self.extract_departure_city(text)
        if departure_city and departure_city != request.departure_city:
            request.departure_city = departure_city
            updated_fields.append("departure_city")

        date_range = self.extract_date_range(text)
        if date_range and date_range != request.date_range:
            request.date_range = date_range
            updated_fields.append("date_range")

        budget = self.extract_budget(text)
        if budget and budget != request.budget:
            request.budget = budget
            updated_fields.append("budget")

        style = self.extract_travel_style(text)
        if style and style != request.travel_style:
            request.travel_style = style
            updated_fields.append("travel_style")

        preferences = self.extract_preferences(text)
        if preferences:
            merged = self.merge_preferences(request.preferences, preferences)
            if merged != request.preferences:
                request.preferences = merged
                updated_fields.append("preferences")

        for city in self.extract_focus_cities(text):
            preference = f"偏重{city}"
            if preference not in request.preferences:
                request.preferences.append(preference)
                updated_fields.append("preferences")

        if "少一点网红打卡" in text and "网红打卡" in request.preferences:
            request.preferences = [item for item in request.preferences if item != "网红打卡"]
            updated_fields.append("preferences")
            if "小众体验" not in request.preferences:
                request.preferences.append("小众体验")

        if request.travel_style == "轻松慢游" and "慢节奏" not in request.preferences:
            request.preferences.append("慢节奏")

        return updated_fields

    def extract_destination(self, text: str) -> str | None:
        for destination in self.destinations:
            if destination in text and f"从{destination}出发" not in text:
                return destination

        pattern_match = re.search(
            r"(?:规划|安排|做|来个|想去|去|到|玩)(?:一个)?\s*([一-龥A-Za-z]{2,10}?)(?:(?:玩)?\s*\d+\s*天|(?:的)?行程|旅行|旅游|之旅)",
            text,
        )
        if pattern_match:
            candidate = pattern_match.group(1).strip()
            if candidate not in self.cities:
                return candidate

        days_match = re.search(r"([一-龥A-Za-z]{2,10})\s*(\d+)\s*天", text)
        if days_match:
            candidate = days_match.group(1).strip()
            if candidate not in self.cities:
                return candidate
        return None

    def extract_days(self, text: str) -> int | None:
        match = re.search(r"(\d+)\s*天", text)
        if not match:
            return None
        days = int(match.group(1))
        return days if 1 <= days <= 15 else None

    def extract_departure_city(self, text: str) -> str | None:
        match = re.search(r"从([一-龥A-Za-z]{2,8})出发", text)
        if match:
            return match.group(1)
        for city in self.cities:
            if city in text and any(token in text for token in [f"{city}出发", f"从{city}", f"{city}走"]):
                return city
        return None

    def extract_date_range(self, text: str) -> str | None:
        explicit = re.search(
            r"(\d{1,2}月(?:上旬|中旬|下旬)?|\d{1,2}月\d{1,2}日|下周|下个月|本月底|周末)",
            text,
        )
        if explicit:
            return explicit.group(1)
        for keyword in self.date_keywords:
            if keyword in text:
                return keyword
        match = re.search(r"(?:时间|出发时间|什么时候)\s*([一-龥A-Za-z0-9]{2,10})", text)
        return match.group(1) if match else None

    def extract_budget(self, text: str) -> int | None:
        match = re.search(r"([1-9]\d{3,5})\s*元", text)
        if match:
            return int(match.group(1))
        match = re.search(r"(?:预算|控制在|降到|压到|改成|总预算)\D*([1-9]\d{3,5})", text)
        if match:
            return int(match.group(1))
        return None

    def extract_preferences(self, text: str) -> list[str]:
        matches: list[str] = []
        for keyword, label in self.preference_keywords.items():
            if keyword in text and label not in matches:
                matches.append(label)
        return matches

    def extract_travel_style(self, text: str) -> str | None:
        if any(token in text for token in ["不要太赶", "轻松一点", "轻松些", "慢一点"]):
            return "轻松慢游"
        if "深度" in text:
            return "深度体验"
        if any(token in text for token in ["高效", "打卡", "特种兵"]):
            return "高效打卡"
        if "慢节奏" in text:
            return "轻松慢游"
        return None

    def extract_extra_days(self, text: str) -> int:
        match = re.search(r"(?:加|多安排|多留)(\d+)天", text)
        if match:
            return int(match.group(1))
        if "加一天" in text or "多一天" in text:
            return 1
        return 0

    def extract_focus_cities(self, text: str) -> list[str]:
        matches: list[str] = []
        for city in self.focus_cities:
            if city in text and any(token in text for token in ["加一天", "多安排", "多留", "想去", "重点", "多待"]):
                matches.append(city)
        return matches

    def detect_confirmation(self, text: str) -> bool:
        return any(token in text for token in ["确认", "就这个", "没问题", "可以，就按这个", "最终方案"])

    def detect_share(self, text: str) -> bool:
        return any(token in text for token in ["保存", "分享", "发到手机", "发送到手机", "发我手机"])

    def detect_revision(self, text: str) -> bool:
        revision_tokens = [
            "调整",
            "改成",
            "改一下",
            "预算",
            "不要太赶",
            "轻松一点",
            "加一天",
            "多安排",
            "少一点",
            "多一点",
            "换成",
            "删掉",
        ]
        return any(token in text for token in revision_tokens)

    @staticmethod
    def merge_preferences(existing: Iterable[str], incoming: Iterable[str]) -> list[str]:
        merged: list[str] = []
        for item in list(existing) + list(incoming):
            if item not in merged:
                merged.append(item)
        return merged


class TravelPlanBuilder:
    def build_plan(self, request: TravelRequest) -> TravelPlan:
        days_count = request.days or 5
        budget = request.budget or max(days_count * 1500, 5000)
        hotel_level = self._hotel_level(budget)
        city_sequence = self._build_city_sequence(request)
        daily_costs = self._split_budget(budget, len(city_sequence))

        days: list[ItineraryDay] = []
        previous_city: str | None = None
        for index, city in enumerate(city_sequence, start=1):
            theme, highlights = self._build_day_content(request, city, index)
            transport = self._build_transport(previous_city, city, index)
            days.append(
                ItineraryDay(
                    day=index,
                    city=city,
                    theme=theme,
                    highlights=highlights,
                    transport=transport,
                    hotel_level=hotel_level,
                    estimated_cost=daily_costs[index - 1],
                )
            )
            previous_city = city

        title = f"{request.destination or '目的地'} {days_count} 天座舱行程方案"
        summary = self._build_summary(request, budget)
        tips = self._build_tips(request)
        return TravelPlan(
            title=title,
            summary=summary,
            days=days,
            total_estimated_cost=sum(daily_costs),
            tips=tips,
        )

    def _build_city_sequence(self, request: TravelRequest) -> list[str]:
        days = request.days or 5
        destination = request.destination or "云南"
        if destination != "云南":
            return [destination for _ in range(days)]

        slow_trip = request.travel_style == "轻松慢游" or "慢节奏" in request.preferences
        if days <= 3:
            sequence = ["昆明", "大理", "丽江"][:days]
        elif days == 4:
            sequence = ["昆明", "大理", "大理", "丽江"] if slow_trip else ["昆明", "大理", "丽江", "丽江"]
        elif days == 5:
            sequence = ["昆明", "大理", "大理", "丽江", "丽江"]
        elif days == 6:
            sequence = ["昆明", "大理", "大理", "丽江", "丽江", "香格里拉"]
        else:
            sequence = ["昆明", "大理", "大理", "丽江", "丽江", "香格里拉", "香格里拉"]
            while len(sequence) < days:
                sequence.append("大理" if slow_trip else "丽江")

        for city in ["大理", "丽江", "香格里拉", "西双版纳"]:
            if f"偏重{city}" in request.preferences and city in sequence:
                replace_index = max(1, len(sequence) // 2)
                sequence[replace_index] = city
        return sequence[:days]

    def _build_day_content(self, request: TravelRequest, city: str, index: int) -> tuple[str, list[str]]:
        natural = "自然风光" in request.preferences
        gourmet = "美食体验" in request.preferences
        ancient = "古城漫游" in request.preferences
        quiet = request.travel_style == "轻松慢游" or "慢节奏" in request.preferences

        city_highlights = {
            "昆明": ["滇池海埂大坝", "翠湖慢逛", "过桥米线晚餐"],
            "大理": ["洱海环线", "喜洲古镇", "双廊日落"],
            "丽江": ["白沙古镇", "玉龙雪山远眺", "束河夜游"],
            "香格里拉": ["独克宗古城", "普达措国家公园", "藏式下午茶"],
            "西双版纳": ["中科院植物园", "告庄夜市", "傣味晚餐"],
        }
        generic_highlights = [
            f"{request.destination}城市地标",
            f"{request.destination}特色街区",
            f"{request.destination}代表性晚餐",
        ]
        highlights = list(city_highlights.get(city, generic_highlights))

        if natural:
            highlights[0] = {
                "昆明": "滇池湖岸轻游",
                "大理": "洱海生态廊道骑行",
                "丽江": "雪山观景台",
                "香格里拉": "普达措自然漫步",
                "西双版纳": "热带雨林步道",
            }.get(city, highlights[0])

        if ancient:
            highlights[1] = {
                "昆明": "老街人文漫游",
                "大理": "大理古城晨逛",
                "丽江": "白沙古镇驻足",
                "香格里拉": "独克宗古城夜色",
            }.get(city, highlights[1])

        if gourmet:
            highlights[2] = {
                "昆明": "菌子火锅体验",
                "大理": "白族风味餐",
                "丽江": "纳西风味晚餐",
                "香格里拉": "藏式牦牛火锅",
                "西双版纳": "傣味手抓饭",
            }.get(city, highlights[2])

        theme = {
            "昆明": "抵达适应与城市缓冲",
            "大理": "海西慢游与松弛感体验",
            "丽江": "古城氛围与雪山景观",
            "香格里拉": "高海拔自然人文延展",
            "西双版纳": "热带风情与夜市体验",
        }.get(city, f"{request.destination}核心景点探索")

        if quiet:
            theme = theme.replace("探索", "慢游")
        return f"Day {index} · {theme}", highlights

    @staticmethod
    def _build_transport(previous_city: str | None, city: str, day_index: int) -> str:
        if day_index == 1:
            return "抵达后座舱提醒接驳酒店"
        if previous_city == city:
            return "本地短途接驳，减少换乘"
        return f"{previous_city} - {city} 城际转场"

    @staticmethod
    def _hotel_level(budget: int) -> str:
        if budget <= 6000:
            return "舒适型民宿"
        if budget <= 10000:
            return "品质酒店"
        return "高端度假酒店"

    @staticmethod
    def _split_budget(total_budget: int, days: int) -> list[int]:
        base = total_budget // days
        remainder = total_budget % days
        costs = [base for _ in range(days)]
        for index in range(remainder):
            costs[index] += 1
        return costs

    @staticmethod
    def _build_summary(request: TravelRequest, budget: int) -> str:
        style = request.travel_style or "舒适平衡"
        preference_text = "、".join(
            [item for item in request.preferences if not item.startswith("偏重")]
        ) or "经典路线"
        return (
            f"从{request.departure_city}出发，预计在{request.date_range}完成一段"
            f"{request.destination}{request.days}天行程。总预算按约 {budget} 元控制，"
            f"整体风格偏{style}，重点照顾 {preference_text}。"
        )

    @staticmethod
    def _build_tips(request: TravelRequest) -> list[str]:
        tips = [
            "座舱内优先展示每日目的地、转场方式和预算摘要，减少阅读负担。",
            "如果你继续口述需求，系统会只改动相关槽位，不会整段重来。",
        ]
        if request.destination == "云南":
            tips.append("云南日夜温差大，建议在打包清单里加入薄外套和防晒。")
        if request.date_range in {"国庆", "十一", "暑假"}:
            tips.append("节假日客流更高，建议把热门景点安排到上午时段。")
        return tips


class TravelAssistantService:
    def __init__(self) -> None:
        self._sessions: dict[str, ConversationState] = {}
        self._parser = UserMessageParser()
        self._builder = TravelPlanBuilder()

    def start_session(self) -> AssistantResponse:
        session_id = uuid4().hex[:8]
        state = ConversationState(session_id=session_id, missing_slots=REQUIRED_SLOTS.copy())
        self._sessions[session_id] = state
        actions = [
            QuickAction(label="示例：云南 5 天", value="帮我规划一个云南5天的行程"),
            QuickAction(label="示例：成都 4 天", value="帮我规划一个成都4天的行程"),
        ]
        message = "你好，我是座舱 AI 行程助手。直接告诉我目的地和天数，我会继续追问出发地、时间和预算。"
        return self._build_response(state, message, actions)

    def handle_message(self, session_id: str, text: str) -> AssistantResponse:
        state = self._get_state(session_id)
        cleaned_text = text.strip()
        if not cleaned_text:
            return self._snapshot(state, "请输入一句乘客语音文本。")

        state.history.append(ConversationTurn(role="user", text=cleaned_text))

        if self._parser.detect_share(cleaned_text) and state.plan:
            return self.share_plan(session_id)

        if self._parser.detect_confirmation(cleaned_text) and state.plan:
            return self.confirm_plan(session_id)

        if state.plan and state.stage in {Stage.PLAN_GENERATED, Stage.REVISING_PLAN, Stage.PLAN_CONFIRMED}:
            if self._parser.detect_revision(cleaned_text):
                return self._revise_state(state, cleaned_text, record_user=False)

        self._parser.apply_message(state.request, cleaned_text)
        state.missing_slots = self._missing_slots(state.request)
        state.stage = Stage.CONFIRMING_INFO

        if state.missing_slots:
            message = self._missing_info_prompt(state.request, state.missing_slots)
            return self._build_response(state, message, self._suggest_info_actions(state.missing_slots))

        state.plan = self._builder.build_plan(state.request)
        state.stage = Stage.PLAN_GENERATED
        message = (
            f"已为你生成第一版 {state.request.destination}{state.request.days} 天行程。"
            "你可以继续说“预算降到 6000”“不要太赶”“加一天大理”之类的修改意见。"
        )
        return self._build_response(state, message, self._plan_actions())

    def revise_plan(self, session_id: str, feedback: str) -> AssistantResponse:
        state = self._get_state(session_id)
        return self._revise_state(state, feedback, record_user=True)

    def _revise_state(
        self,
        state: ConversationState,
        feedback: str,
        record_user: bool,
    ) -> AssistantResponse:
        if not state.plan:
            raise ValueError("当前还没有可调整的方案，请先完成基础信息确认。")
        if record_user:
            state.history.append(ConversationTurn(role="user", text=feedback))
        changes = self._apply_revision(state.request, feedback)
        state.plan = self._builder.build_plan(state.request)
        state.stage = Stage.REVISING_PLAN
        message = f"已按你的反馈调整：{'、'.join(changes)}。你可以继续微调，或直接确认方案。"
        return self._build_response(state, message, self._plan_actions())

    def confirm_plan(self, session_id: str) -> AssistantResponse:
        state = self._get_state(session_id)
        if not state.plan:
            raise ValueError("当前还没有可确认的方案，请先生成行程。")
        state.stage = Stage.PLAN_CONFIRMED
        message = "最终方案已确认。我会保留当前版本，你现在可以保存到手机，或继续补充个性化偏好。"
        actions = [
            QuickAction(label="保存到手机", value="发送到我的手机", kind="share"),
            QuickAction(label="继续优化", value="再优化一下美食和休息节奏"),
        ]
        return self._build_response(state, message, actions)

    def share_plan(self, session_id: str) -> AssistantResponse:
        state = self._get_state(session_id)
        if not state.plan:
            raise ValueError("当前还没有可分享的方案，请先生成行程。")
        state.stage = Stage.SHARED
        message = "行程卡片已保存，并模拟发送到乘客手机。车内大屏将保留摘要，方便继续补充修改。"
        actions = [
            QuickAction(label="重新开始新需求", value="帮我规划一个新的旅行", kind="restart"),
            QuickAction(label="继续改当前方案", value="我想继续改一下当前方案"),
        ]
        return self._build_response(state, message, actions)

    def get_session(self, session_id: str) -> AssistantResponse:
        state = self._get_state(session_id)
        latest_message = self._latest_assistant_message(state) or "会话已加载。"
        return self._snapshot(state, latest_message)

    @staticmethod
    def get_mock_scenes() -> list[SceneHint]:
        return [
            SceneHint(
                title="需求发起",
                utterance="帮我规划一个云南5天的行程",
                note="先只说目的地和天数，触发信息确认。",
            ),
            SceneHint(
                title="信息确认",
                utterance="我从上海出发，国庆去，预算8000，喜欢自然风光和慢节奏",
                note="一次性补齐关键槽位，生成第一版方案。",
            ),
            SceneHint(
                title="方案调整",
                utterance="预算降到6000，不要太赶，加一天大理",
                note="演示预算、节奏和城市偏好的联动调整。",
            ),
            SceneHint(
                title="方案确认",
                utterance="确认这个方案",
                note="进入确认态。",
            ),
            SceneHint(
                title="保存分享",
                utterance="发送到我的手机",
                note="完成最后一个关键帧。",
            ),
        ]

    def _apply_revision(self, request: TravelRequest, feedback: str) -> list[str]:
        changes: list[str] = []
        self._parser.apply_message(request, feedback)

        budget = self._parser.extract_budget(feedback)
        if budget:
            request.budget = budget
            changes.append(f"总预算调整为 {budget} 元")

        style = self._parser.extract_travel_style(feedback)
        if style:
            request.travel_style = style
            changes.append(f"行程节奏调整为 {style}")

        extra_days = self._parser.extract_extra_days(feedback)
        if extra_days:
            request.days = (request.days or 0) + extra_days
            changes.append(f"行程天数增加 {extra_days} 天")

        focus_cities = self._parser.extract_focus_cities(feedback)
        for city in focus_cities:
            preference = f"偏重{city}"
            if preference not in request.preferences:
                request.preferences.append(preference)
            changes.append(f"增加 {city} 停留权重")

        preferences = self._parser.extract_preferences(feedback)
        for item in preferences:
            if item == "网红打卡" and "少一点网红打卡" in feedback:
                continue
            if item not in request.preferences:
                request.preferences.append(item)
                changes.append(f"补充偏好：{item}")

        if "少一点网红打卡" in feedback:
            request.preferences = [item for item in request.preferences if item != "网红打卡"]
            if "小众体验" not in request.preferences:
                request.preferences.append("小众体验")
            changes.append("减少网红打卡，增加小众体验")

        if not changes:
            changes.append("细化了每日亮点和休息节奏")
        return changes

    def _missing_slots(self, request: TravelRequest) -> list[str]:
        missing: list[str] = []
        for field_name in REQUIRED_SLOTS:
            value = getattr(request, field_name)
            if value is None:
                missing.append(field_name)
        return missing

    def _missing_info_prompt(self, request: TravelRequest, missing_slots: list[str]) -> str:
        known_parts: list[str] = []
        if request.destination:
            known_parts.append(f"{request.destination}")
        if request.days:
            known_parts.append(f"{request.days} 天")
        prefix = "我先记下了你的需求" if not known_parts else f"我已收到 {' '.join(known_parts)} 的需求"
        missing_text = "、".join(SLOT_LABELS[item] for item in missing_slots)
        return f"{prefix}。还需要确认：{missing_text}。你可以一次性补齐，也可以分开告诉我。"

    def _suggest_info_actions(self, missing_slots: list[str]) -> list[QuickAction]:
        if {"departure_city", "date_range", "budget"}.issubset(set(missing_slots)):
            return [
                QuickAction(label="补充：上海/国庆/8000", value="我从上海出发，国庆去，预算8000"),
                QuickAction(label="补充偏好", value="喜欢自然风光和慢节奏"),
            ]
        suggestions: list[QuickAction] = []
        if "departure_city" in missing_slots:
            suggestions.append(QuickAction(label="从上海出发", value="我从上海出发"))
        if "date_range" in missing_slots:
            suggestions.append(QuickAction(label="国庆出发", value="国庆去"))
        if "budget" in missing_slots:
            suggestions.append(QuickAction(label="预算 8000", value="预算8000"))
        return suggestions[:3]

    @staticmethod
    def _plan_actions() -> list[QuickAction]:
        return [
            QuickAction(label="预算降到 6000", value="预算降到6000"),
            QuickAction(label="不要太赶", value="不要太赶"),
            QuickAction(label="加一天大理", value="加一天大理"),
            QuickAction(label="确认方案", value="确认这个方案", kind="confirm"),
        ]

    def _build_response(
        self,
        state: ConversationState,
        message: str,
        actions: list[QuickAction],
    ) -> AssistantResponse:
        state.history.append(ConversationTurn(role="assistant", text=message))
        return self._snapshot(state, message, actions)

    def _snapshot(
        self,
        state: ConversationState,
        message: str,
        actions: list[QuickAction] | None = None,
    ) -> AssistantResponse:
        return AssistantResponse(
            session_id=state.session_id,
            stage=state.stage,
            message=message,
            collected_info=self._collected_info(state.request),
            missing_info=[SLOT_LABELS[item] for item in state.missing_slots],
            plan=state.plan,
            actions=actions or self._default_actions_for_stage(state.stage),
            history=state.history,
        )

    @staticmethod
    def _latest_assistant_message(state: ConversationState) -> str | None:
        for turn in reversed(state.history):
            if turn.role == "assistant":
                return turn.text
        return None

    @staticmethod
    def _collected_info(request: TravelRequest) -> dict[str, str]:
        info: dict[str, str] = {}
        if request.destination:
            info["目的地"] = request.destination
        if request.days:
            info["天数"] = f"{request.days} 天"
        if request.departure_city:
            info["出发地"] = request.departure_city
        if request.date_range:
            info["出行时间"] = request.date_range
        if request.budget:
            info["预算"] = f"{request.budget} 元"
        visible_preferences = [item for item in request.preferences if not item.startswith("偏重")]
        if visible_preferences:
            info["偏好"] = "、".join(visible_preferences)
        if request.travel_style:
            info["节奏"] = request.travel_style
        return info

    @staticmethod
    def _default_actions_for_stage(stage: Stage) -> list[QuickAction]:
        if stage == Stage.SHARED:
            return [
                QuickAction(label="继续调整", value="我想继续改一下当前方案"),
                QuickAction(label="重新开始", value="帮我规划一个新的旅行", kind="restart"),
            ]
        if stage == Stage.PLAN_CONFIRMED:
            return [QuickAction(label="保存到手机", value="发送到我的手机", kind="share")]
        return []

    def _get_state(self, session_id: str) -> ConversationState:
        state = self._sessions.get(session_id)
        if not state:
            raise KeyError("会话不存在，请重新开始。")
        return state
