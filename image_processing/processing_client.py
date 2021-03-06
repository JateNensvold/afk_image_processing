"""
Helper Script that can be used to connect to the feature detection server when
it is online, or start a new temporary feature detection section to parse the
image/arguments passed to this script
"""
import sys
import json
import pprint
from typing import List
from image_processing.afk.hero.hero_data import RosterJson

import zmq
import jsonpickle

import image_processing.globals as GV


def remote_compute_results(address: str, timeout: int, args: List[str]):
    """_summary_

    Args:
        address (str): address to connect the socket to
        timeout (int): timeout in ms to wait for results
        args (str): local path to image, or discord image URL and other global
            args
    """

    ZMQ_CONTEXT = zmq.Context()
    ZMQ_SOCKET: zmq.Socket = ZMQ_CONTEXT.socket(
        zmq.DEALER)  # pylint: disable=no-member

    ZMQ_SOCKET.connect(address)
    # pylint: disable=no-member
    ZMQ_SOCKET.setsockopt(zmq.RCVTIMEO, timeout)

    print(f"Arguments: {args}")

    ZMQ_SOCKET.send_string(json.dumps(args))
    received = ZMQ_SOCKET.recv()

    roster_json: RosterJson = jsonpickle.decode(received)
    # json_dict = json.loads(received)
    return roster_json


def main():
    """_summary_
    """

    address = "tcp://localhost:5555"
    GV.global_parse_args()

    roster_json = remote_compute_results(address, 15000, sys.argv[1:])

    pprint.pprint(roster_json.json_dict(), width=200)


if __name__ == "__main__":
    main()
