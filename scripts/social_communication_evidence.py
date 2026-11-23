"""Join trusted live-fixture receipts; not an authenticator or causal estimator."""
import re
from uuid import UUID


def fields(text, prefix):
    if not text.startswith(prefix + " "):
        raise ValueError("Wrong receipt type")
    pairs = re.findall(r"(?:^|\s)([a-z_][a-z_0-9]*)=(\S+)", text)
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate receipt field")
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def communication_evidence(data):
    """Strictly scoped to the existing two-citizen, one-haul fixture.

    Used means selected by the policy AND bound to an assigned job, not merely
    delivered/read. Physical attribution is an association, not improvement.
    The trusted harness checks actual inventories; JSON cannot authenticate them.
    """
    assignment = fields(data['pre_action_decision_receipt'], 'REPORT_HAUL_DISPATCH')
    completion = fields(data['executor_completion_receipt'], 'REPORT_HAUL_EXECUTION')
    require(assignment['status'] == 'ASSIGNED', 'No assigned job')
    require(completion['status'] == 'EXECUTOR_COMPLETED', 'No executor completion')
    for key in ('job', 'world', 'executor'):
        UUID(assignment[key])
        require(assignment[key] == completion[key], 'Cross-job/world/executor completion')
    for key in ('source_report_id', 'source', 'destination', 'model_sha256',
                'decision_tick', 'assigned_tick', 'policy', 'decision_origin'):
        require(assignment[key] == completion[key], 'Completion provenance mismatch: ' + key)
    require(assignment['recipient'] == assignment['executor'], 'Wrong memory owner')
    require(assignment['exposure'] == 'EXPOSED', 'Withheld report used')
    require(assignment['policy'] == data['policy'] == 'SIMULATOR_TRAINED_FROZEN_MLP', 'Wrong policy')
    require(assignment['model_sha256'] == data['model_sha256'] and
            re.fullmatch('[0-9a-f]{64}', data['model_sha256']), 'Unpinned model')
    require(data['physical_transfer_verified'] is True, 'Missing physical witness')
    require(tuple(data[k] for k in ('source_a_before', 'source_a_after',
            'source_b_before', 'source_b_after', 'destination_before', 'destination_after'))
            == (3, 2, 1, 1, 0, 1), 'Invalid physical deltas')
    require(assignment['source'] == 'minecraft:overworld|3,101,1' and
            assignment['destination'] == 'minecraft:overworld|10,101,2', 'Wrong physical endpoints')
    withheld = fields(data['withheld_result'], 'REPORT_HAUL_DISPATCH')
    require(withheld['status'] == 'ABSTAIN' and withheld['exposure'] == 'WITHHELD'
            and withheld['task_assigned'] == 'false' and withheld['job'] == 'NONE', 'Invalid control')
    records, identities = [], set()
    for raw in data['communication_deliveries']:
        delivery = fields(raw, 'KNOWLEDGE_SHARE')
        for key in ('world', 'sender', 'recipient', 'observation_session'):
            UUID(delivery[key])
        require(delivery['status'] == 'DELIVERED', 'Not a delivered report')
        require(delivery['world'] == assignment['world'] and
                delivery['recipient'] == assignment['recipient'], 'Cross-world/recipient report')
        require(delivery['sender'] != delivery['recipient'], 'Self communication')
        require(delivery['channel'] == 'EXPLICIT_LOCAL_DIRECT_REPORT', 'Wrong channel')
        identity = (delivery['world'], delivery['recipient'], delivery['report_id'])
        require(identity not in identities, 'Duplicate delivery')
        identities.add(identity)
        observed, delivered = int(delivery['observed_tick']), int(delivery['delivered_tick'])
        require(0 <= observed <= delivered <= int(assignment['decision_tick']) <=
                int(assignment['assigned_tick']), 'Invalid chronology')
        require(delivery['state'] == 'AVAILABLE' and int(delivery['wheat']) > 0 and
                int(delivery['source_revision']) > 0, 'Invalid source report')
        selected = delivery['report_id'] == assignment['source_report_id']
        if selected:
            for left, right in [('sender', 'sender'), ('source', 'source'),
                                ('observed_tick', 'observed_tick'),
                                ('delivered_tick', 'report_delivered_tick')]:
                require(delivery[left] == assignment[right], 'Selected delivery mismatch')
        records.append({**delivery, 'selected_for_job': selected,
                        'job': assignment['job'] if selected else None,
                        'physical_units_associated': 1 if selected else None,
                        'other_use': 'NOT_MEASURED'})
    require(len(records) == 2 and sum(r['selected_for_job'] for r in records) == 1,
            'Expected two delivered reports and one selected report')
    return {'schema': 'hearthbound.social_communication.v1', 'records': records,
            'directed_edges': sorted({(r['sender'], r['recipient']) for r in records}),
            'delivered_reports': len(records), 'selected_reports': 1,
            'physical_units_associated': 1, 'physical_improvement': None,
            'organization_membership': None, 'learned_collaboration': False,
            'scope': 'OPERATOR_TRIGGERED_TWO_CITIZEN_SINGLE_HAUL',
            'limits': ['Harness assertions require original CI logs and commit binding',
                       'Delivery is not use; selection is not causation',
                       'One directed edge is not an organization or a topology comparison',
                       'Withheld abstention is not a matched physical control rollout']}
