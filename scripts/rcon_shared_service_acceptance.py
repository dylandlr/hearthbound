#!/usr/bin/env python3
"""Fixed-budget real Minecraft comparison. All arms share menus and executors.

Two worlds x three policies; world seed does not control entity UUIDs or server
scheduling. This is bounded integration evidence, not a population effect study.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import time
import numpy as np
from rcon_private_communication_trial import connection
from rcon_need_services_acceptance import require, records, response_json, xyz
from rcon_production_services_acceptance import inventory, unique
from service_option_env import encode, authored
from train_service_policy import Network

COMMAND='hearthbound-services'
SOURCES=((36,101,3),(36,101,19)); MILLS=((11,101,3),(11,101,19)); OUTPUTS=((4,101,3),(4,101,19))
TAGS=('hb_shared_a','hb_shared_b','hb_shared_c','hb_shared_d')
SCHEDULE=((0,(2,1)),(800,(2,4)),(1600,(5,4)))
HORIZON=2400; DRAIN=600
SCHEMA='hearthbound.shared-service-live.v0.22'
ARMS=('neural','untrained','authored')
WORLDS=(22001,22002)


def status(rcon):
    value=response_json(rcon.run(COMMAND+' status'),'NEED_SERVICES_STATUS')
    require(not value.get('failure') and not value.get('errors'),'Runtime failure: '+repr(value))
    require(value.get('enrolled')==4 and len(value.get('citizens',[]))==4,'Lost enrolled citizen')
    require(all(c.get('loaded') for c in value['citizens']),'Citizen not loaded')
    require(value.get('neural_weight_updates')==0 and value.get('frozen') is True,'Live network is not frozen')
    return value


def tick(rcon):
    raw=rcon.run('time query gametime'); match=re.search(r'(\d+)\s*$',raw)
    require(match,'Missing native game time: '+raw); return int(match.group(1))


def setup(rcon,arm):
    commands=['gamerule doMobSpawning false','gamerule doDaylightCycle false','gamerule doWeatherCycle false',
              'time set 6000','weather clear','forceload add 0 0 47 31',
              'fill 0 104 0 44 104 24 minecraft:stone','fill 0 100 0 44 103 24 minecraft:air',
              'fill 0 100 0 44 100 24 minecraft:stone','fill 0 101 0 44 103 0 minecraft:stone',
              'fill 0 101 24 44 103 24 minecraft:stone','fill 0 101 0 0 103 24 minecraft:stone',
              'fill 44 101 0 44 103 24 minecraft:stone']
    for s,m,b in zip(SOURCES,MILLS,OUTPUTS):
        commands += [f'setblock {xyz(s)} minecraft:chest{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:16b}}]}} replace',
                     f'setblock {xyz(b)} minecraft:chest replace',
                     f'setblock {m[0]} 100 {m[2]} create:creative_motor[facing=up] replace',
                     f'setblock {xyz(m)} create:millstone replace']
    for command in commands:
        raw=rcon.run(command)
        require(not any(word in raw.lower() for word in ('unknown command','incorrect argument','not loaded','failed')),'Setup failed: '+raw)
    power=[]
    for m in MILLS:
        deadline=time.monotonic()+25
        while True:
            raw=rcon.run(f'data get block {xyz(m)} Speed'); match=re.search(r'data: (-?\d+(?:\.\d+)?)f',raw)
            if match and abs(float(match.group(1)))>0: power.append(raw); break
            require(time.monotonic()<deadline,'Unpowered fixture mill'); time.sleep(.25)
    for tag,(x,z) in zip(TAGS,((3,2),(35,2),(3,18),(35,18))):
        rcon.require(f'execute positioned {x} 101 {z} run sable spawn','Sable spawned')
        selector=f'@e[type=minecraft:villager,name=Sable,x={x},y=101,z={z},distance=..4,limit=1,sort=nearest]'
        rcon.require(f'tag {selector} add {tag}','Added tag')
        rcon.require(f'data get entity @e[tag={tag},limit=1] Health','20.0f')
        rcon.require(f'{COMMAND} enroll @e[tag={tag},limit=1]','NEED_SERVICES_OK')
    for i in range(2):
        rcon.require(f'{COMMAND} configure-mill {xyz(MILLS[i])} {xyz(OUTPUTS[i])} {SCHEDULE[0][1][i]}','NEED_SERVICES_OK')
        rcon.require(f'{COMMAND} configure-source {xyz(SOURCES[i])}','NEED_SERVICES_OK')
    rcon.require(f'{COMMAND} policy {arm}','NEED_SERVICES_OK')
    before=dict(sources=[inventory(rcon,p,allowed={'minecraft:wheat'}) for p in SOURCES],
                outputs=[inventory(rcon,p) for p in OUTPUTS],power=power,status=status(rcon))
    require(all(i['items']=={'minecraft:wheat':16} for i in before['sources']) and all(not i['items'] for i in before['outputs']),'Initial material differs')
    return before


def validate_choices(rows,arm):
    path=Path('src/main/resources/data/hearthbound/policies')/f'service-{ "trained" if arm=="neural" else "untrained"}-v0-22.txt'
    model=None if arm=='authored' else Network.load(path); count=0
    for r in rows:
        if r.get('type')!='POLICY_DECISION': continue
        scores=r['scores']; menu=[dict(id=s['id'],kind=s['kind'],features=s['features']) for s in scores]
        require(menu==sorted(menu,key=lambda c:c['id']),'Noncanonical candidate ordering')
        x=encode(menu)
        np.testing.assert_allclose(x,np.asarray([s['actor_input'] for s in scores]),rtol=0,atol=1e-12)
        expected=np.asarray([dict(SUPPLY_WHEAT=3.,OBSERVE_BUFFER=.6,CARRY_REQUEST=1.,WAIT=0.)[c['kind']]-.3*c['features'][2] for c in menu]) if model is None else model.values(x)
        np.testing.assert_allclose(expected,[s['total'] for s in scores],rtol=1e-10,atol=1e-10)
        require(r['selected']==menu[int(np.argmax(expected))]['id'],'Runtime bypassed frozen policy')
        require(r['frozen'] is True and r['shadow_rls'] is True,'Hidden live learning treatment')
        require(r['model_sha256']==('' if model is None else model.digest()),'Runtime checkpoint differs')
        count+=1
    require(count>0,'No scored live policy choices')
    return count


def validate_physical(rows,after):
    finals=[r for r in rows if r.get('type')=='PRODUCTION_SETTLED']
    require(len({r['job'] for r in finals})==len(finals),'Duplicate production job')
    require(len({r['physical_evidence'] for r in finals})==len(finals),'Duplicate production receipt')
    delivered=[Counter(),Counter()]; consumed=Counter(); sample=Counter(); witnesses=[]
    for final in finals:
        job=final['job']; chain=[unique(rows,k,job) for k in ('MOTOR_ASSIGNED','TRANSFER_VERIFIED','PRODUCTION_OUTPUT_COLLECTED','PRODUCTION_OUTPUT_DELIVERED','SERVICE_SETTLED')]
        assignment,transfer,collected,delivery,settlement=chain
        for row in chain:
            for key in ('citizen','request','commitment','session'): require(row.get(key)==final.get(key) and row.get(key),'Ownership changed: '+key)
        require([r['sequence'] for r in [*chain,final]]==sorted(r['sequence'] for r in [*chain,final]),'Reordered production')
        require(transfer['delivered_tick']<=collected['processing_start_tick']<collected['process_tick']<=collected['tick']<=delivery['tick']==final['tick'],'Invalid physical chronology')
        site=OUTPUTS.index(tuple(delivery['destination'])); source=SOURCES.index(tuple(assignment['source']))
        require(assignment['destination']==transfer['destination']==collected['machine']==list(MILLS[site]),'Machine changed')
        require(assignment['source']==transfer['source'] and assignment['output_destination']==delivery['destination'],'Endpoint changed')
        units=collected['flour_after']-collected['flour_before']
        require(collected['wheat_before']==1 and collected['wheat_after']==0 and collected['flour_before']==0 and units>0,'No independent process delta')
        require(units==collected['units']==delivery['units']==final['units'],'Production amount changed')
        require(collected['items']==delivery['items']==final['items'],'Output/byproducts changed')
        require(collected['physical_evidence']==final['physical_evidence'] and job in final['physical_evidence'],'Wrong physical receipt')
        require(final['reservation_released'] and final['trace_retired'],'Machine not finalized')
        expected=Counter(delivery['items_before']); expected.update(delivery['items'])
        require(dict(expected)==delivery['items_after'] and delivery['stock_after']-delivery['stock_before']==units,'Insertion does not conserve output')
        require(settlement['outcome']=='VERIFIED_TRANSFER' and settlement['tick']==final['tick'],'No settled full service')
        sample[final['citizen']]+=1
        require(final['production_samples']==sample[final['citizen']],'Foreign/duplicate private production sample')
        consumed[source]+=1; delivered[site].update(final['items']); witnesses.append(dict(job=job,site=site,source=source,tick=final['tick'],units=units))
    # Acceptance requires the bounded drain to leave no unresolved cargo. Failed
    # slots retain raw NBT and history rather than asserting this equality.
    for i in range(2):
        require(after['sources'][i]['items'].get('minecraft:wheat',0)==16-consumed[i],'Native source conservation failed')
        require(after['outputs'][i]['items']==dict(delivered[i]),'Native output/byproduct conservation failed')
        require(not after['mill_inputs'][i]['items'] and not after['mill_outputs'][i]['items'],'Unresolved machine material')
    return witnesses


def run_live(rcon,result):
    result['before']=setup(rcon,result['arm'])
    rcon.require(COMMAND+' start','NEED_SERVICES_OK')
    started=status(rcon); rows=records(rcon,started['records_total'])
    start=next(r['tick'] for r in reversed(rows) if r['type']=='SERVICE_STARTED')
    result['start_tick']=start; result['changes']=[]; result['snapshots']=[]
    require('NEED_SERVICES_DENIED' in rcon.run(COMMAND+' policy authored'),'Policy changed while active')
    deadline=time.monotonic()+300; next_change=1; next_snapshot=400
    while True:
        now=tick(rcon); elapsed=now-start
        if next_change<len(SCHEDULE) and elapsed>=SCHEDULE[next_change][0]:
            intended,targets=SCHEDULE[next_change]
            for site,target in enumerate(targets): rcon.require(f'{COMMAND} set-target {xyz(OUTPUTS[site])} {target}','NEED_SERVICES_OK')
            actual=tick(rcon)-start; result['changes'].append(dict(planned=intended,actual=actual,targets=targets))
            require(actual-intended<=20,'Demand intervention exceeded declared timing tolerance')
            next_change+=1
        if elapsed>=next_snapshot:
            current=status(rcon); result['snapshots'].append(dict(relative_tick=elapsed,status=current)); next_snapshot+=400
            require(current['held']==0,'Physical work became held before fixed horizon')
        if elapsed>=HORIZON: break
        require(time.monotonic()<deadline,'Fixed horizon did not finish within wall-clock bound'); time.sleep(.2)
    result['horizon_observed_at']=tick(rcon)-start
    # Stop new demand, allow only existing custody to complete for a fixed bound.
    for output in OUTPUTS: rcon.require(f'{COMMAND} set-target {xyz(output)} 0','NEED_SERVICES_OK')
    while tick(rcon)-start < HORIZON+DRAIN:
        current=status(rcon)
        if current['active_commitments']==0: break
        require(current['held']==0,'Drain encountered unresolved custody'); time.sleep(.5)
    rcon.require(COMMAND+' stop','NEED_SERVICES_OK'); terminal=status(rcon); result['terminal']=terminal
    result['records']=records(rcon,terminal['records_total'])
    result['after']=dict(sources=[inventory(rcon,p,allowed={'minecraft:wheat'}) for p in SOURCES],
                         outputs=[inventory(rcon,p) for p in OUTPUTS],
                         mill_inputs=[inventory(rcon,p,'InputInventory.Items',{'minecraft:wheat'}) for p in MILLS],
                         mill_outputs=[inventory(rcon,p,'OutputInventory.Items') for p in MILLS])
    result['native_citizens']={tag:rcon.run(f'data get entity @e[tag={tag},limit=1]') for tag in TAGS}
    require(terminal['active_commitments']==terminal['held']==0,'Drain did not resolve all native custody')
    for tag in TAGS: rcon.require(f'data get entity @e[tag={tag},limit=1] Health','20.0f')
    result['replayed_policy_choices']=validate_choices(result['records'],result['arm'])
    result['physical_jobs']=validate_physical(result['records'],result['after'])
    callbacks=[]
    for row in result['records']:
        if row['type']!='PRODUCTION_OUTPUT_COLLECTED': continue
        raw=rcon.run('sable mill-process '+row['job'])
        require('MILL_PROCESS VERIFIED_CALLBACK' in raw and f"citizen={row['citizen']}" in raw,'Native callback missing/wrong owner')
        for field,key in (('wheatBefore','wheat_before'),('wheatAfter','wheat_after'),('flourBefore','flour_before'),('flourAfter','flour_after'),('startTick','processing_start_tick'),('tick','process_tick')):
            match=re.search(r'\b'+field+r'=(\d+)\b',raw)
            require(match and int(match.group(1))==row[key],'Callback disagrees: '+field)
        callbacks.append(dict(job=row['job'],native_response=raw))
    result['callbacks']=callbacks
    scored=[j for j in result['physical_jobs'] if j['tick']<=start+HORIZON]
    result['score']=dict(output=sum(j['units'] for j in scored),per_site=[sum(j['units'] for j in scored if j['site']==i) for i in range(2)],
                         settled_personal_cost=sum(r['personal_cost'] for r in result['records'] if r['type']=='SERVICE_SETTLED' and r['tick']<=start+HORIZON),
                         sends=sum(r['type']=='REQUEST_SENT' and r['tick']<=start+HORIZON for r in result['records']),
                         drain_output=sum(j['units'] for j in result['physical_jobs'] if j['tick']>start+HORIZON))
    # Milestone criterion is reported separately from integrity. Do not discard
    # an unsuccessful neural slot or require the untrained arm to be productive.
    adapted=[]
    for i,change in ((0,1600),(1,800)):
        after_change=[]
        for j in scored:
            if j['site']!=i: continue
            a=unique(result['records'],'MOTOR_ASSIGNED',j['job'])
            obs=[r for r in result['records'] if r['type']=='NEED_OBSERVED' and r['request']==a['request'] and r['revision']==a['revision']]
            if obs and obs[0]['tick']>=start+change: after_change.append(j['job'])
        adapted.append(bool(after_change))
    result['responded_to_later_demand']=adapted
    result['milestone_passed']=all(n>0 for n in result['score']['per_site']) and all(adapted)
    result['private_digests']={c['citizen']:c['learning_digest'] for c in terminal['citizens']}
    result['status']='integrity_passed'; rcon.require('save-all flush','Saved the game')
    print('SHARED_SERVICE_LIVE '+json.dumps(dict(arm=result['arm'],world=result['world'],score=result['score'],milestone=result['milestone_passed'])),flush=True)


def restart(rcon,result):
    require(result['status']=='integrity_passed','No completed live trial')
    current=status(rcon)
    require(not current['enabled'] and current['active_commitments']==current['held']==0,'Clean restart resumed work')
    require(current['model_sha256']==result['terminal']['model_sha256'] and current['policy']==result['terminal']['policy'],'Policy changed on restart')
    require({c['citizen']:c['learning_digest'] for c in current['citizens']}==result['private_digests'],'Shadow private histories changed')
    require(records(rcon,current['records_total'])==result['records'],'Evidence changed on replay')
    after=dict(sources=[inventory(rcon,p,allowed={'minecraft:wheat'}) for p in SOURCES],outputs=[inventory(rcon,p) for p in OUTPUTS],
               mill_inputs=[inventory(rcon,p,'InputInventory.Items',{'minecraft:wheat'}) for p in MILLS],mill_outputs=[inventory(rcon,p,'OutputInventory.Items') for p in MILLS])
    require(after==result['after'],'Native inventories changed on restart')
    result['restart']=current; result['status']='passed_live_and_restart'; print('SHARED_SERVICE_FORGE_PASS',flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--arm',choices=ARMS,required=True); p.add_argument('--world',type=int,choices=WORLDS,required=True)
    p.add_argument('--phase',choices=('live','restart'),required=True); p.add_argument('--output',type=Path,default=Path('run/shared-service-acceptance.json')); args=p.parse_args()
    result=json.loads(args.output.read_text()) if args.phase=='restart' else dict(schema=SCHEMA,status='running',origin='REAL_FORGE_CREATE',arm=args.arm,world=args.world,
        commit=os.environ.get('HEARTHBOUND_EXPECTED_COMMIT','UNSPECIFIED'),planned_slots=[dict(world=w,arm=a) for w in WORLDS for a in ARMS],
        schedule=SCHEDULE,horizon_ticks=HORIZON,drain_bound_ticks=DRAIN,timing_tolerance_ticks=20,causal_communication_benefit_claimed=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with connection(os.environ['HEARTHBOUND_RCON_PASSWORD']) as rcon:
        try:
            (run_live if args.phase=='live' else restart)(rcon,result)
        except Exception as failure:
            result.update(status='failed',failed_phase=args.phase,error=type(failure).__name__+': '+str(failure))
            try:
                result['failure_status']=response_json(rcon.run(COMMAND+' status'),'NEED_SERVICES_STATUS')
                result['failure_records']=records(rcon,result['failure_status']['records_total'])
                result['failure_native_citizens']={tag:rcon.run(f'data get entity @e[tag={tag},limit=1]') for tag in TAGS}
            except Exception as capture: result['capture_failure']=str(capture)
            raise
        finally: args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        rcon.stop_server()

if __name__=='__main__': main()
