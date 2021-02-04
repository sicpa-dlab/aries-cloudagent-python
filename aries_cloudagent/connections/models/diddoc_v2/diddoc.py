"""
DID Document classes.

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

import logging

from typing import Union

from .publickey import PublicKey
from .service import Service
from .util import canon_did
from .schemas.diddocschema import DIDDocSchema

LOGGER = logging.getLogger(__name__)


class DIDDoc:
    """
    DID document, grouping a DID with verification keys and services.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    CONTEXT = "https://w3id.org/did/v1"


    def __init__(self, did: str = None, id: str = None, alsoKnownAs: list = None,
                 controller=None, verificationMethod: list = None, authentication=None,
                 assertionMethod=None, keyAgreement=None, capabilityInvocation=None,
                 capabilityDelegation=None, publicKey=None, service=None,
                 json=None) -> None:

        """
        Initialize the DIDDoc instance.

        Retain DID ('id' in DIDDoc context); initialize verification keys
        and services to empty lists.

        Args:
            did: DID for current DIDdoc
            TODO: complete

        Raises:
            ValueError: for bad input DID.

        """
        self._alsoKnownAs = None
        self._controller = None
        self._verificationMethod = None
        self._authentication = None
        self._assertionMethod = None
        self._keyAgreement = None
        self._capabilityInvocation = None
        self._capabilityDelegation = None
        self._publicKey = None
        self._service = None

        if json:
            did_doc = self.deserialize(json)
            self.__clone_did_doc__(did_doc, atributes=json.keys())
            return
        if did:
            self._id = canon_did(did) if did else None  # allow specification post-hoc

        elif id:
            self._id = id
        else:
            raise ValueError('did or id are required for DIDDoc instantiation')

        if alsoKnownAs:
            self._alsoKnownAs = alsoKnownAs

        if controller:
            self._controller = controller

        if verificationMethod:
            self._verificationMethod = verificationMethod

        if authentication:
            self._authentication = authentication

        if assertionMethod:
            self._assertionMethod = assertionMethod

        if keyAgreement:
            self._keyAgreement = keyAgreement

        if capabilityInvocation:
            self._capabilityInvocation = capabilityInvocation

        if capabilityDelegation:
            self._capabilityDelegation = capabilityDelegation

        if publicKey:
            self._publicKey = publicKey

        if service:
            self._service = service

    def deserialize(self, json: dict):
        """
        Deserialize a dict into a DIDDoc object.

        Args:
            json: service or public key to set
        Returns: DIDDoc object
        """
        schema = DIDDocSchema()
        did_doc = schema.load(json)
        return did_doc

    def serialize(self) -> dict:
        """
        Serialize the DIDDoc object into dict.

        Returns: Dict
        """
        schema = DIDDocSchema()
        did_doc = schema.dump(self)
        did_doc["@context"] = self.CONTEXT
        return did_doc

    def __clone_did_doc__(self, did_doc, atributes):
        """
        Clone function from a DIDDoc object.

        Args:
            did_doc: DIDDoc object to clone
            atributes: atributes to clone from the DIDDoc

        Returns: None
        """

        self._id = did_doc.id

        if "alsoKnownAs" in atributes:
            self._alsoKnownAs = did_doc.alsoKnownAs
        if "controller" in atributes:
            self._controller = did_doc.controller

        if "verificationMethod" in atributes:
            self._verificationMethod = did_doc.verificationMethod

        if "authentication" in atributes:
            self._authentication = did_doc.authentication

        if "assertionMethod" in atributes:
            self._assertionMethod = did_doc.assertionMethod

        if "keyAgreement" in atributes:
            self._keyAgreement = did_doc.keyAgreement

        if "capabilityInvocation" in atributes:
            self._capabilityInvocation = did_doc.capabilityInvocation

        if "capabilityDelegation" in atributes:
            self._capabilityDelegation = did_doc.capabilityDelegation

        if "publicKey" in atributes:
            self._publicKey = did_doc.publicKey

        if "service" in atributes:
            self._service = did_doc.service

    @property
    def id(self) -> str:
        """Accessor for DID."""

        return self._id

    @property
    def alsoKnownAs(self):
        return self._alsoKnownAs

    @property
    def controller(self):
        return self._controller

    @property
    def verificationMethod(self):
        return self._verificationMethod

    @property
    def authentication(self):
        return self._authentication

    @property
    def assertionMethod(self):
        return self._assertionMethod

    @property
    def keyAgreement(self):
        return self._keyAgreement

    @property
    def capabilityInvocation(self):
        return self._capabilityInvocation

    @property
    def capabilityDelegation(self):
        return self._capabilityDelegation

    @property
    def publicKey(self):

        return self._publicKey

    @property
    def service(self):

        return self._service

    @id.setter
    def id(self, value: str) -> None:
        """
        Set DID ('id' in DIDDoc context).

        Args:
            value: DID

        Raises:
            ValueError: for bad input DID.

        """

        self._id = canon_did(value) if value else None

    def set(self, item: Union[Service, PublicKey], upsert=False) -> "DIDDoc":
        """
        Add or replace service or public key; return current DIDDoc.
        Raises:
            ValueError: if input item is neither service nor public key.
        Args:
            item: service or public key to set
            upsert: True for overwrite if the ID exists
        Returns: None
        """
        if isinstance(item, Service):
            current_ids = [item.id for item in self.service]
            if not (item.id in current_ids):
                self._service.append(item)
            elif upsert:
                pos = current_ids.index(item.id)
                self._service[pos] = item
        else:
            current_ids = [item.id for item in self.pubkey]
            if not (item.id in current_ids) or upsert:
                self._pubkey.append(item)
            elif upsert:
                pos = current_ids.index(item.id)
                self._pubkey[pos] = item
