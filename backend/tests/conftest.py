"""
Pytest root configuration and global session setup for ArthLens test suite.

Authoritative Reference: ArthLens Build Handbook v1.0.
"""

import os

# Set testing environment indicators
os.environ.setdefault("ENVIRONMENT", "test")
# Ensure that fast-running integration/contract test suites do not exhaust
# the default 60 req/min single-IP limit across hundreds of testclient calls.
os.environ.setdefault("RATE_LIMIT_PER_MINUTE_IP", "10000")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE_USER", "10000")
