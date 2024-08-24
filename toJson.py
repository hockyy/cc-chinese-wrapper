from abc import ABC, abstractmethod
import json
import re
from typing import Dict, List, Union

class DictionaryEntry:
    def __init__(self, id: str = "", content: str = "", simplified: str = "", pinyin: str = "", jyutping: str = "", meaning: List[str] = None, notes: List[str] = None):
        self.id = id
        self.content = content
        self.simplified = simplified
        self.pinyin = pinyin
        self.jyutping = jyutping
        self.meaning = meaning or []
        self.notes = notes or []

class CharacterEntry(DictionaryEntry):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
                        dictionary.add_character(entry)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except PermissionError:
            print(f"Error: Permission denied when trying to read '{filename}'.")
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
            meaning=[cls.get_coalesce(character_data, "definition")] if "definition" in character_data else [],
            decomposition=cls.get_coalesce(character_data, "decomposition"),
            radical=cls.get_coalesce(character_data, "radical"),
            etymology=cls.get_coalesce(character_data, "etymology", {"type": None, "hint": None})
        )

        class CantoDictParser(BaseParser):
    @classmethod
    def parse_file(cls, filename: str) -> Dictionary:
        dictionary = Dictionary()
        dictionary.version = "CantoDict-1.0"  # You may want to adjust this version

        try:
            with open(filename, "r", encoding='utf-8') as file:
                data = json.load(file)
                for entry_data in data.values():
                    entries = cls.parse_entry(entry_data)
                    for entry in entries:
                        if isinstance(entry, CharacterEntry):
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
    def parse_entry(cls, entry: dict) -> List[Union[CharacterEntry, DictionaryEntry]]:
        if cls.is_character_entry(entry):
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
            words.extend(cls.parse_entry(entry_data))
        return words

    @classmethod
    def parse_entry(cls, entry: dict) -> List[DictionaryEntry]:
        base_entry = DictionaryEntry(
            id=str(entry.get("id", "")),
            content=entry.get("variants", [{}])[0].get("w", ""),
            jyutping=cls.extract_jyutping(entry),
            notes=entry.get("labels", []) + entry.get("poses", [])
        )

        entries = []
        for meaning, examples in cls.extract_meanings_and_examples(entry):
            new_entry = DictionaryEntry(
                id=base_entry.id,
                content=base_entry.content,
                jyutping=base_entry.jyutping,
                notes=base_entry.notes.copy(),
                meaning=[meaning],
            )
            if examples:
                new_entry.notes.extend(examples)
            entries.append(new_entry)

        return entries

    @classmethod
    def extract_jyutping(cls, entry: dict) -> str:
        if entry.get("variants") and entry["variants"][0].get("p"):
            return " ".join(syllable.get("S", {}).get("t", "") for syllable in entry["variants"][0]["p"][0])
        return ""

    @classmethod
    def extract_meanings_and_examples(cls, entry: dict) -> List[Tuple[str, List[str]]]:
        meanings_and_examples = []
        for def_entry in entry.get("defs", []):
            for lang in ["yue", "eng"]:
                for definition in def_entry.get(lang, []):
                    meaning = next((item[1] for item in definition if item[0] == "T"), "")
                    examples = [item[1] for item in definition if item[0] == "L"]
                    if meaning:
                        meanings_and_examples.append((meaning, examples))
        return meanings_and_examples

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
                    pinyin=pinyin,
                    jyutping=jyutping,
                    meaning=[cleaned.strip() for cleaned in meaning.strip(' /').split('/')],
                    notes=[comment] if comment else []
                ))
        return words

class DictionaryParser:
    def __init__(self):
        self.dictionary = Dictionary()

    def parse_wordshk(self, filename: str) -> None:
        wordshk_dict = WordsHKParser.parse_file(filename)
        for word in wordshk_dict.words.values():
            self.dictionary.add_word(word)

    def parse_cantodict(self, filename: str) -> None:
        cantodict = CantoDictParser.parse_file(filename)
        for word in cantodict.words.values():
            self.dictionary.add_word(word)
        for char in cantodict.characters.values():
            self.dictionary.add_character(char)

    def parse_makemeahanzi(self, filename: str) -> None:
        makemeahanzi_dict = MakeMeAHanziParser.parse_file(filename)
        for char in makemeahanzi_dict.characters.values():
            self.dictionary.add_character(char)

    def parse_cccedict(self, filename: str) -> None:
        cccedict_dict = CCEDICTParser.parse_file(filename)
        for word in cccedict_dict.words.values():
            self.dictionary.add_word(word)

    def parse_canto(self) -> None:
        self.parse_cccedict("public/cccanto-webdist.txt")
        self.parse_wordshk("public/wordshk_data.json")
        self.parse_cantodict("public/detail-compounds.json")
        self.parse_cantodict("public/detail-characters.json")
        self.parse_makemeahanzi("public/dictionary.txt")

    def parse_chinese(self) -> None:
        self.parse_cccedict("public/cedict_ts.u8")
        self.parse_makemeahanzi("public/dictionary.txt")

    def write(self, filename: str) -> None:
        try:
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