import json
import re

def parse_dictionary_to_json(text):
    # Splitting the text into lines
    lines = text.split('\n')

    # Extracting metadata
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
            words.append({
                "traditional": traditional,
                "simplified": simplified,
                "pinyin": pinyin,
                "jyutping": jyutping,
                "meaning": [cleaned.strip() for cleaned in meaning.strip(' /').split('/')],
                "comments": comment
            })

    # Creating the final dictionary
    dictionary = {
        "version": metadata.get("Version", ""),
        "metadata": metadata,
        "words": words
    }

    return json.dumps(dictionary, ensure_ascii=False)

def main():
    # Reading the dictionary from a file and converting it to JSON
    with open("cccanto-webdist.txt", "r", encoding='utf-8') as file:
        text = file.read()
        json_output = parse_dictionary_to_json(text)

    # Writing the JSON output to a file
    with open("cccanto-webdist.json", "w", encoding='utf-8') as json_file:
        json_file.write(json_output)

if __name__ == "__main__":
    main()
