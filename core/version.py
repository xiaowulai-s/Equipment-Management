__version__ = "2.0.0"

VERSION_INFO = {
    "major": 2,
    "minor": 0,
    "patch": 0,
    "releaselevel": "final",
    "serial": 0,
}


def get_version() -> str:
    return __version__


def get_version_info() -> dict:
    return dict(VERSION_INFO)
