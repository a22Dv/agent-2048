import pyautogui as gui
from PIL.Image import Image

class Visual:
    @staticmethod
    def get_screenshot() -> Image:
        return gui.screenshot()
        



    