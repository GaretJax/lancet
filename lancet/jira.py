from jira.client import GreenHopper  # NOQA
from jira.exceptions import JIRAError

from requests.cookies import RequestsCookieJar


__all__ = ['JIRA', 'JIRAError']


class ObliviousCookieJar(RequestsCookieJar):
    def set_cookie(self, *args, **kwargs):
        """Simply ignore any request to set a cookie."""
        pass

    def copy(self):
        """Make sure to return an instance of the correct class on copying."""
        return ObliviousCookieJar()


class JIRA(GreenHopper):
    def _create_http_basic_session(self, username, password):
        super(JIRA, self)._create_http_basic_session(username, password)

        # XXX: JIRA logs the web user out if we send the session cookies we get
        # back from the first request in any subsequent requests. As we don't
        # need cookies when accessing the API anyway, just ignore all of them.
        self._session.cookies = ObliviousCookieJar()

    def close(self):
        self._session.close()
