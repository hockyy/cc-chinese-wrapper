export interface Word {
  id: string,
  traditional: string;
  simplified: string;
  pinyin: string;
  jyutping: string;
  meaning: string[];
  comments: string;
}

export interface Simplified {
  version: string;
  words: Word[];
}
