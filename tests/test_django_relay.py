from __future__ import annotations

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, SimpleTestCase

from sitepulse.django.identity import get_local_user_id, scoped_user_hash


class TrustedUserTests(SimpleTestCase):
    def test_anonymous_user_has_no_local_id(self) -> None:
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        assert get_local_user_id(request) is None

    def test_authenticated_user_uses_server_side_id(self) -> None:
        request = RequestFactory().post("/", {"local_user_id": "spoofed"})
        user = User(username="demo")
        user.pk = 1842
        request.user = user

        assert get_local_user_id(request) == "1842"
        assert scoped_user_hash("secret", "1842").startswith("uh_")
