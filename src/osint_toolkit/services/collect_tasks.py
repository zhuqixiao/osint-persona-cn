"""采集任务公平调度 / Fair collect task scheduling."""

from __future__ import annotations


def build_fair_collect_tasks(
    queries: list[str] | None = None,
    sources: list[str] | None = None,
    *,
    queries_by_source: dict[str, list[str]] | None = None,
    max_tasks: int,
) -> list[tuple[str, str]]:
    """Fair round-robin across (source, query) pairs."""
    if max_tasks <= 0:
        return []
    sources = list(sources or [])
    if queries_by_source:
        per_source = {s: list(queries_by_source.get(s) or []) for s in sources if queries_by_source.get(s)}
        if not per_source:
            return []
        tasks: list[tuple[str, str]] = []
        depth = 0
        while len(tasks) < max_tasks:
            progressed = False
            for source in sources:
                qs = per_source.get(source) or []
                if depth < len(qs):
                    tasks.append((source, qs[depth]))
                    progressed = True
                    if len(tasks) >= max_tasks:
                        break
            if not progressed:
                break
            depth += 1
        return tasks

    queries = list(queries or [])
    if not queries or not sources:
        return []
    per_query = [[(source, q) for source in sources] for q in queries]
    tasks = []
    depth = 0
    while len(tasks) < max_tasks:
        progressed = False
        for queue in per_query:
            if depth < len(queue):
                tasks.append(queue[depth])
                progressed = True
                if len(tasks) >= max_tasks:
                    break
        if not progressed:
            break
        depth += 1
    return tasks
