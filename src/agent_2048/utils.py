import cv2

class Utils:
    @staticmethod
    def threshold(value : float | int, th1 : float | int, th2 : float | int) -> bool:
        return th1 <= value <= th2
    @staticmethod
    def wait(char : str) -> bool:
        if (cv2.waitKey(1) == ord(char)):
            return True
        return False
        