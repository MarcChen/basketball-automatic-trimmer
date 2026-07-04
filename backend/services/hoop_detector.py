from typing import Optional

import cv2
import numpy as np

ORANGE_HSV_LOW = np.array([5, 50, 50])
ORANGE_HSV_HIGH = np.array([25, 255, 255])


def find_white_rectangles(
    gray: np.ndarray,
    min_area: int = 2000,
    max_area: int = 200000,
    aspect_ratio_range: tuple[float, float] = (0.5, 3.0),
) -> list[tuple[int, int, int, int]]:
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectangles = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio_range[0] <= aspect_ratio <= aspect_ratio_range[1] and area >= w * h * 0.5:
                rectangles.append((x, y, w, h))

    return rectangles


def detect_orange_circles(
    mask: np.ndarray,
    dp: float = 1.5,
    min_dist: int = 30,
    param1: float = 100,
    param2: float = 25,
    min_radius: int = 15,
    max_radius: int = 150,
) -> np.ndarray:
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    blurred = cv2.medianBlur(mask, 5)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=dp,
        minDist=min_dist,
        param1=param1,
        param2=param2,
        minRadius=min_radius,
        maxRadius=max_radius,
    )
    return circles if circles is not None else np.array([])


def auto_detect_hoop(
    frame: np.ndarray,
    use_backboard_constraint: bool = True,
) -> tuple[int, int, int] | None:
    height, width = frame.shape[:2]

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    orange_mask = cv2.inRange(hsv, ORANGE_HSV_LOW, ORANGE_HSV_HIGH)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_CLOSE, kernel)

    backboard_rect = None
    if use_backboard_constraint:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rectangles = find_white_rectangles(gray)
        if rectangles:
            backboard_rect = max(rectangles, key=lambda r: r[2] * r[3])

    circles = detect_orange_circles(
        orange_mask,
        dp=1.5,
        min_dist=max(20, int(height / 30)),
        param1=100,
        param2=25,
        min_radius=int(height / 40),
        max_radius=int(height / 8),
    )

    if circles.size == 0:
        return None

    valid_circles = []
    for circle in circles[0]:
        cx, cy, r = circle

        if backboard_rect is not None:
            bx, by, bw, bh = backboard_rect
            backboard_cx = bx + bw / 2
            backboard_cy = by + bh / 2
            dist = np.sqrt((cx - backboard_cx) ** 2 + (cy - backboard_cy) ** 2)
            expected_rim_radius = bw / 4
            if dist < bw and abs(r - expected_rim_radius) < bw / 2:
                valid_circles.append((cx, cy, r, dist))
        else:
            if height / 40 < r < height / 6:
                valid_circles.append((cx, cy, r, 0))

    if not valid_circles:
        return None

    if backboard_rect is not None:
        valid_circles.sort(key=lambda c: c[3])
    else:
        valid_circles.sort(key=lambda c: -c[2])

    best = valid_circles[0]
    return (int(best[0]), int(best[1]), int(best[2]))


def normalize_hoop_position(
    hoop: tuple[int, int, int],
    frame_width: int,
    frame_height: int,
) -> tuple[float, float, float]:
    x, y, r = hoop
    min_dim = min(frame_width, frame_height)
    return (x / frame_width, y / frame_height, r / min_dim if min_dim > 0 else 0.0)
