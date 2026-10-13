"""Render every example at full size and check each picture for gross failures.

Run:  python selftest.py [out_dir]      (exit code 1 if any check fails)
"""
import importlib.util
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from codepaint import review, save  # noqa: E402

# (example module, builder call, output name)
CASES = [
    ("portrait", "build('anime')", "portrait_anime"),
    ("portrait", "build('illust')", "portrait_illust"),
    ("portrait", "build('painterly')", "portrait_painterly"),
    ("figure", "build('painterly')", "figure_painterly"),
    ("figure", "build('anime')", "figure_anime"),
    ("figure", "build('illust')", "figure_illust"),
    ("figure", "build('seated')", "figure_seated"),
    ("figure", "build('reclining')", "figure_reclining"),
    ("portrait", "build('anime', 'male')", "portrait_male_anime"),
    ("portrait", "build('illust', 'male')", "portrait_male_illust"),
    ("portrait", "build('painterly', 'male')", "portrait_male_painterly"),
    ("figure", "build('male_painterly')", "figure_male_painterly"),
    ("figure", "build('male_anime')", "figure_male_anime"),
    ("figure", "build('male_illust')", "figure_male_illust"),
    ("figure", "build('male_seated')", "figure_male_seated"),
    ("figure", "build('male_reclining')", "figure_male_reclining"),
    ("hands", "build('illust')", "hands_illust"),
    ("landscape", "oil(SPEC)", "landscape_painterly"),
    ("landscape", "anime(SUNSET)", "landscape_anime"),
    ("city", "anime(CitySpec(seed=2, time='day'))", "city_day"),
    ("city", "anime(CitySpec(seed=2, time='dusk', wet_road=0.55))", "city_dusk"),
    ("city", "oil(CitySpec(seed=5, time='golden'))", "city_painterly"),
    ("custom_scene", "build('illust')", "custom_illust"),
    ("desk", "build('anime')", "desk_anime"),
    ("desk", "build(get_style('painterly', painterly=dict(scale=0.55, jitter=3.0)))", "desk_painterly"),
    ("desk", "catalog()", "objects_catalog"),
    ("desk", "study()", "desk_study"),
    ("hands", "gestures()", "hands_gestures"),
    ("portrait", "build_back('illust')", "portrait_back_illust"),
    ("portrait", "build_back('anime', 'male')", "portrait_back_male_anime"),
    ("figure", "build('street')", "figure_street"),
    ("figure", "build('back')", "figure_back"),
    ("figure", "build('phone')", "figure_phone"),
    ("figure", "build('side_study')", "figure_side_study"),
    ("figure", "build('side_seated')", "figure_side_seated"),
    ("figure", "build('male_street')", "figure_male_street"),
    ("figure", "build('male_back')", "figure_male_back"),
    ("figure", "build('male_coffee')", "figure_male_coffee"),
    ("figure", "turnaround()", "figure_turnaround"),
    ("figure", "turnaround('male', 'anime')", "figure_turnaround_male"),
    ("scenes", "pairs()", "scene_pairs"),
    ("scenes", "cafe()", "scene_cafe"),
    ("scenes", "classroom()", "scene_classroom"),
    ("scenes", "living_room()", "scene_living_room"),
    ("scenes", "park()", "scene_park"),
    ("gallery", "rain_night()", "gallery_rain_night"),
    ("gallery", "night_study()", "gallery_night_study"),
    ("gallery", "office()", "gallery_office"),
    ("gallery", "classroom()", "gallery_classroom"),
    ("gallery", "bedroom()", "gallery_bedroom"),
    ("gallery", "park()", "gallery_park"),
    ("gallery", "cafe()", "gallery_cafe"),
    ("gallery", "turnaround()", "gallery_turnaround"),
    ("gallery", "rooftop()", "gallery_rooftop"),
    ("gallery", "dusk_walk()", "gallery_dusk_walk"),
    ("gallery", "beach()", "gallery_beach"),
    ("gallery", "living_room()", "gallery_living_room"),
    ("doomer", "man()", "doomer_man"),
    ("doomer", "woman()", "doomer_woman"),
    ("doomer", "pair_stop()", "doomer_pair"),
    ("doomer", "character_sheet()", "doomer_sheet"),
    ("doomer", "district()", "doomer_district"),
    ("doomer", "field()", "doomer_field"),
    ("doomer", "still_life()", "doomer_still_life"),
    ("faces", "expressions()", "faces_expressions"),
    ("faces", "features()", "faces_features"),
    ("faces", "hairstyles()", "faces_hairstyles"),
    ("faces", "profiles()", "faces_profiles"),
    ("faces", "crowd()", "faces_crowd"),
    ("variety", "rain_two()", "variety_rain_two"),
    ("variety", "bedroom_night()", "variety_bedroom_night"),
    ("variety", "beach_rest()", "variety_beach_rest"),
    ("variety", "park_bench()", "variety_park_bench"),
    ("variety", "classroom_teacher()", "variety_classroom_teacher"),
    ("variety", "pose_sheet()", "variety_pose_sheet"),
    ("variety", "elder_walk()", "variety_elder_walk"),
    ("variety", "back_views()", "variety_back_views"),
    ("variety", "lineup()", "variety_lineup"),
    ("variety", "living_phone()", "variety_living_phone"),
    ("variety", "closeup_cafe()", "variety_closeup_cafe"),
    ("variety", "medium_office()", "variety_medium_office"),
    ("variety", "long_shot()", "variety_long_shot"),
    ("variety", "low_angle()", "variety_low_angle"),
    ("variety", "thirds_beach()", "variety_thirds_beach"),
    ("variety", "group_photo()", "variety_group_photo"),
    ("variety", "sofa_four()", "variety_sofa_four"),
    ("variety", "crosswalk()", "variety_crosswalk"),
    ("variety", "park_pairs()", "variety_park_pairs"),
    ("variety", "meeting()", "variety_meeting"),
    ("variety", "office_late()", "variety_office_late"),
]
LIMITS = dict(contrast=(0.25, 1.0), clipped_white=(0.0, 0.25), clipped_black=(0.0, 0.35), detail=(0.002, 1.0))


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / "examples" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for module_name, call, name in CASES:
        module = load(module_name)
        start = time.time()
        img = eval(call, vars(module))
        save(img, out_dir / f"{name}.png")
        s = review.stats(img)
        bad = [k for k, (lo, hi) in LIMITS.items() if not lo <= s[k] <= hi]
        failures += bool(bad)
        print(f"{'FAIL' if bad else 'ok  '} {name:22s} {time.time() - start:5.1f}s "
              f"contrast={s['contrast']:.2f} white={s['clipped_white']:.3f} black={s['clipped_black']:.3f} "
              f"detail={s['detail']:.4f} {'<- ' + ','.join(bad) if bad else ''}")
    return failures


if __name__ == "__main__":
    sys.exit(1 if main(Path(sys.argv[1] if len(sys.argv) > 1 else "selftest_out")) else 0)
