import base64
import hashlib
import logging
import random
import string
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Type
from urllib.parse import ParseResult, parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests

logger = logging.getLogger()


class OAuthError(Exception):
    pass


SCOPE = "scan"

# potential port range to be used to run local server
# to handle authorization code callback
# this is the largest band of not commonly occupied ports
# https://stackoverflow.com/questions/10476987/best-tcp-port-number-range-for-internal-applications
LOCAL_SERVER_USABLE_PORT_RANGE = (29170, 29998)
LOCAL_SERVER_MAX_WAIT_S = 60
# only consider requests from localhost on the predetermined port
# When starting a local server for OAuth callbacks, binding to all
# interfaces (0.0.0.0) exposes your authentication server to other
# machines on the network. This could allow attackers to intercept
# OAuth codes or inject malicious responses. Always bind only to
# localhost (127.0.0.1) to ensure the callback server is accessible
# only from the local machine.
LOCAL_SERVER_ADDRESS = "127.0.0.1"


def long_running_function_mp(secs):
    print(f"Timout is {secs}s")
    for _ in range(secs):  # Simulate a long running task
        time.sleep(1)
        print("Tick")


def _generate_pkce_pair():
    code_verifier = ''.join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(
            random.randint(43, 128)
        )
    )
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8').replace('=', '')
    return code_verifier, code_challenge


def _get_error_param(parsed_url: ParseResult) -> Optional[str]:
    """
    extract the value of the 'error' url param. If not present, return None.
    """
    params = parse_qs(parsed_url.query)
    if "error" in params:
        return params["error"][0] + ": " + params.get("error_description", [""])[0]
    return None


def _extract_qs_parameter(url_string, key) -> Optional[str]:
    parsed_url = urlparse(url_string)
    query_parameters = parse_qs(parsed_url.query)
    return query_parameters.get(key, [None])[0]


def _add_query_params(url, params):
    url_parts = urlparse(url)
    query = url_parts.query
    new_query_parts = urlencode(params)
    if query:
        new_query = f"{query}&{new_query_parts}"
    else:
        new_query = new_query_parts
    return urlunparse(url_parts._replace(query=new_query))


class OAuthClient:
    _port: Optional[int] = None
    local_server: Optional[HTTPServer] = None
    picterra_uri: str
    pkce_pair: tuple[str, str]
    """
    Helper class to handle the OAuth authentication flow

    The logic is divided in 2 steps:
    - open the browser on login screen and run a local server to wait for callback
    - handle the oauth callback to exchange an authorization code against a valid access token

    Some notes:
     * OAuth application client type must be "public" because we cannot securely store secret
       credentials, and we should NOT use the client secret anywhere; this is also the reason
       of using the PKCE flow , designed for clients that cannot keep a secret
    """

    def __init__(self, client_id: str, server_uri: str) -> None:
        self._client_id = client_id
        self._state = ""  # use the `state` property instead
        self._lifetime_s: Optional[int] = None
        self._handler_wrapper = RequestHandlerWrapper(oauth_client=self)
        self._access_token: Optional[str] = None
        self.picterra_uri = server_uri
        self.pkce_pair = _generate_pkce_pair()

    @property
    def redirect_uri(self) -> str:
        return f"http://{LOCAL_SERVER_ADDRESS}:{self._port}"

    @property
    def authorize_uri(self) -> str:
        base_url = urljoin(self.picterra_uri, "o/authorize/")
        return _add_query_params(
            base_url,
            {
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                # "scope": SCOPE,
                #"state": "foobar",
                "code_challenge": self.pkce_pair[1],
                "code_challenge_method": "S256",
                "client_id": self._client_id,
                "utm_source": "picterra-python",
            }
        )

    @property
    def token_uri(self):
        return urljoin(self.picterra_uri, "o/token/")

    def _get_access_token(self, code: str) -> None:
        print(f"Getting access token with code {code[:4]} from {self.token_uri}...")
        resp = requests.post(
            self.token_uri,
            data={
                "client_id": self._client_id,
                #"client_secret": "pbkdf2_sha256$870000$V13WjHqsdkeKiEVt1sEzWR$NolL9+bb5Mh7S/YyKxQhDbWZbRZw60w/6xdrOXqjO8Y=",
                "code": code,
                "code_verifier": self.pkce_pair[0],
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            },
            timeout=10,
        )
        if resp.ok is False:
            raise OAuthError(f"Error getting access token: {resp.text}")
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        self._lifetime_s = resp.json()["expires_in"]

    def _get_code(self, uri: str) -> str:
        """
        Extract the authorization from the incoming request uri and verify that the state from
        the uri match the one stored internally.
        if no code can be extracted or the state is invalid, raise an OAuthError
        else return the extracted code
        """
        authorization_code = _extract_qs_parameter(uri, "code")
        if authorization_code is None:
            raise OAuthError("Invalid code or state received from the callback.")
        return authorization_code

    def start(self):
        self._spawn_server()
        print(f"Login at {self.authorize_uri}")
        webbrowser.open_new_tab(self.authorize_uri)
        self._wait_for_callback()
        # self.local_server.shutdown()
        return {
            "token": self._access_token,
            "lifetime_s": self._lifetime_s,
        }

    def stop(self, error_message: str) -> None:
        #self.local_server.shutdown()
        raise OAuthError(f"Error after login: {error_message}.")

    def process_callback(self, callback_url: str) -> None:
        """
        This function runs within the request handler do_GET method.
        It takes the url of the callback request as argument and does
        - Extract the authorization code
        - Exchange the code against an access token with GitGuardian's api
        - Validate the new token against GitGuardian's api
        - Save the token in configuration
        Any error during this process will raise a OAuthError
        """
        print(f"Getting token from {callback_url[:7]}...")
        authorization_code = self._get_code(callback_url)
        self._get_access_token(authorization_code)

    def _spawn_server(self) -> None:
        for port in range(*LOCAL_SERVER_USABLE_PORT_RANGE):
            try:
                self.local_server = HTTPServer(
                    (LOCAL_SERVER_ADDRESS, port),
                    # attach the wrapped request handler
                    self._handler_wrapper.request_handler,  # TODO simplify ?
                )
                self.local_server.timeout = LOCAL_SERVER_MAX_WAIT_S
                self._port = port
                print("Started local server on port %d" % port)
                break
            except OSError:
                continue
        else:
            raise OAuthError("Could not find unoccupied port.")

    def _wait_for_callback(self) -> None:
        """
        Wait to receive and process the authorization callback on the local server.
        This actually catches HTTP requests made on the previously opened server.
        The callback processing logic is implemented in the request handler class
        and the `process_callback` method
        """
        assert self.local_server is not None
        try:
            print("Waiting for callback...")
            start_time = time.time()
            while self._handler_wrapper.complete is False:
                print(449580593854096)
                # Wait for callback on localserver including an authorization code
                # any matching request will get processed by the request handler and
                # the `process_callback` function
                self.local_server.handle_request()
                if time.time() - start_time > LOCAL_SERVER_MAX_WAIT_S:
                    raise OAuthError("Timeout waiting for callback.")
            if self._handler_wrapper.error_message is not None:
                raise OAuthError(self._handler_wrapper.error_message)
            print("Callback received.")
        except KeyboardInterrupt:
            raise OAuthError("User stopped login process.")
        if self._handler_wrapper.error_message is not None:
            # if no error message is attached, the process is considered successful
            raise OAuthError(self._handler_wrapper.error_message)


class RequestHandlerWrapper:
    """
    Helper class to link the server and the request handler.
    This allows to kill the server from the request processing.
    """

    oauth_client: OAuthClient
    # tells the server to stop listening to requests
    complete: bool
    # error encountered while processing the callback
    # if None, the process is considered successful
    error_message: Optional[str] = None

    def __init__(self, oauth_client: OAuthClient) -> None:
        self.oauth_client = oauth_client
        self.complete = False
        self.error_message = None

    @property
    def request_handler(self) -> Type[BaseHTTPRequestHandler]:
        class RequestHandler(BaseHTTPRequestHandler):
            def do_GET(self_) -> None:
                """
                This function process every GET request received by the server.
                Non-root request are skipped.
                If an authorization code can be extracted from the URI, attach it to the handler
                so it can be retrieved after the request is processed, then kill the server.
                """
                callback_url: str = self_.path
                parsed_url = urlparse(callback_url)
                if parsed_url.path == "/":
                    error_string = _get_error_param(parsed_url)
                    if error_string is not None:
                        print(455676778676)
                        self_._end_request(200)
                        # self.oauth_client.local_server.shutdown()
                        self.error_message = error_string
                    else:
                        try:
                            print(4354456)
                            self.oauth_client.process_callback(callback_url)
                            print(32222)
                            self_._end_request(200)
                        except Exception as error:
                            print(77777, error)
                            self.error_message = str(error)
                            self_._end_request(400)
                        # else:
                        #     self_._end_request(  # TODO ???
                        #         301,
                        #         urljoin(
                        #             self.oauth_client.dashboard_url, "authenticated"
                        #         ),
                        #     )
                    print(9999999999999999)
                    # indicate to the server to stop
                    self.complete = True
                    #self_._end_request(200)
                else:
                    print(657889)
                    self_._end_request(404)

            def _end_request(self_, status_code: int) -> None:
                assert 100 <= status_code <= 599
                self_.send_response(status_code)
                self_.end_headers()

        return RequestHandler
