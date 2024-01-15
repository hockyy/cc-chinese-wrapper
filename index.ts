import {promises as pfs} from 'fs';

import {Character, Simplified, Word} from './interfaces';
import {ClassicLevel} from "classic-level";
import {AbstractBatchOperation} from "abstract-level";
import {ValueStream} from "level-read-stream";

export * from './interfaces';
type Db = ClassicLevel;
export type SetupType = {
  db: ClassicLevel,
  version: string,
};

export async function setup(dbpath: string, filename = '', verbose = false, omitPartial = false): Promise<SetupType> {
  const db = new ClassicLevel<string, string>(dbpath);
  try {
    const [version] =
        await Promise.all([db.get('version')]) as string[];
    return {db, version};
  } catch {
    // pass
  }

  if (!filename) {
    await db.close();
    throw new Error('database not found but cannot create it if no `filename` given');
  }
  let contents: string = '';
  try {
    contents = await pfs.readFile(filename, 'utf8')
  } catch {
    console.error(`Unable to find ${filename}`);
    process.exit(1);
  }
  const raw: Simplified = JSON.parse(contents);
  try {
    const maxBatches = 10000;
    let batch: AbstractBatchOperation<any, any, any>[] = [];

    {
      // non-JSON, pure strings
      const keys: (keyof Simplified)[] = ['version'];
      for (const key of keys) {
        batch.push({type: 'put', key: `raw/${key}`, value: raw[key]})
      }
    }

    for (const [numWordsWritten, w] of raw.words.entries()) {
      if (batch.length > maxBatches) {
        await db.batch(batch);
        batch = [];
        if (verbose) {
          console.log(`${numWordsWritten} entries written`);
        }
      }
      batch.push({type: 'put', key: `raw/words/${w.id}`, value: JSON.stringify(w)});
      batch.push({type: 'put', key: `indexes/${w.content}-${w.id}`, value: w.id});
      batch.push({type: 'put', key: `indexes/${w.simplified}-${w.id}`, value: w.id});
      if (!omitPartial) {
        for (const substr of allSubstrings(w.content)) {
          // collisions in key ok, since value will be same
          batch.push({type: 'put', key: `indexes/partial/${substr}-${w.id}`, value: w.id});
        }
        for (const substr of allSubstrings(w.simplified)) {
          // collisions in key ok, since value will be same
          batch.push({type: 'put', key: `indexes/partial/${substr}-${w.id}`, value: w.id});
        }
      }
    }
    if (batch.length) {
      await db.batch(batch);
    }

    for (const [numCharWritten, w] of raw.characters.entries()) {
      if (batch.length > maxBatches) {
        await db.batch(batch);
        batch = [];
        if (verbose) {
          console.log(`${numCharWritten} entries written`);
        }
      }
      batch.push({type: 'put', key: `raw/char/${w.id}`, value: JSON.stringify(w)});
      batch.push({type: 'put', key: `indexchar/${w.content}-${w.id}`, value: w.id});
    }
    if (batch.length) {
      await db.batch(batch);
    }

  } catch (e) {
    await db.close()
    throw e;
  }


  return {db, version: raw.version};
}

function drainStream(stream: ValueStream<string, Simplified, Db>): Promise<string[]> {
  const ret: string[] = [];
  return new Promise((resolve, reject) => {
    stream.on('data', x => ret.push(x))
    .on('error', e => reject(e))
    .on('close', () => resolve(ret))
    .on('end', () => resolve(ret));
  })
}

async function searchBeginning(db: Db, prefix: string, limit: number): Promise<Word[]> {
  const gte = `indexes/${prefix}`;
  const values = new ValueStream<string, Simplified, Db>(db, {gte, lt: gte + '\uFFFF', limit});
  return idsToWords(db, await drainStream(values));
}

async function searchAnywhere(db: Db, text: string, limit: number): Promise<Word[]> {
  const gte = `indexes/partial/${text}`;
  const values = new ValueStream<string, Simplified, Db>(db, {gte, lt: gte + '\uFFFF', limit})
  return idsToWords(db, await drainStream(values));
}

async function searchCharacter(db: Db, text: string, limit: number): Promise<Character[]> {
  const gte = `indexchar/${text}`;
  const values = new ValueStream<string, Simplified, Db>(db, {gte, lt: gte + '\uFFFF', limit})
  return idsToChar(db, await drainStream(values));
}

export function idsToChar(db: Db, idxs: string[]): Promise<Character[]> {
  return Promise.all(idxs.map(i => db.get(`raw/char/${i}`).then((x: string) => JSON.parse(x) as Character)))
}

export function idsToWords(db: Db, idxs: string[]): Promise<Word[]> {
  return Promise.all(idxs.map(i => db.get(`raw/words/${i}`).then((x: string) => JSON.parse(x) as Word)))
}

export async function charBeginning(db: Db, prefix: string, limit = -1) {
  return searchBeginning(db, prefix, limit);
}

export async function charAnywhere(db: Db, text: string, limit = -1) {
  return searchAnywhere(db, text, limit);
}

export async function hanzi(db: Db, character: string, limit = -1) {
  return searchCharacter(db, character, limit);
}

type BetterOmit<T, K extends keyof T> = Pick<T, Exclude<keyof T, K>>;

export async function getField(db: Db, key: keyof BetterOmit<Simplified, 'words'>): Promise<string> {
  return db.get(`raw/${key}`);
}

function allSubstrings(s: string) {
  const slen = s.length;
  let ret: Set<string> = new Set();
  for (let start = 0; start < slen; start++) {
    for (let length = 1; length <= slen - start; length++) {
      ret.add(s.substring(start, length));
    }
  }
  return ret;
}

if (module === require.main) {
  (async function () {
    const DBNAME = 'test';
    const {db, version} = await setup(DBNAME, 'public/cantodict.json', true, false);

    console.log({version});

    const res = await charBeginning(db, '事', 10);
    const resPartial = await charAnywhere(db, '餅印', 10);
    console.log(`${res.length} exact found`);
    console.log(`${resPartial.length} partial found`);
    console.log(resPartial)
    console.log(res)

    console.log(await idsToWords(db, ['5']));

    {
      const LIMIT = 4;
      const res = await charAnywhere(db, '死隔', LIMIT);
      console.log(res)
      console.log(`${res.length} found with limit ${LIMIT}`);
    }
    {
      const LIMIT = 4;
      const res = await hanzi(db, '隔', LIMIT);
      console.log(res)
      console.log(`${res.length} found with limit ${LIMIT}`);
    }
  })();
}
