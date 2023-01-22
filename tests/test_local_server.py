from time import sleep
from pamet.services.local_server import LocalServer


def test_local_server(tmp_path):

    # Start the server
    server1 = LocalServer(config_dir=tmp_path)
    server2 = LocalServer(config_dir=tmp_path)
    server1.start()
    sleep(0.1)
    # Check that it's running
    assert server2.another_instance_is_running()

    # Stop the server
    server1.stop()

    # Check that it's not running
    assert not server2.another_instance_is_running()
