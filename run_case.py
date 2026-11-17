"""Execute the supplied synthetic cases and report finite conformance results."""
from pathlib import Path
import argparse
import copy
import csv
import datetime
import hashlib
import json
import platform
import random
import sys
from verifier import evaluate


def run(root, output):
    output.mkdir(parents=True, exist_ok=True)
    profile = json.loads((root / 'profile.json').read_text())
    expected = list(csv.DictReader((root / 'expected.csv').open()))
    rows = []
    checks_rows = []
    details = []
    invariance = 0
    for ex in expected:
        case = json.loads((root / 'cases' / (ex['case_id'] + '.json')).read_text())
        result = evaluate(case, profile)
        match = (result['verdict'] == ex['expected_verdict']
                 and (not ex['required_failed_check'] or ex['required_failed_check'] in result['failed_checks']))
        rows.append([case['case_id'], case['label'], ex['expected_verdict'], result['verdict'],
                     result['acknowledgement_only_verdict'], ';'.join(result['failed_checks']),
                     result['integrated_volume_l'], match])
        checks_rows.extend([[case['case_id'], k, v] for k, v in result['checks'].items()])
        details.append(result)
        # Preserve records and source times while varying input arrival order.
        for seed in range(20):
            permutation = copy.deepcopy(case)
            random.Random(1000 + seed).shuffle(permutation['records'])
            other = evaluate(permutation, profile)
            assert other == result, (case['case_id'], seed, 'arrival-order dependence')
            invariance += 1
    with (output / 'results.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['case_id', 'scenario', 'expected_verdict', 'actual_verdict',
                    'acknowledgement_only_verdict', 'failed_checks', 'integrated_volume_l', 'expectation_matched'])
        w.writerows(rows)
    with (output / 'check_results.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['case_id', 'check_id', 'satisfied']); w.writerows(checks_rows)
    (output / 'verdicts.json').write_text(json.dumps(details, indent=2) + '\n')
    tracked = [root / 'profile.json', root / 'expected.csv', root / 'check_definitions.csv',
               root / 'verifier.py', root / 'run_case.py', *sorted((root / 'cases').glob('*.json'))]
    record = {
        'executed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'python': sys.version, 'platform': platform.platform(),
        'command': 'python3 run_case.py --output outputs',
        'case_count': len(rows), 'expected_matches': sum(r[-1] for r in rows),
        'verified_cases': sum(r[3] == 'verified' for r in rows),
        'not_verified_cases': sum(r[3] == 'not_verified' for r in rows),
        'acknowledgement_only_accepts_in_not_verified_cases': sum(r[3] == 'not_verified' and r[4] == 'verified' for r in rows),
        'arrival_order_invariance_checks': invariance,
        'synthetic': True, 'physical_validation': False,
        'files': [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in tracked]
    }
    (output / 'execution_record.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({k: v for k, v in record.items() if k != 'files'}, indent=2))
    assert all(r[-1] for r in rows), 'At least one fixture did not match its separate expectation.'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='outputs', type=Path)
    args = parser.parse_args()
    run(Path(__file__).resolve().parent, args.output.resolve())
