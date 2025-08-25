import cv2 as cv
import numpy as np
from cv2.typing import Rect
from .types import Image, Symbol, Move
from typing import Callable, Any, Tuple, List, TYPE_CHECKING
from time import perf_counter
from copy import copy

if TYPE_CHECKING:
    from .agent import Agent


def wait(key: str) -> bool:
    return cv.waitKey(1) == ord(key)


def dbg_show(img: Image) -> None:
    while True:
        cv.imshow("", img)
        if wait("q"):
            break


def dbg_close() -> None:
    cv.destroyAllWindows()


def dbg_profile(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    st: float = perf_counter()
    ret: Any = func(*args, **kwargs)
    et: float = perf_counter()
    print(f"{func.__name__} took {(et - st) * 1000} ms")
    return ret


def dbg_latency(lbl: str, rts: float, end="\r") -> None:
    rte: float = perf_counter()
    print(f"{lbl}: {((rte - rts) * 1000):.3f} ms {" " * 20}", end=end)


def show_dbg_state(
    game_state: Tuple[Tuple[int, float], ...] | None,
    agnt: Any,
    rts: float,
    grid: Image,
    cells: List[Image],
    is_active: bool,
    mv: Move,
) -> None:
    GRID_SIDE_LENGTH: int = 4
    GRID_CELL_COUNT: int = GRID_SIDE_LENGTH * GRID_SIDE_LENGTH
    TMPLT_IMG_SIZE: Tuple[int, int] = (32, 64)
    GRID_CELL_SIZE: Tuple[int, int] = (100, 100)
    GRID_MAIN_SIZE: Tuple[int, int] = (400, 400)
    DASHBOARD_CHANNELS: int = 3
    CNNY_UPPER: float = 180.0
    CNNY_LOWER: float = 60.0
    dshbrd: Image = np.zeros(
        dtype=np.uint8,
        shape=(
            TMPLT_IMG_SIZE[1] + GRID_MAIN_SIZE[1],
            GRID_MAIN_SIZE[0] + GRID_CELL_SIZE[0] * GRID_SIDE_LENGTH,
            DASHBOARD_CHANNELS,
        ),
    )
    mgrid: Image = np.zeros(dtype=np.uint8, shape=(*GRID_MAIN_SIZE, DASHBOARD_CHANNELS))
    rsz_shape: Tuple[int, int] = (
        (int(grid.shape[1] * (GRID_MAIN_SIZE[1] / grid.shape[0])), GRID_MAIN_SIZE[1])
        if grid.shape[0] > grid.shape[1]
        else (
            GRID_MAIN_SIZE[0],
            int(grid.shape[0] * (GRID_MAIN_SIZE[0] / grid.shape[1])),
        )
    )
    sgrid: Image = cv.resize(cv.cvtColor(grid, cv.COLOR_RGBA2RGB), rsz_shape)
    x: int = (mgrid.shape[1] - rsz_shape[0]) // 2
    y: int = (mgrid.shape[0] - rsz_shape[1]) // 2
    mgrid[y : y + sgrid.shape[0], x : x + sgrid.shape[1], :] = sgrid
    dshbrd[: mgrid.shape[0], : mgrid.shape[1]] = mgrid[:, :, 1][:, :, np.newaxis]
    cv.putText(
        dshbrd,
        "ACQUIRED" if agnt.tracked else "LOST",
        (10, 20),
        cv.FONT_HERSHEY_PLAIN,
        1.3,
        (0, 255, 0),
        1,
    )
    if len(cells) == GRID_CELL_COUNT:
        for y in range(GRID_SIDE_LENGTH):
            for x in range(GRID_SIDE_LENGTH):
                idx: int = y * GRID_SIDE_LENGTH + x
                y_offset: int = y * GRID_CELL_SIZE[1]
                x_offset: int = GRID_MAIN_SIZE[0] + x * GRID_CELL_SIZE[0]
                dshbrd[
                    y_offset : y_offset + GRID_CELL_SIZE[1],
                    x_offset : x_offset + GRID_CELL_SIZE[0],
                ] = cv.resize(cells[idx], GRID_CELL_SIZE)[:, :, np.newaxis]
                cnnd: Image = cv.Canny(
                    dshbrd[
                        y_offset : y_offset + GRID_CELL_SIZE[1],
                        x_offset : x_offset + GRID_CELL_SIZE[0],
                    ],
                    CNNY_LOWER,
                    CNNY_UPPER,
                )
                if game_state:
                    cntrs, _hrchy = cv.findContours(
                        cnnd, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE
                    )
                    for cntr in cntrs:
                        cx, cy, cw, ch = cv.boundingRect(cntr)
                        cv.rectangle(
                            dshbrd[
                                y_offset : y_offset + GRID_CELL_SIZE[1],
                                x_offset : x_offset + GRID_CELL_SIZE[0],
                            ],
                            (cx, cy),
                            (cx + cw, cy + ch),
                            (0, 255, 0),
                            1,
                        )
                    cv.putText(
                        dshbrd[
                            y_offset : y_offset + GRID_CELL_SIZE[1],
                            x_offset : x_offset + GRID_CELL_SIZE[0],
                        ],
                        f"{game_state[idx][0]} - {game_state[idx][1] * 100:.2f}%",
                        (5, 10),
                        cv.FONT_HERSHEY_PLAIN,
                        0.8,
                        (0, 255, 0),
                        1,
                    )

    for i, im in enumerate(agnt.recognizer.template_images):
        offset: int = i * TMPLT_IMG_SIZE[0]
        dshbrd[GRID_MAIN_SIZE[1] :, offset : offset + TMPLT_IMG_SIZE[0], :] = im[
            :, :, np.newaxis
        ]
        cv.putText(
            dshbrd[GRID_MAIN_SIZE[1] :, offset : offset + TMPLT_IMG_SIZE[0]],
            f"{Symbol(i) if i != Symbol.EMPTY else "E"}",
            (5, 10),
            cv.FONT_HERSHEY_PLAIN,
            1.0,
            (0, 255, 0),
            1,
        )
    tbox: Image = dshbrd[
        GRID_MAIN_SIZE[1] :,
        TMPLT_IMG_SIZE[0] * len(agnt.recognizer.template_images) :,
    ]
    cv.putText(
        tbox,
        f"LATENCY: {((perf_counter() - rts) * 1000):.3f} ms",
        (5, 10),
        cv.FONT_HERSHEY_PLAIN,
        0.8,
        (0, 255, 0),
        1,
    )
    cv.putText(
        tbox,
        f"STATUS: {"ACTIVE" if is_active else "PASSIVE"}",
        (5, 30),
        cv.FONT_HERSHEY_PLAIN,
        0.8,
        (0, 255, 0),
        1,
    )
    mv_s: str = ""
    match mv:
        case Move.UP:
            mv_s = "UP"
        case Move.DOWN:
            mv_s = "DOWN"
        case Move.LEFT:
            mv_s = "LEFT"
        case Move.RIGHT:
            mv_s = "RIGHT"
        case Move.NULL:
            mv_s = "NULL"
    cv.putText(
        tbox,
        f"MOVE: {mv_s}",
        (5, 50),
        cv.FONT_HERSHEY_PLAIN,
        0.8,
        (0, 255, 0),
        1,
    )
    cv.imshow("", dshbrd)
    wait("q")
