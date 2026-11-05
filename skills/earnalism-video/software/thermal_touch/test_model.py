"""Physical invariants for the ideal thermal-touch model.

Values below are synthetic test solids, not asserted skin/metal/wood data.
"""

import math
import unittest

try:
    from .model import Material, IdealContact
except ImportError:
    from model import Material, IdealContact


class ThermalContactTests(unittest.TestCase):
    def setUp(self):
        self.warm_proxy = Material(1.0, 1.0, 1.0)
        self.high_effusivity = Material(100.0, 1.0, 1.0)
        self.low_effusivity = Material(0.04, 1.0, 1.0)
        self.warm_K, self.room_K = 307.15, 295.15

    def contact(self, material, warm=True):
        a, b = (self.warm_K, self.room_K) if warm else (self.room_K, self.warm_K)
        return IdealContact(self.warm_proxy, material, a, b)

    def test_equal_temperatures_have_no_net_transfer(self):
        pair = IdealContact(self.warm_proxy, self.high_effusivity, 295.15, 295.15)
        self.assertAlmostEqual(pair.interface_temperature_K, 295.15)
        for t in (0.001, 1, 10):
            self.assertEqual(pair.flux_A_to_B_W_m2(t), 0)
            self.assertEqual(pair.energy_A_to_B_J_m2(t), 0)
            for body in ("A", "B"):
                self.assertAlmostEqual(pair.temperature_K(body, 0.01, t), 295.15)

    def test_higher_effusivity_cools_contact_more_for_warm_hand_proxy(self):
        high, low = self.contact(self.high_effusivity), self.contact(self.low_effusivity)
        self.assertLess(high.interface_temperature_K, low.interface_temperature_K)
        self.assertLess(abs(high.interface_temperature_K - self.room_K),
                        abs(low.interface_temperature_K - self.room_K))
        self.assertGreater(high.flux_A_to_B_W_m2(0.1), low.flux_A_to_B_W_m2(0.1))
        self.assertGreater(low.flux_A_to_B_W_m2(0.1), 0)
        for pair in (high, low):
            self.assertLess(self.room_K, pair.interface_temperature_K)
            self.assertLess(pair.interface_temperature_K, self.warm_K)

    def test_hotter_object_reverses_transfer_not_material_identity(self):
        high, low = self.contact(self.high_effusivity, warm=False), self.contact(self.low_effusivity, warm=False)
        self.assertLess(high.flux_A_to_B_W_m2(0.1), low.flux_A_to_B_W_m2(0.1))
        self.assertLess(low.flux_A_to_B_W_m2(0.1), 0)
        self.assertGreater(high.interface_temperature_K, low.interface_temperature_K)
        self.assertLess(high.energy_A_to_B_J_m2(1), 0)

    def test_swapping_bodies_preserves_contact_and_reverses_signed_transfer(self):
        first = self.contact(self.high_effusivity)
        swapped = IdealContact(first.material_B, first.material_A,
                               first.initial_B_K, first.initial_A_K)
        self.assertAlmostEqual(first.interface_temperature_K, swapped.interface_temperature_K)
        self.assertAlmostEqual(first.flux_A_to_B_W_m2(0.4), -swapped.flux_A_to_B_W_m2(0.4))
        self.assertAlmostEqual(first.energy_A_to_B_J_m2(0.4), -swapped.energy_A_to_B_J_m2(0.4))

    def test_density_and_heat_capacity_also_affect_initial_contact(self):
        # Equal conductivity alone does not fix transient contact response.
        a = Material(1, 1, 1)
        b = Material(1, 4, 4)
        self.assertEqual(b.effusivity_J_m2K_sqrt_s, 4)
        self.assertEqual(b.diffusivity_m2_s, 1 / 16)
        low, high = self.contact(a), self.contact(b)
        self.assertLess(high.interface_temperature_K, low.interface_temperature_K)
        self.assertGreater(high.flux_A_to_B_W_m2(0.5), low.flux_A_to_B_W_m2(0.5))

    def test_time_scaling_and_zero_energy_at_initial_contact(self):
        pair = self.contact(self.high_effusivity)
        self.assertEqual(pair.energy_A_to_B_J_m2(0), 0)
        self.assertAlmostEqual(pair.flux_A_to_B_W_m2(4), pair.flux_A_to_B_W_m2(1) / 2)
        self.assertAlmostEqual(pair.energy_A_to_B_J_m2(4), pair.energy_A_to_B_J_m2(1) * 2)
        # Independently differentiate the cumulative energy at a positive t.
        dt = 1e-5
        derivative = (pair.energy_A_to_B_J_m2(1 + dt) -
                      pair.energy_A_to_B_J_m2(1 - dt)) / (2 * dt)
        self.assertAlmostEqual(derivative, pair.flux_A_to_B_W_m2(1), places=7)

    def test_spatial_solution_boundaries_and_fourier_flux_match(self):
        pair = self.contact(self.high_effusivity)
        t = 0.5
        for body, material, initial in (("A", pair.material_A, pair.initial_A_K),
                                         ("B", pair.material_B, pair.initial_B_K)):
            self.assertAlmostEqual(pair.temperature_K(body, 0, t), pair.interface_temperature_K)
            far = 12 * math.sqrt(material.diffusivity_m2_s * t)
            self.assertAlmostEqual(pair.temperature_K(body, far, t), initial, places=10)
            depth = 1e-6 * math.sqrt(material.diffusivity_m2_s * t)
            grad = (pair.temperature_K(body, depth, t) - pair.temperature_K(body, 0, t)) / depth
            outward_flux = material.conductivity_W_mK * grad
            expected = pair.flux_A_to_B_W_m2(t) if body == "A" else -pair.flux_A_to_B_W_m2(t)
            self.assertAlmostEqual(outward_flux, expected, delta=abs(expected) * 1e-7)

    def test_numerical_temperature_field_integrals_conserve_energy(self):
        # Integrate rho*cp*DeltaT through each body, not the transfer formula.
        pair = self.contact(self.high_effusivity)
        t = 0.6
        totals = []
        for body, material, initial in (("A", pair.material_A, pair.initial_A_K),
                                         ("B", pair.material_B, pair.initial_B_K)):
            end = 12 * math.sqrt(material.diffusivity_m2_s * t)
            n, step = 2000, end / 2000
            integral = 0.0
            for i in range(n + 1):
                weight = 1 if i in (0, n) else (4 if i % 2 else 2)
                integral += weight * (pair.temperature_K(body, i * step, t) - initial)
            totals.append(material.volumetric_heat_capacity_J_m3K * integral * step / 3)
        self.assertAlmostEqual(totals[0], -totals[1], places=7)
        self.assertAlmostEqual(totals[1], pair.energy_A_to_B_J_m2(t), places=7)

    def test_invalid_physical_inputs_and_singular_zero_time_rejected(self):
        for bad in (0, -1, float("inf"), float("nan"), True, "1"):
            with self.subTest(material=bad), self.assertRaises(ValueError):
                Material(bad, 1, 1)
        pair = self.contact(self.high_effusivity)
        for bad in (0, -1, float("inf"), float("nan")):
            with self.subTest(flux_time=bad), self.assertRaises(ValueError):
                pair.flux_A_to_B_W_m2(bad)
        for temp in (-0.01, float("inf"), float("nan"), True):
            with self.subTest(temperature=temp), self.assertRaises(ValueError):
                IdealContact(self.warm_proxy, self.high_effusivity, temp, 300)
        for body, depth, time in (("C", 0, 1), ("A", -1, 1), ("B", 0, 0)):
            with self.subTest(field=(body, depth, time)), self.assertRaises(ValueError):
                pair.temperature_K(body, depth, time)


if __name__ == "__main__":
    unittest.main()
