/** Native close with original feedback, mastery and saved first-pass history. */
import {DATA} from './content.js';
import {Lesson,GROUPS,frontier,scoreSummary,evaluateAccount,evaluateStatements,
  shuffledOptions,decodeState,encodeState,copy} from './engine.js';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
const escapeHTML=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
let lesson,orders=new Map(),sequence=0;
async function prepareOrders() {
  orders=new Map(await Promise.all(GROUPS.find(group=>group.stage===3).items.flatMap(item=>
    ['effect','omission'].map(async field=>[field+':'+item.id,await shuffledOptions(item[field+'_options'],lesson.state.z,'account-'+field+':'+item.id)]))));
}
async function save() {
  const current=++sequence,state=copy(lesson.state),view=lesson.view;document.documentElement.dataset.saving='true';
  try {const token=await encodeState(state);if(current!==sequence)return;
    const url=new URL(location.href);url.searchParams.set('progress',token);url.searchParams.set('view',String(view));history.replaceState(null,'',url);$('save-error').hidden=true;
  }catch(error){if(current===sequence){$('save-error').textContent='Your address could not be updated. Keep this tab open; refreshing may not preserve the latest input.';$('save-error').hidden=false;console.error(error);}}
  finally{if(current===sequence)document.documentElement.dataset.saving='false';}
}
function scrollTop(){window.scrollTo({top:0,left:0,behavior:'instant'});$('lesson').focus({preventScroll:true});}
function update(scroll=false){render();save();if(scroll)scrollTop();}
async function reset(){if(lesson.reset()){await prepareOrders();update(true);}}
function markdown(text) {
  const fragment=document.createDocumentFragment();let list=null,listTag='';
  for(const line of text.replace(/\\\$/g,'$').split('\n').map(value=>value.trim()).filter(Boolean)) {
    const bullet=/^[-*]\s+(.+)/.exec(line),number=/^\d+\.\s+(.+)/.exec(line),heading=/^(#{1,6})\s+(.+)/.exec(line);
    const tag=bullet?'ul':number?'ol':null,item=el(tag?'li':heading?'h'+heading[1].length:'p');
    item.innerHTML=escapeHTML(bullet?bullet[1]:number?number[1]:heading?heading[2]:line).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
    if(tag){if(!list||listTag!==tag){list=el(tag);listTag=tag;fragment.append(list);}list.append(item);}else{list=null;listTag='';fragment.append(item);}
  }return fragment;
}
function radio(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const stage=lesson.position.stage,group=GROUPS.find(group=>group.stage===stage),item=group?.items[lesson.position.index];
  let id,field,options,value;
  if(stage===4) {
    id=node.key.replace('widget_statement_','');const question=DATA.statements.find(item=>item.id===id);
    options=question.options;value=lesson.state.dr.s[id]??lesson.state.sr[id];
  }else if(stage===3) {
    id=item.id;field=node.key.startsWith('widget_effect_')?'effect':'omission';
    options=orders.get(field+':'+id);value=lesson.state.dr.a[id]?.[field];
  }else {
    id=item.id;options=stage===2?DATA.classificationOptions:item.options;value=lesson.state.dr[group.draft][id];
  }
  const fieldset=el('fieldset');fieldset.append(el('legend',node.label));
  options.forEach((option,index)=>{
    const label=el('label',undefined,'choice'),input=el('input');input.type='radio';input.id=node.key+'_'+index;input.name=node.key;
    input.value=option;input.checked=value===option;
    input.addEventListener('change',()=>{if(lesson.draft(id,option,field)){$('lesson').querySelector('[role="alert"]')?.remove();save();}});
    label.append(input,el('span',option));fieldset.append(label);
  });return fieldset;
}
function action(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const button=el('button',node.label,'primary');button.type='button';
  button.addEventListener('click',()=>{
    if(node.action==='restart_activity'){reset();return;}
    const advance=['advance_item','set_stage'].includes(node.action),changed=advance?lesson.advance():lesson.submit();
    if(changed||lesson.error)update(advance&&changed);
  });return button;
}
function feedbackRow(label,correct,detail) {
  const box=el('div',undefined,'feedback-row '+(correct?'correct':'review')),body=el('div'),heading=el('div',label+' - '+(correct?'Correct':'Review'),'feedback-label');
  body.append(heading,el('div',detail,'feedback-detail'));box.append(body,el('div','','feedback-value'));return box;
}
function csv(rows,columns){return [columns,...rows.map(row=>columns.map(key=>row[key]))].map(row=>row.map(value=>'"'+String(value).replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';}
function table(node) {
  const section=el('section'),wrap=el('div',undefined,'table-wrap'),table=el('table'),columns=Object.keys(node.rows[0]);
  wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Unadjusted and adjusted account balances; scroll horizontally to view every column');
  const caption=el('caption','Account balances before and after adjustment'),head=el('thead'),row=el('tr'),body=el('tbody');
  table.append(caption);let rows=[...node.rows],sort=null,descending=false;
  const draw=()=>body.replaceChildren(...rows.map(record=>{const line=el('tr');columns.forEach((key,index)=>{const cell=el(index===0?'th':'td',record[key]);if(index===0)cell.scope='row';line.append(cell);});return line;}));
  columns.forEach(key=>{const cell=el('th'),button=el('button',key);cell.scope='col';button.type='button';
    button.addEventListener('click',()=>{descending=sort===key?!descending:false;sort=key;rows=[...node.rows].sort((a,b)=>String(a[key]).localeCompare(String(b[key]),'en')*(descending?-1:1));
      [...row.children].forEach(item=>item.removeAttribute('aria-sort'));cell.setAttribute('aria-sort',descending?'descending':'ascending');draw();});
    cell.append(button);row.append(cell);
  });head.append(row);table.append(head,body);draw();wrap.append(table);section.append(wrap);
  const tools=el('div',undefined,'table-tools'),download=el('button','Download table as CSV'),expand=el('button','Expand table');download.type=expand.type='button';
  download.addEventListener('click',()=>{const blob=new Blob([csv(rows,columns)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=el('a');
    link.href=url;link.download='closing-time-account-comparison.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  expand.addEventListener('click',()=>{const dialog=el('dialog',undefined,'expanded-table'),close=el('button','Close table'),placeholder=document.createComment('table position');
    close.type='button';wrap.before(placeholder);dialog.append(el('h2',caption.textContent),close,wrap);document.body.append(dialog);
    close.addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>{placeholder.replaceWith(wrap);dialog.remove();expand.focus();},{once:true});dialog.showModal();});
  tools.append(expand,download);section.append(tools);return section;
}
function renderNode(node) {
  if(node.kind==='radio')return radio(node);
  if(node.kind==='button')return action(node);
  if(node.kind==='table')return table(node);
  if(node.kind==='account-feedback') {
    const group=GROUPS.find(group=>group.stage===3),item=group.items[lesson.position.index],result=evaluateAccount(item.id,lesson.state.ar[item.id]);
    return feedbackRow(node.field==='effect'?'Account directions':'Omission effect',result.checks[node.field],result.expected[node.field]);
  }
  if(node.kind==='statement-feedback') {
    const item=DATA.statements[node.index],result=evaluateStatements(lesson.state.sr)[item.id];
    const detail=(result.correct?'':'Correct response: '+result.expected+'. ')+result.explanation;
    return feedbackRow('Concept '+(node.index+1),result.correct,detail);
  }
  if(node.kind==='html') {
    const template=document.createElement('template');template.innerHTML=node.text;
    const prefixes=['recognition','classification','account','statement','integrity'];
    const counts=[4,6,4,3,4];
    template.content.querySelectorAll('.score-box').forEach((box,index)=>{
      const score=Object.entries(lesson.state.fp).filter(([key,value])=>key.startsWith(prefixes[index]+':')&&value).length;
      box.querySelector('strong').textContent=score+'/'+counts[index];
    });return template.content;
  }
  if(node.kind==='columns'||node.kind==='column') {
    const box=el('div',undefined,node.kind==='columns'?'columns':null);if(node.kind==='columns')box.style.setProperty('--columns',node.children.length);
    node.children.forEach(child=>box.append(renderNode(child)));return box;
  }
  if(node.kind==='progress') {
    const box=el('div',node.text,'case-progress'),progress=el('progress');progress.max=1;progress.value=node.value;progress.setAttribute('aria-label',node.text);box.append(progress);return box;
  }
  if(node.kind==='metric') {const box=el('div',undefined,'metric');box.append(el('span',node.label),el('strong',node.value));return box;}
  if(node.kind==='markdown'||node.kind==='write')return markdown(node.text);
  let textValue=node.text;
  if(node.kind==='caption'&&textValue.startsWith('First-pass decisions:')) {
    const score=scoreSummary(lesson.state);textValue='First-pass decisions: '+score.correct+' of '+score.total+' | Practice revisions used: '+score.revisions+' | Final mastery: complete';
  }
  const item=el(node.kind==='header'?'h2':node.kind==='subheader'?'h3':'p',textValue,
    ['success','warning','info'].includes(node.kind)?'notice '+node.kind:node.kind==='caption'?'caption':null);
  if(['success','warning','info'].includes(node.kind))item.setAttribute('role','status');return item;
}
function variant() {
  const {stage,index}=lesson.position,state=lesson.state;
  if(stage===0)return 'unanswered';
  if(stage===4)return !state.ss?'unanswered':Object.values(evaluateStatements(state.sr)).every(result=>result.correct)?'correct':'wrong';
  const group=GROUPS.find(group=>group.stage===stage),item=group.items[index],answer=state[group.responseKey][item.id];
  if(answer===undefined)return 'unanswered';
  const correct=stage===3?evaluateAccount(item.id,answer).correct:answer===(stage===2?item.classification:item.correct);
  return correct?'correct':'wrong';
}
function render() {
  $('hero').replaceChildren(...DATA.hero.map(renderNode));
  $('back').disabled=lesson.view===0;$('forward').disabled=lesson.view>=frontier(lesson.state);$('reset').disabled=lesson.reviewing;
  $('page-counter').textContent='Page '+(lesson.view+1)+' of 20';
  $('stages').replaceChildren(...DATA.stages.map((label,stage)=>el('div',label,'stage-pill '+(stage<lesson.position.stage?'complete':stage===lesson.position.stage?'active':''))));
  $('review-message').replaceChildren(...(lesson.reviewing?[el('p','Review only. Return to your current page to continue the close.','notice info')]:[]));
  $('lesson').replaceChildren(...DATA.screens[lesson.view].variants[variant()].map(renderNode));
  if(lesson.error){const message=el('p',lesson.error,'notice warning');message.setAttribute('role','alert');$('lesson').append(message);}
  $('lesson').setAttribute('aria-busy','false');document.documentElement.dataset.view=String(lesson.view);document.documentElement.dataset.reached=String(frontier(lesson.state));
}
async function initialize() {
  const query=new URL(location.href).searchParams,token=query.get('progress'),state=token?await decodeState(token):null;
  lesson=new Lesson(state??undefined,query.get('view')??undefined);await prepareOrders();render();
  if(token&&!state)$('lesson').prepend(el('p','This saved link could not be restored. A new May close has been opened.','notice warning'));
  await save();document.documentElement.dataset.ready='true';performance.mark('closing-ready');
}
$('back').addEventListener('click',()=>{if(lesson.move(-1))update(true);});
$('forward').addEventListener('click',()=>{if(lesson.move(1))update(true);});
$('reset').addEventListener('click',reset);
window.addEventListener('popstate',()=>{document.documentElement.dataset.ready='false';initialize();});
initialize().catch(error=>{$('lesson').replaceChildren(el('p','This browser could not open the close. Use a current browser with JavaScript, Web Crypto, BigInt and Compression Streams enabled.','notice warning'));$('lesson').setAttribute('aria-busy','false');console.error(error);});
