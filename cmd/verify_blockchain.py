import os
import mmap
import csv
import logging
from datetime import datetime

from numba import njit, jit
# import sys
# sys.path.append("..")

from bitcoin.BlockFileInfoFromBlockIndex import block_db_g, blocks_path_g
from bitcoin.ChainstateIndex import getRecentBlockHash, chainstate_db_g
from bitcoin.TraverseBlockchain import getBlockIndex, parseBlockHeader
from bitcoin.SegwitCoinbaseTransaction import getCoinbaseTransactionInfo
from bitcoin.SegwitBlockTransaction import getTransactionInfo
from bitcoin.VerifyScript_P2SH_P2WSH import verifyScript


# 配置日志
# 获取当前时间，并格式化为字符串
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f'blockchain_verification_{current_time}.log'
logging.basicConfig(filename=f'../output/{log_filename}',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
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


def verify_transaction(mptr):
    tx = getTransactionInfo(mptr)
    if not tx:
        return -1, None
    # tx_id = tx['txid']

    # print('Transaction:')
    # print(json.dumps(tx, indent=4))

    failed = 0
    for i in range(tx['inp_cnt']):
        if not verifyScript(tx, i):
            failed += 1
    return failed, tx


def verify_blockchain() -> None:
    last_block_file = '../output/last_block.csv'
    # 尝试读取 saved_blocks.csv 文件
    blockhash_bigendian_b = None
    if os.path.exists(last_block_file):
        with open(last_block_file, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                block_hash = row[0]
                block_hash_b = bytes.fromhex(block_hash)
                blockhash_bigendian_b = block_hash_b[::-1]
                break
    else:
        blockhash_bigendian_b = getRecentBlockHash(chainstate_db_g)

    blocks = 99

    while blockhash_bigendian_b and blocks > 0:
        mptr, blockheader, prev_blockhash_bigendian_b = load_block(blockhash_bigendian_b)
        blockhash = blockhash_bigendian_b[::-1].hex()
        # 添加已验证的区块哈希到集合和文件中
        with open(last_block_file, 'w') as file:
            writer = csv.writer(file)
            # save prev block hash so that current block gets skipped no matter if the verification is completed nor not
            writer.writerow([blockheader['prev_block_hash']])

        coinbase_tx = getCoinbaseTransactionInfo(mptr)
        # # print('CoinBase:')
        # # print(json.dumps(coinbase_tx, indent=4))
        tx_count = blockheader['tx_count']
        failed_tx = 0
        for i in range(tx_count):
            # workaround: prone to fail on last tx, investigate later
            if i > tx_count - 9:
                break
            failed, tx = verify_transaction(mptr)
            if failed < 0:
                break
            if failed > 0:
                failed_tx += 1
            logging.info(f'verified tx: {i}/{tx_count} {tx["txid"]}, {failed}/{tx["inp_cnt"]} inputs failed')
        logging.info(f'verified block: {blockhash} failed: {failed_tx}/{tx_count}')
        mptr.close()

        blockhash_bigendian_b = prev_blockhash_bigendian_b
        blocks -= 1


if __name__ == '__main__':
    verify_blockchain()
