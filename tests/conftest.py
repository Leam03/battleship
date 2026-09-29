import os

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        path = str(item.path).replace("\\", "/")
        if "/integration/" in path:
            item.add_marker(pytest.mark.integration)
            if not os.getenv("TEST_DATABASE_URL"):
                item.add_marker(pytest.mark.skip(reason="TEST_DATABASE_URL is not set"))
        if "/e2e/" in path or "/performance/" in path:
            marker = "performance" if "/performance/" in path else "e2e"
            item.add_marker(getattr(pytest.mark, marker))
            if not os.getenv("BATTLESHIP_FIRST_URL") or not os.getenv("BATTLESHIP_SECOND_URL"):
                item.add_marker(pytest.mark.skip(reason="Two HTTP service URLs are required"))
