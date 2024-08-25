from abc import ABC, abstractmethod
import json
import re
from typing import Dict, List, Union, Any, Tuple

class DictionaryEntry:
    def __init__(self, id: str = None, content: str = "", simplified: str = "", pinyin = None, jyutping = None, meaning: List[str] = None, notes: List[str] = None):
        self.id = id
        self.content = content
        self.simplified = simplified
        self.pinyin = pinyin
        self.jyutping = jyutping
        self.meaning = meaning or []
        self.notes = notes or []

class CharacterEntry(DictionaryEntry):
    def __init__(self, id: str = None, content: str = "", simplified: str = "", pinyin = [], jyutping = [], 
                 meaning: List[str] = None, notes: List[str] = None, **kwargs):
        super().__init__(id=id, content=content, simplified=simplified, pinyin=pinyin, jyutping=jyutping, 
                         meaning=meaning, notes=notes)
        self.decomposition = kwargs.get('decomposition', '')
        self.radical = kwargs.get('radical', '')
        self.etymology = kwargs.get('etymology', {})
        self.stroke_count = kwargs.get('stroke_count', '')
        self.variants = kwargs.get('variants', [])
        self.similar = kwargs.get('similar', [])
        self.freq = kwargs.get('freq', '')

class Dictionary:
    def __init__(self):
        self.version: str = "2023-08-24"
        self.words: Dict[str, DictionaryEntry] = {}
        self.characters: Dict[str, CharacterEntry] = {}
        self.word_id_counter: int = 0
        self.character_id_counter: int = 0

    def add_word(self, word: DictionaryEntry) -> None:
        if word.id is None or word.id in self.words:
            word.id = str(self.word_id_counter)
            self.word_id_counter += 1
        self.words[word.id] = word

    def add_character(self, character: CharacterEntry) -> None:
        if character.content in self.characters:
            existing = self.characters[character.content]
            self.resolveSame(existing, character)
        else:
            if character.id is None or character.id in self.characters:
                character.id = str(self.character_id_counter)
                self.character_id_counter += 1
            self.characters[character.content] = character

    def resolveSame(self, existing: CharacterEntry, new: CharacterEntry) -> CharacterEntry:
        """
        Merge properties from a new CharacterEntry into an existing one.
        
        This method updates the existing entry with non-None values from the new entry.
        For list properties, it extends the existing list and removes duplicates.
        For dict properties, it updates the existing dict with new key-value pairs.
        For other types, it replaces the existing value if it's None or an empty string.

        Args:
            existing (CharacterEntry): The existing character entry to update.
            new (CharacterEntry): The new character entry containing updated information.

        Returns:
            CharacterEntry: The updated existing character entry.
        """
        merge_props = ['etymology', 'decomposition', 'meaning', 'pinyin', 'jyutping', 'notes', 'radical', 'stroke_count', 'variants', 'similar']

        for prop in merge_props:
            existing_value = getattr(existing, prop, None)
            new_value = getattr(new, prop, None)

            if new_value is not None:
                if isinstance(new_value, list):
                    if existing_value is None or not existing_value:
                        setattr(existing, prop, new_value)
                    else:
                        existing_value.extend(new_value)
                        setattr(existing, prop, list(dict.fromkeys(existing_value)))
                elif isinstance(new_value, dict):
                    if existing_value is None:
                        setattr(existing, prop, new_value)
                    else:
                        existing_value.update(new_value)
                else:
                    if existing_value is None or existing_value == '':
                        setattr(existing, prop, new_value)

        return existing

    def to_json(self) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
        return {
            "version": self.version,
            "words": [vars(word) for word in self.words.values()],
            "characters": [vars(char) for char in self.characters.values()]
        }

class DictionaryParserInterface(ABC):
    @classmethod
    @abstractmethod
    def parse_file(cls, filename: str) -> Dictionary:
        """
        Parse a dictionary file and return a Dictionary object.
        
        :param filename: Path to the dictionary file
        :return: A Dictionary object containing parsed entries
        """
        pass

    @classmethod
    @abstractmethod
    def parse_entry(cls, entry: Union[str, dict]) -> List[Union[DictionaryEntry, CharacterEntry]]:
        """
        Parse a single dictionary entry and return a list of DictionaryEntry or CharacterEntry objects.
        
        :param entry: A string or dictionary containing entry data
        :return: A list of DictionaryEntry or CharacterEntry objects
        """
        pass

class BaseParser(DictionaryParserInterface):
    @staticmethod
    def get_coalesce(data: dict, prop: str, coalesce: Any = "") -> Any:
        return data.get(prop, coalesce) if data.get(prop) else coalesce

    @staticmethod
    def split_bracketed_string(input_string: str) -> List[str]:
        split_strings = re.split(r'\[\d+\]', input_string)
        return [s.strip() for s in split_strings if s.strip()]

    @classmethod
    def parse_file(cls, filename: str) -> Dictionary:
        raise NotImplementedError("This method should be implemented by subclasses")

    @classmethod
    def parse_entry(cls, entry: Union[str, dict]) -> List[Union[DictionaryEntry, CharacterEntry]]:
        raise NotImplementedError("This method should be implemented by subclasses")

class MakeMeAHanziParser(BaseParser):
    @classmethod
    def parse_file(cls, filename: str) -> Dictionary:
        dictionary = Dictionary()
        dictionary.version = "MakeMeAHanzi-1.0"  # You may want to adjust this version
        
        try:
            with open(filename, "r", encoding='utf-8') as file:
                for line in file:
                    entries = cls.parse_entry(line)
                    for entry in entries:
                        dictionary.add_character(entry)  # Changed from add_word to add_character
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON in '{filename}': {str(e)}")
        except Exception as e:
            print(f"An unexpected error occurred while parsing '{filename}': {str(e)}")
        
        return dictionary

    @classmethod
    def parse_entry(cls, entry: str) -> List[CharacterEntry]:
        try:
            character_data = json.loads(entry)
            parsed_entry = cls.parse(character_data)
            return [parsed_entry] if parsed_entry.content else []
        except json.JSONDecodeError:
            print(f"Error parsing entry: {entry}")
            return []

    @classmethod
    def parse(cls, character_data: dict) -> CharacterEntry:
        return CharacterEntry(
            content=cls.get_coalesce(character_data, "character"),
            pinyin=cls.get_coalesce(character_data, "pinyin", []),
            jyutping=[],
            meaning=[cls.get_coalesce(character_data, "definition")] if "definition" in character_data else [],
            decomposition=cls.get_coalesce(character_data, "decomposition"),
            radical=cls.get_coalesce(character_data, "radical"),
            etymology=cls.get_coalesce(character_data, "etymology", {"type": None, "hint": None}),
        )

class CantoDictParser(BaseParser):
    @classmethod
    def parse_file(cls, filename: str, is_char: bool = True) -> Dictionary:
        dictionary = Dictionary()
        dictionary.version = "CantoDict-1.0"  # You may want to adjust this version

        try:
            with open(filename, "r", encoding='utf-8') as file:
                data = json.load(file)
                for entry_data in data.values():
                    entries = cls.parse_entry(entry_data, is_char)
                    for entry in entries:
                        if is_char:
                            dictionary.add_character(entry)
                        else:
                            dictionary.add_word(entry)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except json.JSONDecodeError:
            print(f"Error: '{filename}' is not a valid JSON file.")
        except Exception as e:
            print(f"An unexpected error occurred while parsing '{filename}': {str(e)}")

        return dictionary

    @classmethod
    def parse_entry(cls, entry: dict, is_char: bool = True) -> List[Union[CharacterEntry, DictionaryEntry]]:
        if is_char:
            return [cls.parse_character(entry)]
        else:
            return [cls.parse_compound(entry)]

    @classmethod
    def is_character_entry(cls, entry: dict) -> bool:
        return "stroke_count" in entry or "radical" in entry

    @classmethod
    def parse_character(cls, json_data: dict) -> CharacterEntry:
        return CharacterEntry(
            content=cls.get_coalesce(json_data, "chinese"),
            pinyin=cls.get_coalesce(json_data, "pinyin", "").split(),
            jyutping=cls.get_coalesce(json_data, "jyutping", "").split(),
            notes=[cls.get_coalesce(json_data, "notes")],
            meaning=[m for meaning in [cls.get_coalesce(json_data, "definition")] if meaning for m in cls.split_bracketed_string(meaning)],
            radical=cls.get_coalesce(json_data, "radical"),
            stroke_count=cls.get_coalesce(json_data, "stroke_count"),
            variants=cls.get_coalesce(json_data, "variants", []),
            similar=cls.get_coalesce(json_data, "similar", []),
            freq=cls.get_coalesce(json_data, "google_frequency")
        )

    @classmethod
    def parse_compound(cls, json_data: dict) -> DictionaryEntry:
        return DictionaryEntry(
            content=cls.get_coalesce(json_data, "chinese"),
            pinyin=cls.get_coalesce(json_data, "pinyin", "").split(),
            jyutping=cls.get_coalesce(json_data, "jyutping", "").split(),
            notes=[cls.get_coalesce(json_data, "notes")],
            meaning=[m for meaning in [cls.get_coalesce(json_data, "definition")] if meaning for m in cls.split_bracketed_string(meaning)]
        )

class WordsHKParser(BaseParser):
    @classmethod
    def parse_file(cls, filename: str) -> Dictionary:
        dictionary = Dictionary()
        
        try:
            with open(filename, "r", encoding='utf-8') as file:
                wordshk_data = json.load(file)
            
            dictionary.version = "WordsHK-" + wordshk_data.get("version", "unknown")
            words = cls.parse_words(wordshk_data)
            
            for word in words:
                dictionary.add_word(word)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except json.JSONDecodeError:
            print(f"Error: '{filename}' is not a valid JSON file.")
        except Exception as e:
            print(f"An unexpected error occurred while parsing '{filename}': {str(e)}")
        
        return dictionary

    @classmethod
    def parse_words(cls, wordshk_data: dict) -> List[DictionaryEntry]:
        words = []
        for entry_data in wordshk_data.values():
            entry = cls.parse_entry(entry_data)
            if(entry.content == "" or entry.jyutping == [] or len(entry.meaning) == 0):
                continue
            words.append(entry)
        return words

    @classmethod
    def parse_entry(cls, entry: dict) -> DictionaryEntry:
        return DictionaryEntry(
            content=cls.extract_content(entry),
            jyutping=cls.extract_jyutping(entry),
            meaning=cls.extract_meanings(entry)
        )

    @classmethod
    def extract_content(cls, entry: dict) -> str:
        try:
            if entry.get("variants"):
                return entry["variants"][0].get("w", "")
        except:
            return ""

    @classmethod
    def extract_jyutping(cls, entry: dict) -> List[str]:
        try:
            if entry.get("variants") and entry["variants"][0].get("p"):
                all_pronunciations = entry["variants"][0]["p"]
                
                jyutping_list = []
                
                for pronunciation in all_pronunciations:
                    jyutping = []
                    for syllable in pronunciation:
                        s_dict = syllable.get("S", {})
                        initial = s_dict.get("i", "")
                        nucleus = s_dict.get("n", "")
                        coda = s_dict.get("c", "")
                        tone = s_dict.get("t", "")
                        
                        # Combine parts, handling potential None values
                        syllable_parts = [initial, nucleus, coda]
                        syllable_str = "".join(part for part in syllable_parts if part)
                        
                        # Add tone if it exists
                        if tone:
                            syllable_str += tone[-1]  # Take only the last character (the tone number)
                        
                        if syllable_str:
                            jyutping.append(syllable_str.lower())
                    
                    if jyutping:
                        jyutping_list.append(" ".join(jyutping))
                if(jyutping_list == []): return ""
                return jyutping_list[0]
        except Exception as e:
            print(f"Error in extract_jyutping: {str(e)}")
        
        return []

    @classmethod
    def extract_meanings(cls, entry: dict) -> List[str]:
        try:
            meanings = []
            for def_entry in entry.get("defs", []):
                for lang in ["eng"]:
                    if lang in def_entry:
                        meaning = [
                            item[1].split(';') for item in def_entry[lang][0] 
                            if item[0] in ["T", "L"]
                        ]
                        meanings.extend(meaning)
            return meanings
        except:
            return []

class CCEDICTParser(BaseParser):
    @classmethod
    def parse_file(cls, filename: str) -> Dictionary:
        dictionary = Dictionary()
        
        try:
            with open(filename, "r", encoding='utf-8') as file:
                text = file.read()
            
            lines = text.split('\n')
            metadata = cls.extract_metadata(lines)
            words = cls.parse_words(lines)
            
            dictionary.version = metadata.get("Version", "") or metadata.get("version", "")
            for word in words:
                dictionary.add_word(word)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except Exception as e:
            print(f"An unexpected error occurred while parsing '{filename}': {str(e)}")
        
        return dictionary

    @classmethod
    def extract_metadata(cls, lines: List[str]) -> Dict[str, str]:
        metadata = {}
        for line in lines:
            if line.startswith('#'):
                parts = line[2:].split(' ', 1)
                if len(parts) == 2:
                    key, value = parts
                    metadata[key.strip()] = value.strip()
                tmp_data = re.search(r'^#! (\w+)=(.+)', line)
                if tmp_data and tmp_data.group(1) and tmp_data.group(2):
                    metadata[tmp_data.group(1).strip()] = tmp_data.group(2).strip()
        return metadata

    @classmethod
    def parse_words(cls, lines: List[str]) -> List[DictionaryEntry]:
        words = []
        for line in lines:
            if not line.startswith('#') and line.strip() != '':
                parts = line.split(maxsplit=2)
                if len(parts) != 3:
                    continue
                traditional, simplified, rest = parts

                rest_parts = rest.split('/', 1)
                if len(rest_parts) != 2:
                    continue
                phonetic_part, meaning_part = rest_parts

                pinyin = re.search(r'\[(.*?)\]', phonetic_part)
                jyutping = re.search(r'\{(.*?)\}', phonetic_part)
                pinyin = pinyin.group(1).strip() if pinyin else ""
                jyutping = jyutping.group(1).strip() if jyutping else ""

                split_meaning = meaning_part.split('#')
                comment = split_meaning[1].strip() if len(split_meaning) > 1 else ""
                meaning = split_meaning[0].replace('M:', '/')

                words.append(DictionaryEntry(
                    content=traditional,
                    simplified=simplified,
                    pinyin=[pinyin],
                    jyutping=[jyutping],
                    meaning=[cleaned.strip() for cleaned in meaning.strip(' /').split('/')],
                    notes=[comment] if comment else []
                ))
        return words

class DictionaryParser:
    def __init__(self, debug=False, debug_limit=10):
        self.dictionary = Dictionary()
        self.debug = debug
        self.debug_limit = debug_limit

    def _parse_limited(self, items, add_method, source_name):
        print(f"Adding {source_name}: {len(items)} entries {add_method.__name__}")
        for i, item in enumerate(items):
            add_method(item)
            if self.debug and i + 1 >= self.debug_limit:
                print(f"Debug limit of {self.debug_limit} entries reached for {source_name}.")
                break

    def parse_wordshk(self, filename: str) -> None:
        wordshk_dict = WordsHKParser.parse_file(filename)
        self._parse_limited(wordshk_dict.words.values(), self.dictionary.add_word, "WordsHK")

    def parse_cantodict_words(self, filename: str) -> None:
        cantodict = CantoDictParser.parse_file(filename, False)
        self._parse_limited(cantodict.words.values(), self.dictionary.add_word, "CantoDict words")

    def parse_cccedict(self, filename: str) -> None:
        cccedict_dict = CCEDICTParser.parse_file(filename)
        self._parse_limited(cccedict_dict.words.values(), self.dictionary.add_word, "CC-CEDICT")

    def parse_cantodict(self, filename: str) -> None:
        cantodict = CantoDictParser.parse_file(filename, True)
        self._parse_limited(cantodict.characters.values(), self.dictionary.add_character, "CantoDict characters")

    def parse_makemeahanzi(self, filename: str) -> None:
        makemeahanzi_dict = MakeMeAHanziParser.parse_file(filename)
        self._parse_limited(makemeahanzi_dict.characters.values(), self.dictionary.add_character, "MakeMeAHanzi")


    def parse_canto(self) -> None:
        self.parse_cccedict("public/cccanto-webdist.txt")
        self.parse_wordshk("public/dict.json")
        self.parse_cantodict_words("public/detail-compounds.json")
        self.parse_cantodict("public/detail-characters.json")
        self.parse_makemeahanzi("public/dictionary.txt")

    def parse_chinese(self) -> None:
        self.parse_cccedict("public/cedict_ts.u8")
        self.parse_makemeahanzi("public/dictionary.txt")

    def write(self, filename: str) -> None:
        try:
            print(f"Words: {len(self.dictionary.words)}")
            print(f"Chars: {len(self.dictionary.characters)}")
            output_json = json.dumps(self.dictionary.to_json(), ensure_ascii=False)
            with open(f"public/{filename}.json", "w", encoding='utf-8') as json_file:
                json_file.write(output_json)
        except Exception as e:
            print(f"An error occurred while writing to '{filename}': {str(e)}")

def main():
    # Parse Cantonese dictionary
    canto_parser = DictionaryParser()
    canto_parser.parse_canto()
    canto_parser.write("cantodict")

    # Parse Chinese (Mandarin) dictionary
    chinese_parser = DictionaryParser()
    chinese_parser.parse_chinese()
    chinese_parser.write("chinese")

if __name__ == "__main__":
    main()