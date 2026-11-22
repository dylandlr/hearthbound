"use strict";
// PA4 + MARBLE methodological contract. Offline only; never controls Minecraft.
const {evaluateCollaboration}=require("./marble-collaboration-bench");
function insist(ok,message){if(!ok)throw new Error(message);}
function finiteNumber(n){return typeof n==="number"&&Number.isFinite(n);}
function nonnegativeInt(n){return Number.isSafeInteger(n)&&n>=0;}
function episodeRecord(input){
 const {seed,scenario,variant,policyVersion,sourceCommit,protocolHash,worldHash,durationTicks,computeBudget,
        outcome,independentEvidence} = input;
 insist(nonnegativeInt(seed),"seed must be a nonnegative integer");
 for(const [name,value] of Object.entries({scenario,variant,policyVersion,sourceCommit,protocolHash,worldHash})){
   insist(typeof value==="string"&&value.length>0, "missing provenance: "+name);
 }
 insist(nonnegativeInt(durationTicks)&&durationTicks>0,"invalid tick horizon");
 insist(nonnegativeInt(computeBudget)&&computeBudget>0,"invalid compute budget");
 insist(independentEvidence===true,"independent evidence attestation required");
 insist(outcome&&nonnegativeInt(outcome.physicalOutputs)&&nonnegativeInt(outcome.conservationViolations),
        "missing physical output/conservation evidence");
 insist(nonnegativeInt(outcome.actionCount)&&nonnegativeInt(outcome.elapsedTicks),"missing actions/ticks");
 insist(outcome.elapsedTicks<=durationTicks,"elapsed ticks exceed horizon");
 insist(Array.isArray(input.events),"missing event stream");
 const score=evaluateCollaboration(input);
 return Object.freeze({
   scenario,seed,variant,policyVersion,sourceCommit,protocolHash,worldHash,durationTicks,computeBudget,
   physicalOutputs:outcome.physicalOutputs,conservationViolations:outcome.conservationViolations,
   actionCount:outcome.actionCount,elapsedTicks:outcome.elapsedTicks,score
 });
}
function pairRecords(a,b){
 insist(a.variant!==b.variant,"treatments must differ");
 const fields=["scenario","seed","worldHash","durationTicks","computeBudget","protocolHash"];
 for(const key of fields)insist(a[key]===b[key],"unmatched pair: "+key);
 insist(a.conservationViolations===0&&b.conservationViolations===0,"conservation violation blocks comparison");
 return {
   scenario:a.scenario,seed:a.seed,
   completionDelta:b.score.completionRate-a.score.completionRate,
   outputDelta:b.physicalOutputs-a.physicalOutputs,
   messagesDelta:b.score.messages-a.score.messages,
   participationDelta:b.score.participationKpi-a.score.participationKpi,
   failureDelta:b.score.failed-a.score.failed,
   blockedMessagesDelta:b.score.blockedMessages-a.score.blockedMessages,
   actionDelta:b.actionCount-a.actionCount,
   ticksDelta:b.elapsedTicks-a.elapsedTicks,
   baseline:a.variant,treatment:b.variant
 };
}
function mean(xs){return xs.reduce((a,b)=>a+b,0)/xs.length}
function quantile(sorted,q){
 const x=(sorted.length-1)*q,i=Math.floor(x),part=x-i;
 return sorted[i]*(1-part)+(sorted[Math.min(i+1,sorted.length-1)]||0)*part;
}
function clusterBootstrap(values,{replicates=2000,seed=17}={}){
 insist(values.length>0&&values.every(finiteNumber),"finite nonempty samples required");
 insist(Number.isSafeInteger(replicates)&&replicates>=100&&replicates<=100000,"invalid bootstrap size");
 insist(nonnegativeInt(seed)&&seed<=0xffffffff,"invalid bootstrap seed");
 let state=seed>>>0;
 const random=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296};
 const stats=[];
 for(let k=0;k<replicates;k++){let total=0;for(let j=0;j<values.length;j++)total+=values[Math.floor(random()*values.length)];stats.push(total/values.length)}
 stats.sort((a,b)=>a-b);
 return {mean:mean(values),lower:quantile(stats,0.025),upper:quantile(stats,0.975),
         replicates,unit:"independent world seed",intervalType:"descriptive percentile bootstrap"};
}
function compareMatchedWorlds(baseline,treatment,opts={}){
 insist(Array.isArray(baseline)&&Array.isArray(treatment)&&baseline.length>0,
        "missing run-level evidence");
 function index(records){
   const map=new Map();
   for(const record of records){
     insist(record&&nonnegativeInt(record.seed)&&typeof record.scenario==="string","invalid record");
     const key=record.scenario+"::"+record.seed;
     insist(!map.has(key),"duplicate world-seed replicate: "+key);
     map.set(key,record);
   }
   return map;
 }
 const A=index(baseline),B=index(treatment);
 insist(A.size===B.size,"different independent-world counts");
 const keys=[...A.keys()].sort();
 insist(keys.every(key=>B.has(key)),"missing matched worlds");
 const paired=keys.map(k=>pairRecords(A.get(k),B.get(k)));
 const measures=["completionDelta","outputDelta","messagesDelta","participationDelta",
                 "failureDelta","blockedMessagesDelta","actionDelta","ticksDelta"];
 const estimates={};
 for(const key of measures)estimates[key]=clusterBootstrap(paired.map(row=>row[key]),opts);
 return {
   baseline:paired[0].baseline,treatment:paired[0].treatment,worldReplicates:paired.length,
   paired,estimates,warning:"Intervals are descriptive; no statistical significance, equilibrium, or generalization claim."
 };
}
module.exports={episodeRecord,pairRecords,clusterBootstrap,compareMatchedWorlds};
