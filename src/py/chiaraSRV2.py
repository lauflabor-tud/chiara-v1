#!/usr/bin/python
"""
:module: chiaraSRV2.py
:synopsis: A tiny server that should be run under the user 'chiara' to allow
    certain actions to be done under the username 'chiara'

:moduleauthor: Moritz Maus <moritz.maus@hm10.net>

LE : 2013, Feb. 10 changed completely to use SocketServer
    (copy & paste from python.org socketserver's help)


"""
import SocketServer
import socket
import os 
import sys
import time
from ConfigParser import SafeConfigParser

# Configuration parser
cfg_parser = SafeConfigParser()
cfg_parser.read('../config.ini')
# Set config parameters
chiara_root = cfg_parser.get('server','chiara_root')
port = int(cfg_parser.get('server','port')) # for the chiara "file server"

os.chdir(chiara_root + 'py/')
__version__ = '0.2'


class config(object):
    """
    A simple object to store the config values
    """
    def __init__(self):
        self.password="chiara"
        self.data_dir = chiara_root + 'data/_chiara_/'  # trailing slash is important!
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)


def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

class MyTCPHandler(SocketServer.BaseRequestHandler):

    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.config = config()
        self.data = self.request.recv(1024).strip()
        res = self.parse(self.data)
        server._do_exit = False
        if not res:
            print "failure!\ninvalid request"
            print self.data
            self.request.sendall('1')
            return
        cmd, param = res
        if cmd=='store':
            if self.store(param):
                self.request.sendall('0')
            else:
                self.request.sendall('1')

        elif cmd=='get':
            if self.get(param):
                self.request.sendall('0')
            else:
                self.request.sendall('1')
        elif cmd=='shutdown':
            self.request.sendall('0')
            self.server._do_exit = True
            print "trying to shut down!"

        else:
            print "failure!\ninvalid command"
            self.request.sendall('2')
            return

    def get(self, param):
        """
        links a file from a file-id into the presented directory
        """

        items = param.split(':')
        filename = ':'.join(items[:-2])
        fileid = items[-2]
        filerev = items[-1]
        if os.path.exists(filename):
            print "failure!\nfile " + filename + " exists!"
            return False
        elif not os.path.exists(self.config.data_dir + fileid + '-' + filerev):
            print ("failure!\narchive file " + fileid + '-' + filerev +
            " does not exist in " + self.config.data_dir)
            return False
        else:

            cmd = ("ln " + self.config.data_dir + fileid + '-' + filerev + " "
                    + filename)
            os.system('pwd')
            print cmd
            res = os.system(cmd)
            if res == 0:
                print ('obtained file ' + filename + ' from archive (' +
                fileid + '-' + filerev + ')')
                return True
            else:
                print "failure!\ncopy operation failed :( - code " + str(res)
                return False


    def parse(self, data):
        """
        returns a tuple (command, param) or False if command if request is
        invalid
        """
        if not data.startswith(self.config.password + ':'):
            return False
        items = data.split(':')
        return items[1], ':'.join(items[2:])

    def store(self, param):
        """
        tries to move file to the given id
        """
        items = param.split(':')
        filename = ':'.join(items[:-2])
        fileid = items[-2]
        filerev = items[-1]
        if not os.path.exists(filename):
            print "failure!\nfile " + filename + " does not exist!"
            print "own path: ", os.getcwd()
            return False
        elif os.path.exists(self.config.data_dir + fileid + '-' + filerev):
            print ("failure!\narchive file " + fileid + '-' + filerev +
            " exists in " + self.config.data_dir)
            return False
        else:
            cmd = ('cp ' + shellquote(filename) + ' ' + self.config.data_dir +
                    fileid + '-' + filerev)
            #print cmd
            res = os.system(cmd)
            if res == 0:
                print ('copied file ' + filename + ' to archive (' +
                fileid + '-' + filerev + ')')
                cmd = ('chmod 444 ' + self.config.data_dir +
                    fileid + '-' + filerev)
                res = os.system(cmd)
                if res != 0:
                    print "FAILURE - PERMISSIONS FOR FILE NOT SET PROPERLY!"
                return True
            else:
                print "failure!\ncopy operation failed :( - code " + str(res)
                return False




if __name__ == "__main__":
    HOST, PORT = "localhost", port

    # Create the server, binding to localhost on port 10001
    launched = False
    print "starting server ..."
#    SocketServer.ThreadingTCPServer.allow_reuse_address = True
    while not launched:
        try:
            server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler, False)
            server.allow_reuse_address = True
            server.server_bind()
            server.server_activate()
            launched = True
            print "server launched!"
        except socket.error as err:
            dir(err)
            print "Error " + str(err.errno) + " : " + err.strerror 
            print "waiting 1 sec before next attempt"
            time.sleep(1)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    while True:
        server.handle_request() #    server.serve_forever()
        if server._do_exit:
            server.server_close()
            break;


sys.exit(0)




# From here: old stuff. delete if you like :)
#
#while True:
#    print "awaiting orders..."
#    c, addr = s.accept() # establish connection [c : socket, addr : address]
#    print "connected from", addr
#    dat = c.recv(1024) # wait for a message. buffer size is 1024 bytes.
#    success = False
#    if not dat.startswith(password+':'):
#        print "failure!\ninvalid password - use <password>:<command> as message"
#    else:
#        items = dat.split(':')
#        if len(items) < 5:
#            print "failure!\ninvalid format when talking to the server"
#        else:
#            command = items[1]
#            filename = ':'.join(items[2:-2])
#            fileid = items[-2]
#            filerev = items[-1]
#            if command=='store':
#                if not os.path.exists(filename):
#                    print "failure!\nfile " + filename + " does not exist!"
#                elif os.path.exists(self.config.data_dir + fileid + '-' +
#                        filerev):
#                    print ("failure!\narchive file " + fileid + '-' + filerev +
#                    " exists in " + self.config.data_dir)
#            
#                else:
#
#                    cmd = ('cp ' + filename + ' ' + self.config.data_dir +
#                            fileid + '-' + filerev)
#                    #print cmd
#                    res = os.system(cmd)
#                    if res == 0:
#                        print ('copied file ' + filename + ' to archive (' +
#                        fileid + '-' + filerev + ')')
#                        success=True
#                        cmd2 = ('chmod 444 ' + self.config.data_dir +
#                                fileid + '-' + filerev)
#                        res2 = os.system(cmd2)
#                    else:
#                        print "copy operation failed :( - code " + str(res)
#            elif command=='get':
#                print "COMMAND <get>: not yet implemented\n"
#            elif command=='shutdown':
#                print "Server shutdown - goodbye!\n"
#                c.send('0')
#                c.shutdown(socket.SHUT_RDWR)
#                c.close()
#                sys.exit(0)
#            else:
#                print "unknown command!\n"
#
#
##        os.system('cp ' + unknown command')
##        print dat
#    if success:
#        c.send('0')
#    else:
#        c.send('1')
#    c.shutdown(socket.SHUT_RDWR)
#    c.close()
##    os.system(
#
