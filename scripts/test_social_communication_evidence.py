import copy
import unittest
from social_communication_evidence import communication_evidence

W = '00000000-0000-4000-8000-000000000001'
S = '00000000-0000-4000-8000-000000000002'
R = '00000000-0000-4000-8000-000000000003'
J = '00000000-0000-4000-8000-000000000004'
A, B, D = 'minecraft:overworld|3,101,1', 'minecraft:overworld|7,101,1', 'minecraft:overworld|10,101,2'
M = 'a' * 64

def fixture():
    common = f'job={J} world={W} executor={R} source_report_id=report-A source={A} destination={D} model_sha256={M} decision_tick=12 assigned_tick=13 policy=SIMULATOR_TRAINED_FROZEN_MLP decision_origin=OPERATOR_TRIGGERED_FROZEN_POLICY'
    return dict(pre_action_decision_receipt='REPORT_HAUL_DISPATCH status=ASSIGNED '+common+f' recipient={R} sender={S} observed_tick=10 report_delivered_tick=11 exposure=EXPOSED',
        executor_completion_receipt='REPORT_HAUL_EXECUTION status=EXECUTOR_COMPLETED '+common,
        communication_deliveries=[f'KNOWLEDGE_SHARE status=DELIVERED report_id=report-{label} world={W} sender={S} recipient={R} observation_session={J} source={source} observed_tick=10 delivered_tick=11 channel=EXPLICIT_LOCAL_DIRECT_REPORT state=AVAILABLE wheat={wheat} source_revision=1' for label,source,wheat in [('A',A,3),('B',B,1)]],
        withheld_result='REPORT_HAUL_DISPATCH status=ABSTAIN exposure=WITHHELD task_assigned=false job=NONE',
        physical_transfer_verified=True, source_a_before=3, source_a_after=2,
        source_b_before=1, source_b_after=1, destination_before=0, destination_after=1,
        policy='SIMULATOR_TRAINED_FROZEN_MLP', model_sha256=M)

class SocialEvidenceTest(unittest.TestCase):
    def test_association_does_not_award_causality_or_organizations(self):
        result=communication_evidence(fixture())
        self.assertEqual(result['delivered_reports'],2)
        self.assertEqual(result['selected_reports'],1)
        self.assertEqual(len(result['directed_edges']),1)
        self.assertIsNone(result['physical_improvement'])
        self.assertIsNone(result['organization_membership'])
        self.assertIsNone(result['records'][1]['physical_units_associated'])
    def test_conflicting_provenance_rejected(self):
        for field,old,new in [
            ('executor_completion_receipt',f'job={J}',f'job={W}'),
            ('executor_completion_receipt',f'world={W}',f'world={S}'),
            ('executor_completion_receipt','source_report_id=report-A','source_report_id=report-B'),
            ('pre_action_decision_receipt',f'recipient={R}',f'recipient={S}'),
            ('pre_action_decision_receipt','decision_tick=12','decision_tick=9'),
            ('pre_action_decision_receipt','report_delivered_tick=11','report_delivered_tick=10'),
            ('withheld_result','task_assigned=false','task_assigned=true')]:
            with self.subTest(field=field,new=new):
                data=fixture(); data[field]=data[field].replace(old,new)
                with self.assertRaises(ValueError): communication_evidence(data)
    def test_delivery_is_not_enough(self):
        for mutation in ('duplicate','missing','self','cross_world','wrong_source','stale','no_physical','wrong_deltas'):
            with self.subTest(mutation=mutation):
                data=fixture()
                if mutation=='duplicate': data['communication_deliveries'][1]=data['communication_deliveries'][0]
                if mutation=='missing': data['communication_deliveries']=[]
                if mutation=='self': data['communication_deliveries'][0]=data['communication_deliveries'][0].replace(f'sender={S}',f'sender={R}')
                if mutation=='cross_world': data['communication_deliveries'][0]=data['communication_deliveries'][0].replace(f'world={W}',f'world={S}')
                if mutation=='wrong_source': data['communication_deliveries'][0]=data['communication_deliveries'][0].replace(A,B)
                if mutation=='stale': data['communication_deliveries'][1]=data['communication_deliveries'][1].replace('observed_tick=10 delivered_tick=11','observed_tick=0 delivered_tick=100')
                if mutation=='no_physical': data['physical_transfer_verified']=False
                if mutation=='wrong_deltas': data['destination_after']=2
                with self.assertRaises(ValueError): communication_evidence(data)

if __name__=='__main__': unittest.main()
