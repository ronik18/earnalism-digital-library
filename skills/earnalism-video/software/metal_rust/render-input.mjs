import {createHash} from 'node:crypto';
import {validateProps} from './layout.mjs';
export function validateRenderInput(props,contract){
 validateProps(props,contract);
 const normalized=props.words.flatMap(w=>w.word.toLowerCase().replaceAll('’',"'").match(/[a-z]+(?:'[a-z]+)?|\d+/g)??[]).join(' ');
 if(createHash('sha256').update(normalized).digest('hex')!==contract.normalized_tokens_sha256)throw Error('Current spoken script digest differs from exact Rust content');
 return props;
}
