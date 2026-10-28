"""Custom exceptions for F5 NAPALM."""


class CommitConfigException(Exception):
    """Exception raised when REST API error occurs during commit_config."""


class DiscardConfigException(Exception):
    """Exception raised when REST API error occurs during discard_config."""


class ReplaceConfigException(Exception):
    """Exception raised when REST API error occurs during replacement of a config."""


class ReadOnlyModeException(Exception):
    """Exception raised when change is attempted when read-only mode is enabled."""
