import os
import sys

# Add src to path so imports resolve correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from main import app

    with TestClient(app) as c:
        yield c


# Common test constants matching the actual data range
TEST_DATE = "2015-01-03"
TEST_HOUR = 8
