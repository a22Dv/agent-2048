import cv2 as cv
import os
from .types import Image
from typing import Callable, Any, Tuple
from time import perf_counter


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


GRID_SIDE_LENGTH: int = 4


def show_dbg_state(
    game_state: Tuple[Tuple[int, float], ...] | None, agnt: Any, rte: float
) -> None:
    _ = os.system("cls" if os.name == "nt" else "clear")
    dbg_latency("DELIBERATION:", rte, "\n")
    print(f"BOARD-ACQUIRED: {"TRUE" if agnt.tracked else "FALSE"}")
    print(
        f"BOARD-AT:\nX: {agnt.bRect[0]} Y: {agnt.bRect[1]}\nW: {agnt.bRect[2]} H: {agnt.bRect[3]}"
        if agnt.bRect != (-1, -1, -1, -1)
        else "N/A"
    )
    # print("NEXT STATE: ")
    # for i in range(GRID_SIDE_LENGTH):
    #     for j in range(GRID_SIDE_LENGTH):
    #         print(-1 if not agnt.predicted_state else agnt.predicted_state[i * GRID_SIDE_LENGTH + j], end=" ")
    #     print()
    print("CURRENT STATE: ")
    for i in range(GRID_SIDE_LENGTH):
        for j in range(GRID_SIDE_LENGTH):
            print(
                -1 if not game_state else game_state[i * GRID_SIDE_LENGTH + j][0],
                end=" ",
            )
        print()
    print("CONFIDENCE SCORE: ")
    for i in range(GRID_SIDE_LENGTH):
        for j in range(GRID_SIDE_LENGTH):
            print(
                (
                    f"0.0%"
                    if not game_state
                    else f"{(game_state[i * GRID_SIDE_LENGTH + j][1] * 100):.1f}%"
                ),
                end=" ",
            )
        print()
