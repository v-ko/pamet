from pamet.services.rest_api.desktop_server import DesktopServer
from pamet.services.rest_api.instance_check import get_running_instance_port


def test_desktop_server_start_stop(tmp_path):
    # Start the server
    server = DesktopServer(config_dir=tmp_path)
    server.start()

    # Check that it's running
    assert get_running_instance_port(tmp_path)

    # Stop the server
    server.stop()

    # Check that it's not running
    assert not get_running_instance_port(tmp_path)
