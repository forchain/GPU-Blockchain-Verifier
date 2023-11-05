# GPU-Blockchain-Verifier
Verify bitcoin transaction with GPU for acceleration

## Steps
### 1. Environment Variables
Edit ~/.zshrc or ~/.bashrc
```shell
export CHAINSTATE_DB=$HOME/.bitcoin/chainstate
export BLOCK_INDEX_DB=$HOME/.bitcoin/blocks/index
export BLOCKS_PATH=$HOME/.bitcoin/blocks
export TX_INDEX_DB=$HOME/.bitcoin/indexes/txindex
```

### 2. Requirement
```shell
pip install ecdsa, cryptotools
```

### 3. Run
```shell
python examples/verify_blockchain.py
```
