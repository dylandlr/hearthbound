import copy
import unittest
import numpy as np
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


if __name__=='__main__': unittest.main()
