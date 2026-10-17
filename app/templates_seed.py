"""内置三分化训练模板（推 / 拉 / 腿）。

设计原则：
- 每次训练动作固定，变的只有配重 + RPE —— 用户只需改重量。
- 每个动作给组数、次数区间、建议休息。
- 模板可被用户复制后改动作；内置模板本身不改。
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session as OrmSession

from .models import Exercise, TemplateItem, WorkoutTemplate

# (动作中文名, 组数, 次数区间, 休息秒, 备注)
_PUSH = [
    ("杠铃卧推", 4, "6-8", 180, "主项，逐周加 2.5kg 直到 RPE 9"),
    ("上斜哑铃卧推", 3, "8-12", 120, "胸上部，控制离心 3 秒"),
    ("杠铃肩推", 3, "6-10", 150, "肩前束"),
    ("侧平举", 3, "12-15", 60, "中束，轻重量高次数"),
    ("绳索下压", 3, "10-15", 60, "三头"),
    ("过顶臂屈伸", 2, "12-15", 60, "三头长头"),
]

_PULL = [
    ("引体向上", 4, "6-10", 180, "做不了就高位下拉替代"),
    ("杠铃划船", 4, "6-10", 150, "背部厚度"),
    ("高位下拉", 3, "10-12", 90, "背阔宽度"),
    ("坐姿绳索划船", 3, "10-12", 90, "中背收缩"),
    ("面拉", 3, "15-20", 60, "后束 + 肩健康"),
    ("杠铃弯举", 3, "8-12", 60, "二头"),
    ("锤式弯举", 2, "12-15", 60, "肱桡肌"),
]

_LEGS = [
    ("杠铃深蹲", 4, "5-8", 240, "主项，注意深度"),
    ("直腿硬拉", 3, "8-10", 180, "腘绳 + 臀"),
    ("腿举", 3, "10-12", 120, "股四，脚位偏中"),
    ("保加利亚分腿蹲", 3, "8-10", 120, "单侧，臀腿"),
    ("腿弯举", 3, "12-15", 60, "腘绳孤立"),
    ("站姿提踵", 4, "15-20", 45, "小腿"),
    ("卷腹", 3, "15-20", 45, "核心收尾"),
]

_SPECS = [
    ("推日 Push", "push", "胸 / 肩 / 三头", _PUSH, 1),
    ("拉日 Pull", "pull", "背 / 后束 / 二头", _PULL, 2),
    ("腿日 Legs", "legs", "股四 / 腘绳 / 臀 / 小腿", _LEGS, 3),
]


def seed_templates(db: OrmSession) -> int:
    """首次启动写入内置三分化。已存在则跳过。"""
    if db.query(WorkoutTemplate).filter(WorkoutTemplate.is_builtin == True).count() > 0:  # noqa: E712
        return 0

    # 名称 -> id，宽松匹配（处理动作库里叫法略有差异的情况）
    ex_map: dict[str, Exercise] = {}
    for e in db.query(Exercise).all():
        ex_map.setdefault(e.name, e)

    created = 0
    for name, focus, note, items, order in _SPECS:
        tpl = WorkoutTemplate(
            user_id=None, name=name, focus=focus, note=note, is_builtin=True, sort_order=order
        )
        db.add(tpl)
        db.flush()
        idx = 0
        for ex_name, sets, reps, rest, item_note in items:
            ex = ex_map.get(ex_name)
            if not ex:
                continue  # 动作库里没有就跳过，不阻塞
            db.add(
                TemplateItem(
                    template_id=tpl.id,
                    exercise_id=ex.id,
                    idx=idx,
                    sets=sets,
                    reps=reps,
                    rest_s=rest,
                    note=item_note,
                )
            )
            idx += 1
        created += 1
    db.commit()
    return created