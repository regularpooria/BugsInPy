import os
import json
import sys


def load_instructions(json_path):
    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_change(file_path, old_code, new_code):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if old_code not in content:
        print(f"⚠️  Code to replace not found in {file_path}")
        return False

    new_content = content.replace(old_code, new_code)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ Successfully replaced code in {file_path}")
    return True


def main():
    if len(sys.argv) != 4:
        print("Usage: python replace_code.py <project> <bug_id> <work_dir>")
        sys.exit(1)

    project = sys.argv[1]
    bug_id = sys.argv[2]
    work_dir = sys.argv[3]
    json_file = "/home/user/BugsInPy/framework/results/llm.json"

    instructions = load_instructions(json_file)
    selected_instruction = None
    for instruction in instructions:
        if instruction["project"].lower() == project.lower() and instruction[
            "bug"
        ] == str(bug_id):
            selected_instruction = instruction

    if selected_instruction is None:
        print(f"❌ No patch found for project '{project}' with bug id '{bug_id}'")
        sys.exit(1)

    file_path = os.path.join(work_dir, selected_instruction["file"])
    for change in selected_instruction["llm"]["changes"]:
        old_code = change["old"]
        new_code = change["new"]
        apply_change(file_path, old_code, new_code)


main()
