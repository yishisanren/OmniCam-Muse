"""Relax only the three normal-photo 25MP nodes of the inspected PME110 tree."""
import copy
import re

NODES = {'ALGO_HR_REAR_UW_DAYTIME_2DOL_25M', 'ALGO_HR_REAR_W1X_DAYTIME_2DOL_25M',
         'ALGO_HR_REAR_T2P8X_DAYTIME_2DOL_25M'}
REMOVE = {'turboRawNightLimiter', 'currentIso', 'mLimitedQBC',
          'paramsHolder->under_water_status', 'paramsHolder->macro_closeup_enable',
          'paramsHolder->motion_capture_enable', 'paramsHolder->current_burst_capture_type',
          'oplusMeta->com.qti.stats_control.motion_detected', 'paramsHolder->livephoto_enable'}


def renumber(node):
    if not isinstance(node, dict):
        return node
    result, counts = {}, {}
    for key, value in node.items():
        base = re.sub(r'\d+$', '', key)
        count = counts.get(base, 0)
        counts[base] = count + 1
        result[base + (str(count) if count else '')] = renumber(value)
    return result


def strip(node, removed):
    """None denotes a removed, now true clause, including a disjunction containing it."""
    result = {}
    for key, value in node.items():
        if isinstance(value, dict):
            operation = re.sub(r'\d+$', '', key)
            if operation not in {'and', 'or'}:
                raise ValueError('Unknown conditional operator: ' + key)
            members = {}
            has_true = False
            for name, clause in value.items():
                if isinstance(clause, dict):
                    inner = strip({name: clause}, removed)
                    if inner is None:
                        has_true = True
                    else:
                        members.update(inner)
                elif isinstance(clause, list) and clause[0] in REMOVE:
                    removed.add(clause[0])
                    has_true = True
                else:
                    members[name] = clause
            if members and not (operation == 'or' and has_true):
                result[key] = members
        else:
            raise ValueError('Expected a condition group')
    return result or None


def patch(tree):
    result = copy.deepcopy(tree)
    changed, removed = set(), set()
    for node in result['multiAlgo']['algo']:
        if node['mode'] in NODES:
            condition = strip(node['condition'], removed)
            if condition is None:
                raise ValueError('25MP condition became unconditional')
            node['condition'] = renumber(condition)
            changed.add(node['mode'])
    if changed != NODES or removed != REMOVE:
        raise ValueError('The inspected MTK decision layout changed')
    return result
