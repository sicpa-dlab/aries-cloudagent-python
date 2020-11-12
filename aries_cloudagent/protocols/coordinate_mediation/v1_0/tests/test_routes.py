from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

# from aiohttp import web as aio_web

# from aries_cloudagent.config.injection_context import InjectionContext
# from aries_cloudagent.storage.error import StorageNotFoundError
# from aries_cloudagent.holder.base import BaseHolder
# from aries_cloudagent.messaging.request_context import RequestContext

from .. import routes as test_module


class TestCoordinateMediationRoutes(AsyncTestCase):
    async def test_mediation_records_list(self):
        pass
    async def test_mediation_records_list_x(self):
        pass
    async def test_mediation_records_retrieve(self):
        pass

    async def test_mediation_records_retrieve_x(self):
        pass
    async def test_mediation_records_create(self):
        pass
    async def test_mediation_records_create_send(self):
        pass
    async def test_mediation_records_send_stored(self):
        pass
    async def test_mediation_invitation(self):
        pass
    async def test_mediation_record_grant(self):
        pass
    async def test_keylist_list_all_records(self):
        pass
    async def test_send_keylists_request(self):
        pass
    async def test_update_keylists(self):
        pass
    
    async def test_send_update_keylists(self):
        pass

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
