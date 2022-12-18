from typing import List
import redis
import random, math
import pickle
import os
import constants


class Channel():

    def __init__(self, hostIP='localhost', portNo=6379):
        self.channel = redis.StrictRedis(host=hostIP, port=portNo, db=0)
        self.osmembers = {}
        self.MAXPROC = constants.NP

    def join(self, subgroup):

        # Atomic ID generation.
        # Without this there are cases that different processes can acquire same ID.
        created = False
        while not created:
            IDLock = self.channel.get("IDLock")

            if IDLock != None:
                IDLock = IDLock.decode("ascii")

            if (IDLock == "True"):
                print("Lock is used. Trying again.")
                continue

            elif (IDLock == None or IDLock == "False"):
                self.channel.set("IDLock", "True")

                # Generate an pid that does not exist on members
                members = self.channel.smembers('members')
                newpid = random.choice(list(set([str(i) for i in range(self.MAXPROC)]) - members))
                if len(members) > 0:
                    xchan = []
                    for otherClient in members:
                        self.channel.rpush('xchan', str([str(newpid), otherClient.decode("ascii")]))
                        self.channel.rpush('xchan', str([otherClient.decode("ascii"), str(newpid)]))

                self.channel.set("IDLock", "False")
                created = True
        assert not self.channel.sismember('members', str(newpid)), f'This id already exists'
        self.channel.sadd('members', str(newpid))
        self.channel.rpush(subgroup, str(newpid))
        return str(newpid)

    def leave(self, subgroup):
        ospid = os.getpid()
        pid = self.osmembers[ospid]
        assert self.channel.sismember('members', str(pid)), ''
        del self.osmembers[ospid]
        self.channel.sdel('members', str(pid))
        members = self.channel.smembers('members')
        if len(members) > 0:
            xchan = [[str(pid), other.decode("ascii")] for other in members] + [[other.decode("ascii"), str(pid)] for
                                                                                other in members]
            for xc in xchan:
                self.channel.rpop('xchan', str(xc))
        self.channel.sdel(subgroup, str(pid))
        return

    def exists(self, pid):
        return self.channel.sismember('members', str(pid))

    def bind(self, pid):
        ospid = os.getpid()
        self.osmembers[ospid] = str(pid)
        print("Process " + str(ospid) + " [" + pid + "] online")

    # print (self.osmembers)

    def subgroup(self, subgroup):
        return list(self.channel.lrange(subgroup, 0, 100))

    def sendTo(self, destinationSet, message):
        '''Give destination pid as bytes or integer and message as string'''

        # I guess it takes the pid of this process.
        caller = self.osmembers[os.getpid()]
        assert self.channel.sismember('members', str(caller)), 'This process did not join members'

        # Push message to every process which its pid in destinationSet
        for i in destinationSet:
            # if the pid is in bytes format, change it into integer.
            try:
                i = i.decode("ascii")
            except (UnicodeDecodeError, AttributeError):
                pass
            assert self.channel.sismember('members', str(i)), f'Destination set member {i}does not exist'
            self.channel.rpush(str([str(caller), str(i)]), str(message))
            self.channel.rpush("log", str(message))

    def sendToAll(self, message):
        caller = self.osmembers[os.getpid()]
        assert self.channel.sismember('members', str(caller)), ''
        for i in self.channel.smembers('members'):
            self.channel.rpush([str(caller), str(i)], pickle.dumps(message))

    def recvFromAny(self, timeout=0):
        caller = self.osmembers[os.getpid()]
        assert self.channel.sismember('members', str(caller)), f'This caller {caller} is not a member '
        members = self.channel.smembers('members')
        xchan = [str([i.decode("ascii"), str(caller)]) for i in members]
        msg = self.channel.blpop(xchan, timeout)

        if msg:
            return [(msg[0]).decode("ascii"), (msg[1].decode("ascii"))]