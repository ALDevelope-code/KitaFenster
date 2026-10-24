"""Geschlossene STL-Netze und Bauraum pruefen."""
import collections
from pathlib import Path
import re

def mesh_check(path: Path, xy_limit: float | None = 230) -> str:
    vertices = [tuple(round(float(v), 5) for v in m) for m in re.findall(
        r"vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)",
        path.read_text(encoding="ascii"))]
    assert vertices and len(vertices) % 3 == 0, "Leeres/ungueltiges STL"
    triangles = [vertices[i:i+3] for i in range(0, len(vertices), 3)]
    edges: collections.Counter = collections.Counter()
    directions: collections.Counter = collections.Counter()
    graph: dict[tuple, set] = collections.defaultdict(set)
    for a, b, c in triangles:
        assert len({a, b, c}) == 3, "Entartete Dreiecke"
        for p, q in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((p, q)))] += 1
            directions[(p, q)] += 1
            graph[p].add(q)
            graph[q].add(p)
    assert all(n == 2 for n in edges.values()), "Offene/nicht-mannigfaltige Kanten"
    assert all(directions[(p, q)] == directions[(q, p)] for p, q in directions), "Inkonsistente Normalen"
    pending = set(graph)
    components = 0
    while pending:
        components += 1
        stack = [pending.pop()]
        while stack:
            for neighbour in graph[stack.pop()] & pending:
                pending.remove(neighbour)
                stack.append(neighbour)
    assert components == 1, "Unverbundene Teilkoerper"
    extent = [max(p[j] for p in vertices)-min(p[j] for p in vertices) for j in range(3)]
    if xy_limit is not None:
        assert 0 < xy_limit <= 256
        assert max(extent[:2]) < xy_limit and extent[2] < 256, "Zu gross fuer geplante P1-Platzierung"
    return f"geschlossen, orientiert, 1 Koerper; {extent[0]:.2f} x {extent[1]:.2f} x {extent[2]:.2f} mm"
