import cv2 as cv
from cv2.typing import Rect
import numpy as np
import pyautogui as gui
from PIL import ImageGrab
from mss.base import MSSBase
from mss.models import Monitor
from enum import IntEnum
from .types import Image
from typing import Tuple, List, Any
from .utils import dbg_show, dbg_profile


class CTopology(IntEnum):
    NEXT = 0
    PREVIOUS = 1
    FIRST_CHILD = 2
    PARENT = 3
    NULL = -1


class RectLayout(IntEnum):
    X_COORD = 0
    Y_COORD = 1
    WIDTH = 2
    HEIGHT = 3


def screen_cap(
    sct: MSSBase, b_rect: Rect
) -> Image:
    """
    Sends a screenshot of the current display. Passing b_rect with just -1 
    makes it capture the entire display.Scaling will be ignored if a capture
    target is provided via b_rect
    """
    no_cptr_trgt: bool = all([v == -1 for v in b_rect])
    monitor: Monitor = (
        sct.monitors[1]
        if no_cptr_trgt
        else {k: int(v) for k, v in zip(("left", "top", "width", "height"), b_rect)}
    )
    scr: Image = np.asarray(sct.grab(monitor))
    return scr


def detect_grid(img: Image) -> Tuple[bool, Image, Rect]:
    """
    Detects a 2048 grid on the display and returns the status, image, and location.
    """
    CLEARANCE: float = 0.01
    MINIMUM: float = 500.0
    CNNY_UPPER: float = 180.0
    CNNY_LOWER: float = 60.0
    ASP_MIN: float = 1.0 - CLEARANCE
    ASP_MAX: float = 1.0 + CLEARANCE
    PADDING: int = 10

    # Filter by no. of children.
    cn: Image = cv.Canny(img, CNNY_LOWER, CNNY_UPPER)
    contours, hrchy = cv.findContours(cn, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    wch_msk: np.ndarray[Any, Any] = hrchy[0, :, CTopology.FIRST_CHILD] != CTopology.NULL
    hrchy_wch: np.ndarray[Any, Any] = hrchy[0, wch_msk]
    cnt_wch: List[np.ndarray[Any, Any]] = [
        cn for i, cn in enumerate(contours) if wch_msk[i]
    ]
    # Filter by aspect ratio.
    cnt_rect: np.ndarray[Any, Any] = np.array(
        [cv.boundingRect(cnt) for cnt in cnt_wch], dtype=np.float32
    )
    cnt_arr: np.ndarray[Any, Any] = np.array(
        [cv.contourArea(cnt) for cnt in cnt_wch], dtype=np.float32
    )
    cnt_asp: np.ndarray[Any, Any] = (
        cnt_rect[:, RectLayout.WIDTH] / cnt_rect[:, RectLayout.HEIGHT]
    )
    sq_msk: np.ndarray[Any, Any] = ((ASP_MIN < cnt_asp) & (cnt_asp < ASP_MAX)) & (
        cnt_arr > MINIMUM
    )
    hrchy_sq: np.ndarray[Any, Any] = hrchy_wch[sq_msk]
    cnt_sq: np.ndarray[Any, Any] = cnt_rect[sq_msk]

    # NOTE: It is INCREDIBLY important that we allow for more than 16 children.
    # although this would allow boards that aren't 4x4 to pass the filter,
    # doing so makes it incredibly sensitive to the noise of single contour being added
    # within the parent. That needs to be taken into account.
    # Filter by no. of children. Must be N <= 16.
    # Will be fooled by grids of the same dimensions but isn't the game.
    # But it isn't really a bad compromise.
    grid_idx: int = -1
    GRID_CELLS: int = 16
    for i, h in enumerate(hrchy_sq):
        fchild: np.ndarray[Any, Any] = hrchy[0][h[CTopology.FIRST_CHILD]]
        for _ in range(GRID_CELLS - 1):
            if fchild[CTopology.NEXT] == CTopology.NULL:
                break
            fchild = hrchy[0][fchild[CTopology.NEXT]]
        else:
            grid_idx = i
            break
    if grid_idx == -1:
        return (False, img, (-1, -1, -1, -1))
    gx, gy, gw, gh = [int(g) for g in cnt_sq[grid_idx]]
    scl_img: np.ndarray[Any, Any] = img[gy : gy + gh, gx : gx + gw, :]
    return (True, scl_img, (gx - PADDING // 2, gy - PADDING // 2, gw + PADDING, gh + PADDING))


def crp(img: Image, prcnt: float) -> Image:
    cx, cy = int(img.shape[1] * prcnt), int(img.shape[0] * prcnt)
    w, h = img.shape[1], img.shape[0]
    return img[cx : w - cx, cy : h - cy]


def detect_digits(grid: Image) -> Tuple[bool, List[Image]]:
    """
    Detects and crops cells of the digits in the grid.
    """
    CNNY_UPPER: float = 180.0
    CNNY_LOWER: float = 60.0
    EDGE_TOLERANCE: int = 5
    CLL_CRP: float = 0.20
    CLL_X_BIAS: int = 0
    CLL_Y_BIAS: int = -1
    GRID_CLL_COUNT: int = 16
    INVERT_THRESHOLD: float = 128.0
    CLL_SCL_FCTR: int = 3

    # Preprocess grid and find cells.
    cgrid: Image = crp(grid, 0.02)
    cn: Image = cv.Canny(cgrid, CNNY_LOWER, CNNY_UPPER)
    cntrs, _ = cv.findContours(cn, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    cells: List[Rect] = [cv.boundingRect(c) for c in cntrs]
    cells.sort(key=lambda e: (e[1] // EDGE_TOLERANCE, e[0]))
    clpx: List[Image] = []

    # Crop and get average area.
    avg: float = 0.0
    for i, cl in enumerate(cells):
        x, y, w, h = cl
        nw, nh = int(w * (1 - CLL_CRP)), int(h * (1 - CLL_CRP))
        nx, ny = x + ((w - nw) // 2), y + ((h - nh) // 2)
        nx += CLL_X_BIAS
        ny += CLL_Y_BIAS
        cells[i] = (nx, ny, nw, nh)
        avg += nw * nh
    avg /= len(cells)
    th: float = avg * 0.15

    # Threshold by central tendency.
    for i, cl in enumerate(cells):
        x, y, w, h = cl
        if abs(avg - (w * h)) < th:
            cll_gscl: Image = cv.cvtColor(
                cgrid[y : y + h, x : x + w], cv.COLOR_RGB2GRAY
            )
            _, cth = cv.threshold(
                cll_gscl,
                0,
                255,
                cv.THRESH_BINARY + cv.THRESH_OTSU,
            )
            m: float = float(np.mean(cth.astype(np.float32)))
            if m > INVERT_THRESHOLD:
                cth = np.where(cth < m, 255, 0).astype(np.uint8)
            clpx.append(
                cv.resize(
                    cth,
                    (cth.shape[1] * CLL_SCL_FCTR, cth.shape[0] * CLL_SCL_FCTR),
                    interpolation=cv.INTER_LINEAR_EXACT,
                )
            )
    if len(clpx) != GRID_CLL_COUNT:
        return (False, [])
    return (True, clpx)


def get_state(digits: List[Image]) -> Tuple[bool, Tuple[int, ...]]:
    """
    Extracts the digits from the list of images.
    """
    CNNY_UPPER: float = 180.0
    CNNY_LOWER: float = 60.0
    for d in digits:
        cnd: Image = cv.Canny(d, CNNY_LOWER, CNNY_UPPER)
        dbg_show(d)

    # TODO:
    # Find a way to determine cells that are empty or not.
    #   - Filter via the entropy of each row with cells in
    #     the center weighed more than at the edges.
    #     basically allowing us to get a feel for which cells
    #     have more "action" in the middle. Thus, empty or not.
    # Find a way to reliably get the digits without getting an OCR library.
    #   - Bootstrap 2 and 4 via child contour recognition. (4 has a hole, 2 doesn't.)
    #   - Subdivide and normalize image into a 5x5, do a dot product based on pre-determined weights
    #     (Center pixels matter more). Translate into high dimensional vector, and add a digit dimension
    #     with a large weight. 2 digits and 4 digits should be far apart. Then track merges and learn as you
    #     go.

    return (True, ())
