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

import json
from typing import Sequence, Union

from .util import canon_did, canon_ref
from .schemas.verificationmethodschema import VerificationMethodSchema
from .publickeytype import PublicKeyType


class PublicKey:
    """
    Public key specification to embed in DID document.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    def __init__(
            self,
            did: str = None,
            ident: str = None,
            id: str = None,
            type: PublicKeyType = None,
            controller: Union[str, Sequence] = None,
            usage: str = None,
            value: str = None,
            authn: bool = False,
            json: dict = {},
            **kwargs) -> None:

        """
        Retain key specification particulars.

        Args:
            did: DID of DID document embedding public key
            ident: identifier for public key
            value: key content, encoded as key specification requires
            pk_type: public key type (enum), default ED25519_SIG_2018
            controller: controller DID (default DID of DID document)
            authn: whether key as has DID authentication privilege (default False)

        Raises:
            ValueError: on any bad input DID.

        """
        if json:
            self.json = json

        else:
            args = (type, controller, usage)
            optional_args = [did, ident, id]
            if any(param is None for param in args) and optional_args.count(None) > 1:
                raise ValueError("Missing args in the PublicKey instantation {}")

            if id:
                self._id = id
            else:
                did = canon_did(did)
                self._id = canon_ref(did, ident)

            self._type = type
            self._controller = canon_did(controller) if controller else did
            self._usage = usage
            if kwargs:
                value = kwargs.get(PublicKeyType.get(type).specifier)
            self.__fill_key__(value)

    def __fill_key__(self, value: str):
        if self._type == "RsaVerificationKey2018":
            self.publicKeyPem = value

        elif self._type == "Ed25519VerificationKey2018":
            self.publicKeyBase58 = value

        elif self._type == "Secp256k1VerificationKey2018":
            self.publicKeyHex = value

        elif self._type == "EcdsaSecp256k1RecoveryMethod2020":
            try:
                value = dict(value)
            except:
                value = json.loads(value)
            self.publicKeyJwk = value

    def __get_key__(self):
        if self._type == "RsaVerificationKey2018":
            return self.publicKeyPem

        elif self._type == "Ed25519VerificationKey2018":
            return self.publicKeyBase58

        elif self._type == "Secp256k1VerificationKey2018":
            return self.publicKeyHex

        elif self._type == "EcdsaSecp256k1RecoveryMethod2020":
            return str(self.publicKeyJwk)

    @property
    def id(self) -> str:
        """Getter for the public key identifier."""

        return self._id

    @id.setter
    def id(self, value: str):
        """Setter for the public key identifier."""

        self._id = value

    @property
    def type(self) -> PublicKeyType:
        """Getter for the public key type."""

        return self._type

    @type.setter
    def type(self, value: PublicKeyType):
        """Setter for the public key type."""

        self._type = value

    @property
    def value(self) -> str:
        """Getter for the public key value."""

        return self.__get_key__()

    @value.setter
    def value(self, value: str):
        """Setter for the public key value."""

        self.__fill_key__(value)

    @property
    def usage(self) -> PublicKeyType:
        """Getter for the public key usage."""

        return self._usage

    @usage.setter
    def usage(self, value: PublicKeyType):
        """Setter for the public key usage."""

        self._usage = value

    @property
    def controller(self) -> Union[str, Sequence]:
        """Getter for the controller DID."""

        return self._controller

    @controller.setter
    def controller(self, value: Union[str, Sequence]):
        """Setter for the controller DID."""

        self._controller = value

    @property
    def authn(self) -> bool:
        """Accessor for the authentication marker.

        Returns: whether public key is marked as having DID authentication privilege
        """

        return self._authn

    @authn.setter
    def authn(self, value: bool) -> None:
        """Setter for the authentication marker.

        Args:
            value: authentication marker
        """

        self._authn = value

    @property
    def json(self) -> dict:
        """Return dict representation of public key to embed in DID document."""
        schema = VerificationMethodSchema()
        result = schema.dump(self)
        return result

    @json.setter
    def json(self, value: dict):
        schema = VerificationMethodSchema()
        result = schema.load(value)
        self.type = result.type
        self.controller = result.controller
        self.id = result.id
        self.usage = result.usage
        self.__fill_key__(result.value)
        self.authn = False
