"""Preserve every planned fresh-world trial, including missing/infra failures."""
import hashlib
import json
import math
import sys
from pathlib import Path

SEEDS = ['hearthbound-four-citizen-v0-3', 'hearthbound-four-citizen-v0-8-1',
         'hearthbound-four-citizen-v0-8-2']


def classify(log, benchmark):
    if benchmark is not None:
        if benchmark['aggregate']['physicalDeliveries'] != 4:
            raise ValueError('Invalid passing evidence')
        return 'PASS'
    marker = 'HEARTHBOUND_TERMINAL_ACCOUNTING_V1 '
    terminal = [json.loads(line[len(marker):]) for line in log.splitlines() if line.startswith(marker)]
    if len(terminal) > 1:
        raise ValueError('Multiple terminal trials in one log')
    if terminal:
        t = terminal[0]
        if t['deadline_exhausted'] is not True:
            raise ValueError('Nonterminal failure')
        if t['done'] == 3 and t['destination_has_four_wheat'] is True:
            return 'THREE_OF_FOUR_ACCOUNTING_FAILURE'
        return 'OTHER_TERMINAL_FAILURE'
    return 'UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE'


def summarize(root):
    trials = []
    for index, seed in enumerate(SEEDS):
        folder = root / f'real-four-citizen-colony-evidence-{index}'
        metadata_path = folder / 'trial-metadata.json'
        if not metadata_path.exists():
            trials.append({'trial': index, 'seed': seed, 'status': 'MISSING_ARTIFACT'})
            continue
        metadata = json.loads(metadata_path.read_text())
        if metadata['trial'] != index or metadata['seed'] != seed or metadata['fresh_world'] is not True:
            raise ValueError('Wrong trial manifest')
        log_path = folder / 'real-four-citizen-rcon.log'
        log = log_path.read_text() if log_path.exists() else ''
        path = folder / 'four-citizen-benchmark-evidence.json'
        benchmark = json.loads(path.read_text()) if path.exists() else None
        if benchmark:
            p = benchmark['provenance']
            if (p['fixtureSeed'] != seed or p['commit'] != metadata['commit'] or
                    p['workflowRunId'] != metadata['run_id'] or
                    p['logSha256'] != hashlib.sha256(log.encode()).hexdigest()):
                raise ValueError('Unbound benchmark evidence')
        trials.append({**metadata, 'status': classify(log, benchmark)})
    present = [t for t in trials if 'commit' in t]
    if len({(t['commit'], t['run_id'], t['attempt']) for t in present}) > 1:
        raise ValueError('Mixed revisions or workflow attempts')
    observed = sum(t['status'] in ('PASS', 'THREE_OF_FOUR_ACCOUNTING_FAILURE',
                                  'OTHER_TERMINAL_FAILURE') for t in trials)
    failures = sum(t['status'] == 'THREE_OF_FOUR_ACCOUNTING_FAILURE' for t in trials)
    # Wilson interval for observed terminal trials only; unresolved trials remain
    # in the planned denominator and in the separate identification bounds.
    interval = None
    if observed:
        z, p = 1.959963984540054, failures / observed
        center = (p + z*z/(2*observed)) / (1 + z*z/observed)
        half = z * math.sqrt(p*(1-p)/observed + z*z/(4*observed**2)) / (1+z*z/observed)
        interval = [max(0, center-half), min(1, center+half)]
    return {'schema': 'hearthbound.colony_reliability.v1', 'trials': trials,
            'planned_worlds': len(SEEDS), 'observed_terminal_worlds': observed,
            'unclassified_worlds': len(SEEDS)-observed,
            'three_of_four_failures': failures,
            'observed_failure_fraction': failures/observed if observed else None,
            'wilson_95_observed_only': interval,
            'planned_failure_fraction_bounds': [failures/len(SEEDS),
                (failures+len(SEEDS)-observed)/len(SEEDS)],
            'limits': 'Three prespecified seeds are a pilot, not population reliability. '
                      'Fresh runners/worlds, same constructed arena; no memory transfer. '
                      'Unknown trials are not successes. No claim the earlier bug is fixed.'}


if __name__ == '__main__':
    result = summarize(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
