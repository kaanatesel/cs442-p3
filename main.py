import time

import constants
import sys
import threading
import random
import datetime
import channel

NP = str(sys.argv[1])
MINT = str(sys.argv[2])
MAXT = int(sys.argv[3])
AVGT = int(sys.argv[4])
NR = int(sys.argv[5])  # in ms

constants.NP = int(NP)
constants.MINT = int(MINT)
constants.MAXT = int(MAXT)
constants.AVGT = int(AVGT)
constants.NR = int(NR)


class ChildProcess(threading.Thread):
    def __init__(self, PID):
        threading.Thread.__init__(self)
        self.PID = PID
        self.ci = channel.Channel()
        self.req_count = 1


    # helper function to execute the threads
    def run(self):
        random_t = -1

        while self.req_count < constants.NP:
            while not (constants.MINT < random_t < constants.MAXT):
                current_time = datetime.datetime.now().timestamp()
                lam = 1 / constants.AVGT
                random.seed(current_time + self.PID)
                random_t = int(random.expovariate(lam))

                # send request
            self.ci.sendToAll('selam ben ' + str(self.PID) + ' ve benim send coun  ' + str(self.req_count))
            time.sleep(random_t)
            self.req_count += self.req_count

def listen_all():
    chal = channel.Channel()
    while True:
        x = chal.recvFromAny(1000)
        print(x)


for i in range(1, constants.NP + 1):
    new_tread = ChildProcess(i)
    new_tread.start()
