"""Estimate transforms from user-selected control point pairs."""

from .models import ControlPointPair, Transform

MINIMUM_POINTS = {"translation": 1, "similarity": 2, "affine": 3}


def _points(pairs):
    result = []
    for pair in pairs:
        if isinstance(pair, ControlPointPair):
            source, reference = pair.source, pair.reference
        else:
            source, reference = pair
        if len(source) != 2 or len(reference) != 2:
            raise ValueError("control points must contain x and y")
        result.append(((float(source[0]), float(source[1])),
                       (float(reference[0]), float(reference[1]))))
    return result


def _solve_least_squares(rows, values, variables):
    # Normal equations keep this core dependency-free. Pivot checks also provide
    # a deterministic diagnostic for collinear/otherwise unsolvable geometry.
    a = [[sum(row[i] * row[j] for row in rows) for j in range(variables)]
         for i in range(variables)]
    b = [sum(row[i] * value for row, value in zip(rows, values))
         for i in range(variables)]
    scale = max((abs(v) for row in a for v in row), default=1.0) or 1.0
    for col in range(variables):
        pivot = max(range(col, variables), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) <= 1e-12 * scale:
            raise ValueError("control-point geometry is degenerate; transform cannot be solved")
        a[col], a[pivot] = a[pivot], a[col]
        b[col], b[pivot] = b[pivot], b[col]
        divisor = a[col][col]
        for j in range(col, variables):
            a[col][j] /= divisor
        b[col] /= divisor
        for row in range(variables):
            if row == col:
                continue
            factor = a[row][col]
            for j in range(col, variables):
                a[row][j] -= factor * a[col][j]
            b[row] -= factor * b[col]
    return b


def estimate_transform(pairs, kind="affine"):
    """Return the least-squares transform mapping source points to reference.

    ``kind`` is ``translation``, ``similarity`` (rotation/uniform scale), or
    ``affine``. Duplicate points are rejected instead of silently reducing rank.
    """
    kind = str(kind).lower()
    if kind not in MINIMUM_POINTS:
        raise ValueError("kind must be translation, similarity, or affine")
    pairs = _points(list(pairs))
    if len(pairs) < MINIMUM_POINTS[kind]:
        raise ValueError("%s transform requires at least %d control point(s)" %
                         (kind, MINIMUM_POINTS[kind]))
    sources = [p[0] for p in pairs]
    references = [p[1] for p in pairs]
    if len(set(sources)) != len(sources) or len(set(references)) != len(references):
        raise ValueError("duplicate control points are not allowed")

    if kind == "translation":
        tx = sum(q[0] - p[0] for p, q in pairs) / len(pairs)
        ty = sum(q[1] - p[1] for p, q in pairs) / len(pairs)
        return Transform(((1.0, 0.0, tx), (0.0, 1.0, ty),
                          (0.0, 0.0, 1.0)), kind)

    rows, values = [], []
    for (x, y), (u, v) in pairs:
        if kind == "similarity":
            rows.extend(((x, -y, 1.0, 0.0), (y, x, 0.0, 1.0)))
        else:
            rows.extend(((x, y, 1.0, 0.0, 0.0, 0.0),
                         (0.0, 0.0, 0.0, x, y, 1.0)))
        values.extend((u, v))
    solution = _solve_least_squares(rows, values, len(rows[0]))
    if kind == "similarity":
        a, b, tx, ty = solution
        matrix = ((a, -b, tx), (b, a, ty), (0.0, 0.0, 1.0))
    else:
        a, b, tx, c, d, ty = solution
        matrix = ((a, b, tx), (c, d, ty), (0.0, 0.0, 1.0))
    return Transform(matrix, kind)
