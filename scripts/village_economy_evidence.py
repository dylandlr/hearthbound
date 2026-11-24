"""Independent replay and native material accounting for the village acceptance.

The fixed utilities, local fact protocol and skill library are authored. Only
private execution duration, movement/communication cost and success are learned.
"""
from collections import Counter, defaultdict
import math

KINDS = ('HARVEST_REPLANT', 'MILL_FLOUR', 'PREPARE_DOUGH', 'BAKE_BREAD',
         'REFILL_WATER', 'EAT_BREAD', 'OBSERVE', 'WAIT')
PRIORS = (100, 220, 100, 220, 60, 20, 20, 40)
VALUES = (1.2, 1.8, 2.2, 3.2, 1.4, 5., .6, 0.)
WHEAT, SEED, FLOUR, DOUGH, BREAD, WATER, BUCKET = (
    'minecraft:wheat', 'minecraft:wheat_seeds', 'create:wheat_flour', 'create:dough',
    'minecraft:bread', 'minecraft:water_bucket', 'minecraft:bucket')
ITEMS = {WHEAT, SEED, FLOUR, DOUGH, BREAD, WATER, BUCKET, 'minecraft:coal'}
PRODUCTIVE = set(KINDS[:6])


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close(a, b):
    require(math.isclose(a, b, abs_tol=1e-9, rel_tol=1e-10), f'Numeric replay differs: {a} / {b}')


def xyz(packed):
    x, y, z = packed >> 38, packed & 4095, (packed >> 12) & 0x3ffffff
    if x >= 2**25: x -= 2**26
    if z >= 2**25: z -= 2**26
    if y >= 2**11: y -= 2**12
    return x, y, z


class PrivateModel:
    def __init__(self):
        self.weights = [[[p / 1200, 384 / 1200, 0., 0.], [0., .64, 0., 0.]] for p in PRIORS]
        self.covariance = [[[[float(i == j) for j in range(4)] for i in range(4)] for _ in range(2)] for _ in KINDS]
        self.count = [0] * 8
        self.success = [0] * 8
        self.seen = set()

    @staticmethod
    def features(offer):
        return [1., min(1., offer['distance'] / 64), offer['deficit'], offer['hunger']]

    def score(self, o, adaptive):
        k = KINDS.index(o['kind']); x = self.features(o)
        value = VALUES[k] * (.5 + .5 * o['deficit'])
        if o['kind'] == 'EAT_BREAD': value *= .5 + o['hunger']
        if o['kind'] == 'OBSERVE': value = .65 + .3 * o['age']
        ticks = max(0, sum(a*b for a, b in zip(self.weights[k][0], x)) * 1200) if adaptive else PRIORS[k] + 384*x[1]
        cost = max(0, sum(a*b for a, b in zip(self.weights[k][1], x))) if adaptive else .64*x[1]
        success = (self.success[k]+3) / (self.count[k]+3) if adaptive else 1.
        total = 0. if o['kind'] == 'WAIT' else success*value - .001*ticks - .25*cost
        if o['kind'] == 'OBSERVE': total = max(.03, total)
        return dict(id=o['id'], authoredValue=value, predictedTicks=ticks, predictedCost=cost,
                    success=success, total=total, privateSamples=self.count[k])

    def learn(self, o):
        require(o['job'] not in self.seen, 'Duplicate private outcome')
        self.seen.add(o['job']); k = KINDS.index(o['kind']); x = o['features']
        for head, target in enumerate(((o['finish']-o['start']) / 1200, o['cost'])):
            weights, covariance = self.weights[k][head], self.covariance[k][head]
            px = [sum(row[j] * x[j] for j in range(4)) for row in covariance]
            denominator = 1 + sum(x[j] * px[j] for j in range(4))
            error = target - sum(a*b for a, b in zip(weights, x))
            for i in range(4):
                weights[i] += px[i] * error / denominator
                for j in range(4): covariance[i][j] -= px[i] * px[j] / denominator
        self.count[k] += 1; self.success[k] += int(o['completed'])


def validate_history(rows, adaptive):
    require([r['sequence'] for r in rows] == list(range(1, len(rows)+1)), 'Evidence sequence gap')
    require(len({r['world'] for r in rows}) == 1, 'Mixed worlds')
    facts, books, packets, pending, jobs, witnesses = {}, defaultdict(dict), {}, {}, {}, {}
    models = defaultdict(PrivateModel); productive = defaultdict(Counter)
    decisions = peer_uses = changed_rankings = 0
    sends_per_tick = Counter(); settled = set(); packet_cost = Counter()
    for row in rows:
        kind = row['type']; actor = row.get('citizen'); now = row['tick']
        if kind == 'LOCAL_OBSERVATION':
            fact = row['fact']; require(fact['id'] not in facts and fact['observer'] == actor and fact['tick'] == now, 'Invalid firsthand fact')
            pos = xyz(fact['position'])
            require(math.dist([row['x'], row['y'], row['z']], [p+.5 for p in pos]) <= 16+1e-9, 'Remote stock observation')
            facts[fact['id']] = fact; books[actor][fact['position']] = (fact['id'], 0)
        elif kind == 'FACTS_SENT':
            require(row['packet'] not in packets and len(row['facts']) <= 8 and 0 <= row['distance'] <= 12, 'Invalid local packet')
            sends_per_tick[(actor, now)] += 1; require(sends_per_tick[(actor, now)] <= 2, 'Peer budget exceeded')
            for known in row['facts']:
                fact = known['fact']; require(facts.get(fact['id']) == fact, 'Invented/revised peer fact')
                require(books[actor].get(fact['position']) == (fact['id'], known['hops']) and known['hops'] < 2 and 0 <= now-fact['tick'] <= 600, 'Sender bypassed private memory')
            packets[row['packet']] = row
            if row.get('job') and row['job'] in jobs and row['job'] not in settled: packet_cost[row['job']] += 1
        elif kind == 'FACTS_RECEIVED':
            send = packets.get(row['packet']); require(send and send['recipient'] == actor and send['citizen'] == row['sender'] and send['tick'] == now, 'Unsent/remote receipt')
            require(math.dist([send[k] for k in ('x','y','z')], [row[k] for k in ('x','y','z')]) <= 12+1e-9, 'Delivery outside contact radius')
            accepted, rejected = [], []
            for known in send['facts']:
                fact = known['fact']; prior = books[actor].get(fact['position'])
                if prior is None or facts[prior[0]]['tick'] < fact['tick']:
                    books[actor][fact['position']] = (fact['id'], known['hops']+1); accepted.append(fact['id'])
                else: rejected.append(fact['id'])
            require(accepted == row['accepted'] and rejected == row['rejected'], 'Fact consumption differs')
        elif kind == 'WORK_DECISION':
            menu = row['offers']; require(menu and [o['id'] for o in menu] == sorted({o['id'] for o in menu}), 'Noncanonical private menu')
            computed = []
            for offer, actual in zip(menu, row['scores'], strict=True):
                require(offer['citizen'] == actor, 'Foreign actor features')
                for fid in filter(None, offer['evidence'].split(',')):
                    fact = facts.get(fid); require(fact and books[actor].get(fact['position'], ('',))[0] == fid and 0 <= now-fact['tick'] <= 600, 'Actor used unavailable or stale evidence')
                predicted = models[actor].score(offer, adaptive)
                for key in ('authoredValue','predictedTicks','predictedCost','success','total','privateSamples'): close(actual[key], predicted[key])
                computed.append(predicted)
            selected = min(computed, key=lambda s:(-s['total'],s['id']))['id']
            require(row['selected'] == selected, 'Runtime bypassed private selector')
            authored = min(menu, key=lambda o:(-models[actor].score(o, False)['total'], o['id']))['id']
            if adaptive and selected != authored: changed_rankings += 1
            choice = next(o for o in menu if o['id'] == selected); pending[actor] = (choice, now)
            peer_uses += int(any(books[actor][facts[fid]['position']][1] > 0 for fid in filter(None,choice['evidence'].split(','))))
            decisions += 1
        elif kind == 'WORK_STARTED':
            require(row['job'] not in jobs and pending.get(actor) == (row['offer'], now), 'Work lacks selected private proposal')
            jobs[row['job']] = row; pending.pop(actor)
        elif kind in ('HARVEST_REPLANT_VERIFIED','MILL_PROCESS_VERIFIED','NATIVE_CRAFT_VERIFIED','NATIVE_BAKE_VERIFIED','WATER_BUCKET_FILLED','BREAD_EATEN'):
            receipt = row.get('receipt', row.get('proof',{}).get('physicalEvidence'))
            require(receipt and receipt not in witnesses and row['job'] in jobs, 'Duplicate/unowned physical witness')
            witnesses[receipt] = row
        elif kind == 'WORK_SETTLED':
            outcome = row['outcome']; start = jobs.get(row['job'])
            require(start and row['job'] not in settled and start['citizen'] == actor == outcome['citizen'], 'Duplicate/foreign settlement')
            require(outcome['job'] == row['job'] and outcome['start'] == start['tick'] and outcome['finish'] == now and outcome['kind'] == start['offer']['kind'], 'Changed work identity/chronology')
            require(outcome['features'] == PrivateModel.features(start['offer']), 'Learning used hindsight features')
            close(outcome['cost'], .01*row['travel']+.02*row['packets']); require(row['packets'] == packet_cost[row['job']], 'Communication cost differs')
            if outcome['completed'] and outcome['kind'] in PRODUCTIVE:
                witness = witnesses.get(outcome['physicalReceipt']); require(witness and witness['job'] == row['job'] and witness['citizen'] == actor, 'Reward lacks own physical conversion')
                productive[actor][outcome['kind']] += 1
            models[actor].learn(outcome); require(sum(models[actor].count) == row['private_samples'], 'Private sample count differs')
            settled.add(row['job'])
    require(decisions > 0 and set(jobs) == settled, 'Missing decisions or unfinished owned jobs')
    return dict(replayed_decisions=decisions, peer_evidence_selected=peer_uses,
                adaptive_choices_different_from_authored=changed_rankings,
                productive_citizens=len(productive), multi_capability_citizens=sum(len(v)>1 for v in productive.values()),
                productive_jobs={k:dict(v) for k,v in productive.items()}, packets=len(packets))


def validate_physical(rows, before, after, totals):
    inventory = Counter()
    for snapshot in after['inventories']: inventory.update(snapshot['items'])
    initial = Counter()
    for snapshot in before['inventories']: initial.update(snapshot['items'])
    require(initial == Counter({SEED:64, BUCKET:8, 'minecraft:coal':32}), 'Unplanned initial food/material stock')
    expected = Counter(); by_job = defaultdict(list); harvested = Counter(); bake_recipes = Counter()
    for r in rows:
        if r.get('job'): by_job[r['job']].append(r)
        t = r['type']
        if t == 'ITEM_PICKED_UP':
            b = Counter(r['before']); b[r['item']] -= 1; require(+b == Counter(r['after']) and r['units'] == 1, 'Pickup failed conservation')
        elif t == 'ITEMS_DELIVERED':
            b = Counter(r['before']); b.update(r['items']); require(b == Counter(r['after']), 'Delivery failed conservation')
        elif t == 'HARVEST_REPLANT_VERIFIED':
            require(r['before_age'] == 7 and r['after_age'] == 0 and r['native_drops'].get(WHEAT) == 1 and r['seed_consumed'] == 1, 'Unverified harvest/replant')
            require(set(r['native_drops']) <= {WHEAT,SEED}, 'Unexpected crop loot')
            expected.update(wheat_harvested=1,crops_replanted=1,crop_seeds_generated=r['native_drops'].get(SEED,0)); harvested[r['crop']] += 1
        elif t == 'MILL_PROCESS_VERIFIED':
            require(r['wheat_before'] == 1 and r['wheat_after'] == 0 and r['flour_before'] == 0 and r['flour_after'] == r['proof']['units'] == r['items'][FLOUR], 'Native Create conversion differs')
            require(r['native_job'] == r['proof']['job'] and r['proof']['citizen'] == r['citizen'], 'Create callback ownership differs')
            require(r['proof']['startTick'] < r['proof']['processTick'] <= r['tick'], 'Create chronology differs')
            expected.update(wheat_milled=1,flour_produced=r['items'][FLOUR],mill_seeds_generated=r['items'].get(SEED,0))
        elif t == 'MILL_OUTPUT_DELIVERED':
            d=r['delivery']; b=Counter(d['beforeItems']); b.update(d['items']); require(b == Counter(d['afterItems']), 'Create output storage does not conserve')
        elif t == 'NATIVE_CRAFT_VERIFIED':
            require(r['inputs'] == {FLOUR:1,WATER:1} and r['result'] == {DOUGH:1} and r['remaining'] == {BUCKET:1} and r['recipe'] == 'create:crafting/appliances/dough', 'Installed crafting contract differs')
            expected.update(flour_crafted=1,dough_prepared=1)
        elif t == 'NATIVE_BAKE_VERIFIED':
            require(r['recipe'] == 'create:smelting/bread' and r['input_consumed'] == r['bread_produced'] == 1 and r['native_recipe_count_after'] == r['native_recipe_count_before']+1, 'Native furnace recipe count differs')
            require(r['native_recipe_count_before'] == bake_recipes[r['furnace']], 'Native furnace receipt reused')
            bake_recipes[r['furnace']] += 1; expected.update(dough_baked=1,bread_baked=1)
        elif t == 'WATER_BUCKET_FILLED':
            require(r['source_before'] and r['bucket_consumed'] == r['water_bucket_produced'] == 1, 'Water pickup differs')
            expected.update(water_filled=1)
        elif t == 'BREAD_EATEN':
            require(r['bread_consumed'] == 1 and r['satiety_after'] == min(100,r['satiety_before']+40) and r['need_model'] == 'AUTHORED_COLONY_SATIETY_V1', 'Meal/need conversion differs')
            expected.update(meals=1)
    for job, chain in by_job.items():
        settlements=[r for r in chain if r['type']=='WORK_SETTLED']
        if not settlements: continue
        final=settlements[0]; o=final['outcome']
        if not o['completed'] or o['kind'] not in PRODUCTIVE: continue
        kinds={r['type'] for r in chain}
        needed={'MILL_FLOUR':{'NATIVE_MILL_ASSIGNED','MILL_INPUT_DELIVERED','MILL_PROCESS_VERIFIED','MILL_OUTPUT_DELIVERED'},
                'HARVEST_REPLANT':{'ITEM_PICKED_UP','HARVEST_REPLANT_VERIFIED','ITEMS_DELIVERED'},
                'PREPARE_DOUGH':{'ITEM_PICKED_UP','NATIVE_CRAFT_VERIFIED','ITEMS_DELIVERED'},
                'BAKE_BREAD':{'ITEM_PICKED_UP','FURNACE_INPUT_INSERTED','FURNACE_PROGRESS','NATIVE_BAKE_VERIFIED','ITEMS_DELIVERED'},
                'REFILL_WATER':{'ITEM_PICKED_UP','WATER_BUCKET_FILLED','ITEMS_DELIVERED'},
                'EAT_BREAD':{'ITEM_PICKED_UP','BREAD_EATEN'}}[o['kind']]
        require(needed <= kinds, 'Incomplete physical service: '+job)
        if o['kind']=='BAKE_BREAD': expected.update(bread_delivered=1)
    for key, count in expected.items(): require(totals.get(key,0)==count, 'Runtime total differs: '+key)
    require(inventory[WHEAT]+expected['wheat_milled']==expected['wheat_harvested'], 'Wheat balance failed')
    require(inventory[FLOUR]+expected['flour_crafted']==expected['flour_produced'], 'Flour balance failed')
    require(inventory[DOUGH]+expected['dough_baked']==expected['dough_prepared'], 'Dough balance failed')
    require(inventory[BREAD]+expected['meals']==expected['bread_baked'], 'Bread balance failed')
    require(inventory[BUCKET]+inventory[WATER]==8, 'Bucket conservation failed')
    require(inventory[WATER]+expected['flour_crafted']==expected['water_filled'], 'Filled-water accounting failed')
    require(inventory[SEED]==64+expected['crop_seeds_generated']+expected['mill_seeds_generated']-expected['crops_replanted'], 'Seed balance failed')
    require(all(not i['items'] for i in after['inventories'] if i['path'] in ('InputInventory.Items','OutputInventory.Items')), 'Unresolved mill inventory')
    require(all(not set(i['items'])-{ 'minecraft:coal' } for i in after['inventories'] if i['role']=='furnace'), 'Unresolved furnace material')
    return dict(verified_totals=dict(expected), final_material=dict(inventory),
                regrown_reharvested_plots=sum(n>=2 for n in harvested.values()), furnace_recipe_counts=dict(bake_recipes))
