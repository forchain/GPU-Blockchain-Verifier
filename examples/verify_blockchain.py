# sys.path.append("lib")

import json
import os
import pandas as pd
import mmap

from lib.BlockFileInfoFromBlockIndex import block_db_g, blocks_path_g
from lib.ChainstateIndex import getRecentBlockHash, chainstate_db_g
from lib.TraverseBlockchain import getBlockIndex, parseBlockHeader
from lib.CoinbaseTransaction import getCoinbaseTransactionInfo
from lib.BlockTransactions import getTransactionInfo


def verify_blockchain() -> None:
    prev_blockhash_bigendian_b = getRecentBlockHash(chainstate_db_g)
    blockheader_list = []
    while True:
        jsonobj = getBlockIndex(prev_blockhash_bigendian_b, block_db_g)
        if 'n_file' not in jsonobj:
            break
        print(jsonobj['n_file'])
        if 'data_pos' in jsonobj:
            block_filepath = os.path.join(blocks_path_g, 'blk%05d.dat' % jsonobj['n_file'])
            start = jsonobj['data_pos']
            print('height = %d' % jsonobj['height'])
        elif 'undo_pos' in jsonobj:
            block_filepath = os.path.join(blocks_path_g, 'rev%05d.dat' % jsonobj['n_file'])
            start = jsonobj['undo_pos']
        # load file to memory
        with open(block_filepath, 'rb') as block_file:
            with mmap.mmap(block_file.fileno(), 0, prot=mmap.PROT_READ,
                           flags=mmap.MAP_PRIVATE) as mptr:  # File is open read-only
                blockheader, prev_blockhash_bigendian_b = parseBlockHeader(mptr, start, jsonobj['height'])
                coinbase_tx = getCoinbaseTransactionInfo(mptr)
                print('CoinBase:')
                print(json.dumps(coinbase_tx, indent=4))
                tx = getTransactionInfo(mptr)
                print('Transaction:')
                print(json.dumps(tx, indent=4))
                break

        blockheader['height'] = jsonobj['height']
        blockheader['tx_count'] = jsonobj['tx_count']
        blockheader_list.append(blockheader)
        if jsonobj['height'] == 1:
            break
    df = pd.DataFrame(blockheader_list)
    df.to_csv('out.csv', index=False)


if __name__ == '__main__':
    verify_blockchain()
