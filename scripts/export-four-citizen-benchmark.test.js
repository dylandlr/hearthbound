"use strict";
const assert=require("node:assert/strict");
const {verifyReceipt}=require("./export-four-citizen-benchmark");
const payload={
 schema:"hearthbound.four_citizen_physical.v1",
 fixture_world:"four-citizen-colony",
 fixture_seed:"hearthbound-four-citizen-v0-3",
 verification:{source_chests_without_original_wheat:4,destination_wheat:4,outstanding_claims:0,
  distinct_completed_citizens:4,scoped_citizen_decisions:4,dispatch_disabled_at_end:true},
 aggregate_milestone:{id:"four-independent-wheat-deliveries",completed:true,physical_units:4,
 individual_contributors:null},
 limits:{individual_contribution_scores:false,independent_world_replicate:false,
 learned_policy:false,journal_crash_atomicity:false}
};
const pass="CIVILIZATION_FOUR_CITIZEN_ACCEPTANCE_PASS observed_proposals=4 physical_deliveries=4 destination_wheat=4 outstanding_claims=0 scoped_citizen_decisions=4 no_reward_claim=true";
const marker=p=>"HEARTHBOUND_BENCHMARK_RECEIPT_V1 "+JSON.stringify(p);
const citizen=i=>[i.toString().padStart(8,"0"),"0000","4000","8000",i.toString().padStart(12,"0")].join("-");
const trace={
 schema:"hearthbound.citizen_decisions.v1",count:4,
 scope:"LOADED_LATEST_CITIZEN_MEMORY_AND_PHYSICAL_JOB",
 policy:"DETERMINISTIC_TRAIT_RANK_V1",learning_authorized:false,
 entries:[1,2,3,4].map(i=>({
  task_id:i,citizen:citizen(i),job:citizen(i+10),decision:citizen(i+20),
  evidence:citizen(i+30),revision:1,observed_tick:10,
  decision_tick:11,assigned_tick:12,delivered_tick:20
 }))
};
const traceLine=t=>"HEARTHBOUND_CITIZEN_TRACES_V1 "+JSON.stringify(t);
const log=(p,t=trace)=>traceLine(t)+"\n"+pass+"\n"+marker(p)+"\n";
const provenance={workflowRunId:"45000000",commit:"a".repeat(40)};
const score=verifyReceipt(log(payload),provenance);
assert.equal(score.aggregate.physicalDeliveries,4);
assert.equal(score.citizenTraces.length,4);
assert.equal(score.scores.verifiedCitizenJobs,4);
assert.equal(score.fixtureParticipation.counts.completed,4);
assert.equal(score.fixtureParticipation.metrics.marbleStyleParticipationKpi,0.25);
assert.equal(score.fixtureParticipation.metrics.topology,null);
assert.equal(score.fixtureParticipation.metrics.learningGain,null);
assert.equal(score.scores.individualParticipation,null);
assert.equal(score.scores.learnedCooperation,null);
assert.equal(score.scores.verifiedAggregateMilestoneCompletion,1);
assert.equal(verifyReceipt(log(payload),provenance).provenance.logSha256,score.provenance.logSha256);
assert.throws(()=>verifyReceipt(log(payload),{...provenance,workflowRunId:"abc"}),/run ID/);
assert.throws(()=>verifyReceipt(log(payload),{...provenance,commit:"bad"}),/commit/);
assert.throws(()=>verifyReceipt(marker(payload),provenance),/exactly one/);
assert.throws(()=>verifyReceipt(log(payload)+marker(payload),provenance),/exactly one/);
assert.throws(()=>verifyReceipt(traceLine(trace)+"\n"+marker(payload)+"\n"+pass,provenance),/out-of-order/);
assert.throws(()=>verifyReceipt(traceLine(trace)+"\n"+pass.replace("physical_deliveries=4","physical_deliveries=3")+"\n"+marker(payload),provenance),/incomplete/);
assert.throws(()=>verifyReceipt(log({...payload,fixture_world:"foreign"}),provenance),/fixture/);
assert.throws(()=>verifyReceipt(log({...payload,verification:{...payload.verification,destination_wheat:3}}),provenance),/failed evidence/);
assert.throws(()=>verifyReceipt(log({...payload,aggregate_milestone:{...payload.aggregate_milestone,individual_contributors:["fake"]}}),provenance),/failed evidence/);
assert.throws(()=>verifyReceipt(log({...payload,limits:{...payload.limits,learned_policy:true}}),provenance),/failed evidence/);
assert.throws(()=>verifyReceipt(traceLine(trace)+"\n"+pass+"\nHEARTHBOUND_BENCHMARK_RECEIPT_V1 {bad",provenance),/JSON/);
assert.throws(()=>verifyReceipt(log(payload,{...trace,entries:[...trace.entries.slice(0,3),trace.entries[0]]}),provenance),/duplicate citizen/);
assert.throws(()=>verifyReceipt(log(payload,{...trace,entries:trace.entries.map((e,i)=>i===0?{...e,delivered_tick:9}:e)}),provenance),/chronology/);
assert.throws(()=>verifyReceipt(log(payload,{...trace,learning_authorized:true}),provenance),/scope/);
assert.throws(()=>verifyReceipt(pass+"\n"+marker(payload),provenance),/citizen trace/);
console.log("four-citizen aggregate export contract assertions passed");

assert.throws(()=>verifyReceipt(log({...payload,fixture_seed:"hearthbound-four-citizen-v0-8-1"}),provenance),/fixture/);
assert.equal(verifyReceipt(log({...payload,fixture_seed:"hearthbound-four-citizen-v0-8-1"}),{...provenance,fixtureSeed:"hearthbound-four-citizen-v0-8-1"}).provenance.fixtureSeed,"hearthbound-four-citizen-v0-8-1");
assert.throws(()=>verifyReceipt(log(payload),{...provenance,fixtureSeed:"unregistered"}),/unregistered/);
