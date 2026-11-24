"""Adversarial replay/accounting contracts; constructed data are not live evidence."""
import copy
import unittest
from village_economy_evidence import *


class EvidenceTests(unittest.TestCase):
    def fixture(self):
        return dict(inventories=[dict(role='depot',path='Items',items={SEED:64}),
                                dict(role='water',path='Items',items={BUCKET:8}),
                                dict(role='furnace',path='Items',items={'minecraft:coal':32})])

    def test_zero_work_is_conserved_but_does_not_imply_milestone(self):
        a=self.fixture(); result=validate_physical([],a,a,{})
        self.assertEqual(result['verified_totals'],{})
        self.assertEqual(result['regrown_reharvested_plots'],0)

    def test_missing_bucket_or_invented_food_rejected(self):
        for item,delta in ((BUCKET,-1),(WHEAT,1),(FLOUR,1),(DOUGH,1),(BREAD,1),(SEED,1)):
            before=self.fixture(); after=copy.deepcopy(before)
            after['inventories'][1]['items'][item]=after['inventories'][1]['items'].get(item,0)+delta
            with self.subTest(item=item),self.assertRaises(AssertionError): validate_physical([],before,after,{})

    def test_delivery_claim_cannot_substitute_for_delta(self):
        row=dict(type='ITEMS_DELIVERED',before={FLOUR:1},items={FLOUR:1},after={FLOUR:1})
        with self.assertRaises(AssertionError): validate_physical([row],self.fixture(),self.fixture(),{})

    def test_furnace_timer_without_native_recipe_increment_rejected(self):
        row=dict(type='NATIVE_BAKE_VERIFIED',recipe='create:smelting/bread',input_consumed=1,bread_produced=1,
                 native_recipe_count_before=0,native_recipe_count_after=0,furnace=123)
        with self.assertRaises(AssertionError): validate_physical([row],self.fixture(),self.fixture(),{})

    def test_missing_returned_bucket_recipe_rejected(self):
        row=dict(type='NATIVE_CRAFT_VERIFIED',inputs={FLOUR:1,WATER:1},result={DOUGH:1},remaining={},recipe='create:crafting/appliances/dough')
        with self.assertRaises(AssertionError): validate_physical([row],self.fixture(),self.fixture(),{})

    def test_replay_rejects_remote_observation(self):
        row=dict(sequence=1,world='w',citizen='a',tick=10,type='LOCAL_OBSERVATION',x=100.,y=0.,z=0.,
                 fact=dict(id='f',observer='a',tick=10,position=0,items={},mature=False,water=False))
        with self.assertRaisesRegex(AssertionError,'Remote'): validate_history([row],True)

    def test_private_cost_update_changes_ranking_and_control_is_fixed(self):
        m=PrivateModel(); offer=dict(id='bake',kind='BAKE_BREAD',distance=16,deficit=1,hunger=.5,age=0)
        old=m.score(offer,True); fixed=m.score(offer,False); x=m.features(offer); xx=sum(v*v for v in x)
        m.learn(dict(job='j',kind='BAKE_BREAD',features=x,start=0,finish=1200,cost=3,completed=True))
        self.assertAlmostEqual(m.score(offer,True)['predictedTicks'],old['predictedTicks']+xx/(1+xx)*(1200-old['predictedTicks']))
        self.assertEqual(m.score(offer,False)['total'],fixed['total'])
        self.assertLess(m.score(offer,True)['total'],old['total'])
        self.assertEqual(PrivateModel().count,[0]*8)
        with self.assertRaises(AssertionError): m.learn(dict(job='j'))


if __name__=='__main__': unittest.main()
