"""Message type identifiers for Routing."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "fa8dc4ea1e667eb07db8f9ffeaf074a4455697c0/features/0211-route-coordination"
)

# Message types
FORWARD = f"routing/1.0/forward"
ROUTE_QUERY_REQUEST = f"routing/1.0/route-query-request"
ROUTE_QUERY_RESPONSE = f"routing/1.0/route-query-response"
ROUTE_UPDATE_REQUEST = f"routing/1.0/route-update-request"
ROUTE_UPDATE_RESPONSE = f"routing/1.0/route-update-response"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.routing.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        FORWARD: f"{PROTOCOL_PACKAGE}.messages.forward.Forward",
        ROUTE_QUERY_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.route_query_request.RouteQueryRequest"
        ),
        ROUTE_QUERY_RESPONSE: (
            f"{PROTOCOL_PACKAGE}.messages.route_query_response.RouteQueryResponse"
        ),
        ROUTE_UPDATE_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.route_update_request.RouteUpdateRequest"
        ),
        ROUTE_UPDATE_RESPONSE: (
            f"{PROTOCOL_PACKAGE}.messages.route_update_response.RouteUpdateResponse"
        ),
    }
)
