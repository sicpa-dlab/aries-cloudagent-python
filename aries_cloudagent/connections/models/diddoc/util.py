"""
DIDDoc utility methods.

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

from base58 import b58decode
from urllib.parse import urlparse
from .config import AVAILABLE_DIDS


def resource(ref: str, delimiter: str = None) -> str:
    """
    Extract the resource for an identifier.

    Given a (URI) reference, return up to its delimiter (exclusively), or all of it if
    there is none.

    Args:
        ref: reference
        delimiter: delimiter character
            (default None maps to '#', or ';' introduces identifiers)
    """

    return ref.split(delimiter if delimiter else "#")[0]


def canon_did(uri: str) -> str:
    """
    Convert a URI into a DID if need be, left-stripping 'did:XXX:' if present.

    Args:
        uri: input URI or DID

    Raises:
        ValueError: for invalid input.

    """
    error_msg = 'Bad specification {} does not correspond to a DID'.format(uri)

    uri_aux = uri.split(':')
    if len(uri_aux) > 1:
        uri = uri_aux[-1]
        if not '{}:{}'.format(uri_aux[0], uri_aux[1]) in AVAILABLE_DIDS:
            error_msg = 'Bad specification with DID {}. ' \
                        'Method {} not available'.format(uri, uri_aux[1])
            uri = ''

    if ok_did(uri):
        return uri

    raise ValueError(error_msg)


def compose_did(method: str, ref: str, network: str = None):
    """
    Compose DID with the method, ref & network
    """
    if network:
        did = 'did:{}:{}:{}'.format(method, network, ref)
    else:
        did = 'did:{}:{}'.format(method, ref)
    return did


def canon_ref(did: str, ref: str, delimiter: str = None, method: str = 'sov', network: str = None):
    """
    Given a reference in a DID document, return it in its canonical form of a URI.

    Args:
        did: DID acting as the identifier of the DID document
        ref: reference to canonicalize, either a DID or a fragment pointing to a
            location in the DID doc
        delimiter: delimiter character marking fragment (default '#') or
            introducing identifier (';') against DID resource
        method: DID method, 'sov' by default
        network: DID network if its exists.

    """

    if not ok_did(did):
        raise ValueError("Bad DID {} cannot act as DID document identifier".format(did))

    if ok_did(ref):  # e.g., LjgpST2rjsoxYegQDRm7EL
        return compose_did(method, did, network)

    if ok_did(resource(ref, delimiter)):  # e.g., LjgpST2rjsoxYegQDRm7EL#keys-1
        return compose_did(method, ref, network)

    did_prefix = 'did:{}:'.format(method)
    if network:
        did_prefix += '{}:'.format(network)
    if ref.startswith(did_prefix):  # e.g., did:sov:LjgpST2rjsoxYegQDRm7EL, did:sov:LjgpST2rjsoxYegQDRm7EL#3
        rv = ref.split(':')[-1]
        if ok_did(resource(rv, delimiter)):
            return ref
        raise ValueError("Bad URI {} does not correspond to a {} DID".format(ref, method))

    if urlparse(ref).scheme:  # e.g., https://example.com/messages/8377464
        return ref

    return "{}{}{}{}".format(did_prefix, did, delimiter if delimiter else "#", ref)  # e.g., 3


def ok_did(token: str) -> bool:
    """
    Whether input token looks like a valid decentralized identifier.

    Args:
        token: candidate string

    Returns: whether input token looks like a valid schema identifier

    """

    try:
        return len(b58decode(token)) == 16 if token else False
    except ValueError:
        return False
