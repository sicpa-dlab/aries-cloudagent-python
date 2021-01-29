"""
DID Document Service classes.

Copyright 2017-2019 Government of Canada
Public Services and Procurement Canada - buyandsell.gc.ca

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import List, Sequence, Union

from .util import canon_did, canon_ref
from .publickey import PublicKey
from .schemas.serviceschema import ServiceSchema


class Service:
    """
    Service specification to embed in DID document.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    """"""

    def __init__(
            self,
            *args,
            priority: int = 0,
            **kwargs
    ):
        """
        Initialize the Service instance.

        Retain service specification particulars.

        Args:
            did: DID of DID document embedding service, specified raw
                (operation converts to URI)
            ident: identifier for service
            typ: service type
            recip_keys: recipient key or keys
            routing_keys: routing key or keys
            endpoint: service endpoint
            priority: service priority

        Raises:
            ValueError: on bad input controller DID

        """
        if args:
            self._did = canon_did(args[0])
            self._id = id if id else canon_ref(self._did, args[1], ";")
            self._type = args[2]
            self._recip_keys = (
                [args[3]]
                if isinstance(args[3], PublicKey)
                else list(args[3])
                if [args[3]]
                else None
            )
            self._routing_keys = (
                [args[4]]
                if isinstance(args[4], PublicKey)
                else list(args[4])
                if args[4]
                else None
            )
            self._endpoint = args[5]
        else:
            self._id = kwargs.get('id')
            self._type = kwargs.get('type')
            self._recip_keys = kwargs.get('recipientKeys')
            self._endpoint = kwargs.get('serviceEndpoint')
            self._routing_keys = kwargs.get('routingKeys')
        self._priority = priority

    @property
    def did(self) -> str:
        """Accessor for the DID value."""

        return self._did

    @property
    def id(self) -> str:
        """Accessor for the service identifier."""

        return self._id

    @property
    def type(self) -> str:
        """Accessor for the service type."""

        return self._type

    @property
    def recip_keys(self) -> List[PublicKey]:
        """Accessor for the recipient keys."""

        return self._recip_keys

    @property
    def recipientKeys(self) -> List[PublicKey]:
        """Accessor for the recipient keys."""

        return self._recip_keys

    @property
    def routing_keys(self) -> List[PublicKey]:
        """Accessor for the routing keys."""

        return self._routing_keys

    @property
    def routingKeys(self) -> List[PublicKey]:
        """Accessor for the routing keys."""

        return self._routing_keys

    @property
    def endpoint(self) -> str:
        """Accessor for the endpoint value."""

        return self._endpoint

    @property
    def serviceEndpoint(self) -> str:
        """Accessor for the endpoint value."""

        return self._endpoint

    @property
    def priority(self) -> int:
        """Accessor for the priority value."""

        return self._priority

    def to_dict(self) -> dict:
        """Return dict representation of service to embed in DID document."""

        schema = ServiceSchema()
        result = schema.dump(self)
        return result
