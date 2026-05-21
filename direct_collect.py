from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# =========================
# Settings you can edit
# =========================

OUTPUT_FILE = Path("output/comments.txt")
MAX_ITEMS = 2000
MIN_TOP_RATIO = 0.08
MIN_COMMENT_CHARS = 4
MAX_STUCK_ROUNDS = 80
RESET_OUTPUT_ON_START = True

EXPAND_TEXTS = ("展开", "全文", "查看更多", "展开全部", "显示更多")


# =========================
# Filtering rules
# =========================

UI_BLACKLIST = {
    "进店",
    "客服",
    "加购物车",
    "立即购买",
    "图集",
    "成分",
    "¥",
    "全部",
    "综合",
    "最新",
    "有用",
    "回复",
    "被折叠评价",
    "此用户未填写评价内容",
    "展开",
    "收起",
    "返回",
    "评价",
    "商品评价",
    "全部评价",
    "用户评价",
    "买家评价",
    "图/视频",
    "追评",
    "正品",
    "回头客",
    "好评",
    "中评",
    "差评",
    "为你挑选真实、有帮助的评价",
}

SHORT_TAGS = {
    "口感很好",
    "日期新鲜",
    "味道好喝",
    "性价比高",
    "包装很好",
    "发货快",
    "物流快",
    "服务好",
    "值得回购",
    "营养丰富",
    "适合儿童",
    "钙含量高",
}

REVIEW_CLUES = {
    "好喝",
    "难喝",
    "味道",
    "口感",
    "日期",
    "新鲜",
    "保质期",
    "包装",
    "奶香",
    "奶味",
    "浓",
    "淡",
    "甜",
    "酸",
    "顺滑",
    "回购",
    "满意",
    "孩子",
    "早餐",
    "牛奶",
}


@dataclass(slots=True)
class TextNode:
    text: str
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0


def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"(外观包装|口感味道|营养成分|性价比|整体评价|用户.*?追评|系统标签)[:：]", "", text)
    text = re.sub(r"https?://\S+", "[LINK]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1[3-9]\d{9}\b", "[CONTACT]", text)
    text = re.sub(r"[\w.-]*\*{2,}[\w.-]*", "[MASKED_USER]", text)
    text = text.replace("\n", " ")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0\u3000\r\t]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_metadata(text: str) -> bool:
    text = clean_text(text)
    return bool(
        re.fullmatch(r"(昨天|今天|刚刚)", text)
        or re.fullmatch(r"\d+\s*(秒前|分钟前|小时前|天前|个月前|年前)", text)
        or re.fullmatch(r"浏览\s*\d+", text)
        or re.fullmatch(r"\d+\s*浏览", text)
    )


def is_product_spec(text: str) -> bool:
    text = clean_text(text)
    return bool(
        re.search(r"^\d+\s*(箱|盒|瓶|包|袋|罐)", text)
        or re.search(r"\d+\s*(ml|mL|ML|g|kg|L)\b", text)
        or re.search(r"\d+\s*[*xX×]\s*\d+", text)
    )


def is_masked_user(text: str) -> bool:
    text = clean_text(text)
    return text == "[MASKED_USER]" or bool(re.fullmatch(r".{0,4}\*{1,4}.{0,4}", text))


def has_review_clue(text: str) -> bool:
    return any(clue in text for clue in REVIEW_CLUES)


def should_skip(text: str) -> bool:
    text = clean_text(text)
    if not text:
        return True
    if text in UI_BLACKLIST or text in SHORT_TAGS:
        return True
    if is_masked_user(text):
        return True
    if is_metadata(text):
        return True
    if is_product_spec(text):
        return True
    if text.isdigit():
        return True
    if re.fullmatch(r"[\W_]+", text):
        return True
    if re.search(r"KB/s|MB/s|^\+\d+$", text):
        return True
    if re.search(r"箱】|发货|盒/|已售|去抢购|购物车|店铺销量|官方认证|正品保障|售后无忧", text):
        return True
    if len(text) < MIN_COMMENT_CHARS and not has_review_clue(text):
        return True
    if len(text) <= 8 and any(word in text for word in ("全部", "评价", "排序", "筛选", "客服")):
        return True
    return False


def is_candidate_comment(text: str) -> bool:
    text = clean_text(text)
    if should_skip(text):
        return False
    if re.search(r"[\u4e00-\u9fff]", text) is None:
        return False
    if len(text) >= 12:
        return True
    return has_review_clue(text)


# =========================
# UI Tree reading
# =========================

def parse_bounds(bounds: str) -> tuple[int, int, int, int]:
    nums = re.findall(r"\d+", bounds or "")
    if len(nums) == 4:
        return tuple(int(num) for num in nums)  # type: ignore[return-value]
    return 0, 0, 0, 0


def nodes_from_hierarchy(device: Any) -> list[TextNode]:
    try:
        try:
            xml_text = device.dump_hierarchy(compressed=False)
        except TypeError:
            xml_text = device.dump_hierarchy()
        root = ET.fromstring(xml_text)
    except Exception:
        return []

    nodes: list[TextNode] = []
    for node in root.iter("node"):
        raw = node.attrib.get("text") or node.attrib.get("content-desc") or ""
        text = clean_text(raw)
        if not text:
            continue
        left, top, right, bottom = parse_bounds(node.attrib.get("bounds", ""))
        nodes.append(TextNode(text=text, left=left, top=top, right=right, bottom=bottom))
    return nodes


def nodes_from_xpath(device: Any) -> list[TextNode]:
    nodes: list[TextNode] = []
    try:
        xpath_nodes = device.xpath("//android.widget.TextView").all()
    except Exception:
        return nodes

    for node in xpath_nodes:
        text = clean_text(getattr(node, "text", "") or "")
        if not text:
            continue
        left = top = right = bottom = 0
        bounds = getattr(node, "bounds", None)
        if isinstance(bounds, (list, tuple)) and len(bounds) >= 4:
            left, top, right, bottom = map(int, bounds[:4])
        elif hasattr(bounds, "left"):
            left = int(bounds.left)
            top = int(bounds.top)
            right = int(bounds.right)
            bottom = int(bounds.bottom)
        nodes.append(TextNode(text=text, left=left, top=top, right=right, bottom=bottom))
    return nodes


def get_text_nodes(device: Any) -> list[TextNode]:
    nodes = nodes_from_hierarchy(device)
    if not nodes:
        nodes = nodes_from_xpath(device)
    return sorted(nodes, key=lambda item: (item.top, item.left, item.text))


def click_expand_buttons(device: Any) -> int:
    clicked = 0
    for label in EXPAND_TEXTS:
        try:
            target = device(text=label)
            if target.exists:
                target.click()
                clicked += 1
                time.sleep(0.25)
        except Exception:
            continue
    return clicked


def save_comment(comment: str, collected: set[str]) -> bool:
    comment = clean_text(comment)
    if not comment or comment in collected:
        return False
    collected.add(comment)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("a", encoding="utf-8", newline="\n") as file:
        file.write(comment + "\n")
    print(f"[saved {len(collected)}] {comment[:90]}")
    return True


def page_fingerprint(nodes: list[TextNode]) -> str:
    visible = [node.text for node in nodes if node.text]
    return "|".join(visible[:80])


def connect_device() -> Any:
    try:
        import uiautomator2 as u2
    except ImportError:
        print("ERROR: uiautomator2 is not installed.")
        print("Run this first:")
        print("python -m pip install uiautomator2")
        raise SystemExit(1)
    return u2.connect()


def main() -> None:
    print("[Android UI Tree Review Collector] start")
    print("Open the phone to the real review text area before running.")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Max items: {MAX_ITEMS}")
    print()

    if RESET_OUTPUT_ON_START and OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    device = connect_device()
    screen_height = int(device.info.get("displayHeight") or 0)
    fringe_height = screen_height * MIN_TOP_RATIO

    collected: set[str] = set()
    stuck_count = 0
    last_fingerprint = ""

    while len(collected) < MAX_ITEMS:
        click_expand_buttons(device)
        time.sleep(0.45)

        try:
            nodes = get_text_nodes(device)
            current_fingerprint = page_fingerprint(nodes)
            page_new = 0

            for node in nodes:
                if node.top and node.top < fringe_height:
                    continue

                text = clean_text(node.text)
                if not is_candidate_comment(text):
                    continue

                if save_comment(text, collected):
                    page_new += 1
                    if len(collected) >= MAX_ITEMS:
                        break

            if page_new == 0 or current_fingerprint == last_fingerprint:
                stuck_count += 1
                if stuck_count % 8 == 0:
                    print(f"[swipe] no new comments for {stuck_count} rounds, long swipe")
                    device.swipe(0.5, 0.9, 0.5, 0.1, 0.05)
                else:
                    device.swipe(0.5, 0.82, 0.5, 0.25, 0.08)
            else:
                stuck_count = 0
                device.swipe(0.5, 0.85, 0.5, 0.2, 0.08)

            last_fingerprint = current_fingerprint

            if stuck_count >= MAX_STUCK_ROUNDS:
                print("[stop] too many rounds without new comments.")
                break

        except KeyboardInterrupt:
            print("Stopped by user.")
            break
        except Exception as exc:
            print(f"[warn] {exc}")
            time.sleep(1)

    print()
    print(f"Done. Saved {len(collected)} comments.")
    print(f"File: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

