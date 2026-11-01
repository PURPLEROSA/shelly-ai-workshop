const sharp=require('sharp'),fs=require('fs');
const S='/tmp/site/assets/';
const imgs={'shelly-disco-agents.png':[1400,'jpg'],'shelly-portrait-blue.png':[1000,'jpg'],'agents-gift-illustration-v2.png':[1000,'png'],
 'mini-agent-clients.png':[420,'png'],'mini-agent-content.png':[420,'png'],'mini-agent-home.png':[420,'png']};
(async()=>{
for(const [f,[w,fmt]] of Object.entries(imgs)){const o='assets/img/'+f.replace('.png','.'+fmt);
 let p=sharp(S+f).resize({width:w,withoutEnlargement:true}); p= fmt==='jpg'?p.jpeg({quality:84}):p.png({compressionLevel:9,palette:false});
 await p.toFile(o); console.log(o,fs.statSync(o).size);}
const icons=process.argv.slice(2);
for(const n of icons){const src='node_modules/lucide-static/icons/'+n+'.svg'; if(!fs.existsSync(src)){console.log('MISSING',n);continue;}
 for(const [suf,col] of [['','#3C3C40'],['-p','#72536F'],['-w','#FFFDFB']]){
 let s=fs.readFileSync(src,'utf8').replace(/stroke="currentColor"/,`stroke="${col}"`).replace(/stroke-width="2"/,'stroke-width="1.8"').replace(/width="24"/,'width="256"').replace(/height="24"/,'height="256"');
 await sharp(Buffer.from(s)).png().toFile(`assets/ic/${n}${suf}.png`);}}
})();
