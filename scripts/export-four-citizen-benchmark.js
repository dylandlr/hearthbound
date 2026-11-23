"use strict";
/**
 * Offline exporter for an existing, fully checked Forge acceptance RCON log.
 * Does not authenticate arbitrary logs, assign citizen identities, or grade MARL.
 */
const fs=require("node:fs");
const crypto=require("node:crypto");
const {scoreCitizenParticipation}=require("./score-verified-citizen-participation.js");
const MARKER="HEARTHBOUND_BENCHMARK_RECEIPT_V1 ";
const PASS="CIVILIZATION_FOUR_CITIZEN_ACCEPTANCE_PASS ";
const TRACES="HEARTHBOUND_CITIZEN_TRACES_V1 ";
const EXPECTED={
 schema:"hearthbound.four_citizen_physical.v1",
 fixture_world:"four-citizen-colony",
 fixture_seed:"hearthbound-four-citizen-v0-3"
};
function verifyReceipt(log,{workflowRunId,commit}={}){
 if(typeof log!=="string"||!log)throw Error("missing log");
 if(typeof workflowRunId!=="string"||!/^[0-9]+$/.test(workflowRunId))throw Error("workflow run ID required");
 if(typeof commit!=="string"||!/^[0-9a-f]{40}$/i.test(commit))throw Error("40-character source commit required");
 const lines=log.split(/\r?\n/), receipts=lines.filter(line=>line.startsWith(MARKER));
 const passes=lines.filter(line=>line.startsWith(PASS));
 if(receipts.length!==1||passes.length!==1)throw Error("exactly one success and one receipt required");
 const traceLines=lines.filter(line=>line.startsWith(TRACES));
 if(traceLines.length!==1)throw Error("exactly one citizen trace receipt required");
 const traceIndex=lines.indexOf(traceLines[0]);
 if(traceIndex>=lines.indexOf(passes[0]))throw Error("citizen traces must precede final acceptance");
 let trace;
 try{trace=JSON.parse(traceLines[0].slice(TRACES.length))}
 catch{throw Error("invalid citizen trace JSON")}
 if(!trace||trace.schema!=="hearthbound.citizen_decisions.v1"
    ||trace.count!==4||!Array.isArray(trace.entries)||trace.entries.length!==4
    ||trace.scope!=="LOADED_LATEST_CITIZEN_MEMORY_AND_PHYSICAL_JOB"
    ||trace.policy!=="DETERMINISTIC_TRAIT_RANK_V1"
    ||trace.learning_authorized!==false)throw Error("invalid citizen trace scope");
 const unique=["task_id","citizen","job","decision","evidence"];
 for(const field of unique){
  const values=trace.entries.map(entry=>entry[field]);
  if(new Set(values).size!==4)throw Error("duplicate citizen trace identity: "+field);
 }
 for(const t of trace.entries){
  if(!Number.isSafeInteger(t.task_id)||t.task_id<=0
      ||!Number.isSafeInteger(t.revision)||t.revision<1
      ||!["observed_tick","decision_tick","assigned_tick","delivered_tick"].every(
          field=>Number.isSafeInteger(t[field])&&t[field]>=0)
      ||t.observed_tick>t.decision_tick||t.decision_tick>t.assigned_tick
      ||t.assigned_tick>t.delivered_tick||t.assigned_tick-t.observed_tick>20
      ||!["citizen","job","decision","evidence"].every(
          field=>typeof t[field]==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(t[field])))
    throw Error("invalid citizen trace chronology or identity");
 }
 const passIndex=lines.indexOf(passes[0]),receiptIndex=lines.indexOf(receipts[0]);
 if(passIndex<0||receiptIndex<=passIndex)throw Error("out-of-order receipt");
 const expectedPass=["observed_proposals=4","physical_deliveries=4","destination_wheat=4",
 "outstanding_claims=0","scoped_citizen_decisions=4","no_reward_claim=true"];
 if(expectedPass.some(token=>!passes[0].includes(token)))throw Error("incomplete acceptance marker");
 let obj;try{obj=JSON.parse(receipts[0].slice(MARKER.length))}catch{throw Error("invalid receipt JSON")}
 if(!obj||typeof obj!=="object"||Array.isArray(obj))throw Error("invalid receipt object");
 for(const [k,v] of Object.entries(EXPECTED))if(obj[k]!==v)throw Error("wrong fixture: "+k);
 const v=obj.verification,m=obj.aggregate_milestone,l=obj.limits;
 if(!v||!m||!l||
 v.source_chests_without_original_wheat!==4||v.destination_wheat!==4||
 v.outstanding_claims!==0||v.distinct_completed_citizens!==4||
 v.scoped_citizen_decisions!==4||v.dispatch_disabled_at_end!==true||
 m.id!=="four-independent-wheat-deliveries"||m.completed!==true||
 m.physical_units!==4||m.individual_contributors!==null||
 l.individual_contribution_scores!==false||l.independent_world_replicate!==false||
 l.learned_policy!==false||l.journal_crash_atomicity!==false)
 throw Error("failed evidence or unsupported scope");
 const verified = {
  schema:"hearthbound.collaboration_evidence.v0.4",
  provenance:{workflowRunId,commit,fixtureWorld:obj.fixture_world,
   fixtureSeed:obj.fixture_seed,logSha256:crypto.createHash("sha256").update(log).digest("hex")},
  aggregate:{physicalDeliveries:4,sourceChestsEmptied:4,destinationWheat:4,distinctCitizens:4,
   scopedDecisions:4,outstandingClaims:0},
  citizenTraces:trace.entries,
  scores:{verifiedAggregateMilestoneCompletion:1,verifiedCitizenJobs:4,individualParticipation:null,
   messageEfficiency:null,politicalEmergence:null,learnedCooperation:null},
  audit:{passedLiveAcceptanceMarker:true,fromExplicitReceipt:true,
   limit:"Log-bound CI export; this offline parser cannot independently authenticate a forged RCON log or prove unobserved citizen events. Individual roles and participation beyond these four physical jobs remain unmeasured."}
 };
 verified.fixtureParticipation = scoreCitizenParticipation(verified);
 return verified;
}
function main(argv=process.argv.slice(2),env=process.env){
 if(argv.length!==2)throw Error("usage: node scripts/export-four-citizen-benchmark.js <rcon-log> <output-json>");
 const result=verifyReceipt(fs.readFileSync(argv[0],"utf8"),{
  workflowRunId:env.GITHUB_RUN_ID,commit:env.GITHUB_SHA
 });
 fs.writeFileSync(argv[1],JSON.stringify(result,null,2)+"\n",{flag:"wx"});
 console.log("HEARTHBOUND_COLLABORATION_EVIDENCE_EXPORTED "+result.provenance.logSha256);
}
if(require.main===module)main();
module.exports={verifyReceipt};
