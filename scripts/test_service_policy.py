import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
from service_option_env import Env, encode, features, KINDS, episode, GAMMA
from train_service_policy import Network


class ServicePolicyContracts(unittest.TestCase):
    def test_hidden_world_changes_do_not_change_private_menu(self):
        env = Env(53); before = copy.deepcopy(env.menu(1))
        # No sensing call: a distant world inventory/private memory is not an actor input.
        env.stock[0] = 99; env.wheat[1] = 0; env.actors[0].needs.clear()
        self.assertEqual(before, env.menu(1))
        self.assertTrue(np.array_equal(encode(before), encode(env.menu(1))))

    def test_source_candidates_expire_without_remote_refresh(self):
        env = Env(53); actor = env.actors[1]
        actor.needs[0] = dict(units=2,tick=0,revision=1,sender=0)
        self.assertTrue(any(c['kind']=='SUPPLY_WHEAT' for c in env.menu(1)))
        env.t=3
        self.assertFalse(any(c['kind']=='SUPPLY_WHEAT' for c in env.menu(1)))
        self.assertTrue(any(c['kind']=='CARRY_REQUEST' for c in env.menu(1)))

    def test_menu_aggregation_is_local_permutation_equivariant(self):
        menu=[dict(features=features(k,3,32,200)) for k in KINDS]
        a=encode(menu); b=encode(list(reversed(menu)))
        np.testing.assert_allclose(a,b[::-1],rtol=0,atol=1e-15)
        self.assertEqual(a.shape,(4,30))
        with self.assertRaises(ValueError): encode([])
        with self.assertRaises(ValueError): encode([dict(features=(float('nan'),)*10)])

    def test_double_dqn_uses_online_choice_target_evaluation_and_duration(self):
        model=Network(11); target=Network(12)
        model.values=lambda x: np.asarray([8.,2.,8.,2.])
        target.values=lambda x: np.asarray([3.,100.,3.,100.])
        batch=[dict(next=np.zeros((2,30)),reward=1.,duration=5,terminal=False),
               dict(next=np.zeros((2,30)),reward=2.,duration=2,terminal=True)]
        np.testing.assert_allclose(model.targets(batch,target),[1+GAMMA**5*3,2])
        batch[0]['duration']=0
        with self.assertRaises(ValueError): model.targets(batch,target)

    def test_gradients_against_finite_differences(self):
        model=Network(13); rng=np.random.default_rng(19); x=rng.uniform(.1,.9,(5,30)); expected=np.asarray([-.2,.5,2.,-3.,.7])
        _,g=model.loss_gradients(x,expected)
        for k,v in model.p.items():
            for i in rng.choice(v.size,min(8,v.size),replace=False):
                old=v.flat[i]; v.flat[i]=old+1e-6; plus=model.loss_gradients(x,expected)[0]
                v.flat[i]=old-1e-6; minus=model.loss_gradients(x,expected)[0]; v.flat[i]=old
                self.assertAlmostEqual(g[k].flat[i],(plus-minus)/2e-6,places=6,msg=k)

    def test_checkpoint_hash_and_finite_values(self):
        model=Network(11)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.txt'; model.save(path)
            loaded=Network.load(path); self.assertEqual(model.digest(),loaded.digest())
            x=np.ones((3,30))*.5; np.testing.assert_array_equal(model.values(x),loaded.values(x))
            path.write_bytes(path.read_bytes().replace(b'w1 ',b'w2 ',1))
            with self.assertRaises(ValueError): Network.load(path)

    def test_wait_has_cost_no_productivity_and_terminal_does_not_bootstrap(self):
        transitions=[]; env=Env(71,horizon=5)
        result=episode(env,lambda menu,x: next(i for i,c in enumerate(menu) if c['kind']=='WAIT'), transitions.append)
        self.assertEqual(result['output'],0); self.assertEqual(result['sent'],0)
        self.assertEqual(sum(t['terminal'] for t in transitions),4)
        self.assertTrue(all(t['reward'] < 0 and t['colony']==0 for t in transitions))
        self.assertEqual(sum(t['duration'] for t in transitions),20)
        first=next(t for t in transitions if t['duration']==2)
        self.assertAlmostEqual(first['reward'],.75*(-.002)*(1+GAMMA))

    def test_material_conservation_and_frozen_inference_with_arbitration(self):
        from service_option_env import authored
        model=Network(29); before=model.digest()
        for seed in range(8):
            result=episode(Env(seed),lambda menu,x: authored(menu))
            self.assertTrue(result['material_conserved']); self.assertGreater(result['output'],0)
        self.assertEqual(before,model.digest())

if __name__=='__main__': unittest.main()
