"""Quick and dirty fix to use as alternative to pyld downloader.

Allows keeping some context in local filesystem.
"""
import logging
import re
import string
from typing import Dict, Optional
import urllib.parse as urllib_parse
import importlib

import requests
from pyld import jsonld
from pyld.jsonld import JsonLdError, parse_link_header, LINK_HEADER_REL

logger = logging.getLogger(__name__)


def _load_jsonld_file(original_url, filename: str):
    return {
        "contentType": "application/ld+json",
        "contextUrl": None,
        "documentUrl": original_url,
        "document": (
            importlib.resources.files("aries_cloudagent.resources") / filename
        ).read_text(),
    }


class StaticCacheJsonLdDownloader:
    """Downloader checking local filesystem for known contexts."""

    CONTEXT_FILE_MAPPING = {
        "https://www.w3.org/2018/credentials/v1": "credentials_context.jsonld",
        "https://w3id.org/vc/status-list/2021/v1": "status_list_context.jsonld",
        "https://www.w3.org/ns/did/v1": "did_documents_context.jsonld",
        "https://w3id.org/security/v1": "security-v1-context.jsonld",
        "https://w3id.org/security/v2": "security-v2-context.jsonld",
        "https://w3id.org/security/suites/ed25519-2020/v1": "ed25519-2020-context.jsonld",
    }

    def __init__(self):
        """."""
        self.documents_downloader = JsonLdDocumentDownloader()
        self.document_parser = JsonLdDocumentParser()

        self.cache = {
            url: self.document_parser.parse(_load_jsonld_file(url, filename), None)
            for url, filename in StaticCacheJsonLdDownloader.CONTEXT_FILE_MAPPING.items()
        }

    def load(self, url, options=None):
        """Load a jsonld document from url."""
        cached = self.cache.get(url)

        if cached is not None:
            logger.info("Cache hit for context: %s", url)
            return cached

        logger.info("Context %s not in static cache, resolving from URL.", url)
        return self._live_load(url, options)

    def _live_load(self, url, options=None):
        doc, link_header = self.documents_downloader.download(url, options)
        return self.document_parser.parse(doc, link_header)


class JsonLdDocumentDownloader:
    """JsonLd documents downloader."""

    def download(self, url: str, options: Dict, **kwargs):
        """Download json ld files, checking preconditions on URL."""
        """Retrieves JSON-LD at the given URL.

        :param url: the URL to retrieve.

        :return: the RemoteDocument.
        """
        options = options or {}

        try:
            # validate URL
            pieces = urllib_parse.urlparse(url)
            if (
                not all([pieces.scheme, pieces.netloc])
                or pieces.scheme not in ["http", "https"]
                or set(pieces.netloc)
                > set(string.ascii_letters + string.digits + "-.:")
            ):
                raise JsonLdError(
                    'URL could not be dereferenced; only "http" and "https" '
                    "URLs are supported.",
                    "jsonld.InvalidUrl",
                    {"url": url},
                    code="loading document failed",
                )
            if options.get("secure") and pieces.scheme != "https":
                raise JsonLdError(
                    "URL could not be dereferenced; secure mode enabled and "
                    'the URL\'s scheme is not "https".',
                    "jsonld.InvalidUrl",
                    {"url": url},
                    code="loading document failed",
                )
            headers = options.get("headers")
            if headers is None:
                headers = {"Accept": "application/ld+json, application/json"}
            response = requests.get(url, headers=headers, **kwargs)

            content_type = response.headers.get("content-type")
            if not content_type:
                content_type = "application/octet-stream"
            doc = {
                "contentType": content_type,
                "contextUrl": None,
                "documentUrl": response.url,
                "document": response.json(),
            }

            return doc, response.headers.get("link")
        except Exception as cause:
            raise JsonLdError(
                "Could not retrieve a JSON-LD document from the URL.",
                "jsonld.LoadDocumentError",
                code="loading document failed",
                cause=cause,
            )


class JsonLdDocumentParser:
    """JsonLd documents parser."""

    def parse(self, doc: Dict, link_header: Optional[str]):
        """Parse a jsonld document after retrieval."""
        try:
            if link_header:
                linked_context = parse_link_header(link_header).get(LINK_HEADER_REL)
                # only 1 related link header permitted
                if linked_context and doc["content_type"] != "application/ld+json":
                    if isinstance(linked_context, list):
                        raise JsonLdError(
                            "URL could not be dereferenced, "
                            "it has more than one "
                            "associated HTTP Link Header.",
                            "jsonld.LoadDocumentError",
                            {"url": doc["url"]},
                            code="multiple context link headers",
                        )
                    doc["contextUrl"] = linked_context["target"]
                linked_alternate = parse_link_header(link_header).get("alternate")
                # if not JSON-LD, alternate may point there
                if (
                    linked_alternate
                    and linked_alternate.get("type") == "application/ld+json"
                    and not re.match(
                        r"^application\/(\w*\+)?json$", doc["content_type"]
                    )
                ):
                    doc["contentType"] = "application/ld+json"
                    doc["documentUrl"] = jsonld.prepend_base(
                        doc["url"], linked_alternate["target"]
                    )
            return doc
        except JsonLdError as e:
            raise e
        except Exception as cause:
            raise JsonLdError(
                "Could not retrieve a JSON-LD document from the URL.",
                "jsonld.LoadDocumentError",
                code="loading document failed",
                cause=cause,
            )
