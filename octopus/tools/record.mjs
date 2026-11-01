// Records the OC-8 tour frame by frame: render(t) is pure, so no frame is ever dropped.
// usage: node tools/record.mjs [--fps 60] [--size 1600x900] [--dpr 1.2] [--out oc8.mp4]
// needs: a static server on :8765 serving this folder, playwright, ffmpeg.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
const arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i>0?process.argv[i+1]:d};
const fps=+arg('fps',60),[W,H]=arg('size','1600x900').split('x').map(Number),dpr=+arg('dpr',1.2),out=arg('out','oc8.mp4');
const url=arg('url','http://localhost:8765/index.html');
const b=await chromium.launch({args:['--ignore-gpu-blocklist','--enable-gpu-rasterization','--use-gl=angle']});
const p=await b.newPage({viewport:{width:W,height:H},deviceScaleFactor:dpr});
await p.goto(url);await p.waitForFunction(()=>window.__oc8&&__oc8.ready,{timeout:60000});
const LOOP=await p.evaluate(()=>__oc8.LOOP),N=Math.round(LOOP*fps);
const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-i','-','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
const t0=Date.now();
for(let i=0;i<N;i++){
  await p.evaluate(t=>__oc8.render(t),i/fps);
  const buf=await p.screenshot({type:'jpeg',quality:92});
  if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));
  if(i%30===0)process.stdout.write(`\rframe ${i}/${N}  ${((Date.now()-t0)/1000).toFixed(0)} s`);
}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();
console.log(`\nwrote ${out}`);
