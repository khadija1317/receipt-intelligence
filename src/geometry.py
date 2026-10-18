import statistics

ROW_TOL = 0.5  # decision 1: max y-distance between row members, in text heights


def box_geometry(piece):
    """Reduce one OCR piece (four corners) to the numbers the merge needs."""
    xs = [pt[0] for pt in piece["box"]]
    ys = [pt[1] for pt in piece["box"]]
    return {
        "text": piece["text"],
        "conf": piece["conf"],
        "x_left": min(xs),
        "x_right": max(xs),
        "y_center": (min(ys) + max(ys)) / 2,
        "h": max(ys) - min(ys),
    }


def group_rows(pieces, tol=ROW_TOL):
    """Group pieces into rows, then sort each row left to right."""
    boxes = sorted((box_geometry(p) for p in pieces), key=lambda b: b["y_center"])
    rows = []
    for b in boxes:
        if rows:
            row = rows[-1]
            row_y = sum(r["y_center"] for r in row) / len(row)
            row_h = statistics.median(r["h"] for r in row)
            limit = tol * min(row_h, b["h"])
            if abs(b["y_center"] - row_y) <= limit:
                row.append(b)
                continue
        rows.append([b])
    return [sorted(row, key=lambda r: r["x_left"]) for row in rows]