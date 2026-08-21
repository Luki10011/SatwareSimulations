

from core.physics.disturbance.atmoshperic_drag import AthompshericDragDisturbance
from core.physics.disturbance.gravity_gradient import GravityGradientDisturbance
from core.physics.disturbance.j2_disturbance import J2Disturbance
from typing import List
import numpy as np


class Disturbance:

    def __init__(self):

        self.j2_disturbance = J2Disturbance()
        self.gravity_gradient_disturbance = GravityGradientDisturbance()
        self.atmospheric_drag_disturbance = AthompshericDragDisturbance()

    def get_disturbance(self) -> List[np.ndarray, np.ndarray, np.ndarray]:

        XYZ_J2 = self.j2_disturbance.compute_disturbance()
        LMN_ad = self.atmospheric_drag_disturbance.compute_disturbance()
        LMN_gradient = self.gravity_gradient_disturbance.comupte_disturbance()

        return XYZ_J2, LMN_ad, LMN_gradient