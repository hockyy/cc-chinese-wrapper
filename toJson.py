import json
import re

characters_map = dict()
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
        "pinyin": [get_coalesce(json_data, "pinyin")],
        "jyutping": [get_coalesce(json_data, "jyutping")],
        "notes": [get_coalesce(json_data, "notes", None)],
        "meaning": [get_coalesce(json_data, "definition", None)],
        "dialect": get_coalesce(json_data, "dialect", None),
        "freq": get_coalesce(json_data, "google_frequency", None),
        "variants": get_coalesce(json_data, "variants", []),
        "similar": get_coalesce(json_data, "similar", []),
        "stroke_count": get_coalesce(json_data, "stroke_count", None),
        "radical": get_coalesce(json_data, "radical", None),
    }

    return character_interface

def parse_cantodict_compound(json_data):
    global dictionary
    character_interface = {
        "id": len(dictionary['words']),
        "content": get_coalesce(json_data, "chinese"),
        "cantodict_id": get_coalesce(json_data, "cantodict_id"),
        "pinyin": [get_coalesce(json_data, "pinyin")],
        "jyutping": [get_coalesce(json_data, "jyutping")],
        "notes": [get_coalesce(json_data, "notes", None)],
        "meaning": [get_coalesce(json_data, "definition", None)],
        "dialect": get_coalesce(json_data, "dialect", None),
        "freq": get_coalesce(json_data, "google_frequency", None),
        "variants": get_coalesce(json_data, "variants", []),
        "similar": get_coalesce(json_data, "similar", []),
    }
    dictionary['words'].append(character_interface)

def parse_dictionary_to_json(text):
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
    dictionary = {
        "version": metadata.get("Version", ""),
        "words": words,
        # "characters" : # TODO: put it here, and read public/dictionary.txt, having entries as the one I sent
    }

    return dictionary

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

def main():
    global characters_map
    global dictionary
    # Reading the dictionary from a file and converting it to JSON
    with open("public/cccanto-webdist.txt", "r", encoding='utf-8') as file:
        text = file.read()
        dictionary = parse_dictionary_to_json(text)

    characters_list = []
    # Parsing and adding entries from "make me a hanzi" file
    with open("public/dictionary.txt", "r", encoding='utf-8') as file:
        for line in file:
            entry = parse_character_makemeahanzi(line)
            if entry["content"]:
                characters_map[entry["content"]] = entry
    print(len(characters_map))
    ans = 0
    with open("public/detail-characters.json", "r", encoding='utf-8') as file:
        cantodict_characters = json.load(file)
        print(len(cantodict_characters.items()))
        for key, val in cantodict_characters.items():
            entry = parse_cantodict(val)
            # If there is already an entry in characters_map, update it
            if entry["content"] in characters_map:
                ans += 1
                merged = resolveSame(entry, characters_map[entry["content"]])
                characters_map[entry["content"]].update(merged)
            else:
                characters_map[entry["content"]] = entry
    print(ans, " has the same entry")

    # Assigning IDs and creating characters list
    characters_list = []
    for idx, val in enumerate(characters_map.values()):
        val["id"] = str(idx)
        characters_list.append(val)

    with open("public/detail-compounds.json", "r", encoding='utf-8') as file:
        compounds = json.load(file)
        print(len(compounds.items()))
        for key, val in compounds.items():
            entry = parse_cantodict_compound(val)

    dictionary["characters"] = characters_list
    output_json = json.dumps(dictionary, ensure_ascii=False)
    print(len(dictionary['words']))
    print(len(dictionary['characters']))

    # Writing the JSON output to a file
    with open("public/cantodict.json", "w", encoding='utf-8') as json_file:
        json_file.write(output_json)

if __name__ == "__main__":
    main()
