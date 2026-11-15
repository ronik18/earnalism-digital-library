"""Focused material, charge and carrier-path invariants; not actual AV review."""
import math
import unittest
from . import model as m


class CorrosionConditionsTests(unittest.TestCase):
    def test_oxygen_and_water_and_exposed_iron_required_for_shown_route(self):
        self.assertTrue(m.corrosion_conditions()['active'])
        for options in ({'oxygen':False},{'water':False},{'intact_barrier':True}):
            self.assertFalse(m.corrosion_conditions(**options)['active'])

    def test_salt_is_optional_and_has_no_invented_rate_law(self):
        for salt in (False,True):
            c=m.corrosion_conditions(salt=salt)
            self.assertTrue(c['active']);self.assertFalse(c['salt_required'])
            self.assertNotIn('rate',c)

    def test_half_reactions_cancel_electrons_and_conserve_atoms_and_charge(self):
        net=m.coupled_half_reactions()
        self.assertNotIn('e-',net)
        self.assertEqual(net,{'Fe':-2,'Fe2+':2,'O2':-1,'H2O':-2,'OH-':4})
        composition={'Fe':(1,0,0,0),'Fe2+':(1,0,0,2),'O2':(0,2,0,0),'H2O':(0,1,2,0),'OH-':(0,1,1,-1)}
        for dimension in range(4):self.assertEqual(sum(n*composition[s][dimension] for s,n in net.items()),0)

    def test_carriers_stay_in_their_actual_conductive_medium(self):
        for bounds in ((100,300,1820,770),(72,560,900,1170)):
            g=m.mechanism_geometry(bounds)
            for i in range(101):
                p=i/100
                self.assertTrue(m.inside(m.interpolate(g['electron_path'],p),g['metal']))
                for path in ('iron_ion_path','hydroxide_path','oxygen_path'):
                    self.assertTrue(m.inside(m.interpolate(g[path],p),g['water']))

    def test_invalid_progress_and_geometry_rejected(self):
        for value in (math.nan,math.inf,-math.inf):
            with self.assertRaises(ValueError):m.progress(value)
        with self.assertRaises(ValueError):m.mechanism_geometry((0,0,10,10))
        with self.assertRaises(ValueError):m.corrosion_conditions(salt='yes')


if __name__=='__main__':unittest.main()
