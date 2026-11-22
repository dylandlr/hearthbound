"use strict";
// Pure research-only event projection. Not a durable Minecraft journal or authenticity proof.
const {learnWork,inferredOccupations,reviseBeliefs,discoverOrganizations}=require("./society-emergence.js");
const TYPES=new Set(["work_success","work_failure","cooperation","civic_signal"]);
function makeSociety(worldId,citizens,maxEvents=4096){
 if(typeof worldId!=="string"||!worldId||!Number.isSafeInteger(maxEvents)||maxEvents<1)throw Error("invalid scope/capacity");
 const ids=citizens.map(c=>c.id);
 if(ids.some(id=>typeof id!=="string"||!id)||new Set(ids).size!==ids.length)throw Error("invalid citizen identity");
 return {worldId,maxEvents,initial:structuredClone(citizens),events:[]};
}
function projectSociety(state,{nowTick=Infinity,cooperationWindow=24000}={}){
 const agents=new Map(state.initial.map(c=>[c.id,structuredClone(c)]));
 const half=new Map(),pairs=[];
 const sorted=[...state.events].sort((a,b)=>a.tick-b.tick||a.eventId.localeCompare(b.eventId));
 for(const e of sorted){
  if(e.tick>nowTick)continue;
  const citizen=agents.get(e.citizenId);
  if(e.kind==="work_success"||e.kind==="work_failure"){
   const job={id:e.jobId,domain:e.domain};
   agents.set(e.citizenId,learnWork(citizen,job,{evidenceId:e.eventId,verifiedSuccess:e.kind==="work_success",verifiedFailure:e.kind==="work_failure"}));
  }else if(e.kind==="civic_signal"){
   agents.set(e.citizenId,reviseBeliefs(citizen,[{evidenceId:e.eventId,topic:e.topic,value:e.value,reliability:e.reliability}]));
  }else if(e.kind==="cooperation"&&e.tick>=nowTick-cooperationWindow){
   const key=e.transactionId;
   if(!half.has(key))half.set(key,[]);
   half.get(key).push(e);
  }
 }
 for(const [transactionId,receipts] of half){
  if(receipts.length!==2)continue;
  const [a,b]=receipts;
  if(a.citizenId===b.partnerId&&b.citizenId===a.partnerId&&a.domain===b.domain&&a.citizenId!==b.citizenId){
   pairs.push({a:a.citizenId,b:b.citizenId,domain:a.domain,verified:true,evidenceId:transactionId});
  }
 }
 // Distinct transactions are counted once; duplicate receipts do not amplify groups.
 const organizations=discoverOrganizations([...agents.values()],pairs);
 const occupations=Object.fromEntries([...agents].map(([id,c])=>[id,inferredOccupations(c)]));
 return {citizens:[...agents.values()].sort((a,b)=>a.id.localeCompare(b.id)),occupations,organizations,cooperations:pairs};
}
function acceptSocietyEvent(state,event){
 const e=structuredClone(event);
 if(!e||e.worldId!==state.worldId||!TYPES.has(e.kind)||typeof e.eventId!=="string"||!e.eventId||
 !Number.isSafeInteger(e.tick)||e.tick<0||typeof e.citizenId!=="string"||
 !state.initial.some(c=>c.id===e.citizenId)||e.verified!==true)throw Error("invalid or unverified evidence");
 if(state.events.some(x=>x.eventId===e.eventId)){
  const prior=state.events.find(x=>x.eventId===e.eventId);
  if(JSON.stringify(prior)!==JSON.stringify(e))throw Error("conflicting replay");
  return state;
 }
 if(state.events.length>=state.maxEvents)throw Error("evidence capacity reached: persist externally or halt");
 if(state.events.length&&e.tick<state.events[state.events.length-1].tick)throw Error("out of order evidence");
 if(e.kind.startsWith("work_")){
  if(typeof e.jobId!=="string"||!e.jobId||typeof e.domain!=="string"||!e.domain)throw Error("invalid work evidence");
 }else if(e.kind==="cooperation"){
  if(typeof e.transactionId!=="string"||!e.transactionId||typeof e.partnerId!=="string"||
    e.citizenId===e.partnerId||!state.initial.some(c=>c.id===e.partnerId)||
    typeof e.domain!=="string"||!e.domain)throw Error("invalid joint evidence");
  const receipts=state.events.filter(x=>x.kind==="cooperation"&&x.transactionId===e.transactionId);
  if(receipts.some(x=>x.citizenId===e.citizenId)||receipts.length>=2||
    receipts.some(x=>x.domain!==e.domain||x.partnerId!==e.citizenId||x.citizenId!==e.partnerId))throw Error("conflicting joint receipts");
 }else if(e.kind==="civic_signal"){
  if(typeof e.topic!=="string"||!Number.isFinite(e.value)||e.value< -1||e.value>1||
    !Number.isFinite(e.reliability)||e.reliability<0||e.reliability>1)throw Error("invalid civic signal");
 }
 // This adapter cannot authenticate inputs; it accepts only receipts authenticated by its caller.
 return {...state,events:[...state.events,e]};
}
module.exports={makeSociety,acceptSocietyEvent,projectSociety};
