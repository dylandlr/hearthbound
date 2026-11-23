"use strict";
/**
 * Four-citizen fixture-only task contribution scorer.
 * Must receive output of verifyReceipt, not an arbitrary claimed Minecraft log.
 * Participation is NOT collective intelligence, communication, or occupation emergence.
 */
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function assert(condition,message){if(!condition)throw new Error(message)}
function scoreCitizenParticipation(evidence){
 assert(evidence&&evidence.schema==="hearthbound.collaboration_evidence.v0.4","requires verified v0.4 receipt");
 assert(evidence.audit?.passedLiveAcceptanceMarker===true&&evidence.audit?.fromExplicitReceipt===true,
   "acceptance attestation absent");
 assert(evidence.provenance?.fixtureWorld==="four-citizen-colony"&&
  evidence.provenance?.fixtureSeed==="hearthbound-four-citizen-v0-3"&&
  /^[0-9a-f]{64}$/i.test(evidence.provenance?.logSha256||"")&&
  /^[0-9a-f]{40}$/i.test(evidence.provenance?.commit||"")&&
  /^[0-9]+$/.test(evidence.provenance?.workflowRunId||""),
  "unsupported provenance");
 const a=evidence.aggregate;
 assert(a&&a.physicalDeliveries===4&&a.sourceChestsEmptied===4&&
   a.destinationWheat===4&&a.distinctCitizens===4&&a.scopedDecisions===4&&
   a.outstandingClaims===0,"aggregate physical mismatch");
 const traces=evidence.citizenTraces;
 assert(Array.isArray(traces)&&traces.length===4,"requires four independently joined jobs");
 for(const field of ["citizen","job","decision","evidence","task_id"]){
  const values=traces.map(e=>e[field]);
  assert(new Set(values).size===4,"duplicate trace "+field);
 }
 const byCitizen={};
 for(const t of traces){
  assert(Number.isSafeInteger(t.task_id)&&t.task_id>0&&Number.isSafeInteger(t.revision)&&t.revision>=1,
    "invalid task scope");
  assert(["citizen","job","decision","evidence"].every(field=>UUID.test(t[field]||"")),
    "invalid job identity");
  assert(["observed_tick","decision_tick","assigned_tick","delivered_tick"].every(
    field=>Number.isSafeInteger(t[field])&&t[field]>=0),"invalid chronology");
  assert(t.observed_tick<=t.decision_tick&&t.decision_tick<=t.assigned_tick&&
    t.assigned_tick<=t.delivered_tick&&t.assigned_tick-t.observed_tick<=20,
    "invalid job time order");
  byCitizen[t.citizen]=1;
 }
 // A separate, completed real-world task is the scoring unit here, not a whole
 // production-chain stage. Each successful task has one witnessed executor.
 const jobs=traces.map(t=>({
  milestoneId:"physical-haul-task:"+t.task_id,
  jobId:t.job,citizenId:t.citizen,decisionId:t.decision,evidenceId:t.evidence,
  assignedTick:t.assigned_tick,deliveredTick:t.delivered_tick,
  status:"physically_completed",verified:true
 })).sort((x,y)=>x.milestoneId.localeCompare(y.milestoneId));
 const nCitizens=4,nMilestones=jobs.length,credited=jobs.length;
 return {
  schema:"hearthbound.fixture_participation.v0.7",
  fixtureWorld:evidence.provenance.fixtureWorld,
  provenance:evidence.provenance,
  counts:{citizens:nCitizens,verifiedTaskMilestones:nMilestones,
    completed:nMilestones,creditedIncidences:credited,participatingCitizens:Object.keys(byCitizen).length},
  metrics:{
   taskCompletionRate:nMilestones/nMilestones,
   perCitizenTaskParticipation:byCitizen,
   marbleStyleParticipationKpi:credited/(nCitizens*nMilestones),
   topology:null,communicationScore:null,planningScore:null,
   learningGain:null,organizationEmergence:null
  },
  jobs,
  limits:"Four successful, already verified scripted physical hauls in one fixture world. No uncompleted-world denominator, comparable topology, learning, social emergence, or independent seed replication."
 };
}
module.exports={scoreCitizenParticipation};
