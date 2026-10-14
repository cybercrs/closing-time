import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {DATA} from '../content.js';
import {Lesson,GROUPS,POSITIONS,newState,parseSnapshotJSON,validateSnapshot,encodeState,decodeState,
  evaluateSimple,evaluateAccount,evaluateStatements,adjustedBalances,statementValues,balanceRows,equationCheck,
  scoreSummary,shuffledOptions,frontier,canonicalJSON} from '../engine.js';
const oracle=JSON.parse(readFileSync(new URL('./python-oracles.json',import.meta.url)));
const legacy=JSON.parse(readFileSync(new URL('./legacy-links.json',import.meta.url)));
function chooseCorrect(lesson) {
  if(lesson.state.s===4) {
    DATA.statements.forEach(item=>lesson.draft(item.id,item.correct));
  }else if(lesson.state.s===3) {
    lesson.draft(lesson.item.id,lesson.item.correct_effect,'effect');lesson.draft(lesson.item.id,lesson.item.correct_omission,'omission');
  }else lesson.draft(lesson.item.id,lesson.state.s===2?lesson.item.classification:lesson.item.correct);
}
function complete() {
  const lesson=new Lesson(newState(9223372036854775807n));assert.equal(lesson.advance(),true);
  while(!lesson.complete) {
    chooseCorrect(lesson);assert.equal(lesson.submit(),true);
    if(!lesson.complete)assert.equal(lesson.advance(),true);
  }return lesson;
}
test('all adjusted accounts, statements, equations and formatted comparison rows equal Python',()=>{
  assert.deepEqual(adjustedBalances(),oracle.adjusted);assert.deepEqual(statementValues(),oracle.statements);
  assert.deepEqual(statementValues(DATA.unadjusted),oracle.before);assert.deepEqual(balanceRows(),oracle.rows);
  assert.deepEqual(equationCheck(),oracle.equation);
});
test('all 92 original answer/paired-account evaluations match independent Python outcomes',()=>{
  assert.equal(oracle.evaluations.length,92);
  for(const fixture of oracle.evaluations)
    assert.deepEqual(fixture.group==='account'?evaluateAccount(fixture.id,fixture.answer):evaluateSimple(fixture.group,fixture.id,fixture.answer),fixture.result);
  const statements=Object.fromEntries(DATA.statements.map(item=>[item.id,item.correct]));
  assert.equal(Object.values(evaluateStatements(statements)).every(result=>result.correct),true);
});
test('sixty original saved states retain every answer, draft, first-pass value, position and exact 63-bit seed',async()=>{
  for(const fixture of oracle.snapshots) {
    const expected=parseSnapshotJSON(fixture.wire),decoded=await decodeState(fixture.token);
    assert.deepEqual(decoded,expected);assert.deepEqual(scoreSummary(decoded),fixture.score);
    assert.deepEqual(await decodeState(await encodeState(decoded)),decoded);
  }
  for(const fixture of legacy)assert.deepEqual(await decodeState(fixture.token),parseSnapshotJSON(fixture.wire));
});
test('ordinary native v4 links are accepted by unchanged Python without seed precision loss',async()=>{
  const state=complete().state,token=await encodeState(state);
  const result=spawnSync(process.env.PYTHON??'python3',['-c',
    'import json,sys;from closing_time.progress import decode_snapshot,snapshot_from_state;print(json.dumps(snapshot_from_state(decode_snapshot(sys.argv[1])),sort_keys=True))',token],
    {cwd:new URL('../../',import.meta.url),encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);assert.deepEqual(parseSnapshotJSON(result.stdout),state);
  assert.equal(state.z,9223372036854775807n);
});
test('all forty SHA-256/CPython shuffled account orders match, including seeds above Number safe range',async()=>{
  for(const fixture of oracle.shuffles)
    assert.deepEqual(await shuffledOptions(fixture.input,BigInt(fixture.seed),fixture.salt),fixture.output);
});
test('a full perfect close reaches inline final mastery with all original 21 checkpoints',()=>{
  const lesson=complete();assert.equal(frontier(lesson.state),19);assert.equal(lesson.complete,true);
  assert.deepEqual(scoreSummary(lesson.state),{correct:21,attempted:21,total:21,revisions:0});
  assert.equal(lesson.advance(),false);assert.equal(lesson.submit(),false);
});
test('wrong simple and paired-account revisions preserve first pass and count every original practice check',()=>{
  const lesson=new Lesson();lesson.advance();
  const item=lesson.item,wrong=item.options.find(value=>value!==item.correct);
  assert.equal(lesson.advance(),false);assert.equal(lesson.submit(),false);
  lesson.draft(item.id,wrong);lesson.submit();lesson.submit();
  assert.equal(lesson.state.at['recognition:'+item.id],2);assert.equal(lesson.state.fp['recognition:'+item.id],false);
  chooseCorrect(lesson);lesson.submit();assert.equal(lesson.state.at['recognition:'+item.id],3);assert.equal(lesson.advance(),true);
  const accountState=parseSnapshotJSON(oracle.snapshots.find(entry=>entry.position.stage===3&&entry.position.index===0&&entry.status==='unanswered').wire);
  const account=new Lesson(accountState);
  account.draft(account.item.id,account.item.effect_options.find(value=>value!==account.item.correct_effect),'effect');
  account.draft(account.item.id,account.item.correct_omission,'omission');account.submit();
  chooseCorrect(account);account.submit();
  assert.equal(account.state.at['account:'+account.item.id],2);assert.equal(account.state.fp['account:'+account.item.id],false);
});
test('statement resubmission counts only changed answers, with correct fields retaining their first-pass flags',()=>{
  const fixture=oracle.snapshots.find(entry=>entry.position.stage===4&&entry.status==='unanswered');
  const lesson=new Lesson(parseSnapshotJSON(fixture.wire));
  for(const [index,item] of DATA.statements.entries())lesson.draft(item.id,index===0?item.options.find(value=>value!==item.correct):item.correct);
  lesson.submit();const before={...lesson.state.at};lesson.submit();assert.deepEqual(lesson.state.at,before);
  const item=DATA.statements[0];lesson.draft(item.id,item.correct);lesson.submit();
  assert.equal(lesson.state.at['statement:'+item.id],2);assert.equal(lesson.state.fp['statement:'+item.id],false);
  for(const item of DATA.statements.slice(1))assert.equal(lesson.state.at['statement:'+item.id],1);
  assert.equal(lesson.advance(),true);
});
test('every reached page is readonly, hidden future views clamp, and review never changes answers/attempts/scoring',()=>{
  const lesson=complete(),before=canonicalJSON(lesson.state);
  for(let view=18;view>=0;view--) {
    assert.equal(lesson.move(-1),true);assert.equal(lesson.view,view);
    for(const method of ['submit','advance','reset'])assert.equal(lesson[method](),false);
    assert.equal(lesson.draft(GROUPS[0].items[0].id,'$0'),false);
    assert.equal(canonicalJSON(lesson.state),before);
  }
  for(let view=1;view<=19;view++){assert.equal(lesson.move(1),true);assert.equal(lesson.view,view);}
  assert.equal(lesson.move(1),false);assert.equal(canonicalJSON(lesson.state),before);
  for(const view of ['999','-1','x','2.5'])assert.equal(new Lesson(lesson.state,view).view,19);
});
test('draft bookmarks preserve selected revision values without submitting or advancing',async()=>{
  const lesson=new Lesson();lesson.advance();const item=lesson.item;lesson.draft(item.id,item.correct);
  const restored=new Lesson(await decodeState(await encodeState(lesson.state)));
  assert.equal(restored.state.dr.r[item.id],item.correct);assert.deepEqual(restored.state.rr,{});
  assert.equal(frontier(restored.state),1);assert.equal(restored.move(1),false);
});
test('practice beyond the legacy 99-attempt limit upgrades only overflow links and restores full score history',async()=>{
  const lesson=new Lesson(newState(1n));lesson.advance();const item=lesson.item;
  lesson.draft(item.id,item.options.find(value=>value!==item.correct));
  for(let n=0;n<99;n++)assert.equal(lesson.submit(),true);
  assert.equal(lesson.state.v,4);assert.ok(await decodeState(await encodeState(lesson.state)));
  lesson.submit();assert.equal(lesson.state.v,5);assert.equal(lesson.state.at['recognition:'+item.id],100);
  const restored=await decodeState(await encodeState(lesson.state));
  assert.equal(restored.v,5);assert.equal(restored.at['recognition:'+item.id],100);assert.equal(scoreSummary(restored).revisions,99);
  assert.equal(restored.fp['recognition:'+item.id],false);
});
test('malformed indexes, future drafts, unknown accounts/options, wrong gates and invalid seeds are rejected',async()=>{
  for(const token of [null,'','bad!','a'.repeat(16001)])assert.equal(await decodeState(token),null);
  const seed=newState();seed.z=2n**63n;assert.throws(()=>validateSnapshot(seed));
  const future=newState();future.dr.i[GROUPS.find(group=>group.stage===5).items[0].id]='bad';assert.throws(()=>validateSnapshot(future));
  const skip=newState();skip.s=5;assert.throws(()=>validateSnapshot(skip));
  const history=newState();history.at['unknown']=1;assert.throws(()=>validateSnapshot(history));
  assert.throws(()=>parseSnapshotJSON('{"z":"42"}'));assert.throws(()=>parseSnapshotJSON('{"z":1.5}'));
});
test('reset and independent instances retain copied completed bookmarks',async()=>{
  const first=complete(),token=await encodeState(first.state),other=new Lesson();first.reset();
  assert.equal(first.state.s,0);assert.equal(other.state.s,0);assert.equal(new Lesson(await decodeState(token)).complete,true);
  assert.equal(first.state.v,4);
});
test('all sixty teaching variants, feedback, case metadata and page titles contain no provisional branding',()=>{
  const walk=value=>{
    if(Array.isArray(value))return value.forEach(walk);
    if(value&&typeof value==='object')for(const [key,item] of Object.entries(value)){
      if(['text','label','help','prompt','story','explanation'].includes(key)&&typeof item==='string')
        assert.doesNotMatch(item,/\b(?:pilot|preview|test(?:ing)?\s+(?:app|version|site))\b/i);
      else walk(item);
    }
  };walk(DATA);assert.equal(DATA.title,'Closing Time');assert.equal(POSITIONS.length,20);
});
