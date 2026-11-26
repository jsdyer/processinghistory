export function days(label) {
  const match=/^(\d+) (days?|weeks?)$/i.exec(label??'');
  return match?Number(match[1])*(match[2].startsWith('week')?7:1):null;
}
export function observations(values,provenance,program) {
  if(values.length!==provenance.length)throw new Error('Archive and source index differ in length.');
  return values.map((label,i)=>({label:label??'No row in this capture',day:days(label),date:provenance[i].observed.slice(0,10),issued:provenance[i].issued[program]??'Unavailable',source:provenance[i].evidence}));
}
