import cv2
import easyocr as ocr
import pyautogui as gui
import numpy as np
from typing import Any, Tuple, List
from PIL.Image import Image
from agent_2048.utils import Utils

THRESHOLD: int = 10000
CELL_COUNT: int = 4
GRID_COUNT: int = 16


class Visual:
    reader: ocr.Reader = ocr.Reader(["en"], quantize=True, gpu=False)

    # Needs more testing. Accurate up to 3 digit numbers so far.
    # Extremely sensitive. Scale factor improves accuracy by upscaling the
    # image. Crop percentage removes any edges that might have been included.
    SCALE_FACTOR: int = 2
    CROP_PRCNT: float = 0.2

    @staticmethod
    def get_screenshot() -> Image:
        return gui.screenshot()

    @staticmethod
    def get_rgb(img: Image) -> np.ndarray[Any, Any]:
        return cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)

    @staticmethod
    def img_resize(
        img: np.ndarray[Any, Any], dimensions: Tuple[int, int]
    ) -> np.ndarray[Any, Any]:
        return cv2.resize(img, dimensions, interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def apply_canny(
        img: np.ndarray[Any, Any], th1: int, th2: int
    ) -> np.ndarray[Any, Any]:
        return cv2.Canny(img, float(th1), float(th2))

    @staticmethod
    def get_grid_candidates(
        img_edges: np.ndarray[Any, Any], img_colors: np.ndarray[Any, Any]
    ) -> Tuple[List[np.ndarray[Any, Any]], int]:
        """
        Gets the list of grid candidates along with the index of the most likely one.
        """
        contours, hierarchy = cv2.findContours(
            img_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        candidates: List[np.ndarray[Any, Any]] = []
        for i, contour in enumerate(contours):
            # Excludes anything smaller than the threshold, or without children.
            if cv2.contourArea(contour) < THRESHOLD or hierarchy[0][i][2] == -1:
                continue
            _, _, w, h = cv2.boundingRect(contour)
            if not Utils.threshold(w / h, 0.9, 1.1):
                continue
            if not Visual.validate_intersects(img_colors, contour):
                continue
            candidates.append(contour)
        max_area: float = 0.0
        contour_idx: int = 0
        for i, contour in enumerate(candidates):
            area: float = cv2.contourArea(contour)
            if area < max_area:
                continue
            contour_idx = i
            max_area = area
        return (candidates, contour_idx)

    @staticmethod
    def validate_intersects(
        img: np.ndarray[Any, Any], contour: np.ndarray[Any, Any]
    ) -> bool:
        """
        Checks whether a given contour follows the 2048 grid color scheme. Sampling the intersections of the grid to do so.
        """
        SHADE: Tuple[int, ...] = (120, 137, 156)
        points: List[Tuple[int, int]] = Visual.get_grid_central_intersects(contour)
        for point in points:
            for i, channel in enumerate(img[point[1]][point[0]]):
                if not Utils.threshold(channel, SHADE[i] - 15, SHADE[i] + 15):
                    return False
        return True

    @staticmethod
    def get_grid_central_intersects(
        contour: np.ndarray[Any, Any],
    ) -> List[Tuple[int, int]]:
        x, y, w, h = cv2.boundingRect(contour)
        stride_w: int = w // 4
        stride_h: int = h // 4
        points: List[Tuple[int, int]] = [
            (x + stride_w * i, y + stride_h * j)
            for j in range(1, CELL_COUNT)
            for i in range(1, CELL_COUNT)
        ]
        return points

    def extract_state(
        self,
        img: np.ndarray[Any, Any],
        intersects: List[Tuple[int, int]],
        bounding_rect: Tuple[int, ...],
    ) -> Tuple[List[int], List[Tuple[Tuple[int, int], Tuple[int, int]]]]:
        
        
        x, y, w, h = bounding_rect
        cell_coordinates: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        base: Tuple[int, int] = intersects[0]

        # Extract cell coordinates for cropping.
        cell_width: int = base[0] - x
        cell_height: int = base[1] - y
        for i in range(CELL_COUNT):
            for j in range(CELL_COUNT):
                offset_width: int = cell_width * j
                offset_height: int = cell_height * i
                cell_coordinates.append(
                    (
                        (x + offset_width, y + offset_height),
                        (base[0] + offset_width, base[1] + offset_height),
                    )
                )
        state: List[int] = [0 for _ in range(CELL_COUNT * CELL_COUNT)]
        i: int = 0
        for y_i in range(CELL_COUNT):
            for x_i in range(CELL_COUNT):
                y_offset: int = cell_height * y_i
                x_offset: int = cell_height * x_i
                cell: np.ndarray[Any, Any] = cv2.cvtColor(
                    img[
                        y + y_offset : y + y_offset + cell_height,
                        x + x_offset : x + x_offset + cell_width,
                    ],
                    cv2.COLOR_RGB2GRAY,
                )
                py = int(cell_height * self.CROP_PRCNT)
                px = int(cell_width * self.CROP_PRCNT)
                cell_crp: np.ndarray[Any, Any] = cell[
                    py : cell_height - py,
                    px : cell_width - px,
                ]
                cell_rs: np.ndarray[Any, Any] = cv2.resize(
                    cell_crp,
                    (cell_crp.shape[1] * self.SCALE_FACTOR, cell_crp.shape[0] * self.SCALE_FACTOR),
                    interpolation=cv2.INTER_NEAREST,
                )
                _, cell_th = cv2.threshold(
                    cell_rs, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                # while True:
                #     cv2.imshow("", cell_th)
                #     if Utils.wait("q"):
                #         break
                output = self.reader.recognize(
                    img_cv_grey=cell_th, allowlist="0123456789"
                )
                if len(output) != 1:
                    return (
                        [0 for _ in range(CELL_COUNT * CELL_COUNT)],
                        cell_coordinates,
                    )
                _, txt, conf = output[0]
                state[i] = int(txt) if txt.isnumeric() else 0
                if state[i] < 2 or (state[i] & (state[i] - 1)) != 0:
                    state[i] = 0
                i += 1
        return (state, cell_coordinates)
