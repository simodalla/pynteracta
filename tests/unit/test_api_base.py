# SPDX-License-Identifier: Apache-2.0
"""Caratterizzazione di ``ResourceClient``: una risposta che non è un oggetto JSON è un errore.

Scritti alla riapertura di 02-T01: i rami ``TypeError`` di ``_get`` e ``_post`` erano senza test,
``_put`` e ``_delete`` li hanno copiati.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from api_helpers import BASE_URL, make_transport

from pynteracta.api._base import ResourceClient
from pynteracta.exceptions import NotFoundError

_PATH = "some/resource/1"
_EXPECTED_MESSAGE = f"Expected JSON object response from {_PATH}"
_HTTP_NO_CONTENT = 204


def _mock_array(method: str) -> respx.Route:
    return respx.route(method=method, url=f"{BASE_URL}/{_PATH}").mock(
        return_value=httpx.Response(200, json=[1, 2, 3])
    )


class TestResourceClientRejectsNonObjectBodies:
    @respx.mock
    def test_get_array_raises_type_error(self) -> None:
        _mock_array("GET")
        with pytest.raises(TypeError, match=_EXPECTED_MESSAGE):
            ResourceClient(make_transport())._get(_PATH)

    # criterio: 02-C01
    @respx.mock
    def test_post_array_raises_type_error(self) -> None:
        _mock_array("POST")
        with pytest.raises(TypeError, match=_EXPECTED_MESSAGE):
            ResourceClient(make_transport())._post(_PATH, json={})

    # criterio: 02-C04
    @respx.mock
    def test_put_array_raises_type_error(self) -> None:
        _mock_array("PUT")
        with pytest.raises(TypeError, match=_EXPECTED_MESSAGE):
            ResourceClient(make_transport())._put(_PATH, json={})

    # criterio: 02-C06
    @respx.mock
    def test_delete_array_raises_type_error(self) -> None:
        _mock_array("DELETE")
        with pytest.raises(TypeError, match=_EXPECTED_MESSAGE):
            ResourceClient(make_transport())._delete(_PATH)


class TestResourceClientEmptyBodies:
    # criterio: 05-C27
    @respx.mock
    def test_get_204_raises_not_found(self) -> None:
        """Il tenant risponde ``204`` vuoto al form di un utente inesistente (T15 della spec 05)."""
        route = respx.get(f"{BASE_URL}/{_PATH}").mock(return_value=httpx.Response(204))
        with pytest.raises(NotFoundError) as info:
            ResourceClient(make_transport())._get(_PATH)
        assert info.value.status_code == _HTTP_NO_CONTENT
        assert info.value.request_method == "GET"
        assert info.value.request_url == _PATH
        assert route.call_count == 1

    # criterio: 03-C08
    @respx.mock
    def test_put_without_body_returns_empty_dict(self) -> None:
        route = respx.put(f"{BASE_URL}/{_PATH}").mock(return_value=httpx.Response(200))
        assert ResourceClient(make_transport())._put(_PATH, json={}) == {}
        assert route.call_count == 1
