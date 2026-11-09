// Actual ComfyUI integration: retains graphs, checks exported prompts, tests both renderers.
const {chromium}=require(process.env.PLAYWRIGHT_PATH || '/home/wwhvw/.codex/plugins/cache/personal-media-tools/local-library/0.3.0/node_modules/playwright');
function normalizeInputs(value){const result={...value};for(const key of Object.keys(result)){if(key.startsWith('voices.')){result.voices ||= {};result.voices[key.slice(7)]=result[key];delete result[key]}}return result}
const assert=require('node:assert/strict');const path=require('node:path');const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/wwhvw/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',args:['--no-sandbox','--no-proxy-server']});
 const page=await browser.newPage({viewport:{width:1660,height:1100}});const errors=[],queuedRequests=[];
 page.on('request',request=>{if(request.method()==='POST' && new URL(request.url()).pathname.endsWith('/prompt'))queuedRequests.push(request.url())});
 page.on('pageerror',error=>{if(error.stack?.includes('tts_gallery'))errors.push(error.stack)});
 await page.goto('http://127.0.0.1:8188/');await page.waitForFunction(()=>window.LiteGraph?.registered_node_types?.TTSExampleGallery,{timeout:90000});
 await page.waitForFunction(()=>window.comfyAPI.app.app.vueAppReady && document.querySelectorAll('button').length>5,{timeout:120000});
 await page.getByText('语音图库',{exact:true}).first().waitFor({state:'visible',timeout:120000});
 await page.waitForTimeout(1500);
 console.log('ComfyUI ready');
 await page.evaluate(()=>{const app=window.comfyAPI.app.app;app.graph.clear();const n=window.LiteGraph.createNode('PrimitiveStringMultiline');n.title='TTS test sentinel';n.widgets[0].value='Preserve this graph';n.pos=[50,50];app.graph.add(n);const e=window.LiteGraph.createNode('TTSExampleGallery');e.pos=[600,50];app.graph.add(e);app.graph.change();app.canvas.ds.scale=1;app.canvas.ds.offset=[20,100];app.canvas.setDirty(true,true)});
 await page.screenshot({path:'/tmp/tts-integration-before.png'});

 await page.getByRole('button',{name:'模型示例',exact:true}).click();
 let frame=page.frameLocator('iframe[src*="/tts_gallery/gallery"]');
 await frame.locator('.card[data-id="breeze-chef-happy"] .detail-link').click();
 await frame.getByRole('button',{name:'使用此参考 → ComfyUI',exact:true}).click();
 await page.waitForFunction(()=>window.comfyAPI.app.app.graph._nodes.find(n=>n.type==='TTSExampleGallery')?.widgets[0].value==='breeze-chef-happy');
 console.log('Node selection written back');
 const saved=await page.evaluate(()=>window.comfyAPI.app.app.graph.serialize());
 await page.evaluate(async graph=>{await window.comfyAPI.app.app.loadGraphData(graph,true,true,'TTS sentinel preserved')},saved);
 assert.equal(await page.evaluate(()=>window.comfyAPI.app.app.graph._nodes.find(n=>n.type==='TTSExampleGallery').widgets[0].value),'breeze-chef-happy');
 await page.getByRole('button',{name:'模型示例',exact:true}).click();frame=page.frameLocator('iframe[src*="/tts_gallery/gallery"]');
 await frame.locator('.card[data-id="breeze-chef-happy"] .detail-link').click();
 await frame.getByRole('button',{name:'打开示例工作流',exact:true}).click();
 await page.waitForFunction(()=>window.comfyAPI.app.app.graph._nodes.some(n=>n.type==='BreezeTTS2VoiceDirection'),{timeout:20000});
 const tabs=await page.evaluate(()=>{const w=window.comfyAPI.app.app.extensionManager.workflow;return {open:w.openWorkflows.map(x=>({name:x.name,path:x.path})),body:document.body.innerText.slice(0,2000)}});console.log('Workflow tabs:',tabs.open.map(w=>w.path));
 assert(tabs.open.some(workflow=>workflow.path==='workflows/TTS sentinel preserved.json'),'Previous workflow must remain open');
 const prompt=await page.evaluate(async()=> (await window.comfyAPI.app.app.graphToPrompt()).output);
 assert.equal(prompt['20'].inputs.text[0],'1');assert.equal(prompt['4'].inputs.reference_id,'huola-dachu');
 assert.equal(prompt['5'].inputs.value,4);assert.equal(prompt['2'].inputs.value,20261109);
 assert.equal(prompt['20'].inputs.max_new_tokens,504);assert.equal(prompt['20'].inputs.stitch_reference,'none');
 const required=await (await page.request.get('http://127.0.0.1:8188/tts_gallery/workflow/breeze-chef-happy?format=api')).json();
 for(const id of Object.keys(required))assert.deepEqual(prompt[id].inputs,required[id].inputs,'UI/API mismatch node '+id);
 await page.screenshot({path:path.join(__dirname,'../docs/comfy-workflow.png')});
 // Check native autogrow serialization and both renderer modes on a Drama3 graph.
 const drama=await (await page.request.get('http://127.0.0.1:8188/tts_gallery/workflow/drama3-chef-scoped')).json();
 await page.evaluate(async graph=>{await window.comfyAPI.app.app.loadGraphData(graph,true,true,'TTS Drama3 integration')},drama);
 const dramaPrompt=await page.evaluate(async()=> (await window.comfyAPI.app.app.graphToPrompt()).output);
 const expectedDrama=await (await page.request.get('http://127.0.0.1:8188/tts_gallery/workflow/drama3-chef-scoped?format=api')).json();
 for(const id of Object.keys(expectedDrama))assert.deepEqual(normalizeInputs(dramaPrompt[id].inputs),normalizeInputs(expectedDrama[id].inputs),'Drama3 UI/API mismatch node '+id);
 const before=await page.evaluate(()=>window.comfyAPI.app.app.ui.settings.getSettingValue('Comfy.VueNodes.Enabled'));
 try{
  for(const enabled of [false,true]){
   await page.evaluate(async enabled=>{await window.comfyAPI.app.app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled',enabled)},enabled);
   await page.waitForTimeout(800);
   await page.getByRole('button',{name:'音色参考',exact:true}).click();frame=page.frameLocator('iframe[src*="/tts_gallery/gallery"]');
   await frame.locator('.card[data-id="huola-dachu"] .detail-link').click();
   await frame.getByRole('button',{name:'使用此参考 → ComfyUI',exact:true}).click();
   await page.locator('iframe[src*="/tts_gallery/gallery"]').waitFor({state:'detached'});
   assert.equal(await page.evaluate(()=>window.comfyAPI.app.app.graph._nodes.find(n=>n.type==='TTSVoiceGallery').widgets[0].value),'huola-dachu');
   await page.screenshot({path:path.join(__dirname,enabled?'../docs/nodes-2.png':'../docs/nodes-classic.png')});
  }
 }finally{await page.evaluate(async enabled=>{await window.comfyAPI.app.app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled',enabled)},before)}
 assert.equal(queuedRequests.length,0,'Browsing and workflow loading must never enqueue');
 assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(__dirname,'../.generation/ui-api-prompt.json'),JSON.stringify(prompt,null,2));
 fs.writeFileSync(path.join(__dirname,'../.generation/drama-ui-api-prompt.json'),JSON.stringify(dramaPrompt,null,2));
 await page.goto('http://127.0.0.1:8188/?tts_gallery_example=breeze-design-zh-female&tts_gallery_lang=en');
 await page.waitForFunction(()=>window.comfyAPI?.app?.app?.graph?._nodes.some(n=>n.type==='BreezeTTS2VoiceDesign'),{timeout:120000});
 assert(!page.url().includes('tts_gallery_example'));
 console.log('ComfyUI integration passed: node selection/restore, new tabs, exact UI/API settings, both renderers, no automatic queueing.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
