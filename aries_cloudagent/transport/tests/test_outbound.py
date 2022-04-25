"""Test outbound message class."""

import pytest

from ...connections.models.connection_target import ConnectionTarget

from ..outbound.message import OutboundMessage


@pytest.fixture
def outbound():
    yield OutboundMessage(
        connection_id="connection id",
        payload="payload",
        enc_payload="enc_payload",
        reply_session_id="reply_session_id",
        reply_thread_id="reply_thread_id",
        reply_to_verkey="reply_to_verkey",
        reply_from_verkey="reply_from_verkey",
        target=ConnectionTarget(),
        target_list=[ConnectionTarget()],
        to_session_only=True,
    )


def test_serde(outbound: OutboundMessage):
    serialized = outbound.serialize()
    deserialized = outbound.deserialize(serialized)
    assert outbound.connection_id == deserialized.connection_id
    assert outbound.payload == deserialized.payload
    assert outbound.enc_payload == deserialized.enc_payload
    assert outbound.reply_session_id == deserialized.reply_session_id
    assert outbound.reply_thread_id == deserialized.reply_thread_id
    assert outbound.reply_to_verkey == deserialized.reply_to_verkey
    assert outbound.reply_from_verkey == deserialized.reply_from_verkey
    assert outbound.target.serialize() == deserialized.target.serialize()
    assert [target.serialize() for target in outbound.target_list] == [
        target.serialize() for target in deserialized.target_list
    ]
    assert outbound.to_session_only == deserialized.to_session_only

    assert serialized == deserialized.serialize()
