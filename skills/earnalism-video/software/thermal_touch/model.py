"""Ideal early-time contact between two semi-infinite solids.

SI inputs; temperatures are kelvin. This is a mechanism model, not a measured
skin-temperature or thermal-sensation prediction. The two bodies start uniform,
make perfect planar contact, have constant properties, and exchange energy by
one-dimensional conduction. Finite thickness, contact resistance, moisture,
surface finish, blood flow and sensory adaptation are outside this model.

The interface-temperature and flux solution is documented in Strotos et al.
(2011), section 3, equations 1–5, accepted manuscript in City Research Online:
https://openaccess.city.ac.uk/id/eprint/13580/
https://doi.org/10.1016/j.ijthermalsci.2010.11.021

The contact temperature stays constant in this ideal solution. The heat flux
decays as t**(-1/2); its t=0 singularity is an idealization, so flux at zero is
deliberately unavailable. No default material numbers or biological curves are
supplied. Any rendered arrows/colour change must be labelled schematic.
"""

from dataclasses import dataclass
import math
from numbers import Real


def _number(name, value, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


@dataclass(frozen=True)
class Material:
    """Constant properties: k [W/(m K)], rho [kg/m³], cp [J/(kg K)]."""

    conductivity_W_mK: float
    density_kg_m3: float
    specific_heat_J_kgK: float

    def __post_init__(self):
        for name in ("conductivity_W_mK", "density_kg_m3", "specific_heat_J_kgK"):
            object.__setattr__(self, name, _number(name, getattr(self, name), positive=True))
        # Reject inputs whose derived SI properties cannot be represented.
        _number("volumetric heat capacity", self.volumetric_heat_capacity_J_m3K, positive=True)
        _number("effusivity squared", self.conductivity_W_mK * self.volumetric_heat_capacity_J_m3K,
                positive=True)
        _number("diffusivity", self.diffusivity_m2_s, positive=True)

    @property
    def volumetric_heat_capacity_J_m3K(self):
        return self.density_kg_m3 * self.specific_heat_J_kgK

    @property
    def diffusivity_m2_s(self):
        return self.conductivity_W_mK / self.volumetric_heat_capacity_J_m3K

    @property
    def effusivity_J_m2K_sqrt_s(self):
        """sqrt(k rho cp), in J/(m² K sqrt(s))."""
        return math.sqrt(self.conductivity_W_mK * self.volumetric_heat_capacity_J_m3K)


@dataclass(frozen=True)
class IdealContact:
    """Signed transfer is positive from body A into body B.

    A can be a warm-hand proxy and B a cooler object for a schematic. Calling
    a body 'skin' does not make the ideal solid solution a biological model.
    """

    material_A: Material
    material_B: Material
    initial_A_K: float
    initial_B_K: float

    def __post_init__(self):
        if not isinstance(self.material_A, Material) or not isinstance(self.material_B, Material):
            raise ValueError("Both bodies need validated Material properties")
        for name in ("initial_A_K", "initial_B_K"):
            object.__setattr__(self, name, _number(name, getattr(self, name), nonnegative=True))

    @property
    def interface_temperature_K(self):
        """Effusivity-weighted mean; common interface for all t > 0."""
        a = self.material_A.effusivity_J_m2K_sqrt_s
        b = self.material_B.effusivity_J_m2K_sqrt_s
        return (a / (a + b)) * self.initial_A_K + (b / (a + b)) * self.initial_B_K

    @property
    def effective_effusivity_J_m2K_sqrt_s(self):
        a = self.material_A.effusivity_J_m2K_sqrt_s
        b = self.material_B.effusivity_J_m2K_sqrt_s
        lo, hi = sorted((a, b))
        return lo / (1.0 + lo / hi)

    def flux_A_to_B_W_m2(self, time_s):
        """Early-time interface flux; no finite t=0 value is invented."""
        t = _number("time_s", time_s, positive=True)
        return (self.effective_effusivity_J_m2K_sqrt_s *
                (self.initial_A_K - self.initial_B_K) / math.sqrt(math.pi * t))

    def energy_A_to_B_J_m2(self, time_s):
        """Signed integral of flux from first contact to t; energy/area."""
        t = _number("time_s", time_s, nonnegative=True)
        return (2 * self.effective_effusivity_J_m2K_sqrt_s *
                (self.initial_A_K - self.initial_B_K) * math.sqrt(t / math.pi))

    def temperature_K(self, body, depth_m, time_s):
        """Temperature at nonnegative depth measured INTO either body.

        At depth zero both sides share the interface temperature. At large
        depth, each tends to its own initial temperature. The field describes
        ideal solid conduction only, not an experimentally validated hand.
        """
        if body not in ("A", "B"):
            raise ValueError("body must be 'A' or 'B'")
        depth = _number("depth_m", depth_m, nonnegative=True)
        t = _number("time_s", time_s, positive=True)
        material, initial = ((self.material_A, self.initial_A_K) if body == "A" else
                             (self.material_B, self.initial_B_K))
        contact = self.interface_temperature_K
        eta = depth / (2 * math.sqrt(material.diffusivity_m2_s) * math.sqrt(t))
        return contact + (initial - contact) * math.erf(eta)
