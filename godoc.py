#!/usr/bin/env python3
"""Start the godoc server and open the docs in a browser window.

This uses the 'open' command to open a web browser.

"""

import argparse
import http
import http.client
import subprocess
import time


def is_ready(host, port):
    """Check if the web server returns an OK status."""
    conn = http.client.HTTPConnection(host, port)
    try:
        conn.request('HEAD', '/')
        resp = conn.getresponse()
        return resp.status == 200
    except ConnectionRefusedError:
        return False


def main():
    """Do the thing."""
    parser = argparse.ArgumentParser(description='Spawn godoc and open browser window.')
    parser.add_argument('--port', help='port on which to run godoc', default=6060)
    args = parser.parse_args()

    host = "localhost"
    port = args.port

    # If not already running, start godoc in the background and wait for it
    # to be ready by making an HTTP request and checking the status.
    if not is_ready(host, port):
        subprocess.Popen(["godoc", "-http=:{port}".format(port=port)])
        while True:
            if is_ready(host, port):
                break
            print('Waiting for server to start...')
            time.sleep(1)

    # Open the docs in a browser window.
    url = "http://{host}:{port}".format(host=host, port=port)
    subprocess.check_call(["open", url])


if __name__ == "__main__":
    main()
