"use strict";
const assert=require("node:assert/strict");
const {evaluateCollaboration,allowedEdge}=require("./marble-collaboration-bench");
const base={worldId:"w",runId:"r",agents:["a","b","c","d"],milestones:["source","haul","mill","deliver"],mode:"chain"};
const event=(id,tick,type,fields={})=>({id,tick,type,worldId:"w",runId:"r",...fields});
const ok=(id,tick,milestone,contributors)=>event(id,tick,"milestone",{verified:true,status:"completed",milestone,contributors});
const fail=(id,tick,milestone)=>event(id,tick,"milestone",{verified:true,status:"failed",milestone,contributors:[]});
const episode={...base,events:[
 event("m1",1,"message",{from:"a",to:"b"}),
 event("bad",2,"message",{from:"a",to:"d"}),
 ok("p1",3,"source",["a"]),
 ok("p2",4,"haul",["b","c"]),
 fail("p3",5,"mill"),
 event("self",6,"milestone",{verified:false,milestone:"deliver",status:"completed",contributors:["a"]}),
 ok("p4",7,"deliver",["d"]),
 ok("p4",7,"deliver",["d"])
]};
const s=evaluateCollaboration(episode);
assert.equal(s.completed,3);assert.equal(s.failed,1);
assert.equal(s.completionRate,0.75);
assert.equal(s.participationKpi,4/16);
assert.equal(s.participants,4);
assert.equal(s.validMessages,1);assert.equal(s.blockedMessages,1);
assert.equal(s.diagnostics.verification_gap,1);assert.equal(s.diagnostics.duplicateEvents,1);
assert.equal(s.diagnostics.invalidEvidence,1);
assert.equal(s.agentContributions.b,1);
assert.equal(evaluateCollaboration({...episode,agents:["a","b","c","d","e"]}).completionRate,0.75);
assert.equal(evaluateCollaboration({...episode,agents:["a","b","c","d","e"]}).participationKpi,4/20);
assert.equal(allowedEdge("a","d",base.agents,"graph",{}),true);
assert.equal(allowedEdge("a","d",base.agents,"chain",{}),false);
assert.equal(allowedEdge("a","d",base.agents,"star",{}),true);
assert.equal(allowedEdge("b","d",base.agents,"star",{}),false);
assert.equal(allowedEdge("b","a",base.agents,"tree",{b:"a",c:"a",d:"c"}),true);
assert.equal(allowedEdge("b","d",base.agents,"tree",{b:"a",c:"a",d:"c"}),false);
assert.throws(()=>evaluateCollaboration({...episode,events:[...episode.events,event("p4",8,"milestone",{verified:true,status:"failed",milestone:"deliver",contributors:[]})]}),/conflicting evidence replay/);
assert.throws(()=>evaluateCollaboration({...episode,events:[event("foreign",0,"message",{from:"a",to:"b",worldId:"other"})]}),/foreign episode/);
assert.throws(()=>evaluateCollaboration({...episode,events:[ok("p",0,"source",["outsider"])]}),/contributor/);
assert.equal(evaluateCollaboration({...episode,events:[]}).completionRate,0);
assert.equal(evaluateCollaboration({...episode,events:[]}).participationKpi,0);
assert.equal(evaluateCollaboration({...episode,events:[ok("x",0,"source",["a"]),ok("y",1,"source",["b"])]}).diagnostics.duplicate_milestone,1);
console.log("MARBLE-inspired collaboration benchmark: 24 assertions passed");
