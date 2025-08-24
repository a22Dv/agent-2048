import cv2 as cv
from .types import Image
from typing import Callable, Any, Tuple
from time import perf_counter

def wait(key: str) -> bool:
    return cv.waitKey(1) == ord(key)
        
def dbg_show(img: Image) -> None:
    while True:
        cv.imshow("", img)
        if (wait("q")):
            break

def dbg_close() -> None:
    cv.destroyAllWindows() 
def dbg_profile(func : Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    st: float = perf_counter()
    ret: Any = func(*args, **kwargs)
    et: float = perf_counter()
    print(f"{func.__name__} took {(et - st) * 1000} ms")
    return ret
