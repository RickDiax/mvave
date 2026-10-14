/* Frontend contract test with a small DOM double; no browser rendering or USB.
   Run from the repo root: node tests/test_studio_ui.cjs
   Optional: node tests/test_studio_ui.cjs path/to/diagnostic.json
   Set PYTHON if the Python command is not named "python". */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const {spawn} = require('node:child_process');
const root = path.resolve(__dirname, '..');
class Element {
  constructor(tag) { this.tag=tag;this.children=[];this.value='';this.textContent='';this.hidden=false;this.disabled=false;this.checked=false;this.files=[];this.classList={add(){},remove(){}}; }
  append(...items) { this.children.push(...items);if(this.tag==='select'&&!this.value&&items.length)this.value=String(items[0].value); }
  replaceChildren(...items) {this.children=[];this.value='';this.append(...items);}
  setAttribute() {}
  addEventListener() {}
  showModal(){this.open=true;}
  close(){this.open=false;}
  click(){return this.onclick?.();}
}
async function main(){
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'mk300-ui-'));
  const server=spawn(process.env.PYTHON||'python',[path.join(root,'studio/server.py'),'--no-browser','--port','0'],{env:{...process.env,LOCALAPPDATA:temp}});
  try{
    const url=await new Promise((resolve,reject)=>{let output='';server.stdout.on('data',d=>{output+=d;const m=output.match(/http:\/\/127\.0\.0\.1:\d+/);if(m)resolve(m[0]);});server.once('error',reject);server.once('exit',code=>reject(Error('Server exited: '+code)));});
    let raw;
    if(process.argv[2])raw=Buffer.from(JSON.parse(fs.readFileSync(process.argv[2])).edit_buffer_raw_hex,'hex');
    else{raw=Buffer.alloc(448);raw.write('TESTE USB');raw.writeInt16LE(80,24);raw.writeInt16LE(80,26);for(let i=0;i<11;i++)raw[32+i]=i;for(let i=330;i<448;i++)raw[i]=i%256;}
    const draft={raw_hex:raw.toString('hex'),name:'TESTE USB',volume:raw.readInt16LE(24),bpm:raw.readInt16LE(26),pan:raw.readInt16LE(28),chain:[...raw.subarray(32,43)].map(i=>['WAH','FX','GATE','DS','AMP','CAB','EQ','MOD','DLY','REV','VOL'][i]),blocks:{}};
    ['WAH','FX','GATE','DS','AMP','CAB','EQ','MOD','DLY','REV','VOL'].forEach((b,i)=>draft.blocks[b]={model_index:raw[54+i],enabled:!!raw[43+i],knobs:Array.from({length:12},(_,k)=>raw.readInt16LE(66+i*24+k*2))});
    const html=await(await fetch(url)).text(),ids={};
    for(const m of html.matchAll(/<(\w+)\b[^>]*\bid="([^"]+)"[^>]*>/g)){const e=new Element(m[1]);e.value=m[0].match(/\bvalue="([^"]*)"/)?.[1]||'';e.hidden=/\bhidden\b/.test(m[0]);ids[m[2]]=e;}
    const document={body:new Element('body'),getElementById:id=>{assert.ok(ids[id],'Unknown element '+id);return ids[id];},createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)};
    let saves=0,clipboard='',receiverPrefs=null,receiverState={enabled:false,phase:'paused',message:'Paused'};
    const context=vm.createContext({document,structuredClone,Blob,URL,console,setTimeout:(f,n)=>{const t=setTimeout(f,n);t.unref();return t;},clearTimeout,setInterval:()=>0,navigator:{clipboard:{writeText:async t=>{clipboard=t;}}},confirm:()=>true,fetch:async(p,options)=>{
      if(['/api/current','/api/read-slot'].includes(p))return {ok:true,json:async()=>({...draft,slot:137,sha256:'simulated-destination'})};
      if(p==='/api/automation-enable'){const b=JSON.parse(options.body);assert.equal(b.slot,137);receiverState={enabled:true,phase:'waiting',slot:137,message:'Active',settings:receiverPrefs};return {ok:true,json:async()=>receiverState};}
      if(p==='/api/automation-disable'){receiverState={...receiverState,enabled:false,phase:'paused',message:'Paused'};return {ok:true,json:async()=>receiverState};}
      if(p==='/api/automation-status')return {ok:true,json:async()=>receiverState};
      if(p==='/api/automation-latest')return {ok:true,json:async()=>({...draft,name:'REMOTE TONE',slot:137,verified:true})};
      if(p==='/api/save'){const job=JSON.parse(options.body);assert.equal(job.slot,137);assert.equal(job.draft.name,'NEW TONE');assert.equal(job.expected_sha,'simulated-destination');saves++;return {ok:true,json:async()=>({verified:true,slot:137,backup:'simulated.json'})};}
      const r=await fetch(url+p,options);if(p==='/api/bootstrap'){const data=await r.json();receiverPrefs=data.automation.settings;data.ports={inputs:['USB-Midi 0'],outputs:['Microsoft GS Wavetable Synth 0','USB-Midi 1']};return {ok:true,json:async()=>data};}if(p==='/api/settings'){const data=await r.json();receiverPrefs=data.settings;return {ok:r.ok,json:async()=>data};}return r;
    }});
    vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
    async function idle(){const deadline=Date.now()+5000;while(vm.runInContext('busy',context)){assert.ok(Date.now()<deadline,'UI operation timed out');await new Promise(r=>setTimeout(r,10));}assert.ok(!(ids.status.className||'').split(' ').includes('error'),ids.status.textContent);}
    async function act(id){ids[id].onclick();await idle();}
    await idle();assert.equal(ids.output.value,'USB-Midi 1');await act('automationEnable');assert.equal(vm.runInContext('currentPage',context),'Settings');assert.ok(!ids.automationDialog.open);await act('navLibrary');assert.ok(ids.pageHome.hidden);await act('readCurrent');assert.equal(ids.presetTitle.textContent,'TESTE USB');
    vm.runInContext("active='DS';render()",context);ids.model.value='47';ids.model.onchange();ids.name.value='NEW TONE';ids.name.oninput();
    vm.runInContext("active='DS';render()",context);ids.enabled.checked=true;ids.enabled.onchange();
    const slider=ids.params.children[0].children[1];slider.value='20';slider.oninput();
    assert.equal(vm.runInContext('draft.blocks.DS.knobs[0]',context),20);
    await act('saveLibrary');assert.equal(ids.library.children.length,1);
    await act('exportBtn');assert.match(ids.status.textContent,/exportado/);
    await act('prepareSave');assert.ok(ids.confirmDialog.open);assert.equal(saves,0);await act('cancelSave');assert.equal(saves,0);
    await act('prepareSave');await act('commitSave');assert.equal(saves,1);assert.match(ids.status.textContent,/Gravação verificada/);
    const backup={format:'mk300-studio-1',before_raw_hex:raw.toString('hex')};ids.importFile.files=[{size:2000,text:async()=>JSON.stringify(backup)}];ids.importFile.onchange();await idle();assert.equal(ids.presetTitle.textContent,'TESTE USB');
    ids.automationSlot.value='137';await act('automationEnable');assert.ok(ids.automationDialog.open);assert.equal(receiverState.enabled,false);await act('automationConfirmEnable');assert.equal(receiverState.enabled,true);assert.ok(ids.automationSlot.disabled);
    ids.songRequest.value='Time - Pink Floyd';await act('copyRequest');assert.ok(clipboard.includes(receiverPrefs.channel_id));assert.ok(clipboard.includes('Time - Pink Floyd'));
    receiverState={...receiverState,phase:'verified',last_job_id:'a'.repeat(32),last_result:{verified:true,slot:137},last_name:'REMOTE TONE',message:'Received'};await vm.runInContext('pollAutomation()',context);assert.equal(ids.presetTitle.textContent,'REMOTE TONE');
    ids.name.value='MY DRAFT';ids.name.oninput();receiverState={...receiverState,last_job_id:'b'.repeat(32)};await vm.runInContext('pollAutomation()',context);assert.equal(ids.presetTitle.textContent,'MY DRAFT');
    await act('automationPause');assert.equal(receiverState.enabled,false);assert.equal(ids.automationSlot.disabled,false);
    console.log('PASS: HTTP API + frontend: navigation, first-run setup, ports, editor, library, export, save/cancel, restore, channel prompt, arm/receive/pause, dirty draft preserved. USB and DOM simulated; no browser rendering.');
  }finally{server.kill();await new Promise(r=>server.once('exit',r));fs.rmSync(temp,{recursive:true,force:true});}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
