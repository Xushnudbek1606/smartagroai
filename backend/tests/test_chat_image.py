from __future__ import annotations

import base64
import json

# 1x1 transparent PNG
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _open_socket(client, token):
    from fastapi.testclient import TestClient  # noqa: F401

    return client.websocket_connect(f"/ws/chat/{None}?token={token}")


def test_send_image_in_chat(client, farmer, agronom):
    """Farmer sends a PNG over the WebSocket; message with attachment persists."""
    from tests.conftest import auth_headers, login

    # farmer starts a conversation
    aid = agronom.id
    conv = client.post(
        "/api/v1/conversations",
        json={"agronomist_id": aid},
        headers=auth_headers(client, "farmer1"),
    ).json()
    cid = conv["id"]
    tok = login(client, "farmer1")["access_token"]

    data_url = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode()
    with client.websocket_connect(f"/ws/chat/{cid}?token={tok}") as ws:
        ws.send_text(
            json.dumps({"event": "message.send_image", "image": data_url, "text": "bor holat"})
        )
        # the broadcast frame for our own message comes back to us too
        frame = json.loads(ws.receive_text())
        assert frame["event"] == "message.created"
        msg = frame["message"]
        assert msg["attachment_url"].startswith("/static/chat_images/")
        assert msg["attachment_name"].endswith(".png")
        assert msg["message_text"] == "bor holat"


def test_invalid_image_rejected(client, farmer, agronom):
    from tests.conftest import auth_headers, login

    conv = client.post(
        "/api/v1/conversations",
        json={"agronomist_id": agronom.id},
        headers=auth_headers(client, "farmer1"),
    ).json()
    tok = login(client, "farmer1")["access_token"]

    with client.websocket_connect(f"/ws/chat/{conv['id']}?token={tok}") as ws:
        ws.send_text(
            json.dumps({"event": "message.send_image", "image": "data:image/png;base64,###"})
        )
        frame = json.loads(ws.receive_text())
        assert frame["event"] == "error"
        assert frame["code"] == "invalid_image"


def test_non_participant_cannot_send_image(client, farmer, farmer2, db):
    import pytest
    from fastapi import WebSocketDisconnect

    from tests.conftest import auth_headers, login, make_user

    agr = make_user(db, "agronomImg", "agronom")
    conv = client.post(
        "/api/v1/conversations",
        json={"agronomist_id": agr.id},
        headers=auth_headers(client, "farmer1"),
    ).json()
    tok2 = login(client, "farmer2")["access_token"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/chat/{conv['id']}?token={tok2}"):
            pass  # server rejects non-participants at connect time (code 4403)
