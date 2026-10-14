"""Named hairstyles: ready HairSpecs for women and men.

Use: Figure(..., hair=hairstyle('ponytail', color='#2a2220')). Any HairSpec field can be changed
the same way. The names only describe the cut; color, seed and the rest stay free.
"""
from dataclasses import replace

from .hair import HairSpec

_MALE_COLOR = '#2e2420'

FEMALE_STYLES = {
    'long': HairSpec(),
    'long_wavy': HairSpec(bangs='side', part=-30.0, bangs_length=-0.05, wave=0.8, fullness=1.1, length=2.8),
    'center_long': HairSpec(bangs='curtain', part=0.0, length=2.7, side_length=1.4),
    'hime': HairSpec(bangs='full', bangs_length=-0.12, part=0.0, side_length=0.95, length=3.0),
    'bob': HairSpec(bangs='full', bangs_length=-0.12, length=1.25, side_length=1.05),
    'pixie': HairSpec(bangs='side', part=-30.0, bangs_length=0.0, length=0.80, volume=0.10),
    'ponytail': HairSpec(tie='ponytail', bangs='wispy', volume=0.07, side_length=1.0, tail_length=2.6),
    'low_ponytail': HairSpec(tie='low_ponytail', bangs='side', part=-30.0, bangs_length=-0.05, volume=0.06,
                             side_length=0.0, tail_length=2.7),
    'braid': HairSpec(tie='braid', bangs='wispy', volume=0.06, side_length=0.9, tail_length=2.9),
    'bun': HairSpec(tie='bun', bangs='none', volume=0.06, side_length=0.9),
    'low_bun': HairSpec(tie='low_bun', bangs='parted', part=0.0, bangs_length=0.05, volume=0.06, side_length=0.0),
    'half_up': HairSpec(tie='half_up', bangs='wispy', length=2.6),
}

MALE_STYLES = {
    'buzz': HairSpec(color=_MALE_COLOR, bangs='none', length=0.62, volume=0.02, fade=0.35, fade_line=-1.5,
                     shine=0.2),
    'crew': HairSpec(color=_MALE_COLOR, bangs='short', bangs_length=-0.62, part=-10.0, length=0.62, volume=0.06,
                     fade=0.45, fade_line=-0.10, shine=0.4),
    'side_part': HairSpec(color=_MALE_COLOR, bangs='short', bangs_length=-0.52, part=-24.0, length=0.62,
                          volume=0.09, wave=0.1, shine=0.6),
    'fringe': HairSpec(color=_MALE_COLOR, bangs='wispy', bangs_length=-0.20, length=0.62, volume=0.09, shine=0.6),
    'two_block': HairSpec(color=_MALE_COLOR, bangs='wispy', bangs_length=-0.12, length=0.62, volume=0.12,
                          fade=0.55, fade_line=-0.40, shine=0.6),
    'comma': HairSpec(color=_MALE_COLOR, bangs='side', part=-30.0, bangs_length=-0.05, length=0.70, volume=0.11,
                      wave=0.2, shine=0.6),
    'center_part': HairSpec(color=_MALE_COLOR, bangs='parted', part=0.0, bangs_length=-0.05, length=0.85,
                            volume=0.11, shine=0.6),
    'slicked_back': HairSpec(color=_MALE_COLOR, bangs='back', length=0.62, volume=0.10, shine=0.9),
    'spiky': HairSpec(color=_MALE_COLOR, bangs='spiky', bangs_length=-0.30, length=0.60, volume=0.08, shine=0.5),
    'shoulder': HairSpec(color=_MALE_COLOR, bangs='parted', part=0.0, bangs_length=0.15, length=1.75,
                         side_length=1.3, volume=0.10, wave=0.3, shine=0.6),
    'man_bun': HairSpec(color=_MALE_COLOR, tie='bun', bangs='back', volume=0.08, side_length=0.0, shine=0.6),
    'low_tail': HairSpec(color=_MALE_COLOR, tie='low_ponytail', bangs='back', volume=0.08, side_length=0.0,
                         tail_length=1.7, shine=0.6),
}

HAIRSTYLES = {**FEMALE_STYLES, **MALE_STYLES}


def hairstyle(name, **changes):
    """A copy of the named style with any HairSpec fields changed (color, seed, length, ...)."""
    if name not in HAIRSTYLES:
        raise ValueError(f'unknown hairstyle {name!r}; choose from {sorted(HAIRSTYLES)}')
    return replace(HAIRSTYLES[name], **changes)
