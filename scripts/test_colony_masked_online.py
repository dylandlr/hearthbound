import copy
import unittest
import numpy as np
import json
import hashlib
import tempfile
from pathlib import Path
from colony_masked_policy import load_policy
from train_colony_task_allocation import source_manifest
from colony_task_env import Env
from colony_allocation_alias import decision_mask
from train_colony_masked_online import MaskedNetwork, train


class MaskedOnlineTests(unittest.TestCase):
    def test_removed_head_cannot_supply_bootstrap_value(self):
        world=Env(3)
        world.step({0:1,1:0})
        while 0 not in world.ready(): world.step({a:0 for a in world.ready()})
        obs=tuple(world.obs(0))
        self.assertFalse(decision_mask(obs,True)[1])
        models=[MaskedNetwork(17,p) for p in (False,True)]
        changed=[]
        for model in models:
            for value in model.parameters.values(): value.fill(0)
            model.parameters['b2'][1]=100
            target=copy.deepcopy(model)
            target.parameters['b2'][1]=1000
            before=model.parameters['b2'][0]
            model.update([dict(observation=obs,next_observation=obs,action=0,
                               discounted_reward=0,duration=1,terminal=False)],target)
            changed.append(model.parameters['b2'][0]!=before)
            self.assertFalse(model.backup_mask)
        self.assertEqual(changed,[True,False])

    def test_mask_keeps_wait_and_finite_inference_values(self):
        model=MaskedNetwork(5,True)
        obs=Env(3).obs(0)
        self.assertTrue(decision_mask(obs,True)[0])
        self.assertTrue(np.isfinite(model.values(obs)).all())
        self.assertTrue(decision_mask(obs,True)[model.greedy(obs)])

    def test_equal_tick_budgets_produce_equal_actual_updates(self):
        for prune in (False,True):
            model=train(101,5,prune)
            self.assertEqual(model.updates,64)

    def test_loader_preserves_mask_and_rejects_missing_or_changed_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.json'
            model=MaskedNetwork(17,True)
            model.save(path)
            data=json.loads(path.read_text())
            with self.assertRaises(ValueError): load_policy(path)
            protocol=dict(schema='hearthbound.online-masked-allocation.v0.7',
                source_sha256=hashlib.sha256(Path(__file__).with_name('train_colony_masked_online.py').read_bytes()).hexdigest(),
                original_sources=source_manifest())
            data['online_mask_contract']=dict(prune=True,protocol=protocol)
            path.write_text(json.dumps(data))
            restored=load_policy(path)
            self.assertTrue(restored.prune)
            self.assertEqual(restored.digest(),model.digest())
            data['online_mask_contract']['prune']='true'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): load_policy(path)
            data['online_mask_contract']['prune']=True
            protocol['source_sha256']='invalid'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): load_policy(path)


if __name__=='__main__': unittest.main()
