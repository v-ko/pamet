from pathlib import Path
from fusion.visual_inspection.action_camera import ActionCamera


def test_record_new(window_fixture):
    rec_path = Path(__file__).parent / 'test_new.py'
    ActionCamera().record_until_exit(rec_path)
    assert rec_path.exists()
