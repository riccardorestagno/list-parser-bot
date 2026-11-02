from enum import Enum


class RunStatus(str, Enum):
    """How a sweep ended, or that it hasn't yet."""

    RUNNING = "running"
    POSTED = "posted"
    NOTHING_NEW = "nothing-new"
    # Reddit or a site couldn't be reached for a moment: the next sweep tries again
    UNREACHABLE = "unreachable"
    FAILED = "failed"
