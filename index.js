"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getField = exports.charAnywhere = exports.charBeginning = exports.idsToWords = exports.setup = void 0;
const fs_1 = require("fs");
const classic_level_1 = require("classic-level");
const level_read_stream_1 = require("level-read-stream");
__exportStar(require("./interfaces"), exports);
function setup(dbpath, filename = '', verbose = false, omitPartial = false) {
    return __awaiter(this, void 0, void 0, function* () {
        const db = new classic_level_1.ClassicLevel(dbpath);
        try {
            const [version] = yield Promise.all([db.get('version')]);
            return { db, version };
        }
        catch (_a) {
            // pass
        }
        if (!filename) {
            yield db.close();
            throw new Error('database not found but cannot create it if no `filename` given');
        }
        let contents = '';
        try {
            contents = yield fs_1.promises.readFile(filename, 'utf8');
        }
        catch (_b) {
            console.error(`Unable to find ${filename}`);
            process.exit(1);
        }
        const raw = JSON.parse(contents);
        try {
            const maxBatches = 10000;
            let batch = [];
            {
                // non-JSON, pure strings
                const keys = ['version'];
                for (const key of keys) {
                    batch.push({ type: 'put', key: `raw/${key}`, value: raw[key] });
                }
            }
            for (const [numWordsWritten, w] of raw.words.entries()) {
                if (batch.length > maxBatches) {
                    yield db.batch(batch);
                    batch = [];
                    if (verbose) {
                        console.log(`${numWordsWritten} entries written`);
                    }
                }
                batch.push({ type: 'put', key: `raw/words/${w.id}`, value: JSON.stringify(w) });
                batch.push({ type: 'put', key: `indexes/${w.traditional}-${w.id}`, value: w.id });
                if (!omitPartial) {
                    for (const substr of allSubstrings(w.traditional)) {
                        // collisions in key ok, since value will be same
                        batch.push({ type: 'put', key: `indexes/partial/${substr}-${w.id}`, value: w.id });
                    }
                }
            }
            if (batch.length) {
                yield db.batch(batch);
            }
        }
        catch (e) {
            yield db.close();
            throw e;
        }
        return { db, version: raw.version };
    });
}
exports.setup = setup;
function drainStream(stream) {
    const ret = [];
    return new Promise((resolve, reject) => {
        stream.on('data', x => ret.push(x))
            .on('error', e => reject(e))
            .on('close', () => resolve(ret))
            .on('end', () => resolve(ret));
    });
}
function searchBeginning(db, prefix, limit) {
    return __awaiter(this, void 0, void 0, function* () {
        const gte = `indexes/${prefix}`;
        const values = new level_read_stream_1.ValueStream(db, { gte, lt: gte + '\uFFFF', limit });
        return idsToWords(db, yield drainStream(values));
    });
}
function searchAnywhere(db, text, limit) {
    return __awaiter(this, void 0, void 0, function* () {
        const gte = `indexes/partial/${text}`;
        const values = new level_read_stream_1.ValueStream(db, { gte, lt: gte + '\uFFFF', limit });
        return idsToWords(db, yield drainStream(values));
    });
}
function idsToWords(db, idxs) {
    return Promise.all(idxs.map(i => db.get(`raw/words/${i}`).then((x) => JSON.parse(x))));
}
exports.idsToWords = idsToWords;
function charBeginning(db, prefix, limit = -1) {
    return __awaiter(this, void 0, void 0, function* () {
        return searchBeginning(db, prefix, limit);
    });
}
exports.charBeginning = charBeginning;
function charAnywhere(db, text, limit = -1) {
    return __awaiter(this, void 0, void 0, function* () {
        return searchAnywhere(db, text, limit);
    });
}
exports.charAnywhere = charAnywhere;
function getField(db, key) {
    return __awaiter(this, void 0, void 0, function* () {
        return db.get(`raw/${key}`);
    });
}
exports.getField = getField;
function allSubstrings(s) {
    const slen = s.length;
    let ret = new Set();
    for (let start = 0; start < slen; start++) {
        for (let length = 1; length <= slen - start; length++) {
            ret.add(s.substring(start, length));
        }
    }
    return ret;
}
if (module === require.main) {
    (function () {
        return __awaiter(this, void 0, void 0, function* () {
            const DBNAME = 'test';
            const { db, version } = yield setup(DBNAME, 'cccanto-webdist.json', true, false);
            console.log({ version });
            const res = yield charBeginning(db, '事', 10);
            const resPartial = yield charAnywhere(db, '餅印', 10);
            console.log(`${res.length} exact found`);
            console.log(`${resPartial.length} partial found`);
            console.log(resPartial);
            console.log(res);
            console.log(yield idsToWords(db, ['5']));
            {
                const LIMIT = 4;
                const res = yield charAnywhere(db, '死隔', LIMIT);
                console.log(res);
                console.log(`${res.length} found with limit ${LIMIT}`);
            }
        });
    })();
}
