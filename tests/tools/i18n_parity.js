// EN/FR dictionary parity. Usage: node tests/tools/i18n_parity.js index.html  (exit 1 on mismatch)
const fs=require('fs');const s=fs.readFileSync(process.argv[2],'utf8');
const i=s.indexOf('const I18N_DICT={');let d=0,j=s.indexOf('{',i);const st=j;
for(;;j++){if(s[j]==='{')d++;else if(s[j]==='}'){d--;if(d===0)break;}}
const D=eval('('+s.slice(st,j+1)+')');const en=Object.keys(D.en),fr=Object.keys(D.fr);
const mFR=en.filter(k=>!(k in D.fr)),mEN=fr.filter(k=>!(k in D.en));
console.log('EN',en.length,'FR',fr.length,'missingFR',mFR.length,'missingEN',mEN.length);
if(mFR.length||mEN.length){console.log('missing FR:',mFR.slice(0,50),'missing EN:',mEN.slice(0,50));process.exit(1);}
