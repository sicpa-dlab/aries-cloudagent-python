"""
DID Document Public Key classes.

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

from collections import namedtuple
from enum import Enum
import json
from .util import canon_did, canon_ref
from .schemas.publickeyschema import PublicKeySchema

LinkedDataKeySpec = namedtuple("LinkedDataKeySpec", "ver_type authn_type specifier")


class PublicKeyType(Enum):
    """Class encapsulating public key types."""

    RSA_SIG_2018 = LinkedDataKeySpec(
        "RsaVerificationKey2018", "RsaSignatureAuthentication2018", "publicKeyPem"
    )
    ED25519_SIG_2018 = LinkedDataKeySpec(
        "Ed25519VerificationKey2018",
        "Ed25519SignatureAuthentication2018",
        "publicKeyBase58",
    )
    EDDSA_SA_SIG_SECP256K1 = LinkedDataKeySpec(
        "Secp256k1VerificationKey2018",
        "Secp256k1SignatureAuthenticationKey2018",
        "publicKeyHex",
    )

    @staticmethod
    def get(val: str) -> "PublicKeyType":
        """
        Find enum instance corresponding to input value (RsaVerificationKey2018 etc).

        Args:
            val: input value marking public key type

        Returns: the public key type

        """

        for pktype in PublicKeyType:
            if val in (pktype.ver_type, pktype.authn_type):
                return pktype
        return None

    @property
    def ver_type(self) -> str:
        """Accessor for the verification type identifier."""

        return self.value.ver_type

    @property
    def authn_type(self) -> str:
        """Accessor for the authentication type identifier."""

        return self.value.authn_type

    @property
    def specifier(self) -> str:
        """Accessor for the value specifier."""

        return self.value.specifier

    def specification(self, val: str) -> str:
        """
        Return specifier and input value for use in public key specification.

        Args:
            val: value of public key

        Returns: dict mapping applicable specifier to input value

        """

        return {self.specifier: val}


class PublicKey:
    """
    Public key specification to embed in DID document.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    def __init__(
            self,
            *args,
            type: PublicKeyType = None,
            controller: str = None,
            authn: bool = False,
            **kwargs
    ) -> None:
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

        self._type = type or PublicKeyType.ED25519_SIG_2018
        if args:
            self._did = canon_did(args[0])
            self._id = canon_ref(self._did, args[1])
            self._value = args[2]

        else:
            self._id = kwargs.get('id')

        self.__fill_key__(kwargs)
        self._controller = canon_did(controller) if controller else self._did
        self._authn = authn

    def __fill_key__(self, kwargs=None):
        if self._type == 'RsaVerificationKey2018':
            if kwargs:
                self.publicKeyPem = kwargs.get('publicKeyPem')
            else:
                self.publicKeyPem = self._value

        elif self._type == 'Ed25519VerificationKey2018':
            if kwargs:
                self.publicKeyBase58 = kwargs.get('publicKeyBase58')
            else:
                self.publicKeyBase58 = self.value

        elif self._type == 'Secp256k1VerificationKey2018':
            if kwargs:
                self.publicKeyHex = kwargs.get('publicKeyHex')
            else:
                self.publicKeyHex = self._value

        elif self._type == 'EcdsaSecp256k1RecoveryMethod2020':
            try:
                if kwargs:
                    value = kwargs.get('publicKeyJwk')
                else:
                    value = dict(self._value)
            except:
                value = json.loads(self._value)
            self.publicKeyJwk = value

    @property
    def did(self) -> str:
        """Accessor for the DID."""

        return self._did

    @property
    def id(self) -> str:
        """Accessor for the public key identifier."""

        return self._id

    @property
    def type(self) -> PublicKeyType:
        """Accessor for the public key type."""

        return self._type

    @property
    def value(self) -> str:
        """Accessor for the public key value."""

        return self._value

    @property
    def controller(self) -> str:
        """Accessor for the controller DID."""

        return self._controller

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

    def to_dict(self) -> dict:
        """Return dict representation of public key to embed in DID document."""
        schema = PublicKeySchema()
        result = schema.dump(self)
        result['controller'] = canon_ref(self.did, self.controller)
        return result

    def __repr__(self) -> str:
        """Return string representation of the public key instance."""

        return "PublicKey({}, {}, {}, {}, {}, {})".format(
            self.did, self.id, self.value, self.type, self.controller, self.authn
        )
