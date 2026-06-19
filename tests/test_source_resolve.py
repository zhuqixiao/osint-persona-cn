"""信源自动调度测试 / Source auto-route resolution tests."""

from osint_toolkit.collectors.source_resolve import blend_rule_and_ai_scores, resolve_search_sources
from osint_toolkit.collectors.source_routing import apply_source_routing, compute_source_scores, match_domain_route


def test_compute_scores_dev_tech_query():
    scores = compute_source_scores("如何评价开源 GLM-5.2")
    assert scores["github"] >= 45
    assert scores["juejin"] >= 45
    assert scores["weixin"] < 20


def test_gentle_auto_enables_github_for_glm():
    result = resolve_search_sources(
        "如何评价最新发布并开源的 GLM-5.2",
        ["zhihu", "bilibili", "web", "weixin"],
        profile="default",
        mode="gentle",
    )
    assert "github" in result["auto_enabled"]
    assert "github" in result["active_sources"]
    assert "weixin" in result["active_sources"]
    assert "bilibili" in result["active_sources"]


def test_user_comprehensive_native_not_skipped_without_domain_match():
    result = resolve_search_sources(
        "xyzzy专有模糊词",
        ["zhihu", "bilibili", "web"],
        mode="gentle",
    )
    assert set(result["active_sources"]) == {"zhihu", "bilibili", "web"}
    assert result["skipped"] == []


def test_gentle_skips_irrelevant_music_site_for_tech():
    result = resolve_search_sources(
        "GLM-5.2 开源 大模型",
        ["zhihu", "web", "netease_music", "kugou"],
        mode="gentle",
    )
    assert "netease_music" in result["skipped"]
    assert "kugou" in result["skipped"]


def test_off_mode_keeps_all_user_sources():
    result = resolve_search_sources(
        "GLM-5.2",
        ["zhihu", "weixin", "web"],
        mode="off",
    )
    assert set(result["active_sources"]) == {"zhihu", "weixin", "web"}
    assert result["auto_enabled"] == []


def test_zhihu_deep_profile_restricts_pool():
    result = resolve_search_sources(
        "周杰伦 新歌",
        ["zhihu", "bilibili", "web"],
        profile="zhihu_deep",
        mode="gentle",
    )
    assert result["active_sources"] == ["zhihu"]
    assert "bilibili" in result["skipped"]


def test_music_route_does_not_auto_enable_streaming_without_user_pick():
    result = apply_source_routing("晴天", ["zhihu", "bilibili", "web"], None)
    assert "netease_music" not in result["auto_enabled"]
    assert "netease_music" not in result["active_sources"]
    assert "bilibili" in result["active_sources"]


def test_music_route_uses_streaming_when_user_picked():
    result = apply_source_routing("晴天", ["zhihu", "bilibili", "netease_music", "web"], None)
    assert "netease_music" in result["active_sources"]
    assert "netease_music" not in result["auto_enabled"]


def test_match_music_route_requires_explicit_keywords():
    assert match_domain_route("晴天") is None
    route = match_domain_route("周杰伦 新歌 歌词")
    assert route is not None
    assert route["id"] == "music"


def _world_model_ai_plan() -> dict:
    return {
        "ai_invoked": True,
        "is_cryptic": True,
        "query_substance": "substantive",
        "auto_enable": ["bilibili", "github"],
        "source_scores": {
            "bilibili": {"score": 82, "tier": "strong", "reason": "科普讲解与讨论视频多"},
            "github": {"score": 72, "tier": "strong", "reason": "开源实现与论文代码"},
            "zhihu": {"score": 78, "tier": "strong", "reason": "概念讨论"},
            "web": {"score": 60, "tier": "medium", "reason": "综合检索"},
        },
    }


def test_ai_plan_auto_enables_bilibili_for_cryptic_tech_query():
    query = "神经辐射场表征"
    rule_scores = compute_source_scores(query)
    ai_plan = _world_model_ai_plan()
    blended, breakdown = blend_rule_and_ai_scores(rule_scores, ai_plan, is_cryptic=True)
    result = resolve_search_sources(
        query,
        ["zhihu", "web"],
        scores=blended,
        score_breakdown=breakdown,
        ai_plan=ai_plan,
        mode="gentle",
    )
    assert "bilibili" in result["auto_enabled"]
    assert "bilibili" in result["active_sources"]
    assert "github" in result["auto_enabled"]
    assert result["is_cryptic"] is True


def test_nonsense_plan_blocks_ai_auto_enable():
    ai_plan = {
        "ai_invoked": True,
        "query_substance": "nonsense",
        "auto_enable": ["github", "bilibili"],
        "source_scores": {
            "github": {"score": 95, "tier": "strong", "reason": "不应启用"},
            "bilibili": {"score": 90, "tier": "strong", "reason": "不应启用"},
        },
    }
    rule_scores = compute_source_scores("aaaaa")
    blended, breakdown = blend_rule_and_ai_scores(rule_scores, ai_plan, is_cryptic=False)
    result = resolve_search_sources(
        "aaaaa",
        ["zhihu", "web"],
        scores=blended,
        score_breakdown=breakdown,
        ai_plan=ai_plan,
        mode="gentle",
    )
    assert result["auto_enabled"] == []
    assert set(result["active_sources"]) == {"zhihu", "web"}


def test_ai_explicit_auto_enable_prioritized_under_cap():
    ai_plan = {
        "ai_invoked": True,
        "query_substance": "substantive",
        "auto_enable": ["github", "juejin", "v2ex", "hackernews", "reddit", "ithome", "sspai"],
        "source_scores": {
            sid: {"score": 80 - i, "tier": "strong", "reason": "相关"}
            for i, sid in enumerate(
                ["github", "juejin", "v2ex", "hackernews", "reddit", "ithome", "sspai"]
            )
        },
    }
    rule_scores = compute_source_scores("rust async runtime")
    blended, breakdown = blend_rule_and_ai_scores(rule_scores, ai_plan, is_cryptic=False)
    result = resolve_search_sources(
        "rust async runtime",
        ["zhihu", "web"],
        scores=blended,
        score_breakdown=breakdown,
        ai_plan=ai_plan,
        mode="gentle",
    )
    assert "github" in result["auto_enabled"]
    assert len(result["auto_enabled"]) <= 6
