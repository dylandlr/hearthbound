"use strict";
const assert=require("node:assert/strict");
const {scoreCitizenParticipation}=require("./score-verified-citizen-participation.js");
function uuid(n){return n.toString(16).padStart(8,"0")+"-0000-4000-8000-"+n.toString(16).padStart(12,"0")}
const receipt={
 schema:"hearthbound.collaboration_evidence.v0.4",
 audit:{passedLiveAcceptanceMarker:true,fromExplicitReceipt:true},
 provenance:{fixtureWorld:"four-citizen-colony",fixtureSeed:"hearthbound-four-citizen-v0-3",
  logSha256:"a".repeat(64),commit:"b".repeat(40),workflowRunId:"123456"},
 aggregate:{physicalDeliveries:4,sourceChestsEmptied:4,destinationWheat:4,
  distinctCitizens:4,scopedDecisions:4,outstandingClaims:0},
 citizenTraces:[1,2,3,4].map(i=>({
  task_id:i,citizen:uuid(i),job:uuid(i+10),decision:uuid(i+20),evidence:uuid(i+30),
  revision:1,observed_tick:10,decision_tick:11,assigned_tick:12,delivered_tick:20
 }))
};
const result=scoreCitizenParticipation(receipt);
assert.equal(result.counts.completed,4);
assert.equal(result.counts.participatingCitizens,4);
assert.equal(result.metrics.taskCompletionRate,1);
assert.equal(result.metrics.marbleStyleParticipationKpi,0.25);
assert.equal(result.metrics.topology,null);
assert.equal(result.metrics.learningGain,null);
assert.equal(result.jobs.length,4);
assert.deepEqual(scoreCitizenParticipation(receipt),result);
const mutate=change=>({ ...receipt,...change });
assert.throws(()=>scoreCitizenParticipation(mutate({schema:"wrong"})),/verified/);
assert.throws(()=>scoreCitizenParticipation(mutate({audit:{passedLiveAcceptanceMarker:false}})),/attestation/);
assert.throws(()=>scoreCitizenParticipation(mutate({aggregate:{...receipt.aggregate,destinationWheat:3}})),/aggregate/);
assert.throws(()=>scoreCitizenParticipation(mutate({citizenTraces:receipt.citizenTraces.slice(1)})),/four/);
assert.throws(()=>scoreCitizenParticipation(mutate({citizenTraces:[...receipt.citizenTraces.slice(0,3),receipt.citizenTraces[0]]})),/duplicate/);
assert.throws(()=>scoreCitizenParticipation(mutate({citizenTraces:receipt.citizenTraces.map((t,i)=>i===0?{...t,delivered_tick:0}:t)})),/time order/);
assert.throws(()=>scoreCitizenParticipation(mutate({provenance:{...receipt.provenance,logSha256:"garbage"}})),/provenance/);
assert.throws(()=>scoreCitizenParticipation(mutate({citizenTraces:receipt.citizenTraces.map((t,i)=>i===0?{...t,job:"not-a-job"}:t)})),/identity/);
console.log("PASS 16 fixture-scoped verified participation assertions");
