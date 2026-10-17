"""AI 教练：调用 DeepSeek（OpenAI 兼容协议）。"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from .config import settings
from .llm_config import LlmCfg

SYSTEM_PROMPT = """你是一个由三位专家组成的私人教练团队，服务同一个用户：

1. 营养师：根据用户的力量训练量、跑步消耗、目标（减脂同时增肌）计算热量与宏量营养素，
   给出具体可执行的饮食建议。要具体到食物和克数，不要泛泛而谈。关注蛋白质摄入、训练日碳水时机。
2. 跑步数据分析师：解读配速、心率区间分布、有氧解耦、步频、训练负荷（TRIMP/ACWR）。
   指出有氧能力的变化趋势、心率漂移、配速稳定性问题，并给出下一次跑步的具体建议。
3. 力量教练：根据肌肉覆盖热力图、推拉腿平衡、容量趋势、个人记录，指出薄弱环节并调整计划。

铁律：
- 只依据提供的数据说话。数据不足时明确说「这项数据还缺」，不要编造。
- 结论要给出具体数字和动作，例如「周三加 2 组面拉，3×15」而不是「多练背」。
- 优先解决风险项：负荷过高、肌肉严重失衡、蛋白质不足、减重过快。
- 用户目标是「减脂同时增肌」，属于身体重组，体重可能不怎么变，要看围度和训练表现。
- 用中文回答，结构化输出，篇幅控制在 500 字以内，除非用户明确要求详细。
- 不要用「作为AI」之类的免责声明。你就是他的教练。"""


class LLMNotConfigured(RuntimeError):
    pass


def _client(cfg: LlmCfg) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=cfg.base_url.rstrip("/"),
        timeout=settings.LLM_TIMEOUT,
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        },
    )


def is_configured(cfg: LlmCfg | None = None) -> bool:
    return bool(cfg.api_key) if cfg is not None else bool(settings.LLM_API_KEY)


async def chat(cfg: LlmCfg, messages: list[dict], temperature: float = 0.6, max_tokens: int = 2000) -> str:
    if not is_configured():
        raise LLMNotConfigured("未配置 GRF_LLM_API_KEY，请在 .env 中填写 DeepSeek API Key")
    payload = {
        "model": cfg.model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    async with _client(cfg) as c:
        r = await c.post("/chat/completions", json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"LLM 调用失败 {r.status_code}: {r.text[:300]}")
        data = r.json()
    return data["choices"][0]["message"]["content"]


async def chat_stream(cfg: LlmCfg, messages: list[dict], temperature: float = 0.6) -> AsyncIterator[str]:
    """流式输出，用于网页逐字显示。"""
    if not is_configured(cfg):
        raise LLMNotConfigured("未配置 API Key")
    payload = {
        "model": cfg.model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "temperature": temperature,
        "stream": True,
    }
    async with _client(cfg) as c:
        async with c.stream("POST", "/chat/completions", json=payload) as r:
            if r.status_code >= 400:
                body = await r.aread()
                raise RuntimeError(f"LLM 调用失败 {r.status_code}: {body[:300]!r}")
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                chunk = line[6:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                    delta = obj["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def analyze_meal_image(cfg: LlmCfg, image_b64: str, mime: str = "image/jpeg", note: str = "") -> dict:
    """用 DeepSeek 原生多模态（deepseek-flash）识别餐食，返回结构化宏量。"""
    if not is_configured(cfg):
        raise LLMNotConfigured("未配置 API Key")

    prompt = (
        "你是营养师。识别这张照片里的食物，估算每种食物的重量（克）和营养。\n"
        "只输出 JSON，不要任何解释、不要 markdown 代码块。格式：\n"
        '{"items":[{"name":"食物名(中文)","grams":120,"kcal":200,'
        '"protein_g":10,"carb_g":25,"fat_g":6}],'
        '"confidence":"high|medium|low","note":"一句话说明估算依据或不确定的地方"}\n'
        "规则：\n"
        "- 中餐常见菜按常见份量估算；能分辨出主食/蛋白质/蔬菜就分开列。\n"
        "- 重量是「可食部分」的克数。\n"
        "- 看不清或不确定的把 confidence 设为 low。\n"
        "- 只列食物，不要列餐具。"
    )
    if note:
        prompt += f"\n用户补充说明：{note}"

    payload = {
        "model": cfg.vision_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"},
                    },
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
        "stream": False,
    }
    async with _client(cfg) as c:
        r = await c.post("/chat/completions", json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"视觉模型调用失败 {r.status_code}: {r.text[:300]}")
        data = r.json()
    text = data["choices"][0]["message"]["content"].strip()

    # 容忍模型偶尔包一层 ```json
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"items": [], "confidence": "low", "note": f"解析失败，原始输出：{text[:300]}"}


def build_context(
    profile: dict,
    run_summary: dict | None = None,
    strength_summary: dict | None = None,
    nutrition_summary: dict | None = None,
    extra: str = "",
) -> str:
    """把结构化数据压成给模型的上下文。"""
    parts = ["## 用户档案"]
    parts.append(json.dumps(profile, ensure_ascii=False, indent=1, default=str))

    if run_summary:
        parts.append("\n## 跑步数据")
        parts.append(json.dumps(run_summary, ensure_ascii=False, indent=1, default=str))
    if strength_summary:
        parts.append("\n## 力量训练数据")
        parts.append(json.dumps(strength_summary, ensure_ascii=False, indent=1, default=str))
    if nutrition_summary:
        parts.append("\n## 营养数据")
        parts.append(json.dumps(nutrition_summary, ensure_ascii=False, indent=1, default=str))
    if extra:
        parts.append("\n## 补充说明")
        parts.append(extra)
    return "\n".join(parts)