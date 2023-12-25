export interface Entry {
  content: string;
  id: string,
  cantodict_id?: number;
  pinyin: string;
  jyutping: string;
  notes: string;
  meaning: string[];
  dialect: string;
  freq: number;
  variants: string[];
  similar: [];
}

export interface Word extends Entry{
  simplified: string;
  pos: string[];
}

export interface Etymology {
  type: string;
  hint: string;
}

export interface Character extends Entry{
  stroke_count: number;
  decomposition: string;
  radical: string;
  etymology: Etymology;
}

export interface Simplified {
  version: string;
  words: Word[];
}
