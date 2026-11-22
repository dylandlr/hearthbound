"use strict";
/* MARBLE-inspired, NOT MARBLE-equivalent. Offline evidence-only Hearthbound evaluator. */
const MODES=new Set(["star","tree","graph","chain"]);
function requireValid(v,msg){if(!v)throw new Error(msg);}
function allowedEdge(from,to,ids,mode,parent){
 if(from===to)return false;
 const a=ids.indexOf(from),b=ids.indexOf(to);
 if(mode==="graph")return true;
 if(mode==="chain")return Math.abs(a-b)===1;
 if(mode==="star")return a===0||b===0;
 return parent[from]===to||parent[to]===from;
}
function evaluateCollaboration({worldId,runId,agents,milestones,events,mode="graph",parent={},maxTicks=Infinity}){
 requireValid(typeof worldId==="string"&&worldId&&typeof runId==="string"&&runId,"scope required");
 requireValid(MODES.has(mode),"unknown topology");
 requireValid(Array.isArray(agents)&&agents.length>0&&new Set(agents).size===agents.length&&agents.every(x=>typeof x==="string"&&x),"invalid agents");
 requireValid(Array.isArray(milestones)&&milestones.length>0&&new Set(milestones).size===milestones.length,"invalid milestones");
 requireValid(Array.isArray(events),"events required");
 requireValid(maxTicks===Infinity||(Number.isSafeInteger(maxTicks)&&maxTicks>=0),"bad horizon");
 const agentSet=new Set(agents),milestoneSet=new Set(milestones),seen=new Map(),outcomes=new Map();
 const attempts={messages:0,validMessages:0,blockedMessages:0,duplicateEvents:0,invalidEvidence:0,failedMilestones:0};
 const errors={verification_gap:0,communication_block:0,conflicting_replay:0,duplicate_milestone:0};
 let lastTick=-1;
 for(const e of events){
   requireValid(e&&typeof e==="object"&&typeof e.id==="string"&&e.id&&Number.isSafeInteger(e.tick)&&e.tick>=0,"malformed event");
   requireValid(e.worldId===worldId&&e.runId===runId,"foreign episode event");
   if(seen.has(e.id)){
     if(JSON.stringify(seen.get(e.id))!==JSON.stringify(e)) {errors.conflicting_replay++;throw new Error("conflicting evidence replay")}
     attempts.duplicateEvents++;continue;
   }
   requireValid(e.tick>=lastTick,"event order violation");
   lastTick=e.tick;seen.set(e.id,e);
   if(e.tick>maxTicks)continue;
   if(e.type==="message"){
     attempts.messages++;
     if(!agentSet.has(e.from)||!agentSet.has(e.to)||!allowedEdge(e.from,e.to,agents,mode,parent)){
       attempts.blockedMessages++;errors.communication_block++;continue;
     }
     attempts.validMessages++;continue;
   }
   if(e.type==="milestone"){
     requireValid(milestoneSet.has(e.milestone),"unknown milestone");
     if(e.verified!==true){attempts.invalidEvidence++;errors.verification_gap++;continue;}
     requireValid(e.status==="completed"||e.status==="failed","invalid outcome");
     requireValid(Array.isArray(e.contributors)&&new Set(e.contributors).size===e.contributors.length&&e.contributors.every(a=>agentSet.has(a)),"invalid contributor identities");
     if(outcomes.has(e.milestone)){
       attempts.invalidEvidence++;errors.duplicate_milestone++;continue;
     }
     outcomes.set(e.milestone,e);
     if(e.status==="failed")attempts.failedMilestones++;
   }else throw new Error("unknown event type");
 }
 const completed=[...outcomes.values()].filter(e=>e.status==="completed");
 const byAgent=Object.fromEntries(agents.map(a=>[a,0]));
 for(const e of completed)for(const a of e.contributors)byAgent[a]++;
 const credited=Object.values(byAgent).reduce((x,y)=>x+y,0);
 const total=milestones.length,number=agents.length;
 return {
   worldId,runId,mode,agents:number,milestones:total,
   completionRate:completed.length/total,
   completed:completed.length,
   failed:attempts.failedMilestones,
   unresolved:total-outcomes.size,
   participationKpi:credited/(number*total), // exact MARBLE-style formula with trusted contributors
   participants:agents.filter(a=>byAgent[a]>0).length,
   creditedIncidences:credited,
   agentContributions:byAgent,
   messages:attempts.messages,
   validMessages:attempts.validMessages,
   blockedMessages:attempts.blockedMessages,
   messageCostPerCompleted:completed.length?attempts.messages/completed.length:null,
   diagnostics:{...attempts,...errors},
   // This intentionally omits MARBLE's LLM judge communication and planning scores.
   // Those would require separate human validation and are not ground truth.
   scoreVersion:"hearthbound-marble-adaptation-v0.1"
 };
}
module.exports={allowedEdge,evaluateCollaboration};
