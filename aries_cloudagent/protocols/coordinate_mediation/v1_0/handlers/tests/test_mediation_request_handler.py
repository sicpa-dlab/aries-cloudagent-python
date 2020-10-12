import pytest

from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

#from ...handlers.mediate_request_handler import MediationRequestHandler
#from ...messages.mediate_request import MediationRequest
#from ...messages.mediate_grant import MediationGrant

"""
    Tests for Mediation based on "0211: Mediator Coordination Protocol" aries-rfc. 
"""


class TestMediationRequestHandler:
    @pytest.mark.asyncio
    async def test_for_denied_mediation_request(self):
        """Test for MEDIATE_REQUEST request that results in MEDIATE_DENY response."""
        ctx = RequestContext()
        
        assert False
    
    async def test_for_granted_mediation_request(self):
        """Test for MEDIATE_REQUEST request that results in MEDIATE_GRANT response."""
        assert False

    async def test_for_list_keys_request(self):
        """Test for KEYLIST_QUERY request that results in KEYLIST response."""
        assert False

    async def test_for_updated_key_request(self):
        """Test for KEYLIST_UPDATE request that results in "
            "KEYLIST_UPDATE_RESPONSE response."""
        assert False
    
    async def test_for_updated_key_request(self):
        """Test for KEYLIST_QUERY request that results in KEYLIST response."""
        assert False