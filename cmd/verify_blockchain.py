import os
import mmap
import csv
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
            blockheader, prev_blockhash_bigendian_b = parseBlockHeader(mptr, start, jsonobj['height'])
            # blockheader['height'] = jsonobj['height']
            # mptr.close()
            return mptr, blockheader, prev_blockhash_bigendian_b
    return None


def verify_input(tx, i):
    # print(f'{i}-------------')
    ret = verifyScript(tx, i)
    # if not ret:
    #     print(f"signature verification failed, txid:{tx['txid']} i: {i}")
    # print(f'-------------{i}')
    return ret


def verify_transaction(mptr):
    tx = getTransactionInfo(mptr)
    if not tx:
        return -1
    # print('Transaction:')
    # print(json.dumps(tx, indent=4))

    failed = 0
    for i in range(tx['inp_cnt']):
        if not verify_input(tx, i):
            failed += 1
    return failed


def verify_block(block_hash):
    mptr, blockheader, prev_blockhash_bigendian_b = load_block(block_hash)

    coinbase_tx = getCoinbaseTransactionInfo(mptr)
    # print('CoinBase:')
    # print(json.dumps(coinbase_tx, indent=4))
    tx_count = blockheader['tx_count']
    for i in range(tx_count):
        failed = verify_transaction(mptr)
        if failed == -1:
            break
        print(f'verified tx: {i}/{tx_count}, {failed} inputs failed')
    print(f'verified block: {block_hash[::-1].hex()} tx_count: {tx_count}')
    mptr.close()
    return blockheader, prev_blockhash_bigendian_b


def verify_blockchain() -> None:
    saved_blocks_file = '../output/saved_blocks.csv'
    # 尝试读取 saved_blocks.csv 文件
    if os.path.exists(saved_blocks_file):
        with open(saved_blocks_file, 'r') as file:
            reader = csv.reader(file)
            saved_block_set = {row[0] for row in reader}
    else:
        # 如果文件不存在，则创建一个空的集合并新建文件
        saved_block_set = set()
        with open(saved_blocks_file, 'w') as file:
            pass

    blockhash_bigendian_b = getRecentBlockHash(chainstate_db_g)
    blocks = 9

    while blockhash_bigendian_b and blocks > 0:
        mptr, blockheader, prev_blockhash_bigendian_b = load_block(blockhash_bigendian_b)
        blockhash = blockhash_bigendian_b[::-1].hex()

        # 检查该区块是否已经验证过
        if blockhash not in saved_block_set:

            coinbase_tx = getCoinbaseTransactionInfo(mptr)
            # # print('CoinBase:')
            # # print(json.dumps(coinbase_tx, indent=4))
            tx_count = blockheader['tx_count']
            for i in range(tx_count):
                failed = verify_transaction(mptr)
                if failed == -1:
                    break
                print(f'verified tx: {i}/{tx_count}, {failed} inputs failed')
            print(f'verified block: {blockhash} tx_count: {tx_count}')
            mptr.close()
            # 添加已验证的区块哈希到集合和文件中
            saved_block_set.add(blockhash)
            with open(saved_blocks_file, 'a') as file:
                writer = csv.writer(file)
                writer.writerow([blockhash])

        blockhash_bigendian_b = prev_blockhash_bigendian_b
        blocks -= 1


if __name__ == '__main__':
    verify_blockchain()
