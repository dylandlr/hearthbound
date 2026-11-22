"use strict";
const assert=require("node:assert/strict");
const {episodeRecord,pairRecords,clusterBootstrap,compareMatchedWorlds}=require("./collaboration-evaluation-v0-2");
const agents=["a","b"],milestones=["harvest","haul"],worldId="world",runId="r";
const event=(id,worldId,runId,fields)=>({id,worldId,runId,...fields});
function fixture(seed,variant,outputs){
 const events=[event("completed",worldId,runId,{tick:1,type:"milestone",milestone:"harvest",status:"completed",verified:true,contributors:["a"]})];
 if(outputs>1)events.push(event("haul",worldId,runId,{tick:2,type:"milestone",milestone:"haul",status:"completed",verified:true,contributors:["b"]}));
 return {seed,scenario:"mill",variant,policyVersion:"v1",sourceCommit:"abc",protocolHash:"frozen",
   worldHash:"world-"+seed,durationTicks:64,computeBudget:100,worldId,runId,agents,milestones,events,
   independentEvidence:true,mode:"graph",
   outcome:{physicalOutputs:outputs,conservationViolations:0,actionCount:10,elapsedTicks:32}};
}
const baseline=[episodeRecord(fixture(1,"script",1)),episodeRecord(fixture(2,"script",1)),episodeRecord(fixture(3,"script",1))];
const improved=[episodeRecord(fixture(1,"learned",2)),episodeRecord(fixture(2,"learned",2)),episodeRecord(fixture(3,"learned",1))];
const comparison=compareMatchedWorlds(baseline,improved,{replicates:150,seed:123});
assert.equal(comparison.worldReplicates,3);
assert.equal(comparison.estimates.outputDelta.mean,2/3);
assert.equal(comparison.estimates.completionDelta.mean,1/3);
assert.equal(comparison.estimates.outputDelta.unit,"independent world seed");
assert.deepEqual(compareMatchedWorlds(baseline,improved,{replicates:150,seed:123}),comparison);
assert.throws(()=>episodeRecord({...fixture(5,"script",1),independentEvidence:false}),/independent evidence/);
assert.throws(()=>episodeRecord({...fixture(5,"script",1),outcome:{physicalOutputs:2,conservationViolations:0,actionCount:0,elapsedTicks:65}}),/horizon/);
assert.throws(()=>episodeRecord({...fixture(5,"script",1),protocolHash:""}),/provenance/);
assert.throws(()=>pairRecords(baseline[0],{...improved[0],computeBudget:99}),/unmatched pair/);
assert.throws(()=>pairRecords(baseline[0],{...improved[0],conservationViolations:1}),/conservation/);
assert.throws(()=>compareMatchedWorlds(baseline,[...improved,improved[0]]),/duplicate world/);
assert.throws(()=>compareMatchedWorlds(baseline,improved.slice(1)),/different independent-world counts/);
assert.throws(()=>compareMatchedWorlds(baseline,improved.map((x,i)=>i===1?{...x,seed:22}:x)),/missing matched worlds/);
assert.throws(()=>clusterBootstrap([]),/nonempty/);
assert.throws(()=>clusterBootstrap([1,2,Infinity]),/nonempty/);
assert.throws(()=>clusterBootstrap([1],{replicates:5}),/bootstrap/);
assert.deepEqual(clusterBootstrap([0,0],{replicates:100}),{mean:0,lower:0,upper:0,replicates:100,unit:"independent world seed",intervalType:"descriptive percentile bootstrap"});
console.log("PA4/MARBLE matched-world evaluations passed");
