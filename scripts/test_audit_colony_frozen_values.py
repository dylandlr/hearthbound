import copy
import unittest
from audit_colony_frozen_values import context, finish
from colony_task_env import Env
from train_colony_task_allocation import Network


class AuditTests(unittest.TestCase):
    def test_branch_leaves_original_world_and_model_unchanged(self):
        world, model = Env(345), Network(17)
        before = copy.deepcopy(world.__dict__)
        digest = model.digest()
        output = finish(world, {0:0,1:0}, model, False)
        self.assertIsInstance(output,int)
        self.assertEqual(world.__dict__,before)
        self.assertEqual(model.digest(),digest)

    def test_same_branch_is_deterministic(self):
        world, model=Env(71),Network(17)
        self.assertEqual(finish(world,{0:1,1:2},model,False),
                         finish(world,{0:1,1:2},model,False))

    def test_coverage_key_contains_only_supplied_observation(self):
        world=Env(90)
        obs=tuple(world.obs(0))
        self.assertEqual(context(obs),context(tuple(obs)))
        self.assertEqual(context(obs)[1],-1)


if __name__=='__main__':
    unittest.main()
