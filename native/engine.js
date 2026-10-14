/** Closing Time's original accounts, first-pass practice, gates and saved-state schema. */
import {DATA} from './content.js';
import {assert,object,exact,int,copy,canonicalJSON,encodeJSON,decodeJSON,PythonRandom,currency} from './shared.js';
export {copy,canonicalJSON,currency,pyFixed} from './shared.js';
export const GROUPS=DATA.groups;
export const POSITIONS=DATA.positions;
const own=(value,key)=>Object.hasOwn(value,key);
const groupAt=stage=>GROUPS.find(group=>group.stage===stage);
export function newState(seed) {
  if(seed===undefined){const words=crypto.getRandomValues(new Uint32Array(2));seed=(BigInt(words[0]&0x7fffffff)<<32n)|BigInt(words[1]);}
  return {v:4,s:0,z:BigInt(seed),dr:{r:{},c:{},a:{},s:{},i:{}},ri:0,rr:{},ci:0,cr:{},ai:0,ar:{},
    sr:{},ss:false,ii:0,ir:{},at:{},fp:{}};
}
const optionsFor=(group,item)=>group.prefix==='classification'?DATA.classificationOptions:item.options;
const correctFor=(group,item)=>group.prefix==='classification'?item.classification:item.correct;
export function evaluateSimple(groupName,id,selected) {
  const group=GROUPS.find(group=>group.prefix===groupName),item=group.items.find(item=>item.id===id);
  const result={correct:selected===correctFor(group,item),selected,expected:correctFor(group,item),explanation:item.explanation};
  if(groupName==='integrity')result.statement_effect=item.statement_effect;
  return result;
}
export function evaluateAccount(id,answer) {
  const item=groupAt(3).items.find(item=>item.id===id),checks={effect:answer.effect===item.correct_effect,omission:answer.omission===item.correct_omission};
  return {correct:Object.values(checks).every(Boolean),checks,expected:{effect:item.correct_effect,omission:item.correct_omission},explanation:item.explanation};
}
export function evaluateStatements(answers) {
  return Object.fromEntries(DATA.statements.map(item=>[item.id,{label:item.prompt,submitted:answers[item.id]??'',expected:item.correct,
    correct:answers[item.id]===item.correct,explanation:item.explanation}]));
}
export function adjustedBalances() {
  const balances={...DATA.unadjusted};
  for(const item of DATA.adjustments)for(const [account,change] of item.changes)balances[account]=(balances[account]??0)+change;
  return balances;
}
export function statementValues(balances) {
  const source=balances&&Object.keys(balances).length?balances:adjustedBalances();
  const total=keys=>keys.reduce((sum,key)=>sum+(source[key]??0),0);
  const service_revenue=source['Service Revenue']??0,total_expenses=total(DATA.accountSets.expenses),net_income=service_revenue-total_expenses;
  const total_assets=total(DATA.accountSets.assets),total_liabilities=total(DATA.accountSets.liabilities),total_equity=total(DATA.accountSets.equity)+net_income;
  return {service_revenue,total_expenses,net_income,beginning_retained_earnings:0,dividends:0,ending_retained_earnings:net_income,
    total_assets,total_liabilities,total_equity,total_liabilities_equity:total_liabilities+total_equity};
}
export function balanceRows() {
  const ending=adjustedBalances();
  return Object.entries(DATA.unadjusted).map(([account,opening])=>({Account:account,Unadjusted:currency(opening),
    Change:(ending[account]-opening>0?'+':'')+currency(ending[account]-opening),Adjusted:currency(ending[account])}));
}
export function equationCheck(balances) {
  const values=statementValues(balances);
  return {assets:values.total_assets,liabilities_equity:values.total_liabilities_equity,balanced:values.total_assets===values.total_liabilities_equity};
}
export function validScoreKeys() {
  return new Set([...GROUPS.flatMap(group=>group.items.map(item=>group.prefix+':'+item.id)),...DATA.statements.map(item=>'statement:'+item.id)]);
}
export function scoreSummary(state) {
  return {correct:Object.values(state.fp).filter(Boolean).length,attempted:Object.keys(state.fp).length,total:21,
    revisions:Object.values(state.at).reduce((sum,value)=>sum+Math.max(0,value-1),0)};
}
function answerPrefix(raw,group) {
  assert(object(raw),'Invalid answer map');
  const ids=group.items.slice(0,Object.keys(raw).length).map(item=>item.id);
  assert(ids.length===Object.keys(raw).length&&ids.every(id=>own(raw,id)),'Answers must follow the activity order');
  for(const item of group.items.slice(0,ids.length)) {
    const value=raw[item.id];
    if(group.prefix==='account')assert(exact(value,['effect','omission'])&&item.effect_options.includes(value.effect)&&item.omission_options.includes(value.omission),'Invalid account answer');
    else assert(typeof value==='string'&&optionsFor(group,item).includes(value),'Unknown answer');
  }
  return copy(raw);
}
function statementAnswers(raw,submitted) {
  assert(object(raw)&&Object.keys(raw).every(id=>DATA.statements.some(item=>item.id===id)),'Unknown statement answer');
  if(submitted)assert(Object.keys(raw).length===DATA.statements.length,'Incomplete submitted statements');
  for(const [id,value] of Object.entries(raw))assert(typeof value==='string'&&DATA.statements.find(item=>item.id===id).options.includes(value),'Invalid statement answer');
  return copy(raw);
}
function drafts(raw,group,index) {
  assert(object(raw)&&Object.keys(raw).every(id=>group.items.slice(0,index+1).some(item=>item.id===id)),'Draft answers are out of sequence');
  for(const [id,value] of Object.entries(raw)) {
    const item=group.items.find(item=>item.id===id);
    if(group.prefix==='account') {
      assert(object(value)&&Object.keys(value).every(key=>['effect','omission'].includes(key)),'Invalid account draft');
      for(const [field,selected] of Object.entries(value))assert(item[field+'_options'].includes(selected),'Unknown account draft');
    }else assert(typeof value==='string'&&optionsFor(group,item).includes(value),'Unknown draft');
  }return copy(raw);
}
export function validateSnapshot(raw) {
  assert(exact(raw,['v','s','z','dr','ri','rr','ci','cr','ai','ar','sr','ss','ii','ir','at','fp'])&&[4,5].includes(raw.v),'Unsupported closing snapshot');
  assert(int(raw.s,0,5)&&typeof raw.z==='bigint'&&raw.z>=0n&&raw.z<2n**63n,'Invalid stage or exact seed');
  assert(exact(raw.dr,['r','c','a','s','i'])&&typeof raw.ss==='boolean','Invalid draft groups/status');
  const state=copy(raw);
  for(const group of GROUPS) {
    const index=raw[group.indexKey];assert(int(index,0,group.items.length-1),'Invalid activity index');
    state[group.responseKey]=answerPrefix(raw[group.responseKey],group);
    state.dr[group.draft]=drafts(raw.dr[group.draft],group,index);
    assert(raw.s>=group.stage||Object.keys(state.dr[group.draft]).length===0,'Future draft');
    const answers=state[group.responseKey],count=Object.keys(answers).length;
    for(const item of group.items.slice(0,index)) {
      const answer=answers[item.id];
      assert(group.prefix==='account'?answer&&evaluateAccount(item.id,answer).correct:answer===correctFor(group,item),'Prior answer is unresolved');
    }
    assert([index,index+1,group.items.length].includes(count),'Inconsistent activity position');
    if(raw.s>group.stage) {
      assert(count===group.items.length&&group.items.every(item=>group.prefix==='account'?evaluateAccount(item.id,answers[item.id]).correct:answers[item.id]===correctFor(group,item)),'Unresolved prior stage');
    }
  }
  state.dr.s=statementAnswers(raw.dr.s,false);assert(raw.s>=4||!Object.keys(state.dr.s).length,'Future statement draft');
  state.sr=statementAnswers(raw.sr,raw.ss);
  if(raw.s>=5)assert(raw.ss&&Object.values(evaluateStatements(raw.sr)).every(result=>result.correct),'Unresolved statements');
  assert(object(raw.at)&&object(raw.fp),'Invalid practice history');
  const valid=validScoreKeys();
  for(const [key,value] of Object.entries(raw.at))assert(valid.has(key)&&int(value,1,raw.v===4?99:Number.MAX_SAFE_INTEGER),'Invalid attempts');
  for(const [key,value] of Object.entries(raw.fp))assert(valid.has(key)&&typeof value==='boolean','Invalid first-pass history');
  return state;
}
export function parseSnapshotJSON(text) {
  assert(/"z"\s*:\s*-?\d+(?=\s*[,}])/.test(text),'Seed must be an integer');
  const replaced=text.replace(/("z"\s*:\s*)(-?\d+)(?=\s*[,}])/g,'$1"$2"'),raw=JSON.parse(replaced);
  assert(typeof raw.z==='string'&&/^\d{1,19}$/.test(raw.z),'Invalid exact seed encoding');
  raw.z=BigInt(raw.z);return validateSnapshot(raw);
}
export const encodeState=state=>encodeJSON(validateSnapshot(state),32000,16000);
export async function decodeState(token){try{return await decodeJSON(token,32000,16000,parseSnapshotJSON);}catch{return null;}}
export function frontier(state) {
  const group=groupAt(state.s);
  return POSITIONS.findIndex(position=>position.stage===state.s&&position.index===(group?state[group.indexKey]:0));
}
export async function shuffledOptions(options,seed,salt) {
  const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(seed.toString()+':'+salt)));
  let number=0n;for(const byte of bytes.slice(0,8))number=(number<<8n)|BigInt(byte);
  const rng=new PythonRandom(number),ordered=[...options];
  for(let i=ordered.length-1;i>0;i--){const j=rng.below(i+1);[ordered[i],ordered[j]]=[ordered[j],ordered[i]];}
  return ordered.length>1&&ordered.every((value,i)=>value===options[i])?[...ordered.slice(1),ordered[0]]:ordered;
}
export class Lesson {
  constructor(state=newState(),view) {
    this.state=validateSnapshot(state);const reached=frontier(this.state);
    const number=typeof view==='string'&&/^-?\d+$/.test(view)?Number(view):view;
    this.view=int(number,0,reached)?number:reached;this.error='';
  }
  get reviewing(){return this.view<frontier(this.state);}
  get position(){return POSITIONS[this.view];}
  move(direction) {
    if(![-1,1].includes(direction)||!int(this.view+direction,0,frontier(this.state)))return false;
    this.view+=direction;this.error='';return true;
  }
  get group(){return groupAt(this.state.s);}
  get item(){return this.group?this.group.items[this.state[this.group.indexKey]]:null;}
  get complete(){return this.state.s===5&&groupAt(5).items.every(item=>this.state.ir[item.id]===item.correct);}
  currentCorrect() {
    const state=this.state;
    if(state.s===0)return false;
    if(state.s===4)return state.ss&&Object.values(evaluateStatements(state.sr)).every(result=>result.correct);
    const value=state[this.group.responseKey][this.item.id];
    return value===undefined?false:this.group.prefix==='account'?evaluateAccount(this.item.id,value).correct:value===correctFor(this.group,this.item);
  }
  draft(id,value,field) {
    if(this.reviewing||this.currentCorrect()||this.state.s===0)return false;
    const state=this.state;
    if(state.s===4) {
      const item=DATA.statements.find(item=>item.id===id);
      if(!item||!item.options.includes(value))return false;state.dr.s[id]=value;
    }else {
      if(id!==this.item.id)return false;
      if(this.group.prefix==='account') {
        if(!['effect','omission'].includes(field)||!this.item[field+'_options'].includes(value))return false;
        state.dr.a[id]??={};state.dr.a[id][field]=value;
      }else {
        if(!optionsFor(this.group,this.item).includes(value))return false;state.dr[this.group.draft][id]=value;
      }
    }
    this.error='';return true;
  }
  record(key,correct) {
    const attempts=(this.state.at[key]??0)+1;
    // Preserve repeated practice beyond the legacy validator's 99-attempt limit.
    if(attempts>99)this.state.v=5;
    this.state.at[key]=attempts;if(!own(this.state.fp,key))this.state.fp[key]=Boolean(correct);
  }
  submit() {
    const state=this.state;
    if(this.reviewing||state.s===0||this.currentCorrect())return false;
    if(state.s===4) {
      const answers=Object.fromEntries(DATA.statements.map(item=>[item.id,state.dr.s[item.id]??state.sr[item.id]]));
      if(DATA.statements.some(item=>!item.options.includes(answers[item.id]))){this.error='Answer all three conceptual questions before checking your reasoning.';return false;}
      for(const item of DATA.statements) {
        const key='statement:'+item.id;
        if(!own(state.fp,key)||state.sr[item.id]!==answers[item.id])this.record(key,answers[item.id]===item.correct);
      }
      state.dr.s=copy(answers);state.sr=answers;state.ss=true;
    }else if(this.group.prefix==='account') {
      const answer=state.dr.a[this.item.id];
      if(!answer||!this.item.effect_options.includes(answer.effect)||!this.item.omission_options.includes(answer.omission)){
        this.error='Complete both choices before checking your reasoning.';return false;
      }
      state.ar[this.item.id]=copy(answer);this.record('account:'+this.item.id,evaluateAccount(this.item.id,answer).correct);
    }else {
      const value=state.dr[this.group.draft][this.item.id];
      if(!optionsFor(this.group,this.item).includes(value)){
        this.error=state.s===2?'Choose an accrual accounting transaction type before checking your reasoning.':
          state.s===5?'Choose a response before evaluating the proposal.':'Choose a response before checking your reasoning.';return false;
      }
      state[this.group.responseKey][this.item.id]=value;this.record(this.group.prefix+':'+this.item.id,value===correctFor(this.group,this.item));
    }
    this.error='';validateSnapshot(state);return true;
  }
  advance() {
    if(this.reviewing||this.complete)return false;
    if(this.state.s===0){this.state.s=1;this.view=frontier(this.state);return true;}
    if(!this.currentCorrect())return false;
    if(this.state.s===4)this.state.s=5;
    else if(this.state[this.group.indexKey]<this.group.items.length-1)this.state[this.group.indexKey]++;
    else this.state.s++;
    this.view=frontier(this.state);this.error='';validateSnapshot(this.state);return true;
  }
  reset() {
    if(this.reviewing)return false;this.state=newState();this.view=0;this.error='';return true;
  }
}
