"""Adversarial replay/accounting contracts; constructed data are not live evidence."""
import copy
import json
from pathlib import Path
import unittest
from village_economy_evidence import *


class EvidenceTests(unittest.TestCase):
    def test_shipped_setup_is_an_enabled_minecraft_data_pack(self):
        root=Path(__file__).resolve().parents[1]/'src/main/resources'
        metadata=json.loads((root/'pack.mcmeta').read_text())
        self.assertEqual(metadata['pack']['pack_format'],15)
        function=(root/'data/hearthbound/functions/village_setup.mcfunction').read_text()
        self.assertIn('hearthbound-village keep-ticking on',function)
        self.assertEqual(function.count('run sable spawn'),8)
        self.assertIn('fill 0 99 0 48 99 44 minecraft:stone_bricks',function)
        self.assertEqual(function.count('minecraft:sea_lantern'),2)

    def fixture(self):
        return dict(inventories=[dict(role='depot',path='Items',items={SEED:64}),
                                dict(role='water',path='Items',items={BUCKET:8}),
                                dict(role='furnace',path='Items',position=[36,101,5],items={'minecraft:coal':16}),
                                dict(role='furnace',path='Items',position=[36,101,27],items={'minecraft:coal':16})],
                    furnace_recipes=[self.furnace_response(5),self.furnace_response(27)])

    @staticmethod
    def furnace_response(z,count=None):
        compound={} if count is None else {FURNACE_RECIPE:count}
        return f'36, 101, {z} has the following block data: '+json.dumps(compound)+'\n'

    def food_chain(self):
        """Constructed accounting example: all event counters and material balances agree."""
        before=self.fixture(); after=copy.deepcopy(before); furnace=(36<<38)|(5<<12)|101
        after['inventories'][2]['items']['minecraft:coal']=15
        after['inventories'].append(dict(role='pantry',path='Items',items={BREAD:1}))
        after['furnace_recipes'][0]=self.furnace_response(5,1)
        rows=[
            dict(type='HARVEST_REPLANT_VERIFIED',before_age=7,after_age=0,native_drops={WHEAT:1,SEED:1},seed_consumed=1,crop=456),
            dict(type='MILL_PROCESS_VERIFIED',wheat_before=1,wheat_after=0,flour_before=0,flour_after=1,
                 native_job='native-mill',citizen='citizen',tick=2,items={FLOUR:1},
                 proof=dict(units=1,job='native-mill',citizen='citizen',startTick=1,processTick=2)),
            dict(type='WATER_BUCKET_FILLED',source_before=True,bucket_consumed=1,water_bucket_produced=1),
            dict(type='NATIVE_CRAFT_VERIFIED',inputs={FLOUR:1,WATER:1},result={DOUGH:1},remaining={BUCKET:1},recipe='create:crafting/appliances/dough'),
            dict(type='NATIVE_BAKE_VERIFIED',recipe=FURNACE_RECIPE,input_consumed=1,bread_produced=1,
                 native_recipe_count_before=0,native_recipe_count_after=1,furnace=furnace),
        ]
        totals=dict(wheat_harvested=1,crops_replanted=1,crop_seeds_generated=1,wheat_milled=1,
                    flour_produced=1,mill_seeds_generated=0,water_filled=1,flour_crafted=1,
                    dough_prepared=1,dough_baked=1,bread_baked=1)
        return rows,before,after,totals

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

    def test_independent_furnace_response_matches_self_consistent_food_chain(self):
        rows,before,after,totals=self.food_chain()
        result=validate_physical(rows,before,after,totals)
        self.assertEqual(result['verified_totals'],totals)
        self.assertEqual(result['furnace_recipe_counts'],{(36<<38)|(5<<12)|101:1})
        # Bind by the native response position, not its position in the response list.
        before['furnace_recipes'].reverse(); after['furnace_recipes'].reverse()
        self.assertEqual(validate_physical(rows,before,after,totals),result)

    def test_self_consistent_bake_ledger_cannot_replace_missing_or_mismatched_native_witness(self):
        for case,responses in {
            'absent':None,
            'partial':[self.furnace_response(5,1)],
            'no_native_increment':[self.furnace_response(5),self.furnace_response(27)],
            'extra_native_increment':[self.furnace_response(5,2),self.furnace_response(27)],
            'swapped_position':[self.furnace_response(5),self.furnace_response(27,1)],
            'unrecorded_second_furnace':[self.furnace_response(5,1),self.furnace_response(27,1)],
            'duplicate_position':[self.furnace_response(5,1),self.furnace_response(5,1)],
            'foreign_position':[self.furnace_response(6,1),self.furnace_response(27)],
            'extra_response':[self.furnace_response(5,1),self.furnace_response(27),self.furnace_response(27)],
            'command_error':['Found no elements matching RecipesUsed\n',self.furnace_response(27)],
            'trailing_response_text':[self.furnace_response(5,1)+'unexpected',self.furnace_response(27)],
        }.items():
            rows,before,after,totals=self.food_chain()
            after['furnace_recipes']=responses
            with self.subTest(case=case),self.assertRaisesRegex(AssertionError,'(?i)native furnace'):
                validate_physical(rows,before,after,totals)
        rows,before,after,totals=self.food_chain(); after.pop('furnace_recipes')
        with self.assertRaisesRegex(AssertionError,'Missing'):
            validate_physical(rows,before,after,totals)

    def test_malformed_native_recipe_compounds_never_default_to_zero_or_a_success_count(self):
        for compound in (
            '"create:smelting/bread":', '"create:smelting/bread": 1b',
            '"create:smelting/bread": "1"', '"create:smelting/bread": true',
            '"create:smelting/bread": -1', '"create:smelting/bread": 1.0',
            '"create:smelting/bread": NaN', '"create:smelting/bread": 2147483648',
            '"create:smelting/bread": 1, "create:smelting/bread": 1',
            '"create:smelting/bread": 1, "minecraft:iron_ingot": 1',
        ):
            rows,before,after,totals=self.food_chain()
            after['furnace_recipes'][0]='36, 101, 5 has the following block data: {'+compound+'}\n'
            with self.subTest(compound=compound),self.assertRaisesRegex(AssertionError,'(?i)native furnace'):
                validate_physical(rows,before,after,totals)

    def test_fresh_fixture_requires_complete_zero_initial_native_counters(self):
        for case,responses in {
            'missing':None,
            'initial_history':[self.furnace_response(5,1),self.furnace_response(27)],
            'malformed':['36, 101, 5 has the following block data: {',self.furnace_response(27)],
        }.items():
            rows,before,after,totals=self.food_chain()
            before['furnace_recipes']=responses
            with self.subTest(case=case),self.assertRaisesRegex(AssertionError,'(?i)native furnace'):
                validate_physical(rows,before,after,totals)

    def test_bake_receipt_cannot_reference_an_uncaptured_furnace(self):
        for packed in (123, True, ((36<<38)|(5<<12)|101)+(1<<64)):
            rows,before,after,totals=self.food_chain(); rows[-1]['furnace']=packed
            with self.subTest(packed=packed),self.assertRaisesRegex(AssertionError,'foreign furnace'):
                validate_physical(rows,before,after,totals)

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

    def test_control_and_adaptive_priors_match_even_for_long_routes(self):
        m=PrivateModel()
        for kind in KINDS:
            for distance in (0,16,64,128,4096):
                o=dict(id='a',kind=kind,distance=distance,deficit=1,hunger=.5,age=0)
                self.assertAlmostEqual(m.score(o,True)['total'],m.score(o,False)['total'])


if __name__=='__main__': unittest.main()
