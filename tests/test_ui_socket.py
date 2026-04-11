import json
import socket
import threading
import time
import os


def _start_fake_server(path: str, received: list) -> threading.Thread:
    """Serveur Unix socket minimal qui capture le premier message reçu."""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(1)

    def serve():
        conn, _ = srv.accept()
        data = conn.recv(1024)
        received.append(data)
        conn.close()
        srv.close()
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return t


def test_send_state_sends_correct_json():
    path = "/tmp/jarvis_test_1.sock"
    received = []

    t = _start_fake_server(path, received)
    time.sleep(0.05)

    import ui_socket as uisock
    uisock._send_to(path, "listening", 0.72)

    t.join(timeout=1.0)
    assert received, "Aucun message reçu"
    msg = json.loads(received[0])
    assert msg["state"] == "listening"
    assert abs(msg["amplitude"] - 0.72) < 0.01


def test_send_state_silent_on_no_socket():
    """send_state ne doit pas lever d'exception si la socket n'existe pas."""
    import ui_socket as uisock
    uisock._send_to("/tmp/nonexistent_jarvis_test.sock", "standby", 0.0)
    # Pas d'exception = succès


def test_send_state_rounds_amplitude():
    path = "/tmp/jarvis_test_2.sock"
    received = []

    t = _start_fake_server(path, received)
    time.sleep(0.05)

    import ui_socket as uisock
    uisock._send_to(path, "speaking", 0.123456789)

    t.join(timeout=1.0)
    msg = json.loads(received[0])
    # Arrondi à 3 décimales
    assert msg["amplitude"] == 0.123
