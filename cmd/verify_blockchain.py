import os
import mmap
from numba import njit, jit
# import sys
# sys.path.append("..")

from bitcoin.BlockFileInfoFromBlockIndex import block_db_g, blocks_path_g
from bitcoin.ChainstateIndex import getRecentBlockHash, chainstate_db_g
from bitcoin.TraverseBlockchain import getBlockIndex, parseBlockHeader
from bitcoin.SegwitCoinbaseTransaction import getCoinbaseTransactionInfo
from bitcoin.SegwitBlockTransaction import getTransactionInfo
from bitcoin.VerifyScript_P2SH_P2WSH import verifyScript


def load_block(block_hash):
    """
    load a block from file into memory, purse IO operation
    :param block_hash:
    :return: previous memory map of block, block header
    """
    jsonobj = getBlockIndex(block_hash, block_db_g)
    if 'n_file' not in jsonobj:
        return None
    # print(jsonobj['n_file'])
    if 'data_pos' in jsonobj:
        block_filepath = os.path.join(blocks_path_g, 'blk%05d.dat' % jsonobj['n_file'])
        start = jsonobj['data_pos']
        # print('height = %d' % jsonobj['height'])
    elif 'undo_pos' in jsonobj:
        block_filepath = os.path.join(blocks_path_g, 'rev%05d.dat' % jsonobj['n_file'])
        start = jsonobj['undo_pos']
    # load file to memory
    block_file = open(block_filepath, 'rb')
    if block_file:
        mptr = mmap.mmap(block_file.fileno(), 0, prot=mmap.PROT_READ, flags=mmap.MAP_PRIVATE)
        block_file.close()
        if mptr:
            blockheader, prev_block_header_hash = parseBlockHeader(mptr, start, jsonobj['height'])
            # blockheader['height'] = jsonobj['height']
            # mptr.close()
            return mptr, blockheader
    return None


def verify_input(tx, i):
    # print(f'{i}-------------')
    ret = verifyScript(tx, i)
    if not ret:
        print(f"signature verification failed, txid:{tx['txid']} i: {i}")
    # print(f'-------------{i}')


def verify_transaction(mptr):
    tx = getTransactionInfo(mptr)
    # print('Transaction:')
    # print(json.dumps(tx, indent=4))

    for i in range(tx['inp_cnt']):
        verify_input(tx, i)


def verify_block(block_hash):
    mptr, blockheader = load_block(block_hash)

    coinbase_tx = getCoinbaseTransactionInfo(mptr)
    # print('CoinBase:')
    # print(json.dumps(coinbase_tx, indent=4))
    tx_count = blockheader['tx_count']
    for i in range(tx_count):
        verify_transaction(mptr)
    mptr.close()
    return blockheader


def verify_blockchain() -> None:
    prev_blockhash_bigendian_b = getRecentBlockHash(chainstate_db_g)
    blockheader_list = []
    blocks = 9
    errors = 0

    while prev_blockhash_bigendian_b and blocks > 0:
        blockheader = verify_block(prev_blockhash_bigendian_b)
        prev_blockhash_bigendian_b = blockheader['prev_block_hash']
        blocks -= 1


if __name__ == '__main__':
    verify_blockchain()
