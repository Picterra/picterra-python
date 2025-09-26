import base64
import hashlib
import multiprocessing
import os
import random
import string
import time
import urllib.parse as urlparse
import webbrowser
from base64 import urlsafe_b64encode
from datetime import datetime
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
from random import random
from typing import Any, Dict, Optional, Type, no_type_check
from urllib.parse import parse_qs, urljoin, urlparse

import requests


class OAuthError(Exception):
    pass

CLIENT_ID = "ggshield_oauth"
SCOPE = "scan"

# potential port range to be used to run local server
# to handle authorization code callback
# this is the largest band of not commonly occupied ports
# https://stackoverflow.com/questions/10476987/best-tcp-port-number-range-for-internal-applications
LOCAL_SERVER_USABLE_PORT_RANGE = (29170, 29998)
LOCAL_SERVER_MAX_WAIT_S = 60
LOCAL_SERVER_ADDRESS = "127.0.0.1"


def long_running_function_mp(secs):
    for _ in range(secs): # Simulate a long running task
        time.sleep(1)


def _generate_pkce_pair():
    code_verifier = ''.join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(
            random.randint(43, 128)
        )
    )
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8').replace('=', '')
    return code_verifier, code_challenge


def _get_error_param(parsed_url: urlparse.ParseResult) -> Optional[str]:
    """
    extract the value of the 'error' url param. If not present, return None.
    """
    params = urlparse.parse_qs(parsed_url.query)
    if "error" in params:
        return params["error"][0]
    return None


def extract_qs_parameter(url_string, key) -> Optional[str]:
    parsed_url = urlparse(url_string)
    query_parameters = parse_qs(parsed_url.query)
    return query_parameters.get(key, [None])[0]


class OAuthClient:
    _port: Optional[int] = None
    local_server: Optional[HTTPServer] = None
    picterra_uri: str
    pkce_pair: tuple[str, str]
    """
    Helper class to handle the OAuth authentication flow
    the logic is divided in 2 steps:
    - open the browser on GitGuardian login screen and run a local server to wait for callback
    - handle the oauth callback to exchange an authorization code against a valid access token
    """

    def __init__(self, client_id: str, server_uri: str) -> None:
        self._client_id = client_id
        self._state = ""  # use the `state` property instead
        self._lifetime: Optional[int] = None
        self._login_path = "auth/login"
        self._handler_wrapper = RequestHandlerWrapper(oauth_client=self)
        self._access_token: Optional[str] = None
        self.picterra_uri = server_uri
        self.pkce_pair = _generate_pkce_pair()

    @property
    def redirect_uri(self) -> str:
        return "http://" + LOCAL_SERVER_ADDRESS + ":" + self._port

    @property
    def authorize_uri(self) -> str:
        return urljoin(self.picterra_uri, "o/authorize/")

    def start(self):
        webbrowser.open_new_tab(self.authorize_uri)

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
        authorization_code = self._get_code(callback_url)
        self._claim_token(authorization_code)
        token_data = self._validate_access_token()
        self._save_token(token_data)

    def _redirect_to_login(self) -> None:
        """
        Open the user's browser to authentication page
        """
        requests.get(
            self.authorize_uri,
            params={
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": SCOPE,
                "state": self.state,
                "code_challenge": self.pkce_pair[1],
                "code_challenge_method": "S256",
                "client_id": self._client_id,
                "utm_source": "picterra-python",
            }
        )

    def _get_access_token(self, code: str):
        requests.post(
            "http://127.0.0.1:8000/o/token/",
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "code_verifier": self.pkce_pair[0],
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
        )

    def _spawn_server(self) -> None:
        for port in range(*LOCAL_SERVER_USABLE_PORT_RANGE):
            try:
                self.local_server = HTTPServer(
                    # only consider requests from localhost on the predetermined port
                    # When starting a local server for OAuth callbacks, binding to all
                    # interfaces (0.0.0.0) exposes your authentication server to other
                    # machines on the network. This could allow attackers to intercept
                    # OAuth codes or inject malicious responses. Always bind only to
                    # localhost (127.0.0.1) to ensure the callback server is accessible
                    # only from the local machine.
                    (LOCAL_SERVER_ADDRESS, port),
                    # attach the wrapped request handler
                    self._handler_wrapper.request_handler,
                )
                self._port = port
                p = multiprocessing.Process(
                    target=long_running_function_mp,
                    args=(LOCAL_SERVER_MAX_WAIT_S,)
                )
                p.start()
                p.join(LOCAL_SERVER_MAX_WAIT_S)
                if p.is_alive():
                    print("Function timed out, terminating process...")
                    p.terminate()
                    p.join()  # Wait for the process to terminate
                    raise Exception("Function timed out!")
                else:
                    print("Function finished within the time limit.")
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
        try:
            while not self._handler_wrapper.complete:
                # Wait for callback on localserver including an authorization code
                # any matching request will get processed by the request handler and
                # the `process_callback` function
                self.local_server.handle_request()
        except KeyboardInterrupt:
            raise OAuthError("User stopped login process.")

        if self._handler_wrapper.error_message is not None:
            # if no error message is attached, the process is considered successful
            raise OAuthError(self._handler_wrapper.error_message)

    def _get_code(self, uri: str) -> str:
        """
        Extract the authorization from the incoming request uri and verify that the state from
        the uri match the one stored internally.
        if no code can be extracted or the state is invalid, raise an OAuthError
        else return the extracted code
        """
        authorization_code = extract_qs_parameter(uri, "code")
        if authorization_code is None:
            raise OAuthError("Invalid code or state received from the callback.")
        return authorization_code

    @property
    def default_token_lifetime(self) -> Optional[int]:
        """
        return the default token lifetime saved in the instance config.
        if None, this will be interpreted as no expiry.
        """
        instance_lifetime = self.instance_config.default_token_lifetime
        if instance_lifetime is not None:
            return instance_lifetime
        return self.config.auth_config.default_token_lifetime


class RequestHandlerWrapper:
    """
    Utilitary class to link the server and the request handler.
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
                parsed_url = urlparse.urlparse(callback_url)
                if parsed_url.path == "/":
                    error_string = _get_error_param(parsed_url)
                    if error_string is not None:
                        self_._end_request(200)
                        self.error_message = self.oauth_client.get_server_error_message(
                            error_string
                        )
                    else:
                        try:
                            self.oauth_client.process_callback(callback_url)
                        except Exception as error:
                            self_._end_request(400)
                            # attach error message to the handler wrapper instance
                            self.error_message = error.message
                        else:
                            self_._end_request(
                                301,
                                urljoin(
                                    self.oauth_client.dashboard_url, "authenticated"
                                ),
                            )

                    # indicate to the server to stop
                    self.complete = True
                else:
                    self_._end_request(404)

            def _end_request(
                self_, status_code: int, redirect_url: Optional[str] = None
            ) -> None:
                """
                End the current request. If a redirect url is provided,
                the response will be a redirection to this url.
                If not the response will be a user error 400
                """
                self_.send_response(status_code)

                if redirect_url is not None:
                    self_.send_header("Location", redirect_url)
                self_.end_headers()

        return RequestHandler
