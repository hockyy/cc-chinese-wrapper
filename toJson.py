import json
import re


def split_bracketed_string(input_string):
    """
    Splits a string in the format of "[1] ABC [2] DEF ... [x] GHI" into a list of strings "ABC", "DEF", "GHI".

    Args:
    input_string (str): The string to be split.

    Returns:
    list: A list containing the split strings.
    """
    import re

    # Split the string using regular expression to find patterns like '[number]'
    split_strings = re.split(r'\[\d+\]', input_string)

    # Remove empty strings and strip whitespace from each element
    return [s.strip() for s in split_strings if s.strip()]

dictionary = dict()

def get_coalesce(data, prop, coalesce = ""):
    if(prop in data.keys()):
        if(data[prop]):
            return data[prop]
    return coalesce


def parse_character_makemeahanzi(json_string):
    """
    Maps a given JSON string of a Chinese character dictionary entry to the 'Character' interface.

    Args:
    json_string (str): A JSON string representing a dictionary entry.

    Returns:
    dict: A dictionary representing the 'Character' interface.
    """

    # Parse the JSON string into a Python dictionary
    character_data = json.loads(json_string)

    # Map the parsed data to the 'Character' interface
    character_interface = {
        "content": get_coalesce(character_data, "character", None),
        "id": "",  # ID is not provided in the sample, so it's left as an empty string
        "pinyin": get_coalesce(character_data, "pinyin", []),
        "meaning": [get_coalesce(character_data, "definition", None)] if "definition" in character_data else [],
        "decomposition": get_coalesce(character_data, "decomposition", None),
        "radical": get_coalesce(character_data, "radical", None),
        "etymology": get_coalesce(character_data, "etymology", {"type": None, "hint": None})
    }

    return character_interface


def parse_cantodict(json_data):
    """
    Maps a given JSON data of a Chinese character from the Cantodict to the 'Character' interface.

    Args:
    json_data (dict): A dictionary representing a dictionary entry.

    Returns:
    dict: A dictionary representing the 'Character' interface.
    """

    character_interface = {
        "content": get_coalesce(json_data, "chinese"),
        "cantodict_id": get_coalesce(json_data, "cantodict_id"),
        "pinyin": get_coalesce(json_data, "pinyin").split(' '),
        "jyutping": get_coalesce(json_data, "jyutping").split(' '),
        "notes": [get_coalesce(json_data, "notes", None)],
        "meaning": [get_coalesce(json_data, "definition", None)],
        "dialect": get_coalesce(json_data, "dialect", None),
        "freq": get_coalesce(json_data, "google_frequency", None),
        "variants": get_coalesce(json_data, "variants", []),
        "similar": get_coalesce(json_data, "similar", []),
        "stroke_count": get_coalesce(json_data, "stroke_count", None),
        "radical": get_coalesce(json_data, "radical", None),
    }

    tot = []
    for meaning in character_interface["meaning"]:
        if meaning:
            tot.extend(split_bracketed_string(meaning))

    character_interface["meaning"] = tot

    return character_interface

def parse_cantodict_compound(json_data):
    global dictionary
    compound_interface = {
        "id": len(dictionary['words']),
        "content": get_coalesce(json_data, "chinese"),
        "cantodict_id": get_coalesce(json_data, "cantodict_id"),
        "pinyin": get_coalesce(json_data, "pinyin").split(' '),
        "jyutping": get_coalesce(json_data, "jyutping").split(' '),
        "notes": [get_coalesce(json_data, "notes", None)],
        "meaning": [get_coalesce(json_data, "definition", None)],
        "dialect": get_coalesce(json_data, "dialect", None),
        "freq": get_coalesce(json_data, "google_frequency", None),
        "variants": get_coalesce(json_data, "variants", []),
        "similar": get_coalesce(json_data, "similar", []),
    }
    tot = []
    for meaning in compound_interface["meaning"]:
        if meaning:
            tot.extend(split_bracketed_string(meaning))

    compound_interface["meaning"] = tot

    dictionary['words'].append(compound_interface)

def parse_dictionary_to_json(text):
    global dictionary
    # Splitting the text into lines
    lines = text.split('\n')

    # Extracting metadata
    idx = 0
    metadata = {}
    for line in lines:
        if line.startswith('#'):
            # Splitting the line into key and value
            parts = line[2:].split(' ')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                metadata[key] = value
            tmp_data = re.search(r'^#! (\w+)=(.+)', line)
        if(tmp_data and tmp_data.group(1) and tmp_data.group(2)):
            metadata[tmp_data.group(1).strip()] = tmp_data.group(2).strip()


    # Parsing the words
    words = []
    for line in lines:
        if not line.startswith('#') and line.strip() != '':
            # Splitting the line into three parts
            parts = line.split(maxsplit=2)
            traditional, simplified, rest = parts

            # Splitting the rest into two parts
            rest_parts = rest.split('/', 1)
            phonetic_part, meaning_part = rest_parts[0], rest_parts[1]

            # Extracting pinyin and jyutping using regex
            pinyin = re.search(r'\[(.*?)\]', phonetic_part)
            jyutping = re.search(r'\{(.*?)\}', phonetic_part)
            pinyin = pinyin.group(1).strip() if pinyin else ""
            jyutping = jyutping.group(1).strip() if jyutping else ""

            # Extracting comments
            split_meaning = meaning_part.split('#')
            comment = split_meaning[1].strip() if len(split_meaning) > 1 else ""
            meaning = split_meaning[0].replace('M:', '/')
            # Adding the word to the list
            idx = len(words)
            words.append({
                "id": str(idx),
                "content": traditional,
                "simplified": simplified,
                "pinyin": pinyin,
                "jyutping": jyutping,
                "meaning": [cleaned.strip() for cleaned in meaning.strip(' /').split('/')],
                "notes": [comment] if comment else []
            })

    # Creating the final dictionary
    dictionary["version"] = metadata.get("Version", "")
    if(dictionary["version"] == ""):
        dictionary["version"] = metadata.get("version", "")
    dictionary["words"] = words

def resolveSame(cantodict, makemeahanzi):
    # print(cantodict, makemeahanzi)
    ported_data = ['etymology', 'decomposition']
    # // Merge meaning
    for prop in ported_data:
        if(prop in makemeahanzi.keys()):
            cantodict[prop] = makemeahanzi[prop]
    makemeahanzi['meaning'].extend(cantodict['meaning'])
    cantodict['meaning'] = makemeahanzi['meaning']
    cantodict['pinyin'].extend(makemeahanzi['pinyin'])
    return cantodict

def parse_cccanto():
    # Reading the dictionary from a file and converting it to JSON
    with open("public/cccanto-webdist.txt", "r", encoding='utf-8') as file:
        text = file.read()
        parse_dictionary_to_json(text)

    with open("public/detail-compounds.json", "r", encoding='utf-8') as file:
        compounds = json.load(file)
        for key, val in compounds.items():
            entry = parse_cantodict_compound(val)

def parse_cccedict():
    # Reading the dictionary from a file and converting it to JSON
    with open("public/cedict_ts.u8", "r", encoding='utf-8') as file:
        text = file.read()
        parse_dictionary_to_json(text)

def parse_characters():
    global dictionary
    characters_map = dict()
    characters_list = []
    # Parsing and adding entries from "make me a hanzi" file
    with open("public/dictionary.txt", "r", encoding='utf-8') as file:
        for line in file:
            entry = parse_character_makemeahanzi(line)
            if entry["content"]:
                characters_map[entry["content"]] = entry

    with open("public/detail-characters.json", "r", encoding='utf-8') as file:
        cantodict_characters = json.load(file)
        for key, val in cantodict_characters.items():
            entry = parse_cantodict(val)
            # If there is already an entry in characters_map, update it
            if entry["content"] in characters_map:
                merged = resolveSame(entry, characters_map[entry["content"]])
                characters_map[entry["content"]].update(merged)
            else:
                characters_map[entry["content"]] = entry

    # Assigning IDs and creating characters list
    characters_list = []
    for idx, val in enumerate(characters_map.values()):
        val["id"] = str(idx)
        characters_list.append(val)
        
    dictionary["characters"] = characters_list

def write(filename = "cantodict"):
    global dictionary

    output_json = json.dumps(dictionary, ensure_ascii=False)
    # Writing the JSON output to a file
    with open(f"public/{filename}.json", "w", encoding='utf-8') as json_file:
        json_file.write(output_json)

def parse_chinese():
    parse_cccedict()
    parse_characters()
    write("chinese")

def parse_canto():
    parse_cccanto()
    parse_characters()
    write("cantodict")

def main():
    # parse_canto()
    parse_chinese()


if __name__ == "__main__":
    main()
