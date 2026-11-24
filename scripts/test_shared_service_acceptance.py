"""Adversarial evidence checks. Constructed records are never gameplay results."""
import copy
import unittest
import numpy as np
from rcon_shared_service_acceptance import validate_physical, validate_choices
import test_production_services_acceptance as production_tests
from train_service_policy import Network
from service_option_env import Env, encode


class SharedServiceEvidenceTest(unittest.TestCase):
    def evidence(self):
        rows=production_tests.ProductionEvidenceTest().events()
        after=dict(sources=[dict(items={'minecraft:wheat':14}),dict(items={'minecraft:wheat':16})],
                   outputs=[dict(items={'create:wheat_flour':4,'minecraft:wheat_seeds':1}),dict(items={})],
                   mill_inputs=[dict(items={}),dict(items={})],mill_outputs=[dict(items={}),dict(items={})])
        return rows,after

    def test_verified_variable_yield_and_empty_second_site_retained(self):
        rows,after=self.evidence(); jobs=validate_physical(rows,after)
        self.assertEqual(len(jobs),2); self.assertEqual(sum(j['units'] for j in jobs),4)
        self.assertTrue(all(j['site']==0 for j in jobs))

    def test_native_loss_missing_delivery_wrong_owner_duplicate_rejected(self):
        for change in ('loss','delivery','owner','duplicate','byproduct','callback'):
            rows,after=self.evidence()
            if change=='loss': after['sources'][0]['items']['minecraft:wheat']=13
            if change=='delivery': rows=[r for r in rows if r['type']!='PRODUCTION_OUTPUT_DELIVERED']
            if change=='owner': next(r for r in rows if r['type']=='PRODUCTION_SETTLED')['citizen']='foreign'
            if change=='duplicate': rows.append(copy.deepcopy(next(r for r in rows if r['type']=='PRODUCTION_SETTLED')))
            if change=='byproduct': after['outputs'][0]['items'].pop('minecraft:wheat_seeds')
            if change=='callback': next(r for r in rows if r['type']=='PRODUCTION_OUTPUT_COLLECTED')['wheat_after']=1
            with self.subTest(change=change),self.assertRaises(AssertionError): validate_physical(rows,after)

    def decision(self):
        model=Network.load('src/main/resources/data/hearthbound/policies/service-trained-v0-22.txt')
        menu=Env(33).menu(0); x=encode(menu); values=model.values(x)
        scores=[dict(id=c['id'],kind=c['kind'],features=c['features'],actor_input=row.tolist(),total=float(value)) for c,row,value in zip(menu,x,values)]
        return dict(type='POLICY_DECISION',scores=scores,selected=menu[int(np.argmax(values))]['id'],frozen=True,shadow_rls=True,model_sha256=model.digest())

    def test_replay_actual_network_and_reject_input_hash_score_tampering(self):
        row=self.decision(); self.assertEqual(validate_choices([row],'neural'),1)
        for change in ('input','hash','score','choice'):
            row=self.decision()
            if change=='input': row['scores'][0]['actor_input'][11]=.9
            if change=='hash': row['model_sha256']='wrong'
            if change=='score': row['scores'][0]['total']+=.1
            if change=='choice': row['selected']='unlogged'
            with self.subTest(change=change),self.assertRaises(AssertionError): validate_choices([row],'neural')

if __name__=='__main__': unittest.main()
