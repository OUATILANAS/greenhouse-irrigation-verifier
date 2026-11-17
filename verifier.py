"""Offline conformance checker for a declared synthetic irrigation profile.

This module reads profile/record data only. It does not read expected.csv,
operate equipment, connect to a broker, or validate greenhouse performance.
"""
import json
import math
from collections import defaultdict


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def qualified(record, kind, profile):
    return (record.get('quality') == 'valid'
            and record.get('calibration_valid') is True
            and record.get('unit') == profile['units'][kind]
            and record.get('sensor_id') == profile['sensors'][kind]
            and finite(record.get('value')))


def acknowledgement_only(case, profile):
    """Defined reference rule, not a representation of any assessed platform."""
    return any(r.get('type') == 'ack' and r.get('status') == 'accepted'
               and r.get('event_id') == profile['event_id']
               and r.get('command_id') == profile['command_id']
               for r in case.get('records', []))


def evaluate(case, profile):
    records = case.get('records', [])
    groups = defaultdict(list)
    for record in records:
        groups[record.get('type')].append(record)
    commands = groups['command']
    command = min(commands, key=lambda r: r.get('source_time_s', math.inf)) if commands else {}
    command_time = command.get('source_time_s')
    checks = {}

    checks['E1'] = finite(command_time) and any(
        qualified(r, 'context', profile) and finite(r.get('source_time_s'))
        and 0 <= command_time - r['source_time_s'] <= profile['max_context_age_s']
        for r in groups['context'])

    allowed = {'context', 'command', 'ack', 'flow', 'pressure', 'twin'}
    checks['E2'] = (bool(records) and case.get('synthetic') is True
                    and case.get('profile_id') == profile['profile_id'] and all(
        r.get('type') in allowed and r.get('event_id') == profile['event_id']
        and r.get('command_id') == profile['command_id']
        and r.get('zone') == profile['zone'] and finite(r.get('source_time_s'))
        for r in records))

    # Arrival metadata may differ on retransmission; the issued payload may not.
    payloads = {json.dumps({k: v for k, v in r.items()
                           if k not in {'record_id', 'received_time_s'}}, sort_keys=True)
                for r in commands}
    checks['E3'] = (len(payloads) == 1 and command.get('action') == 'irrigate'
                    and finite(command.get('target_volume_l'))
                    and command['target_volume_l'] == profile['target_volume_l'])

    checks['E4'] = finite(command_time) and any(
        r.get('status') == 'accepted' and r.get('event_id') == profile['event_id']
        and r.get('command_id') == profile['command_id']
        and finite(r.get('source_time_s'))
        and 0 <= r['source_time_s'] - command_time <= profile['max_ack_delay_s']
        for r in groups['ack'])

    flow = groups['flow']
    trace_valid = (finite(command_time) and len(flow) >= 2 and all(
        qualified(r, 'flow', profile) and finite(r.get('source_time_s'))
        and r['value'] >= 0
        and command_time <= r['source_time_s'] <= command_time + profile['delivery_deadline_s']
        for r in flow))
    ordered = sorted(flow, key=lambda r: r['source_time_s']) if trace_valid else []
    trace_valid = trace_valid and len({r['source_time_s'] for r in ordered}) == len(ordered)
    positive = [r for r in ordered if r['value'] > 0] if trace_valid else []
    checks['E5'] = bool(trace_valid and positive
                         and positive[0]['source_time_s'] - command_time <= profile['max_flow_start_delay_s'])

    pressure = groups['pressure']
    checks['E6'] = finite(command_time) and bool(pressure) and all(
        qualified(r, 'pressure', profile) and finite(r.get('source_time_s'))
        and command_time <= r['source_time_s'] <= command_time + profile['delivery_deadline_s']
        and profile['min_pressure_bar'] <= r['value'] <= profile['max_pressure_bar']
        for r in pressure)

    volume = None
    if trace_valid:
        volume = sum((a['value'] + b['value']) * .5
                     * (b['source_time_s'] - a['source_time_s']) / 60.0
                     for a, b in zip(ordered, ordered[1:]))
    checks['E7'] = (volume is not None
                    and abs(volume - profile['target_volume_l']) <= profile['volume_tolerance_l'] + 1e-9)

    responses = flow + pressure
    response_times_valid = bool(responses) and all(finite(r.get('source_time_s')) for r in responses)
    last_response = max(r['source_time_s'] for r in responses) if response_times_valid else None
    checks['E8'] = last_response is not None and any(
        r.get('state') == 'delivery_confirmed' and finite(r.get('source_time_s'))
        and r['source_time_s'] >= last_response
        and r.get('event_id') == profile['event_id']
        and r.get('command_id') == profile['command_id']
        and isinstance(r.get('model_version'), str) and bool(r['model_version'].strip())
        and r.get('profile_id') == profile['profile_id']
        for r in groups['twin'])

    return {'case_id': case.get('case_id'), 'verdict': 'verified' if all(checks.values()) else 'not_verified',
            'checks': checks, 'failed_checks': [k for k, v in checks.items() if not v],
            'integrated_volume_l': volume,
            'acknowledgement_only_verdict': 'verified' if acknowledgement_only(case, profile) else 'not_verified'}
