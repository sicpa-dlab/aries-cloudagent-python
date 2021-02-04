"""
DID Document Service classes.

Copyright 2021 Sicpa

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

    def __init__(self,
                 did: str = None,
                 ident: str = None,
                 type: Union[str, List] = None,
                 recipientKeys: Union[Sequence, PublicKey] = None,
                 routingKeys: Union[Sequence, PublicKey] = None,
                 serviceEndpoint: Union[str, Sequence, dict] = None,
                 priority: str = None,
                 id: str = None,
                 json: dict = {}):
        """
        Initialize the Service instance.

        Retain service specification particulars.

        Args:
            id: DID of DID document embedding service, specified raw
                (operation converts to URI)
            type: service type
            recipientKeys: recipient key or keys
            routingKeys: routing key or keys
            serviceEndpoint: service endpoint
            priority: service priority
            json: load from json

        Raises:
            ValueError: on bad input controller DID

        """

        if json:
            self.json = json

        else:

            if not id:
                if not (did and ident):
                    raise ValueError("Missing ID in the Service instantation")
                did = canon_did(did)
                id = canon_ref(did, ident, ";")

            args = (id, type, serviceEndpoint)

            if any(param is None for param in args):
                raise ValueError("Missing args in the Service instantation")

            self._id = id
            self._type = type
            self._endpoint = serviceEndpoint

            if recipientKeys:
                self._recip_keys = recipientKeys
            if routingKeys:
                self._routing_keys = routingKeys
            if priority:
                self._priority = priority

    @property
    def id(self) -> str:
        """Service identifier getter"""

        return self._id

    @id.setter
    def id(self, value: str):
        """Service identifier setter"""
        self._id = value

    @property
    def type(self) -> Union[str, list]:
        """Service type getter"""

        return self._type

    @type.setter
    def type(self, value: Union[str, list]):
        """Service type setter"""

        self._type = value

    @property
    def recipientKeys(self) -> List[PublicKey]:
        """Service Recipient Key getter"""

        return self._recip_keys

    @recipientKeys.setter
    def recipientKeys(self, value: list):
        """Service Recipient Key setter"""

        self._recip_keys = value

    @property
    def routingKeys(self) -> List[PublicKey]:
        """Service Routing Keys getter"""

        return self._routing_keys

    @routingKeys.setter
    def routingKeys(self, value: list):
        """Service Routing Keys setter"""

        self._routing_keys = value

    @property
    def serviceEndpoint(self) -> str:
        """Service Endpoint getter"""

        return self._endpoint

    @serviceEndpoint.setter
    def serviceEndpoint(self, value: Union[str, dict, list]):
        """Service Endpoint setter"""

        self._endpoint = value

    @property
    def priority(self) -> int:
        """Service Priority getter"""

        return self._priority

    @priority.setter
    def priority(self, value: int):
        """Service Priority setter"""
        self._priority = value

    @property
    def json(self) -> dict:
        """Return dict representation of service to embed in DID document."""

        schema = ServiceSchema()
        result = schema.dump(self)
        return result

    @json.setter
    def json(self, value: dict):
        """Load dict representation of service to embed in DID document."""
        schema = ServiceSchema()
        service = schema.load(value)
        self._id = service.id
        self._type = service.type
        self._recip_keys = service.recipientKeys
        self._endpoint = service.serviceEndpoint
        self._routing_keys = service.routingKeys
        self._priority = service.priority
