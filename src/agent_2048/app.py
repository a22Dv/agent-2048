from PIL.Image import Image
from agent_2048.visual import Visual
import cv2
import numpy as np

class Application:
    @classmethod
    def run(cls) -> None:
        while True:
            ss : Image = Visual.get_screenshot()
            cv2.imshow("Screenshot", np.array(ss))
            if cv2.waitKey(1) == ord('q'):
                break
        cv2.destroyAllWindows()

