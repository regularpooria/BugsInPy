import os
import json
import sys
import ast
import re


def load_instructions(json_path):
    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_function_in_code(content, function_name, class_name=None):
    """
    Find a function by name and return its start and end positions in the code.
    Can search for functions in classes or at module level.
    Returns (start_pos, end_pos, indentation) or None if not found.
    """
    try:
        tree = ast.parse(content)

        # Find the function node
        target_node = None

        if class_name:
            # Search for function within a specific class
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Search within this class
                    for child in ast.walk(node):
                        if (
                            isinstance(child, ast.FunctionDef)
                            and child.name == function_name
                        ):
                            target_node = child
                            break
                    break
        else:
            # Search for function anywhere (class methods or module-level functions)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    target_node = node
                    break

        if target_node is None:
            return None

        # Get the lines of the original content
        lines = content.splitlines(True)  # Keep line endings

        # Get start line (subtract 1 because ast uses 1-based indexing)
        start_line = target_node.lineno - 1

        # Find the end of the function by looking for the next line with same or less indentation
        # or another function/class definition
        function_indent = len(lines[start_line]) - len(lines[start_line].lstrip())

        end_line = start_line + 1
        while end_line < len(lines):
            line = lines[end_line]
            # Skip empty lines and comments
            if line.strip() == "" or line.strip().startswith("#"):
                end_line += 1
                continue

            # Check indentation
            current_indent = len(line) - len(line.lstrip())

            # If we find a line with same or less indentation that's not empty/comment, we've found the end
            if current_indent <= function_indent and line.strip():
                break

            end_line += 1

        # Calculate character positions
        start_pos = sum(len(lines[i]) for i in range(start_line))
        end_pos = sum(len(lines[i]) for i in range(end_line))

        return start_pos, end_pos, function_indent

    except SyntaxError:
        # If AST parsing fails, fall back to regex method
        return find_function_regex(content, function_name, class_name)


def find_function_regex(content, function_name, class_name=None):
    """
    Fallback method using regex to find function boundaries.
    Can search within a specific class or anywhere in the module.
    """
    if class_name:
        # Pattern to match function within a specific class
        class_pattern = rf"^(\s*)class\s+{re.escape(class_name)}\s*[:\(]"
        lines = content.splitlines(True)

        # Find the class first
        class_start = None
        class_indent = None
        for i, line in enumerate(lines):
            match = re.match(class_pattern, line)
            if match:
                class_start = i
                class_indent = len(match.group(1))
                break

        if class_start is None:
            return None

        # Find the end of the class to limit our search
        class_end = len(lines)
        for i in range(class_start + 1, len(lines)):
            line = lines[i]
            if line.strip() == "" or line.strip().startswith("#"):
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= class_indent and line.strip():
                class_end = i
                break

        # Now search for the function within the class
        function_pattern = rf"^(\s*)def\s+{re.escape(function_name)}\s*\("
        for i in range(class_start + 1, class_end):
            line = lines[i]
            match = re.match(function_pattern, line)
            if match:
                function_indent = len(match.group(1))
                # Make sure this function is actually within the class (proper indentation)
                if function_indent > class_indent:
                    return find_function_end_regex(lines, i, function_indent)

        return None
    else:
        # Pattern to match function definition anywhere
        pattern = rf"^(\s*)def\s+{re.escape(function_name)}\s*\("

        lines = content.splitlines(True)
        start_line = None
        function_indent = None

        # Find the function start
        for i, line in enumerate(lines):
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                start_line = i
                function_indent = len(match.group(1))
                break

        if start_line is None:
            return None

        return find_function_end_regex(lines, start_line, function_indent)


def find_function_end_regex(lines, start_line, function_indent):
    """
    Helper function to find the end of a function given its start line and indentation.
    """
    # Find the function end
    end_line = start_line + 1
    while end_line < len(lines):
        line = lines[end_line]
        # Skip empty lines and comments
        if line.strip() == "" or line.strip().startswith("#"):
            end_line += 1
            continue

        # Check indentation
        current_indent = len(line) - len(line.lstrip())

        # If we find a line with same or less indentation that's not empty/comment, we've found the end
        if current_indent <= function_indent and line.strip():
            break

        end_line += 1

    # Calculate character positions
    start_pos = sum(len(lines[i]) for i in range(start_line))
    end_pos = sum(len(lines[i]) for i in range(end_line))

    return start_pos, end_pos, function_indent


def apply_function_change(file_path, function_name, new_code, class_name=None):
    """
    Replace an entire function with new code, maintaining proper indentation.
    Can target functions in classes or at module level.
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the function
    result = find_function_in_code(content, function_name, class_name)
    if result is None:
        if class_name:
            print(
                f"⚠️  Function '{function_name}' not found in class '{class_name}' in {file_path}"
            )
        else:
            print(f"⚠️  Function '{function_name}' not found in {file_path}")
        return False

    start_pos, end_pos, function_indent = result

    # Prepare the new code with proper indentation
    indent_str = " " * function_indent
    new_lines = new_code.splitlines()

    # Add indentation to each line (except the first line if it's a function definition)
    indented_new_code = []
    for i, line in enumerate(new_lines):
        if i == 0:
            # First line should have the base indentation
            indented_new_code.append(indent_str + line.lstrip())
        else:
            # Other lines: preserve relative indentation but add base indentation
            if line.strip():  # Don't indent empty lines
                # Calculate relative indentation
                original_indent = len(line) - len(line.lstrip())
                indented_new_code.append(indent_str + line)
            else:
                indented_new_code.append(line)

    # Join with newlines and ensure it ends with a newline
    formatted_new_code = "\n".join(indented_new_code)
    if not formatted_new_code.endswith("\n"):
        formatted_new_code += "\n"

    # Replace the function
    new_content = content[:start_pos] + formatted_new_code + content[end_pos:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    if class_name:
        print(
            f"✅ Successfully replaced function '{function_name}' in class '{class_name}' in {file_path}"
        )
    else:
        print(f"✅ Successfully replaced function '{function_name}' in {file_path}")
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

    # Process changes - now expecting function_name and new_code instead of old/new
    for index, code in enumerate(selected_instruction["change"]):
        function_name = selected_instruction["changes_function_class_names"][index]
        apply_function_change(file_path, function_name, code)


def apply_change(file_path, old_code, new_code):
    """
    Legacy function for backward compatibility.
    """
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


main()
