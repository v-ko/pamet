from time import sleep

from pamet.services.rest_api.desktop_server import DesktopServer


def test_desktop_server(tmp_path):
    # Start the server
    server1 = DesktopServer(config_dir=tmp_path)
    server2 = DesktopServer(config_dir=tmp_path)
    server1.start()
    sleep(0.1)
    # Check that it's running
    assert server2.get_running_instance_port()

    # Stop the server
    server1.stop()

    # Check that it's not running
    assert not server2.get_running_instance_port()
