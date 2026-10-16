import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import {projectPreparation} from '../src/monthly-readiness/projection.mjs';
const here=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export async function buildMonthlyReadiness(root=here){
 const comparison=JSON.parse(await readFile(resolve(root,'dist/data/monthly-comparison.json'),'utf8'));
 const review=JSON.parse(await readFile(resolve(root,'src/monthly-readiness/review.json'),'utf8'));
 const out=projectPreparation(comparison,review);
 await writeFile(resolve(root,'dist/data/monthly-preparation.json'),JSON.stringify(out));
 await writeFile(resolve(root,'dist/monthly-readiness.js'),await readFile(resolve(root,'src/monthly-readiness/view.js')));
 console.log(`Preparation only: ${out.period.signal_months} decisions, ${out.period.required_opening_months} required opening months, 0/${out.planned_comparisons} computed`);
 return out;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await buildMonthlyReadiness();
