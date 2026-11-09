import assert from 'node:assert/strict';
import { test } from 'node:test';
import { matches, validMessage, onePlayer, local } from '../web/core.mjs';

test('filters keep model, language, origin and all query words independent', () => {
 const row={kind:'example',model:'breeze',language:'zh',mode:'direction',category:'pace',origin:'builtin',name_zh:'温柔男声',instruction:'Speak slowly'};
 assert(matches(row,{kind:'example',q:'男声 slowly',model:'breeze'}));
 assert(!matches(row,{kind:'example',q:'男声 unknown'}));
 assert(!matches(row,{kind:'voice'})); assert(!matches(row,{kind:'example',language:'en'}));
 assert.equal(local({name_zh:'中文'},'name','en'),'中文');
});
test('messages require matching origin, iframe window and unguessable channel', () => {
 const source={}; const event={origin:'http://localhost',source,data:{token:'test',type:'tts-gallery-select'}};
 assert(validMessage(event,source,event.origin,'test'));
 assert(!validMessage(event,{},event.origin,'test'));
 assert(!validMessage(event,source,'https://evil.example','test'));
 assert(!validMessage(event,source,event.origin,'wrong'));
});
test('one shared player pauses current audio and switches sources', async () => {
 const events=[]; const player={paused:false,src:'a',pause(){this.paused=true;events.push('pause')},play(){this.paused=false;events.push('play');return Promise.resolve()}};
 await onePlayer(player,'b',false); assert.equal(player.src,'b'); assert.deepEqual(events,['pause','play']);
 await onePlayer(player,'b',true); assert(player.paused); assert.deepEqual(events,['pause','play','pause']);
});
