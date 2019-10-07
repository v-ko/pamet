#!/usr/bin/env python

import os, sys, struct
import Pyro4

sys.excepthook = Pyro4.util.excepthook


def read_message():
    text_length_bytes = sys.stdin.buffer.read(4)

    if len(text_length_bytes) == 0:
        sys.exit(0)

    # Unpack message length as 4 byte integer.
    text_length = struct.unpack('i', text_length_bytes)[0]

    # Read the text (JSON object) of the message.
    text = sys.stdin.buffer.read(text_length).decode('utf-8')
    return text


def send_message(message):
    # Write message size.
    sys.stdout.buffer.write(struct.pack('I', len(message)))
    # Write the message itself.
    sys.stdout.buffer.write(bytes(message,'utf-8'))
    sys.stdout.flush()


def send_text_message(text):
    send_message('{"text":"'+text+'"}')


def main(arguments):
    sys.stderr.write("Started echo host\n")
    sys.stderr.flush()

    # Connect to the quodlibet extension
    interface = Pyro4.Proxy("PYRO:interface@localhost:53546")

    if not interface:
        sys.stderr.write("Could not connect to quodlibet extension")
        return -1

    while True:
        message = read_message()
        if message:
            sys.stderr.write("Received message:"+message+"\n")
            test = interface.test("/sync/Музика/21 pilots/Twenty One Pilots - Blurryface (2015)/02. Stressed Out.mp3")
            sys.stderr.write("Interface test returned:" + test + "\n")
            sys.stderr.flush()
            send_message(test)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
