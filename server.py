#!/usr/bin/env python3

import socketserver
from queue import Queue,Empty
from threading import Thread
import re
import traceback

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

READLIMIT = 1024
MAXNAMELEN = 20
MAXMSGLEN = 200
COORDBOUND = 10000


REG,UNREG = -1,-2

##ERRORS:
ERR_LONGMESSAGE = 1
ERR_ALREADYJOINED = 2
ERR_NOTJOINED = 3
ERR_NOSUCHGROUP = 4
ERR_INVALIDNAME = 5

MSGDELIM = b'\n'
DELIM = b';'
FIELDSEP = b','

class Service(socketserver.BaseRequestHandler):
    def handle(self):
        self.closed = False
        self.queue = Queue()
        self.controller = controller
        try:
            self.sender = Thread(target=self._datasender)
            self.sender.start()
            self.controller.register(self)
            while True:
                data = self.request.recv(READLIMIT)
                if not data:
                    break
                self.controller.put((id(self),data))
        finally:
            self.close()

    def _datasender(self):
        try:
            while not self.closed:
                self.request.sendall(self.queue.get())
        except OSError:
            pass

    def put(self, item, block=True, timeout=None):
        self.queue.put(item, block=True, timeout=None)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.controller.unregister(self)
        self.request.close()

class Controller:
    def __init__(self, workerclass):
        self.queue = Queue()
        self.gen = self._datareceiver()
        self.worker = workerclass(self)
        self.connections = {}
        self.buffers = {}

    def _datareceiver(self):
        while True:
            yield self.queue.get()

    def send(self, cid, item, block=True, timeout=None):
        self.connections[cid].put(item+MSGDELIM, block=True, timeout=None)

    def put(self, item, block=True, timeout=None):
        self.queue.put(item, block=True, timeout=None)

    def register(self, conn):
        self.queue.put((REG,conn))

    def unregister(self, conn):
        self.queue.put((UNREG,id(conn)))

    def _register(self,conn):
        if id(conn) not in self.connections:
            self.connections[id(conn)] = conn
            print('CON',conn.client_address)
            self.buffers[id(conn)] = b''

    def _unregister(self,cid):
        try:
            print('DIS',self.connections[cid].client_address)
            del self.connections[cid]
            del self.buffers[cid]
            self.worker.leave(cid)
        except KeyError:
            pass

    def run(self): #The work
        for cid,data in self._datareceiver():
            if cid==REG: 
                #print('REG')
                self._register(data)
            elif cid==UNREG:
                #print('UNREG')
                self._unregister(data)
            elif cid not in self.connections:
                pass
            else:
                data = self.buffers[cid]+data
                while MSGDELIM in data:
                    self.worker.process(cid,data[:data.index(MSGDELIM)])
                    data = data[data.index(MSGDELIM)+1:]
                self.buffers[cid] = data
                if len(data) > MAXMSGLEN:
                    self.worker.error(cid,ERR_LONGMESSAGE)
                    self.buffers[cid] = b''

class Worker:
    def __init__(self, controller):
        self.controller = controller
        self.clientnames = {}
        self.clientgroups = {}
        self.groups = {}
        self.groupcanvas = {}

    def process(self,cid,msg):
        try:
            elems = msg.split(DELIM)
            if elems[0]==b'join':
                assert(len(elems)==3)
                uname,gname = elems[1:]
                self.join(cid,uname,gname)
            elif elems[0]==b'shape':
                assert(len(elems)==4)
                stype,args,color = elems[1:]
                self.shape(cid,stype,args,color)
            elif elems[0]==b'leave':
                assert(len(elems)==1)
                self.leave(cid)
            elif elems[0]==b'who':
                assert(1<=len(elems)<=2)
                if len(elems)==1:
                    self.who(cid)
                else:
                    gname = elems[1]
                    self.who(cid,gname)
            elif elems[0]==b'groups':
                assert(len(elems)==1)
                self.grouplist(cid)
        except Exception:
            traceback.print_exc()

    def join(self,cid,uname,gname):
        assert(checkname(uname) and checkname(gname))
        if cid in self.clientgroups:
            self.error(cid, ERR_ALREADYJOINED)
            return
        if gname not in self.groups:
            self.groups[gname] = set()
            self.groupcanvas[gname] = []
        for tid in self.groups[gname]:
            self.controller.send(tid,DELIM.join((b'join',uname)))
            self.groupcanvas[gname] = [MSGDELIM.join(self.groupcanvas[gname])]
            self.controller.send(cid,self.groupcanvas[gname][0])
            #for msg in self.groupcanvas[gname]:
            #    self.controller.send(cid,msg)
        self.groups[gname].add(cid)
        self.clientnames[cid] = uname
        self.clientgroups[cid] = gname
        self.who(cid)

    def shape(self,cid,stype,args,color):
        if cid not in self.clientgroups:
            self.error(cid, ERR_NOTJOINED)
            return
        gname = self.clientgroups[cid]
        uname = self.clientnames[cid]
        assert(checkcolor(color) and checkshapeargs(stype,args))
        # TODO: Possibly normalize arg ints
        msg = DELIM.join((b'shape',uname,stype,args,color))
        for tid in self.groups[gname]:
            self.controller.send(tid,msg)
        self.groupcanvas[gname].append(msg)

    def leave(self,cid):
        #print('LEAVE')
        if cid not in self.clientgroups:
            return
        gname = self.clientgroups[cid]
        uname = self.clientnames[cid]
        self.groups[gname].remove(cid)
        for tid in self.groups[gname]:
            self.controller.send(tid,DELIM.join((b'leave',uname)))
        del self.clientnames[cid]
        del self.clientgroups[cid]
        if not self.groups[gname]:
            del self.groups[gname]
            del self.groupcanvas[gname]

    def who(self,cid,gname=None):
        if cid not in self.clientgroups and gname is None:
            self.error(cid, ERR_NOTJOINED)
            return
        if gname is None:
            gname = self.clientgroups[cid]
        if gname not in self.groups:
            self.error(cid, ERR_NOSUCHGROUP)
            return
        self.controller.send(cid,DELIM.join((b'users',FIELDSEP.join(self.clientnames[n] for n in self.groups[gname]))))

    def grouplist(self,cid):
        self.controller.send(cid,DELIM.join((b'groups',FIELDSEP.join(self.groups))))

    def error(self, cid, err):
        messages = {0:b'',
                    ERR_LONGMESSAGE:b'Message too long',
                    ERR_ALREADYJOINED:b'Already joined group',
                    ERR_NOTJOINED:b'Not member of any group',
                    ERR_NOSUCHGROUP:b'Group does not exist',
                    ERR_INVALIDNAME:b'Illegal name',
                }
        self.controller.send(cid,DELIM.join((b'error',messages[err])))

def checkname(name):
    return len(name)<=MAXNAMELEN and bool(re.match(b'[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_]+',name))

def checkshapeargs(stype,args):
    #print(stype,args)
    params = [int(s) for s in args.split(FIELDSEP)]
    length = len(params)
    if max(params)>COORDBOUND or min(params)<-COORDBOUND:
        return False
    if stype == b'triangle':
        return length==6
    if stype in [b'line',b'rectangle',b'oval']:
        return length==4
    return False

def checkcolor(color):
    return color in [b'blue',b'red',b'green',b'yellow',b'black',b'violet',b'orange']

if __name__=="__main__":
    ThreadedTCPServer.allow_reuse_address = True
    global controller
    controller = Controller(Worker)
    import sys
    port = 5678 if len(sys.argv)==1 else int(sys.argv[1])
    t = ThreadedTCPServer(('',port), Service)
    Thread(target=t.serve_forever).start()
    controller.run()