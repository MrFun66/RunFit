"""内置动作库与肌肉映射。"""
from __future__ import annotations

import json

# 肌肉分组（用于热力图）
MUSCLE_GROUPS = {
    "chest": "胸",
    "front_delt": "前束",
    "side_delt": "中束",
    "rear_delt": "后束",
    "triceps": "三头",
    "biceps": "二头",
    "forearm": "小臂",
    "traps": "斜方",
    "lats": "背阔",
    "mid_back": "中背",
    "lower_back": "下背",
    "abs": "腹",
    "obliques": "腹斜",
    "glutes": "臀",
    "quads": "股四",
    "hamstrings": "腘绳",
    "calves": "小腿",
    "hip_flexor": "髂腰",
}

# (名称, 英文, 主动肌, 协同肌, 器械, 类别, 是否复合)
_EX = [
    # 胸
    ("杠铃卧推", "Barbell Bench Press", ["chest"], ["front_delt", "triceps"], "barbell", "push", True),
    ("哑铃卧推", "Dumbbell Bench Press", ["chest"], ["front_delt", "triceps"], "dumbbell", "push", True),
    ("上斜哑铃卧推", "Incline DB Press", ["chest"], ["front_delt", "triceps"], "dumbbell", "push", True),
    ("双杠臂屈伸", "Dips", ["chest"], ["triceps", "front_delt"], "bodyweight", "push", True),
    ("俯卧撑", "Push-up", ["chest"], ["triceps", "front_delt", "abs"], "bodyweight", "push", True),
    ("绳索夹胸", "Cable Fly", ["chest"], ["front_delt"], "cable", "push", False),
    ("蝴蝶机夹胸", "Pec Deck", ["chest"], [], "machine", "push", False),
    # 肩
    ("杠铃肩推", "Overhead Press", ["front_delt"], ["triceps", "traps"], "barbell", "push", True),
    ("哑铃肩推", "Dumbbell Shoulder Press", ["front_delt"], ["triceps", "side_delt"], "dumbbell", "push", True),
    ("侧平举", "Lateral Raise", ["side_delt"], ["traps"], "dumbbell", "push", False),
    ("反向飞鸟", "Rear Delt Fly", ["rear_delt"], ["mid_back"], "dumbbell", "pull", False),
    ("面拉", "Face Pull", ["rear_delt"], ["traps", "mid_back"], "cable", "pull", False),
    # 背
    ("引体向上", "Pull-up", ["lats"], ["biceps", "mid_back"], "bodyweight", "pull", True),
    ("高位下拉", "Lat Pulldown", ["lats"], ["biceps", "mid_back"], "cable", "pull", True),
    ("杠铃划船", "Barbell Row", ["mid_back"], ["lats", "biceps", "rear_delt", "lower_back"], "barbell", "pull", True),
    ("哑铃单臂划船", "One-arm DB Row", ["lats"], ["mid_back", "biceps"], "dumbbell", "pull", True),
    ("坐姿绳索划船", "Seated Cable Row", ["mid_back"], ["lats", "biceps"], "cable", "pull", True),
    ("硬拉", "Deadlift", ["hamstrings"], ["glutes", "lower_back", "traps", "forearm", "mid_back"], "barbell", "pull", True),
    ("直腿硬拉", "Romanian Deadlift", ["hamstrings"], ["glutes", "lower_back"], "barbell", "pull", True),
    ("山羊挺身", "Back Extension", ["lower_back"], ["glutes", "hamstrings"], "bodyweight", "pull", False),
    # 手臂
    ("杠铃弯举", "Barbell Curl", ["biceps"], ["forearm"], "barbell", "pull", False),
    ("哑铃弯举", "Dumbbell Curl", ["biceps"], ["forearm"], "dumbbell", "pull", False),
    ("锤式弯举", "Hammer Curl", ["biceps"], ["forearm"], "dumbbell", "pull", False),
    ("绳索下压", "Triceps Pushdown", ["triceps"], [], "cable", "push", False),
    ("窄距卧推", "Close-grip Bench", ["triceps"], ["chest", "front_delt"], "barbell", "push", True),
    ("过顶臂屈伸", "Overhead Extension", ["triceps"], [], "dumbbell", "push", False),
    ("腕弯举", "Wrist Curl", ["forearm"], [], "dumbbell", "pull", False),
    # 腿
    ("杠铃深蹲", "Barbell Squat", ["quads"], ["glutes", "lower_back", "abs"], "barbell", "legs", True),
    ("前蹲", "Front Squat", ["quads"], ["glutes", "abs"], "barbell", "legs", True),
    ("腿举", "Leg Press", ["quads"], ["glutes"], "machine", "legs", True),
    ("保加利亚分腿蹲", "Bulgarian Split Squat", ["quads"], ["glutes", "hamstrings"], "dumbbell", "legs", True),
    ("箭步蹲", "Lunge", ["quads"], ["glutes", "hamstrings"], "dumbbell", "legs", True),
    ("腿屈伸", "Leg Extension", ["quads"], [], "machine", "legs", False),
    ("腿弯举", "Leg Curl", ["hamstrings"], ["calves"], "machine", "legs", False),
    ("臀桥", "Hip Thrust", ["glutes"], ["hamstrings"], "barbell", "legs", True),
    ("髋外展", "Hip Abduction", ["glutes"], [], "machine", "legs", False),
    ("站姿提踵", "Standing Calf Raise", ["calves"], [], "machine", "legs", False),
    ("坐姿提踵", "Seated Calf Raise", ["calves"], [], "machine", "legs", False),
    # 核心
    ("平板支撑", "Plank", ["abs"], ["obliques", "lower_back"], "bodyweight", "core", False),
    ("卷腹", "Crunch", ["abs"], [], "bodyweight", "core", False),
    ("悬垂举腿", "Hanging Leg Raise", ["abs"], ["hip_flexor"], "bodyweight", "core", False),
    ("俄罗斯转体", "Russian Twist", ["obliques"], ["abs"], "bodyweight", "core", False),
    ("农夫行走", "Farmer's Walk", ["forearm"], ["traps", "abs", "obliques"], "dumbbell", "core", True),
]


def seed_exercises(db) -> int:
    """首次启动时写入内置动作库。"""
    from .models import Exercise

    if db.query(Exercise).filter(Exercise.is_custom == False).count() > 0:  # noqa: E712
        return 0
    n = 0
    for name, en, primary, secondary, equip, cat, compound in _EX:
        db.add(
            Exercise(
                name=name,
                name_en=en,
                primary_muscles=json.dumps(primary, ensure_ascii=False),
                secondary_muscles=json.dumps(secondary, ensure_ascii=False),
                equipment=equip,
                category=cat,
                is_compound=compound,
                is_custom=False,
            )
        )
        n += 1
    db.commit()
    return n