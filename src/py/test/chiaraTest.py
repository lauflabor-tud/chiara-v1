#!/usr/bin/python

import socket
import os # for the os.system call
import sys # for testing only

if __name__ == '__main__':
    s = socket.socket()
    host = socket.gethostname()
    print host
    port = 9999

    s.connect(('127.0.0.1', port))
    msg = sys.argv[1]
    MSGLEN = len(msg)
    print "sending <" + msg + "> (len: ", MSGLEN, ")"

    totalsent = 0
    while totalsent < MSGLEN:
        sent = s.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        totalsent = totalsent + sent

    dat = s.recv(1024) # wait for server response
    if dat == '0':
        print "server command successful"
    else:
        print "failure on server"
    s.shutdown(socket.SHUT_RDWR)
    s.close()

    sys.exit(int(dat))

