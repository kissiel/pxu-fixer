#!/usr/bin/env python3

import os
import sys

from dataclasses import dataclass
from pprint import pprint

from openai import OpenAI


@dataclass
class PxuRecord:
    path: str
    location: tuple[int, int]
    text: str
    replacement: str = ""


def find_pxu_files(path):
    """
    A generator that yield all the .pxu files in the given path (recurssively)
    """
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".pxu"):
                yield os.path.join(root, file)

def find_records_in_pxu(path):
    """
    A generator that yield all the records in the given .pxu file.
    The records are blocks of text separated by one or more empty lines.
    """
    with open(path, "r") as f:
        record = ""
        start_line = 0
        end_line = 0
        for line_no, line in enumerate(f):
            if line.strip():
                if not record:
                    start_line = line_no
                record += line
            elif record:
                end_line = line_no - 1
                yield PxuRecord(path, (start_line, end_line), record)
                record = ""
        if record:
            end_line = line_no
            yield PxuRecord(path, (start_line, end_line), record)

def record_to_dict(record):
    """
    Convert a record to a dictionary.
    If the line of a record starts with a letter, 
    then the word before the colon is the field name.
    if it starts with a whitespace then its a continuation of the previous field.
    """
    result = {}
    field = None
    for line in record:
        if line[0].isalpha() or line[0] == "_":
            try:
                field, value = line.split(":", 1)
                result[field] = value.strip()
            except ValueError:

                print("Error: ", line)
        elif field: 
            result[field] += "\n" + line
    return result
        

class PxuFixer:
    def __init__(self):
        OPENAI_KEY = os.environ.get("OPENAI_KEY")
        if not OPENAI_KEY:
            raise SystemExit("OPENAI_KEY environment variable is not set.")
        self._client = OpenAI(api_key=OPENAI_KEY)
        self._sys_prompt = open('system_prompt.txt', 'r').read()
        self._model = "gpt-4-turbo-preview"
        # self._model = "gpt-3.5-turbo-0125"
    
    def process_pxu(self, pxu_text):
        messages = [
            {
                "role": "system",
                "content": self._sys_prompt
            },
            {
                "role": "user",
                "content": pxu_text
            }
        ]
        completion = self._client.chat.completions.create(
            model=self._model,
            messages = messages,
        )
        return completion.choices[0].message.content.strip()

    

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: fix_pxus.py <path>")
   
    
    # find all the pxu files
    pxu_files = list(find_pxu_files(sys.argv[1]))

    pxu_fixer = PxuFixer()
    for pxu_file in pxu_files:
        recs = list(find_records_in_pxu(pxu_file))
       
        for record in recs:
            print(record.path, record.location)
            #print(record.text)
            res = pxu_fixer.process_pxu(record.text)
            if "===NO CHANGE===" in res:
                record.replacement = record.text
            else:
                record.replacement = res
            print(res)

        # replace the contents of the file with the new contents
        with open(pxu_file, "w") as f:
            for record in recs:
                f.write(record.replacement)
                f.write("\n\n")
            

if __name__ == "__main__":
    main()