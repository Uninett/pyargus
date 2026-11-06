import re
import sys
from argparse import ArgumentParser, Namespace
from enum import IntEnum

import httpx
from simple_rest_client.exceptions import AuthError

from .client import Client

SERVER_URL_RE = re.compile(r"^(?P<url>.*/)(?P<api_version>v\d+)/?$")
# Map up the subparsers so it is easy to get their help texts
PARSER_MAP = {}


# Explicit is better than implicit, especially in opposite land
class ShellExitCode(IntEnum):
    NoError = 0  # None is also treated as NoError
    Error = 1
    NetworkError = 2


class ServerError(Exception):
    pass


def main() -> ShellExitCode:
    parser = create_argparser()
    args = parser.parse_args()
    return args.func(args)


def create_argparser() -> ArgumentParser:
    global PARSER_MAP

    parser = ArgumentParser(
        description="Command line argus glue service",
    )
    parser.add_argument(
        "-u",
        "--argus-api-url",
        dest="server_url",
        default="",
        # For later: Unset when/if we have support for a config file
        required=True,
        help="Talk to argus at the given url",
    )
    parser.add_argument(
        "-t",
        "--token",
        # Cannot be required as we can verify argus without it
        default="",
        help="Use the given token to authenticate with the argus server",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbosity",
    )
    parser.add_argument(
        "--verify-argus-server",
        action="store_true",
        help="Verify that the URL is correct by accessing it",
    )
    parser.set_defaults(func=handle_global_args)

    subparsers = parser.add_subparsers(
        dest="command",
        help="subcommand help",
    )

    # heartbeat
    heartbeat_parser = subparsers.add_parser(
        "heartbeat",
        help="Send a heartbeat",
    )
    heartbeat_parser.set_defaults(func=handle_heartbeat)
    heartbeat_parser.add_argument(
        "--send",
        action="store_true",
        help="Send explicit heartbeat",
    )
    heartbeat_parser.add_argument(
        "--supported",
        action="store_true",
        help="Check if Argus server supports heartbeats",
    )
    PARSER_MAP["heartbeat"] = heartbeat_parser

    # token
    token_parser = subparsers.add_parser(
        "token",
        help="Token manipulation",
    )
    token_parser.set_defaults(func=handle_token)

    token_parser.add_argument(
        "-r",
        "--refresh",
        action="store_true",
        help="Use existing token to get a new token",
    )
    # For later: we need a suitable endpoint for the check first
    # token_parser.add_argument(
    #     "-c",
    #     "--check",
    #     action="store_true",
    #     help="Check if token is valid",
    # )
    PARSER_MAP["token"] = heartbeat_parser

    return parser


def handle_global_args(args: Namespace) -> ShellExitCode:
    if args.verify_argus_server:
        error = check_requisites(args.server_url, args.token)
        return error if error else do_verify_argus_server(args.server_url, args.verbose)
    return ShellExitCode.NoError


def do_verify_argus_server(url: str, verbose: bool = False) -> ShellExitCode:
    try:
        version = find_server_version(url)
        if verbose:
            print("Version:", version)
        return ShellExitCode.NoError
    except ServerError as e:
        msg = f"({e})" if str(e) else ""
        print(f"No Argus server at {url}", msg, file=sys.stderr)
        return ShellExitCode.NetworkError

    return ShellExitCode.NoError


def handle_heartbeat(args: Namespace) -> ShellExitCode:
    error = check_requisites(args.server_url, args.token)
    if error:
        return ShellExitCode.Error

    if args.supported:
        return do_heartbeat_supported(args.server_url, args.token)

    if args.send:
        return do_heartbeat_send(args.server_url, args.token)

    return PARSER_MAP[args.command].print_help()


def do_heartbeat_supported(url: str, token: str) -> ShellExitCode:
    client = Client(url, token)
    try:
        result = client.supports_heartbeat()
    except AuthError as e:
        print(f"Token: FAILED ({e})", file=sys.stderr)
        return ShellExitCode.Error
    except Exception as e:
        print(f"Argus: FAILED ({e})", file=sys.stderr)
        return ShellExitCode.Error
    pretty_supported = "on" if result else "off"
    print(f"Heartbeat support for Argus at {url}:", pretty_supported)
    return ShellExitCode.NoError


def do_heartbeat_send(url: str, token: str) -> ShellExitCode:
    client = Client(url, token)
    try:
        client.send_heartbeat()
    except Exception as e:
        result = do_heartbeat_supported(url, token)
        if result:
            print(f"Heartbeat: FAILED ({e})", file=sys.stderr)
        else:
            print(f"Heartbeat not supported for Argus at {url}", file=sys.stderr)
        return ShellExitCode.Error
    return ShellExitCode.NoError


def handle_token(args: Namespace) -> ShellExitCode:
    error = check_requisites(args.server_url, args.token)
    if error:
        return ShellExitCode.Error

    if args.refresh:
        return do_token_refresh(args.server_url, args.token, args.verbose)

    return PARSER_MAP[args.command].print_help()


def do_token_refresh(url: str, token: str, verbose: bool = False) -> ShellExitCode:
    client = Client(url, token)
    try:
        tokenobj = client.refresh_token()
    except AuthError as e:
        msg = f"({e})" if verbose else ""
        print("Token refresh FAILED", msg, file=sys.stderr)
        return ShellExitCode.Error

    print("Token:", tokenobj.token)
    print("Expiry:", tokenobj.expiry.isoformat() if tokenobj.expiry else "Never")
    return ShellExitCode.NoError


# helpers


def check_requisites(url: str, token: str) -> ShellExitCode:
    """Check if url and token are set and usable

    Does not return early so that all errores can be found in one go.
    """
    errors = False
    if not token:
        errors = True
        print("Token has not been given", file=sys.stderr)
    if check_server_requisites(url) != ShellExitCode.NoError:
        errors = True

    if errors:
        return ShellExitCode.Error
    return ShellExitCode.NoError


def check_server_requisites(url: str) -> ShellExitCode:
    matchobj = SERVER_URL_RE.search(url or "")
    if matchobj is None:
        print(
            f'Url "{url}" is of the wrong format, maybe missing version?',
            file=sys.stderr,
        )
        return ShellExitCode.Error
    return ShellExitCode.NoError


# For later: if we add proper support for "/api/" we can simplify this
def find_server_version(url) -> str:
    """Fetch server version from the Argus metadata endpoint.

    This endpoint is not versioned.

    If not found, raises ServerError
    """
    matchobj = SERVER_URL_RE.search(url)
    if matchobj is None:
        raise ServerError("Url is malformed, does not contain an API version")
    metadata_url, api_version = matchobj.groups()
    try:
        resp = httpx.get(metadata_url, follow_redirects=True)
    except Exception as e:
        raise ServerError from e
    if resp.status_code == 200:
        data = resp.json()
        if api_version in data["jsonapi-schema"]:
            return data.get("server-version")
        else:
            raise ServerError(f"Api version {api_version} not found")
    raise ServerError(f"Nothing found at {url}")


if __name__ == "__main__":
    sys.exit(main())
