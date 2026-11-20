"""Regression tests for the daily import command.

A function-local `from django.utils import timezone` inside
Command.handle() made `timezone` a local name for the whole function, so
the very first use (`timezone.localtime()`) raised UnboundLocalError and the
daily cron failed before it imported anything -- leaving the site with no
new tips and no new results.
"""
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings


class FakeResp:
    status_code = 200

    def json(self):
        return {"results": [], "next": None}


class FakeSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        return FakeResp()


@override_settings(BZZOIRO_API_KEY="test-key")
class ImportCommandTests(TestCase):
    def test_handle_runs_end_to_end_with_an_empty_api(self):
        out, err = StringIO(), StringIO()
        with mock.patch("requests.Session", FakeSession):
            call_command("import_bzzoiro", stdout=out, stderr=err)
        self.assertEqual(err.getvalue().strip(), "")

    def test_missing_api_key_reports_error_instead_of_crashing(self):
        out, err = StringIO(), StringIO()
        with override_settings(BZZOIRO_API_KEY=""):
            call_command("import_bzzoiro", stdout=out, stderr=err)
        self.assertIn("BZZOIRO_API_KEY", err.getvalue())
