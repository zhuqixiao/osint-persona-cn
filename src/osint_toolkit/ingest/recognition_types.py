"""行为认可事件类型 / Recognition event taxonomy (shared with persona)."""

from __future__ import annotations

# Same semantics as persona.behavior_signals.INVENTORY_SNAPSHOT_TYPES
INVENTORY_SNAPSHOT_TYPES = frozenset(
    {
        "bilibili_follow",
        "bilibili_fav",
        "zhihu_fav",
        "zhihu_follow",
    }
)

RECOGNITION_EVENT_TYPES: dict[str, dict[str, str]] = {
    "zhihu_vote": {
        "platform": "zhihu",
        "platform_label": "知乎",
        "action": "vote",
        "action_label": "赞同",
        "group": "recent",
    },
    "zhihu_fav": {
        "platform": "zhihu",
        "platform_label": "知乎",
        "action": "favorite",
        "action_label": "收藏",
        "group": "inventory",
    },
    "bilibili_like": {
        "platform": "bilibili",
        "platform_label": "B站",
        "action": "like",
        "action_label": "点赞",
        "group": "recent",
    },
    "bilibili_coin": {
        "platform": "bilibili",
        "platform_label": "B站",
        "action": "coin",
        "action_label": "投币",
        "group": "recent",
    },
    "bilibili_fav": {
        "platform": "bilibili",
        "platform_label": "B站",
        "action": "favorite",
        "action_label": "收藏",
        "group": "inventory",
    },
    "bilibili_comment_post": {
        "platform": "bilibili",
        "platform_label": "B站",
        "action": "comment",
        "action_label": "评论",
        "group": "recent",
    },
    "bilibili_comment_like": {
        "platform": "bilibili",
        "platform_label": "B站",
        "action": "comment_like",
        "action_label": "赞评论",
        "group": "recent",
    },
    "github_star": {
        "platform": "github",
        "platform_label": "GitHub",
        "action": "star",
        "action_label": "Star",
        "group": "recent",
    },
}

RECENT_EVENT_TYPES = frozenset(
    et for et, meta in RECOGNITION_EVENT_TYPES.items() if meta.get("group") == "recent"
)
INVENTORY_EVENT_TYPES = frozenset(
    et for et, meta in RECOGNITION_EVENT_TYPES.items() if meta.get("group") == "inventory"
)
