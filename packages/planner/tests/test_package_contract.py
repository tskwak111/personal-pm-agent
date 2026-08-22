from importlib.metadata import version

import personal_pm_planner


def test_planner_package_is_importable_and_versioned() -> None:
    assert personal_pm_planner.__version__ == version("personal-pm-planner")
