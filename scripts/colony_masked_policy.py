"""Strict simulator-only loader preserving trained action semantics."""
import hashlib
import json
from pathlib import Path
from train_colony_task_allocation import Network, source_manifest
from train_colony_masked_online import MaskedNetwork


def load_policy(path):
    data=json.loads(Path(path).read_text())
    contract=data.get('online_mask_contract')
    if not isinstance(contract,dict) or type(contract.get('prune')) is not bool:
        raise ValueError('Missing typed online action-mask contract')
    protocol=contract.get('protocol',{})
    digest=hashlib.sha256(Path(__file__).with_name('train_colony_masked_online.py').read_bytes()).hexdigest()
    if (protocol.get('schema')!='hearthbound.online-masked-allocation.v0.7'
            or protocol.get('source_sha256')!=digest
            or protocol.get('original_sources')!=source_manifest()):
        raise ValueError('Incompatible training contract')
    weights=Network.load(Path(path))
    result=MaskedNetwork(0,contract['prune'])
    result.parameters=weights.parameters
    return result
