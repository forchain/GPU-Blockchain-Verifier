import random
import socket
from GetSeedAddresses import getTestnetPeers
from BroadcastCompactBlocksLowBandwidth import sendrecvHandler
from Utils import flog

if __name__ == '__main__':
    peers = getTestnetPeers()
    print(peers)
    p = random.choice(peers)
    s = None
    peerinfo = {}
    print("Trying to connect to ", p, file=flog)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    err = s.connect(p)
    print('connected', file=flog)
    sendrecvHandler(s, 70015)
    s.close()
    flog.close()
