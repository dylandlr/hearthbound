// Hearthbound society experiment. Pure, optional; not a Forge runtime controller.
// Caller owns authoritative observations and verified evidence.
function clamp(x,lo=0,hi=1){return Math.max(lo,Math.min(hi,x))}

function selectWork(agent,jobs,world){
 return jobs.filter(j=>j.available&&j.inputsReady&&(!j.requiredSkill||(agent.skill[j.requiredSkill]||0)>=(j.minimumSkill||0)))
 .map(j=>({...j,utility:1.7*clamp((world.demand[j.output]||0)/(world.demandScale||1))+0.9*(agent.skill[j.domain]||0)+0.8*(agent.interest[j.domain]||0)+1.2*(agent.needs[j.satisfies]||0)+0.4*(j.socialBenefit||0)-1.1*(j.risk||0)*(1-(agent.traits.riskTolerance||0))-0.2*(j.travel||0)}))
 .sort((a,b)=>b.utility-a.utility||a.id.localeCompare(b.id));
}

function learnWork(agent,job,outcome){
 const skill={...agent.skill},interest={...agent.interest},history=[...(agent.history||[])];
 if(outcome.evidenceId&&(outcome.verifiedSuccess||outcome.verifiedFailure)&&!history.some(h=>h.evidenceId===outcome.evidenceId)){
 skill[job.domain]=clamp((skill[job.domain]||0)+(outcome.verifiedSuccess?0.05:0.01));
 interest[job.domain]=clamp((interest[job.domain]||0)+(outcome.verifiedSuccess?0.015:-0.01));
 history.push({jobId:job.id,domain:job.domain,success:!!outcome.verifiedSuccess,evidenceId:outcome.evidenceId});
 }
 return {...agent,skill,interest,history};
}

function inferredOccupations(agent,minimum=3){
 const n={};for(const h of agent.history||[])if(h.success)n[h.domain]=(n[h.domain]||0)+1;
 return Object.entries(n).filter(([_,v])=>v>=minimum).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([domain,completed])=>({domain,completed}));
}

function reviseBeliefs(agent,signals){
 const beliefs={...agent.beliefs},seen=new Set(agent.seenEvidence||[]);
 for(const s of signals){
 if(!s.evidenceId||seen.has(s.evidenceId)||!Object.hasOwn(beliefs,s.topic)||![s.value,s.reliability].every(Number.isFinite)||s.reliability<0||s.reliability>1)continue;
 const strength=clamp((agent.traits.openness??0.5)*s.reliability*0.2);
 beliefs[s.topic]=clamp(beliefs[s.topic]+strength*(clamp(s.value,-1,1)-beliefs[s.topic]),-1,1);seen.add(s.evidenceId);
 }
 return {...agent,beliefs,seenEvidence:[...seen]};
}

function discoverOrganizations(agents,cooperations,{minimum=2,affinity=0.65}={}){
 const byId=new Map(agents.map(a=>[a.id,a])),counts=new Map();
 for(const c of cooperations){
 if(!c.verified||c.a===c.b||!byId.has(c.a)||!byId.has(c.b)||!c.evidenceId)continue;
 const ids=[c.a,c.b].sort(),key=`${ids.join("|")}:${c.domain}`,e=counts.get(key)||{ids,domain:c.domain,evidence:new Set()};
 e.evidence.add(c.evidenceId);counts.set(key,e);
 }
 const edges=[...counts.values()].filter(e=>e.evidence.size>=minimum&&e.ids.every(id=>(byId.get(id).interest[e.domain]||0)>=affinity));
 const result=[];
 for(const domain of [...new Set(edges.map(e=>e.domain))].sort()){
 const parent=new Map(agents.map(a=>[a.id,a.id]));
 function find(x){while(parent.get(x)!==x)x=parent.get(x);return x}
 for(const e of edges.filter(e=>e.domain===domain)){const x=find(e.ids[0]),y=find(e.ids[1]);if(x!==y)parent.set(x<y?y:x,x<y?x:y)}
 const members=new Map();
 for(const a of agents){const r=find(a.id);if(!members.has(r))members.set(r,[]);members.get(r).push(a.id)}
 for(const group of members.values())if(group.length>1)result.push({id:`${domain}:${group.sort().join("+")}`,focus:domain,members:group});
 }
 return result.sort((a,b)=>a.id.localeCompare(b.id));
}

function preferenceBallot(agents,proposals,quorum=0.5){
 const voters=agents.filter(a=>a.participates!==false);
 if(!agents.length||voters.length/agents.length<quorum)return null;
 return proposals.map(p=>({id:p.id,score:voters.reduce((acc,a)=>acc+(a.beliefs[p.topic]||0)*p.direction,0),votes:voters.length})).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id))[0]||null;
}
module.exports={clamp,selectWork,learnWork,inferredOccupations,reviseBeliefs,discoverOrganizations,preferenceBallot};
