"""Screen coordinates after rotation; the secondary percentage is independent of its side."""


def region_rects(size, split, has_secondary):
    width, height = size
    if not split.get("enabled") or not has_secondary:
        return {"main": (0, 0, width, height)}
    direction = split.get("direction", "auto")
    vertical = direction == "vertical" or (direction == "auto" and height > width)
    length = height if vertical else width
    secondary_length = max(1, min(length - 1, round(length * split.get("secondary_percent", 33) / 100)))
    main = 1 if split.get("main_position") == "second" else 0
    cut = secondary_length if main else length - secondary_length
    rectangles = (
        [(0, 0, width, cut), (0, cut, width, height - cut)]
        if vertical
        else [(0, 0, cut, height), (cut, 0, width - cut, height)]
    )
    return {"main": rectangles[main], "secondary": rectangles[1 - main]}
