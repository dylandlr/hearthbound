# Disposable creative-world village demo. Clears x=0..48, y=100..104, z=0..44.
# Run once in a NEW world, then /hearthbound-village start. Native crop growth is accelerated 400/3.
gamerule doMobSpawning false
gamerule mobGriefing false
gamerule doDaylightCycle false
gamerule doWeatherCycle false
gamerule randomTickSpeed 400
time set 6000
weather clear
forceload add 0 0 48 44
fill 0 104 0 48 104 44 minecraft:glass
fill 0 100 0 48 103 44 minecraft:air
fill 0 100 0 48 100 44 minecraft:stone_bricks
fill 0 101 0 48 103 0 minecraft:glass
fill 0 101 44 48 103 44 minecraft:glass
fill 0 101 0 0 103 44 minecraft:glass
fill 48 101 0 48 103 44 minecraft:glass
setblock 10 101 5 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat_seeds",Count:32b}]} replace
setblock 18 100 5 create:creative_motor[facing=up] replace
setblock 18 101 5 create:millstone replace
setblock 25 101 5 minecraft:chest replace
setblock 26 101 8 minecraft:chest{Items:[{Slot:0b,id:"minecraft:bucket",Count:4b}]} replace
setblock 29 101 5 minecraft:crafting_table replace
setblock 32 101 5 minecraft:chest replace
setblock 36 101 5 minecraft:furnace[facing=north]{Items:[{Slot:1b,id:"minecraft:coal",Count:16b}]} replace
setblock 42 101 5 minecraft:chest replace
fill 26 100 10 27 100 11 minecraft:water
setblock 4 100 8 minecraft:water
setblock 5 100 9 minecraft:farmland[moisture=7]
setblock 5 101 9 minecraft:wheat[age=0]
setblock 6 100 9 minecraft:farmland[moisture=7]
setblock 6 101 9 minecraft:wheat[age=0]
setblock 5 100 10 minecraft:farmland[moisture=7]
setblock 5 101 10 minecraft:wheat[age=0]
setblock 6 100 10 minecraft:farmland[moisture=7]
setblock 6 101 10 minecraft:wheat[age=0]
hearthbound-village district 0 101 0
execute positioned 10 101 3 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=10,y=101,z=3,distance=..4,limit=1,sort=nearest] add hb_village_0
hearthbound-village enroll @e[tag=hb_village_0,limit=1]
execute positioned 20 101 3 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=20,y=101,z=3,distance=..4,limit=1,sort=nearest] add hb_village_1
hearthbound-village enroll @e[tag=hb_village_1,limit=1]
execute positioned 30 101 3 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=30,y=101,z=3,distance=..4,limit=1,sort=nearest] add hb_village_2
hearthbound-village enroll @e[tag=hb_village_2,limit=1]
execute positioned 40 101 3 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=40,y=101,z=3,distance=..4,limit=1,sort=nearest] add hb_village_3
hearthbound-village enroll @e[tag=hb_village_3,limit=1]
setblock 10 101 27 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat_seeds",Count:32b}]} replace
setblock 18 100 27 create:creative_motor[facing=up] replace
setblock 18 101 27 create:millstone replace
setblock 25 101 27 minecraft:chest replace
setblock 26 101 30 minecraft:chest{Items:[{Slot:0b,id:"minecraft:bucket",Count:4b}]} replace
setblock 29 101 27 minecraft:crafting_table replace
setblock 32 101 27 minecraft:chest replace
setblock 36 101 27 minecraft:furnace[facing=north]{Items:[{Slot:1b,id:"minecraft:coal",Count:16b}]} replace
setblock 42 101 27 minecraft:chest replace
fill 26 100 32 27 100 33 minecraft:water
setblock 4 100 30 minecraft:water
setblock 5 100 31 minecraft:farmland[moisture=7]
setblock 5 101 31 minecraft:wheat[age=0]
setblock 6 100 31 minecraft:farmland[moisture=7]
setblock 6 101 31 minecraft:wheat[age=0]
setblock 5 100 32 minecraft:farmland[moisture=7]
setblock 5 101 32 minecraft:wheat[age=0]
setblock 6 100 32 minecraft:farmland[moisture=7]
setblock 6 101 32 minecraft:wheat[age=0]
hearthbound-village district 0 101 22
execute positioned 10 101 25 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=10,y=101,z=25,distance=..4,limit=1,sort=nearest] add hb_village_4
hearthbound-village enroll @e[tag=hb_village_4,limit=1]
execute positioned 20 101 25 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=20,y=101,z=25,distance=..4,limit=1,sort=nearest] add hb_village_5
hearthbound-village enroll @e[tag=hb_village_5,limit=1]
execute positioned 30 101 25 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=30,y=101,z=25,distance=..4,limit=1,sort=nearest] add hb_village_6
hearthbound-village enroll @e[tag=hb_village_6,limit=1]
execute positioned 40 101 25 run sable spawn
tag @e[type=minecraft:villager,name=Sable,x=40,y=101,z=25,distance=..4,limit=1,sort=nearest] add hb_village_7
hearthbound-village enroll @e[tag=hb_village_7,limit=1]
hearthbound-village policy adaptive
hearthbound-village keep-ticking on
hearthbound-village target 6
tellraw @a {"text":"Hearthbound village ready: eight citizens, two farm-to-food districts. Run /hearthbound-village start. This demo uses accelerated native crop growth.","color":"gold"}
