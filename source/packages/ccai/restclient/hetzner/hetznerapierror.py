"""
    .. module:: hetznerapierror
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`HetznerApiRequestError` — the transport-level error
               raised for a non-success Hetzner Cloud API response.

    This is deliberately a THIN error carrying the HTTP status, reason and
    body.  Consumers own the policy of translating status codes into their
    own typed hierarchies; the transport's job is to report faithfully.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Optional


class HetznerApiRequestError(Exception):
    """
        Raised when the Hetzner Cloud API returns a non-success status.

        :ivar status: The HTTP status code.
        :ivar reason: The API error code, or the HTTP reason phrase when the
            body carried no error object.
        :ivar body: The raw response body text.
    """

    def __init__(self, message: str, *, status: int = 0,
                 reason: str = "", body: Optional[str] = None) -> None:
        """
            Construct a HetznerApiRequestError.

            :param message: The human-readable error message.
            :param status: The HTTP status code.
            :param reason: The API error code or reason phrase.
            :param body: The raw response body.
        """
        super().__init__(message)
        self.status: int = status
        self.reason: str = reason
        self.body: Optional[str] = body
        return
