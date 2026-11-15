"""Qualitative ordinary atmospheric iron corrosion, not a kinetic simulator.

This model only admits the oxygenated near-neutral aqueous route shown in the
episode. It does not assert that all corrosion needs oxygen or that salt always
increases every corrosion rate. Animation progress is an editorial reveal, not
elapsed chemical time. The neutral-water half-reactions are charge/atom balanced.
"""
import math

KINDS=('opening','film','circuit','product','salt','barrier')
IRON_OXIDATION={'Fe':-1,'Fe2+':1,'e-':2}
OXYGEN_REDUCTION={'O2':-1,'H2O':-2,'e-':-4,'OH-':4}


def progress(value):
    value=float(value)
    if not math.isfinite(value):raise ValueError('Finite editorial progress required')
    return max(0.,min(1.,value))


def corrosion_conditions(*,oxygen=True,water=True,intact_barrier=False,salt=False):
    for value in (oxygen,water,intact_barrier,salt):
        if type(value) is not bool:raise ValueError('Explicit Boolean conditions required')
    return {'route':'oxygenated_neutral_water_ordinary_iron',
      'active':oxygen and water and not intact_barrier,
      'salt_required':False,'salt_present':salt,
      'salt_effect':'Can accelerate this route; no numerical rate law',
      'meaning':'Conditions only; not a prediction of reaction time or amount'}


def coupled_half_reactions():
    """Two iron oxidations supply four electrons for one oxygen reduction."""
    net={}
    for reaction,multiple in ((IRON_OXIDATION,2),(OXYGEN_REDUCTION,1)):
        for species,count in reaction.items():net[species]=net.get(species,0)+count*multiple
    return {species:count for species,count in net.items() if count}


def mechanism_geometry(bounds):
    """Keep the conductive electron path inside metal and ion paths in water."""
    x0,y0,x1,y1=map(float,bounds)
    if not (x1-x0>=200 and y1-y0>=180):raise ValueError('Readable mechanism bounds required')
    w,h=x1-x0,y1-y0
    water_top=y0+.18*h;metal_top=y0+.60*h;metal_bottom=y0+.94*h
    anode=x0+.25*w;cathode=x0+.76*w
    electron_y=metal_top+.20*(metal_bottom-metal_top)
    return {'bounds':(x0,y0,x1,y1),'water':(x0+12,water_top,x1-12,metal_top),
      'metal':(x0+12,metal_top,x1-12,metal_bottom),
      'anode':(anode,metal_top),'cathode':(cathode,metal_top),
      'electron_path':((anode,electron_y),(cathode,electron_y)),
      'iron_ion_path':((anode,metal_top-12),(anode-.035*w,water_top+.48*(metal_top-water_top))),
      'hydroxide_path':((cathode,metal_top-12),(cathode-.06*w,water_top+.48*(metal_top-water_top))),
      'oxygen_path':((cathode+.06*w,water_top+20),(cathode,metal_top-18)),
      'particle_semantics':'Diagram markers identify paths/species, not molecular counts, speeds or sizes'}


def interpolate(path,value):
    value=progress(value)
    return tuple(a+(b-a)*value for a,b in zip(*path))


def inside(point,bounds):
    return bounds[0]<=point[0]<=bounds[2] and bounds[1]<=point[1]<=bounds[3]
