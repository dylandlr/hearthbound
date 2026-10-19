#!/usr/bin/env python3
"""Physical acceptance checks on a disposable Forge world; no mock inventories."""
import importlib.util
from pathlib import Path
import re
import time
spec=importlib.util.spec_from_file_location('rcon',Path(__file__).with_name('forge-rcon-probe.py'))
rcon=importlib.util.module_from_spec(spec); spec.loader.exec_module(rcon)
def cmd(c):
    r=rcon.execute(c); print(c,'=>',r,flush=True); return r
who='execute as @e[type=minecraft:villager,name=Survivor,limit=1] at @s run '
entity='@e[type=minecraft:villager,name=Survivor,limit=1]'
def wait(test,label,seconds=50):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if test(): return
        time.sleep(.5)
    raise AssertionError(label+' timed out: '+cmd(who+'sable survival-inspect'))
def inspect(): return rcon.execute(who+'sable survival-inspect')
def need(food):
    cmd('data merge entity '+entity+' {ForgeData:{"hearthbound.survivalV1":{food:'+str(food)+'d}}}')
def traits(danger,combat,shelter=70):
    cmd('data merge entity '+entity+' {ForgeData:{"hearthbound.instinctV1":{food:60,danger:'+str(danger)+',combat:'+str(combat)+',shelter:'+str(shelter)+'}}}')
for c in ['forceload add 64 64 96 96','fill 64 99 64 96 99 96 stone','fill 64 100 64 96 108 96 air',
          'gamerule doMobSpawning false','gamerule doDaylightCycle false','time set 6000',
          'execute positioned 76 100 76 run sable spawn-named Survivor']:
    cmd(c)
cmd(who+'sable survival-on'); traits(75,25); need(5)
# A real dropped apple must disappear through eating; no bread duplication or phantom reward.
cmd('summon item 77 100 76 {Tags:["hb_food"],PickupDelay:0s,Item:{id:"minecraft:apple",Count:1b}}')
wait(lambda:'meals=1' in inspect(),'consume one real apple')
assert 'test passed' in cmd('execute unless entity @e[tag=hb_food]').lower()
assert 'meals=1' in inspect()
# Threat observations differ by instincts, then adapt to actual health.
cmd('summon zombie 79 100 76 {Tags:["hb_threat"],NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}')
wait(lambda:'action=FLEE' in inspect(),'cautious citizen flees')
cmd('kill @e[tag=hb_threat]'); cmd('tp '+entity+' 76 100 76'); traits(25,75)
cmd('summon zombie 77 100 76 {Tags:["hb_threat"],NoAI:1b,Silent:1b,PersistenceRequired:1b,Health:20f,ArmorItems:[{},{},{},{id:"minecraft:iron_helmet",Count:1b}]}')
wait(lambda: bool(re.search(r'hits=[1-9]',inspect())),'physical defense damage')
cmd('data merge entity '+entity+' {Health:5f}')
wait(lambda:'action=FLEE' in inspect(),'injured defender retreats')
cmd('kill @e[tag=hb_threat]'); cmd('data merge entity '+entity+' {Health:20f}')
# Cover is discovered locally; not teleported there by the controller.
cmd('tp '+entity+' 76 100 76'); cmd('fill 79 103 74 83 103 78 stone'); cmd('time set 18000')
wait(lambda:'outcome=UNDER_COVER' in inspect(),'navigate under physical roof')
cmd('time set 6000'); wait(lambda:'action=WORK' in inspect(),'release work at dawn')
# Repeated delivery uses the production ledger, not a reset or duplicated job.
cmd(who+'sable survival-off'); cmd('tp '+entity+' 76 100 76')
cmd('setblock 75 100 76 chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]}')
cmd('setblock 82 100 76 chest')
cmd(who+'sable auto-work-discover 75 100 76 82 100 76')
cmd(who+'sable haul-priority 1'); cmd(who+'hearthbound library priority 0')
cmd(who+'sable auto-work-repeat-on'); cmd(who+'sable auto-work-on')
wait(lambda:'test passed' in rcon.execute('execute if data block 82 100 76 Items[{id:"minecraft:wheat",Count:3b}]').lower(),'three physical repeat deliveries',100)
assert 'test passed' in cmd('execute unless data block 75 100 76 Items[{id:"minecraft:wheat"}]').lower()
memory=cmd(who+'sable social-inspect')
assert memory.count('source=SELF')>=3,memory
# Pause a cargo-bearing job at night; keep the exact job and item, resume at dawn.
cmd(who+'sable auto-work-off'); cmd('tp '+entity+' 76 100 76')
cmd('item replace block 75 100 76 container.0 with minecraft:wheat 1')
assert 'test passed' in cmd('execute if data block 75 100 76 Items[{id:"minecraft:wheat",Count:1b}]').lower()
cmd('setblock 94 100 76 chest')
cmd(who+'sable haul 75 100 76 94 100 76')
wait(lambda:'cargo=1x' in rcon.execute(who+'sable haul-audit'),'cargo picked up')
before=cmd(who+'sable haul-audit'); job=re.search(r'job=([0-9a-f-]{36})',before)[1]
cmd('fill 72 103 73 80 103 79 stone'); cmd('time set 18000')
cmd(who+'sable survival-on')
wait(lambda:'action=SHELTER' in inspect(),'cargo task suspended')
time.sleep(3)
paused=cmd(who+'sable haul-audit')
assert 'job='+job in paused and 'cargo=1x' in paused,paused
cmd('time set 6000')
wait(lambda:'test passed' in rcon.execute('execute if data block 94 100 76 Items[{id:"minecraft:wheat",Count:1b}]').lower(),'original cargo delivered after emergency',60)
after=cmd(who+'sable haul-audit')
assert 'job='+job in after and 'cargo=0x' in after,after
assert 'test passed' in cmd('execute unless data block 75 100 76 Items[{id:"minecraft:wheat"}]').lower()
print('HB_SURVIVAL_PASS: food conservation, distinct instincts, physical defense, health adaptation, shelter navigation, dawn resumption, repeated cargo-safe work',flush=True)
