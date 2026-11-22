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
const log=p=>pass+"\n"+marker(p)+"\n";
const provenance={workflowRunId:"45000000",commit:"a".repeat(40)};
const score=verifyReceipt(log(payload),provenance);
assert.equal(score.aggregate.physicalDeliveries,4);
assert.equal(score.scores.individualParticipation,null);
assert.equal(score.scores.learnedCooperation,null);
assert.equal(score.scores.verifiedAggregateMilestoneCompletion,1);
assert.equal(verifyReceipt(log(payload),provenance).provenance.logSha256,score.provenance.logSha256);
assert.throws(()=>verifyReceipt(log(payload),{...provenance,workflowRunId:"abc"}),/run ID/);
assert.throws(()=>verifyReceipt(log(payload),{...provenance,commit:"bad"}),/commit/);
assert.throws(()=>verifyReceipt(marker(payload),provenance),/exactly one/);
assert.throws(()=>verifyReceipt(log(payload)+marker(payload),provenance),/exactly one/);
assert.throws(()=>verifyReceipt(marker(payload)+"\n"+pass,provenance),/out-of-order/);
assert.throws(()=>verifyReceipt(pass.replace("physical_deliveries=4","physical_deliveries=3")+"\n"+marker(payload),provenance),/incomplete/);
assert.throws(()=>verifyReceipt(log({...payload,fixture_world:"foreign"}),provenance),/fixture/);
assert.throws(()=>verifyReceipt(log({...payload,verification:{...payload.verification,destination_wheat:3}}),provenance),/failed evidence/);
assert.throws(()=>verifyReceipt(log({...payload,aggregate_milestone:{...payload.aggregate_milestone,individual_contributors:["fake"]}}),provenance),/failed evidence/);
assert.throws(()=>verifyReceipt(log({...payload,limits:{...payload.limits,learned_policy:true}}),provenance),/failed evidence/);
assert.throws(()=>verifyReceipt(pass+"\nHEARTHBOUND_BENCHMARK_RECEIPT_V1 {bad",provenance),/JSON/);
console.log("four-citizen aggregate export contract assertions passed");
