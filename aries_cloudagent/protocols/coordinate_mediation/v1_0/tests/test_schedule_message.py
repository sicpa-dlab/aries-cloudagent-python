import pytest

from ..models.scheduled_message import ScheduledMessage
from .....transport.outbound.message import OutboundMessage
from .....connections.models.connection_target import ConnectionTarget
from .....core.in_memory.profile import InMemoryProfile
from .....core.profile import Profile


@pytest.fixture
def outbound():
    yield OutboundMessage(
        connection_id="connection_id",
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


@pytest.fixture
def scheduled_message(outbound: OutboundMessage):
    yield ScheduledMessage(
        trigger_thread_id="test_thread_id",
        new_state="test_state",
        connection_id="test_conn_id",
        message=outbound,
    )


@pytest.fixture
def profile():
    yield InMemoryProfile.test_profile()


def test_serde(scheduled_message):
    assert scheduled_message == ScheduledMessage.deserialize(
        scheduled_message.serialize()
    )


@pytest.mark.asyncio
async def test_store_and_retrieve(
    profile: Profile, scheduled_message: ScheduledMessage
):
    async with profile.session() as session:
        await scheduled_message.save(session)
        recalled = await ScheduledMessage.retrieve_by_id(
            session, scheduled_message.scheduled_message_id
        )
        assert scheduled_message == recalled

        recalled, *_ = await ScheduledMessage.retrieve_by_trigger_thread_id(
            session, "test_thread_id"
        )
        assert scheduled_message == recalled
