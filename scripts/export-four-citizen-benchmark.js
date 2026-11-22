"use strict";
/**
 * Offline exporter for an existing, fully checked Forge acceptance RCON log.
 * Does not authenticate arbitrary logs, assign citizen identities, or grade MARL.
 */
const fs=require("node:fs");
const crypto=require("node:crypto");
const MARKER="HEARTHBOUND_BENCHMARK_RECEIPT_V1 ";
const PASS="CIVILIZATION_FOUR_CITIZEN_ACCEPTANCE_PASS ";
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
 return {
  schema:"hearthbound.collaboration_evidence.v0.3",
  provenance:{workflowRunId,commit,fixtureWorld:obj.fixture_world,
   fixtureSeed:obj.fixture_seed,logSha256:crypto.createHash("sha256").update(log).digest("hex")},
  aggregate:{physicalDeliveries:4,sourceChestsEmptied:4,destinationWheat:4,distinctCitizens:4,
   scopedDecisions:4,outstandingClaims:0},
  scores:{verifiedAggregateMilestoneCompletion:1,individualParticipation:null,
   messageEfficiency:null,politicalEmergence:null,learnedCooperation:null},
  audit:{passedLiveAcceptanceMarker:true,fromExplicitReceipt:true,
   limit:"Log-bound CI export; this offline parser cannot independently authenticate a forged RCON log or assign per-citizen outcomes."}
 };
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
