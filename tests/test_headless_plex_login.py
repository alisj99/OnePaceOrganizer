import importlib.util
import sys
import types
import unittest
from unittest.mock import AsyncMock


def ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def stub_missing_dependencies():
    import pathlib
    if not hasattr(pathlib, "UnsupportedOperation"):
        pathlib.UnsupportedOperation = Exception
    if importlib.util.find_spec("enzyme") is None:
        ensure_module("enzyme")

    for module_name in ["httpx", "orjson", "aiosqlite", "tomllib"]:
        if importlib.util.find_spec(module_name) is None:
            ensure_module(module_name)

    if importlib.util.find_spec("yaml") is None:
        yaml_module = ensure_module("yaml")
        yaml_module.safe_load = lambda *_args, **_kwargs: {}

    if importlib.util.find_spec("loguru") is None:
        loguru_module = ensure_module("loguru")

        class DummyLogger:
            def __getattr__(self, _name):
                return lambda *args, **kwargs: None

        loguru_module.logger = DummyLogger()

    if importlib.util.find_spec("langcodes") is None:
        langcodes_module = ensure_module("langcodes")

        class DummyLanguage:
            @staticmethod
            def get(lang):
                return lang

        langcodes_module.Language = DummyLanguage

    if importlib.util.find_spec("plexapi") is None:
        plexapi = ensure_module("plexapi")
        exceptions = ensure_module("plexapi.exceptions")
        myplex = ensure_module("plexapi.myplex")
        server = ensure_module("plexapi.server")

        class DummyPlexException(Exception):
            pass

        exceptions.TwoFactorRequired = DummyPlexException
        exceptions.Unauthorized = DummyPlexException
        exceptions.NotFound = DummyPlexException

        class DummyAccount:
            def __init__(self, *args, **kwargs):
                pass

        class DummyJWTLogin:
            def __init__(self, *args, **kwargs):
                pass

        class DummyServer:
            def __init__(self, *args, **kwargs):
                pass

        myplex.MyPlexAccount = DummyAccount
        myplex.MyPlexJWTLogin = DummyJWTLogin
        server.PlexServer = DummyServer

        plexapi.exceptions = exceptions
        plexapi.myplex = myplex
        plexapi.server = server

    if importlib.util.find_spec("cryptography") is None:
        ensure_module("cryptography")
        ensure_module("cryptography.hazmat")
        ensure_module("cryptography.hazmat.primitives")
        ensure_module("cryptography.hazmat.primitives.serialization")
        ensure_module("cryptography.hazmat.primitives.asymmetric")


stub_missing_dependencies()

from src.organizer import OnePaceOrganizer


class DummyPlexServer:
    machineIdentifier = "server-id"
    friendlyName = "Test Server"


class HeadlessPlexLoginTest(unittest.IsolatedAsyncioTestCase):
    async def test_headless_token_login_runs_before_get_servers(self):
        organizer = OnePaceOrganizer()
        organizer.mode = 3
        organizer.plex_config_auth_token = "token"
        organizer.plex_config_url = "http://example"
        organizer.plex_config_remember = False

        async def fake_login():
            organizer.plexapi_server = DummyPlexServer()
            return True

        organizer.plex_login = AsyncMock(side_effect=fake_login)

        success = await organizer.plex_get_servers()

        self.assertTrue(success)
        organizer.plex_login.assert_awaited_once()
        self.assertEqual(organizer.plex_config_server_id, "server-id")
        self.assertIn("server-id", organizer.plex_config_servers)
