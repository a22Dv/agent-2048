import cv2 as cv
import numpy as np
from cv2.typing import Rect
from copy import copy
from mss.base import MSSBase
from mss.models import Monitor
from enum import IntEnum
from .types import Image, Template
from typing import Tuple, List, Any, Dict, Set
from .utils import dbg_show, dbg_profile, dbg_close
from typing import NamedTuple

GRID_CLL_COUNT: int = 16


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


def screen_cap(sct: MSSBase, b_rect: Rect) -> Image:
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
    if hrchy is None:
        return (False, img, (-1, -1, -1, -1))
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
    GRID_CELLS: int = GRID_CLL_COUNT
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
    return (
        True,
        scl_img,
        (gx - PADDING // 2, gy - PADDING // 2, gw + PADDING, gh + PADDING),
    )


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
    EDGE_TOLERANCE: int = 10
    CLL_CRP: float = 0.15
    CLL_X_BIAS: int = 0
    CLL_Y_BIAS: int = -1
    INVERT_THRESHOLD: float = 128.0
    FILTER_THRESHOLD: float = 0.15
    DEVIATION_THRESHOLD: float = 1.5
    CLL_SCL_FCTR: int = 3

    # Preprocess grid and find cells, filter via area difference to largest contour.
    cgrid: Image = crp(grid, 0.015)
    cn: Image = cv.Canny(cgrid, CNNY_LOWER, CNNY_UPPER)
    cntrs, _ = cv.findContours(cn, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    cells: List[Rect] = [cv.boundingRect(c) for c in cntrs]
    mx_c: Rect = max(cells, key=lambda c: c[RectLayout.HEIGHT] * c[RectLayout.WIDTH])
    mxa_c: float = mx_c[RectLayout.HEIGHT] * mx_c[RectLayout.WIDTH]
    fc: List[Rect] = list(
        filter(
            lambda c: 1 - (c[RectLayout.HEIGHT] * c[RectLayout.WIDTH]) / mxa_c
            < FILTER_THRESHOLD,
            cells,
        )
    )
    fc.sort(
        key=lambda e: (
            e[RectLayout.Y_COORD] // EDGE_TOLERANCE,
            e[RectLayout.X_COORD] // EDGE_TOLERANCE,
        )
    )

    # Crop, adjust, and get average area.
    clpx: List[Image] = []
    avg: float = 0.0
    for i, cl in enumerate(fc):
        x, y, w, h = cl
        nw, nh = int(w * (1 - CLL_CRP)), int(h * (1 - CLL_CRP))
        nx, ny = x + ((w - nw) // 2), y + ((h - nh) // 2)
        nx += CLL_X_BIAS
        ny += CLL_Y_BIAS
        fc[i] = (nx, ny, nw, nh)
        avg += nw * nh
    avg /= len(fc)

    # Cannot filter the noise from the data.
    if len(fc) != GRID_CLL_COUNT:
        return (False, [])

    for i, cl in enumerate(fc):
        x, y, w, h = cl
        cll_gscl: Image = cv.cvtColor(cgrid[y : y + h, x : x + w], cv.COLOR_RGB2GRAY)

        # Standard deviation is used to threshold empty cells.
        std_dev: float = float(np.std(cll_gscl))
        _, cth = (
            cv.threshold(
                cll_gscl,
                128,
                255,
                cv.THRESH_BINARY + cv.THRESH_OTSU,
            )
            if std_dev > DEVIATION_THRESHOLD
            else (0.0, np.zeros(dtype=np.uint8, shape=cll_gscl.shape))
        )
        m: float = float(np.mean(cth.astype(np.float32)))
        if m > INVERT_THRESHOLD:
            cth = cv.bitwise_not(cth)
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


class Symbol(IntEnum):
    S0 = 0
    S1 = 1
    S2 = 2
    S3 = 3
    S4 = 4
    S5 = 5
    S6 = 6
    S7 = 7
    S8 = 8
    S9 = 9
    EMPTY = 10


TMPLT_X: int = 32
TMPLT_Y: int = 64
SYMBOL_COUNT: int = 11


class Entry(NamedTuple):
    dcount: int
    msd: int


class Recognizer:
    def __init__(self) -> None:
        self.bootstrapped: bool = False
        self.is_recognized: List[bool] = [False for _ in range(SYMBOL_COUNT)]
        self.templates: List[Template] = [
            (
                np.zeros(dtype=np.int32, shape=(TMPLT_X,)),
                np.zeros(dtype=np.int32, shape=(TMPLT_Y,)),
            )
            for _ in range(SYMBOL_COUNT)
        ]
        self.exp_diff: int = 2
        self.max_loss_y: float = TMPLT_X * ((TMPLT_Y * 255) ** self.exp_diff)
        self.max_loss_x: float = TMPLT_Y * ((TMPLT_X * 255) ** self.exp_diff)

    def reduce(self, img: Image) -> Template:
        """
        Normalizes and reduces the image into a pixel density histogram for both axes.
        """
        return (
            np.sum(img, axis=0, dtype=np.int32),
            np.sum(img, axis=1, dtype=np.int32),
        )

    def _getsim(self, tmplt: Template, sym: Symbol) -> float:
        a: Template = tmplt
        b: Template = self.templates[sym]
        ly: float = np.sum((a[0] - b[0]) ** self.exp_diff)
        lx: float = np.sum((a[1] - b[1]) ** self.exp_diff)
        lt: float = max(lx / self.max_loss_x, ly / self.max_loss_y)
        return 1 - lt

    def match(self, img: Image) -> Tuple[int, float]:
        """
        Returns the most likely match for any tile given.
        To be able to recognize new tiles, add_template() must
        be called before match().
        """
        CNNY_UPPER: float = 180.0
        CNNY_LOWER: float = 60.0

        cny: Image = cv.Canny(img, CNNY_LOWER, CNNY_UPPER)
        cntrs, _ = cv.findContours(cny, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        bboxes: List[Rect] = sorted(
            [cv.boundingRect(c) for c in cntrs],
            key=lambda e: e[RectLayout.X_COORD],
        )

        # Empty.
        if len(bboxes) == 0:
            return (0, 1.0)

        # Get similarity scores for each digit.
        dgts: List[Tuple[int, float]] = []
        for bbox in bboxes:
            x, y, w, h = bbox
            dgtsig: Template = self.reduce(
                cv.resize(img[y : y + h, x : x + w], (TMPLT_X, TMPLT_Y))
            )
            sim: List[float] = [
                self._getsim(dgtsig, Symbol(i)) for i in range(SYMBOL_COUNT)
            ]
            msym: int = max(range(10), key=lambda x: sim[x])
            dgts.append((msym, sim[msym]))
        pr = 0
        for s, _ in dgts:
            pr *= 10
            pr += s
        return (pr, sum([si for _, si in dgts]) / len(dgts))

    def add_template(self, img: Image, val: int) -> None:
        """
        Parses an image and gets the constituent digits.
        Updates internal templates based on value/label provided.
        """
        CNNY_UPPER: float = 180.0
        CNNY_LOWER: float = 60.0
        cny: Image = cv.Canny(img, CNNY_LOWER, CNNY_UPPER)
        cntrs, _ = cv.findContours(cny, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        bboxes: List[Rect] = sorted(
            [cv.boundingRect(c) for c in cntrs],
            key=lambda e: e[RectLayout.X_COORD],
            reverse=True,
        )
        if len(bboxes) == 0 and not self.is_recognized[Symbol.EMPTY]:
            rsz_img: Image = cv.resize(img, (TMPLT_X, TMPLT_Y))
            self.templates[Symbol.EMPTY] = self.reduce(rsz_img)
        n: int = val

        for bbox in bboxes:
            x, y, w, h = bbox
            c_digit: int = n % 10
            n //= 10
            if self.is_recognized[c_digit]:
                continue
            rsz_digit: Image = cv.resize(img[y : y + h, x : x + w], (TMPLT_X, TMPLT_Y))
            self.templates[c_digit] = self.reduce(rsz_digit)
            self.is_recognized[c_digit] = True

    def bootstrap(self, clls: List[Image]) -> None:
        """
        Bootstraps the recognizer on the digits.
        The image list MUST be clear, white on black,
        and must only contain either empty images,
        2, or 4. This can only be called once at the
        start of any session.
        """
        if self.bootstrapped:
            return

        CNNY_UPPER: float = 180.0
        CNNY_LOWER: float = 60.0
        unq_sym: int = 0
        rcgnz: List[bool] = [False for _ in range(3)]
        for dgt in clls:
            # Get raw contours, exclude empty tiles.
            cnd: Image = cv.ximgproc.thinning(cv.Canny(dgt, CNNY_LOWER, CNNY_UPPER))
            cccntrs, cchrchy = cv.findContours(
                cnd, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE
            )
            if len(cccntrs) == 0:
                if not self.is_recognized[Symbol.EMPTY]:
                    unq_sym += 1
                self.is_recognized[Symbol.EMPTY] = True
                rcgnz[0] = True
                self.add_template(dgt, -1)
                continue

            # Exclude duplicated contours.
            dgts: Set[int] = set()
            diff: Set[int] = set()
            for i, hrchy in enumerate(cchrchy[0]):
                _, _, w, h = cv.boundingRect(cccntrs[i])
                area: int = w * h
                if hrchy[CTopology.PARENT] == CTopology.NULL:
                    dgts.add(area)
                    continue
                if area in dgts:
                    continue
                diff.add(area)

            if len(dgts) > 1:
                raise ValueError(
                    "Initial dataset contains a number with more than 1 digit."
                )
            in_cntr: int = len(diff)
            if in_cntr > 1:
                raise ValueError(
                    "Initial dataset contains a number with more than 1 internal contour."
                )

            # Set digit.
            if in_cntr == 0:
                if not self.is_recognized[Symbol.S2]:
                    unq_sym += 1
                rcgnz[1] = True
                self.add_template(dgt, 2)
                continue
            elif in_cntr == 1:
                if not self.is_recognized[Symbol.S4]:
                    unq_sym += 1
                rcgnz[2] = True
                self.add_template(dgt, 4)
                continue
            if all(rcgnz):
                break

        if sum(rcgnz) != unq_sym:
            raise ValueError(
                "Could not initialize recognizer. Failed to distinguish initial symbols."
            )
        self.bootstrapped = True


def get_state(
    digits: List[Image], rcg: Recognizer
) -> Tuple[bool, Tuple[Tuple[int, float], ...]]:
    """
    Extracts the digits from the list of images.
    """
    CNNY_UPPER: float = 180.0
    CNNY_LOWER: float = 60.0

    # Handles setting internal variables.
    # only runs the first time it is called.
    rcg.bootstrap(digits)

    state: List[Tuple[int, float]] = []
    for d in digits:
        cnd: Image = cv.Canny(d, CNNY_LOWER, CNNY_UPPER)
        cntrs, _ = cv.findContours(cnd, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        d_count: int = len(cntrs)
        if d_count == 0:
            state.append((0, 1.0))
            continue
        out, sc = rcg.match(d)
        state.append((out, float(sc)))
    return (True, tuple(state))
