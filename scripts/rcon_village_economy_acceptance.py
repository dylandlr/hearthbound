#!/usr/bin/env python3
"""Eight native citizens, two renewable food chains, matched selector controls.

After setup there are no operator inventory, crop, motor, teleport or completion
commands. The two public demand changes and bounded drain are preregistered.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import time
from rcon_private_communication_trial import connection
from rcon_need_services_acceptance import response_json, xyz
from rcon_production_services_acceptance import inventory
from village_economy_evidence import ITEMS, KINDS, require, validate_history, validate_physical

COMMAND='hearthbound-village'
ARMS=('adaptive','authored'); WORLDS=(23001,23002)
HORIZON=7200; DRAIN=2400; CHANGES=((3600,0),(4200,6))
TAGS=tuple(f'hb_village_{i}' for i in range(8))
SCHEMA='hearthbound.renewable-village-live.v0.23'


def status(rcon):
    s=response_json(rcon.run(COMMAND+' status'),'VILLAGE_STATUS')
    require(not s['failure'] and len(s['citizens'])==8,'Lost citizen or failed controller: '+repr(s))
    require(all(c.get('loaded') and c.get('alive') for c in s['citizens']),'Dead/unloaded citizen')
    return s


def tick(rcon):
    raw=rcon.run('time query gametime'); match=re.search(r'(\d+)\s*$',raw)
    require(match,'Missing native game time'); return int(match.group(1))


def records(rcon,total):
    rows=[]
    while len(rows)<total:
        page=response_json(rcon.run(f'{COMMAND} records {len(rows)}'),'VILLAGE_RECORDS')
        require(page['offset']==len(rows) and page['total']>=total and page['records'],'Missing evidence page')
        rows.extend(page['records'][:total-len(rows)])
    require([r['sequence'] for r in rows]==list(range(1,total+1)),'Evidence gap')
    return rows


def native(rcon):
    snapshots=[]; crops=[]; wells=[]; furnace_recipes=[]
    for z in (0,22):
        for role,x,zz,path in (('depot',10,5,'Items'),('flour',25,5,'Items'),('water',26,8,'Items'),
                               ('dough',32,5,'Items'),('furnace',36,5,'Items'),('pantry',42,5,'Items'),
                               ('mill_input',18,5,'InputInventory.Items'),('mill_output',18,5,'OutputInventory.Items')):
            s=inventory(rcon,(x,101,z+zz),path,ITEMS); s['role']=role; snapshots.append(s)
        furnace_recipes.append(rcon.run(f'data get block 36 101 {z+5} RecipesUsed'))
        for x,zz in ((5,9),(6,9),(5,10),(6,10)):
            point=(x,101,z+zz); age=None
            for candidate in range(8):
                raw=rcon.run(f'execute if block {xyz(point)} minecraft:wheat[age={candidate}]')
                if 'Test passed' in raw: age=candidate; break
            require(age is not None,'Configured wheat plot disappeared: '+str(point)); crops.append(dict(position=point,age=age,native_response=raw))
        raw=rcon.run(f'execute if block 26 100 {z+10} minecraft:water[level=0]'); require('Test passed' in raw,'Well did not regenerate'); wells.append(raw)
    raw=rcon.run('execute if entity @e[type=minecraft:item,x=0,y=98,z=0,dx=48,dy=7,dz=44]')
    require('Test failed' in raw,'Unaccounted dropped material in village')
    return dict(inventories=snapshots,crops=crops,wells=wells,furnace_recipes=furnace_recipes,dropped_items=raw)


def setup(rcon,arm):
    rcon.require('function hearthbound:village_setup','Executed')
    rcon.require(COMMAND+' policy '+arm,'VILLAGE_OK')
    initial=status(rcon); require(len(initial['districts'])==2 and not initial['enabled'],'Incomplete setup')
    power=[]
    for z in (5,27):
        deadline=time.monotonic()+25
        while True:
            raw=rcon.run(f'data get block 18 101 {z} Speed'); match=re.search(r'data: (-?\d+(?:\.\d+)?)f',raw)
            if match and abs(float(match.group(1)))>0: power.append(raw); break
            require(time.monotonic()<deadline,'Unpowered mill'); time.sleep(.25)
    result=native(rcon); result['power']=power; result['status']=initial
    for tag in TAGS: rcon.require(f'data get entity @e[tag={tag},limit=1] Health','20.0f')
    # Other public controllers cannot seize an enrolled actor.
    raw=rcon.run('hearthbound-services enroll @e[tag=hb_village_0,limit=1]')
    require('NEED_SERVICES_DENIED' in raw,'Competing service controller accepted village citizen')
    return result


def live(rcon,result):
    result['before']=setup(rcon,result['arm']); rcon.require(COMMAND+' start','VILLAGE_OK')
    initial=status(rcon); first=records(rcon,initial['records_total']); start=next(r['tick'] for r in reversed(first) if r['type']=='VILLAGE_STARTED')
    result.update(start_tick=start,changes=[],snapshots=[])
    require('VILLAGE_DENIED' in rcon.run(COMMAND+' policy authored'),'Policy changed during trial')
    deadline=time.monotonic()+900; next_change=0; next_snapshot=400
    while True:
        elapsed=tick(rcon)-start
        if next_change<len(CHANGES) and elapsed>=CHANGES[next_change][0]:
            planned,target=CHANGES[next_change]; rcon.require(f'{COMMAND} target {target}','VILLAGE_OK')
            actual=tick(rcon)-start; result['changes'].append(dict(planned=planned,actual=actual,target=target))
            require(actual-planned<=20,'Demand change missed tolerance'); next_change+=1
        if elapsed>=next_snapshot:
            s=status(rcon); result['snapshots'].append(dict(relative_tick=elapsed,status=s)); next_snapshot+=400
            require(s['held']==0,'Unresolved owned work: '+repr(s))
            print('VILLAGE_PROGRESS '+json.dumps(dict(elapsed=elapsed,totals=s['totals'],active=s['active'],held=s['held'])),flush=True)
        if elapsed>=HORIZON: break
        require(time.monotonic()<deadline,'Native horizon exceeded wall-clock bound'); time.sleep(.2)
    result['horizon_status']=status(rcon); result['horizon_observed_at']=tick(rcon)-start
    rcon.require(COMMAND+' drain','VILLAGE_OK'); drain_start=tick(rcon)
    while True:
        s=status(rcon); require(s['held']==0,'Drain retained uncertain custody')
        if s['active']==0: break
        require(tick(rcon)-drain_start<=DRAIN,'Drain exceeded bounded horizon'); time.sleep(.5)
    rcon.require(COMMAND+' stop','VILLAGE_OK'); result['terminal']=status(rcon)
    require(result['terminal']['active']==result['terminal']['held']==0 and not result['terminal']['leases'],'Incomplete custody drain')
    require(all(not c['cargo'] for c in result['terminal']['citizens']),'Owned cargo survived drain')
    result['records']=records(rcon,result['terminal']['records_total']); result['after']=native(rcon)
    result['native_citizens']={tag:rcon.run(f'data get entity @e[tag={tag},limit=1]') for tag in TAGS}
    for tag in TAGS: rcon.require(f'data get entity @e[tag={tag},limit=1] Health','20.0f')
    result['policy_audit']=validate_history(result['records'],result['arm']=='adaptive')
    result['physical_audit']=validate_physical(result['records'],result['before'],result['after'],result['terminal']['totals'])
    result['callbacks']=[]
    for row in result['records']:
        if row['type']!='MILL_PROCESS_VERIFIED': continue
        raw=rcon.run('sable mill-process '+row['native_job'])
        require('MILL_PROCESS VERIFIED_CALLBACK' in raw and f"citizen={row['citizen']}" in raw,'Native Create callback missing')
        result['callbacks'].append(dict(job=row['job'],native_job=row['native_job'],native_response=raw))
    # During withdrawal, existing work may finish; new material jobs cannot start.
    target_rows=[r for r in result['records'] if r['type']=='FOOD_TARGET_SET']; withdrawal=next(r for r in target_rows if r['target']==0)
    returned=next(r for r in target_rows if r['target']==6 and r['tick']>withdrawal['tick'])
    require(not any(r['type']=='WORK_STARTED' and r['kind']!='WAIT' and withdrawal['sequence']<r['sequence']<returned['sequence'] for r in result['records']),'New material work ignored withdrawn target')
    result['returned_demand_jobs']=sum(r['type']=='WORK_SETTLED' and r['outcome']['completed'] and r['outcome']['kind'] in KINDS[:6] and r['outcome']['start']>returned['tick'] for r in result['records'])
    counts=result['physical_audit']['verified_totals']; audit=result['policy_audit']
    result['milestone_checks']=dict(
        eight_survived=True, meals_at_least_four=counts.get('meals',0)>=4,
        repeated_native_regrowth=result['physical_audit']['regrown_reharvested_plots']>0,
        repeated_complete_food_chain=all(counts.get(k,0)>=2 for k in ('wheat_harvested','wheat_milled','dough_prepared','bread_baked','water_filled')),
        at_least_four_productive=audit['productive_citizens']>=4,
        at_least_two_change_capability=audit['multi_capability_citizens']>=2,
        resumes_after_withdrawal=result['returned_demand_jobs']>0)
    result['milestone_passed']=all(result['milestone_checks'].values())
    result['private_digests']={c['citizen']:c['learning_digest'] for c in result['terminal']['citizens']}
    result['status']='integrity_passed'; rcon.require('save-all flush','Saved the game')
    print('VILLAGE_LIVE '+json.dumps(dict(arm=result['arm'],world=result['world'],physical=result['physical_audit'],policy=audit,milestone=result['milestone_checks'])),flush=True)


def restart(rcon,result):
    require(result['status']=='integrity_passed','Live phase incomplete'); current=status(rcon)
    require(not current['enabled'] and not current['draining'] and current['active']==current['held']==0 and not current['leases'],'Restart resumed resolved work')
    require(current['adaptive']==result['terminal']['adaptive'] and current['totals']==result['terminal']['totals'],'Policy/totals changed on restart')
    require({c['citizen']:c['learning_digest'] for c in current['citizens']}==result['private_digests'],'Private learner replay changed')
    require(records(rcon,current['records_total'])==result['records'],'Evidence changed on restart')
    after=native(rcon)
    require(after['inventories']==result['after']['inventories'] and after['furnace_recipes']==result['after']['furnace_recipes'],'Native material changed on restart')
    # Native crops may continue growing while dispatch is stopped; never freeze or
    # rewrite them just to manufacture an identical snapshot.
    require(all(a['age']>=b['age'] for a,b in zip(after['crops'],result['after']['crops'],strict=True)),'Stopped controller harvested a plot')
    result['restart']=current; result['restart_native']=after; result['status']='passed_live_and_restart'
    print('VILLAGE_FORGE_PASS '+json.dumps(dict(world=result['world'],arm=result['arm'],milestone=result['milestone_passed'])),flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--arm',choices=ARMS,required=True); p.add_argument('--world',type=int,choices=WORLDS,required=True)
    p.add_argument('--phase',choices=('live','restart'),required=True); p.add_argument('--output',type=Path,default=Path('run/village-acceptance.json')); a=p.parse_args()
    result=json.loads(a.output.read_text()) if a.phase=='restart' else dict(schema=SCHEMA,status='running',origin='REAL_FORGE_CREATE',arm=a.arm,world=a.world,
        commit=os.environ.get('HEARTHBOUND_EXPECTED_COMMIT','UNSPECIFIED'),planned_slots=[dict(world=w,arm=arm) for w in WORLDS for arm in ARMS],
        horizon_ticks=HORIZON,drain_bound_ticks=DRAIN,changes_planned=CHANGES,timing_tolerance_ticks=20,random_tick_speed=400,
        causal_learning_advantage_claimed=False,causal_communication_benefit_claimed=False,neural_controller=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with connection(os.environ['HEARTHBOUND_RCON_PASSWORD']) as rcon:
        try: (live if a.phase=='live' else restart)(rcon,result)
        except Exception as e:
            result.update(status='failed',failed_phase=a.phase,error=type(e).__name__+': '+str(e))
            try:
                result['failure_status']=response_json(rcon.run(COMMAND+' status'),'VILLAGE_STATUS')
                result['failure_records']=records(rcon,result['failure_status']['records_total'])
                result['failure_native_citizens']={tag:rcon.run(f'data get entity @e[tag={tag},limit=1]') for tag in TAGS}
                result['failure_native']=native(rcon)
            except Exception as capture: result['capture_failure']=str(capture)
            raise
        finally: a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        rcon.stop_server()


if __name__=='__main__': main()
