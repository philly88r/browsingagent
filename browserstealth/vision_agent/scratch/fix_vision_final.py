import sys

file_path = r'c:\Users\info\browserstealth\vision_agent\vision_analyzer.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We'll replace the entire find_coordinates method to be sure
# Finding the start and end by markers
start_marker = "                # Layer 1: find last balanced JSON object in text"
end_marker = "                # Layer 4: prose coordinate extraction"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_block = """                # Layer 1: find last balanced JSON object in text (models often wrap prose around JSON)
                candidates = []
                pos = 0
                while True:
                    start = text.find('{', pos)
                    if start < 0:
                        break
                    depth, in_string, escape = 0, False, False
                    for idx in range(start, len(text)):
                        ch = text[idx]
                        if in_string:
                            escape = (ch == '\\\\and not escape)
                            if not escape and ch == '"':
                                in_string = False
                            continue
                        if ch == '"':
                            in_string = True
                        elif ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                candidates.append(text[start:idx + 1].strip())
                                pos = idx + 1
                                break
                    else:
                        break
                for c in reversed(candidates):
                    if '"x"' in c and '"y"' in c:
                        try:
                            coords = json.loads(c)
                            if 'nx' in coords and 'ny' in coords:
                                x = int(float(coords['nx']) * img_w / 1000)
                                y = int(float(coords['ny']) * img_h / 1000)
                                print(f"   [Verifier] -> Normalized ({coords['nx']}, {coords['ny']}) scaled to ({x}, {y})")
                                return x, y
                            x, y = int(coords.get('x', 0)), int(coords.get('y', 0))
                            if 0 < x < 1 and 0 < y < 1:
                                x, y = int(x * img_w), int(y * img_h)
                                print(f"   [Verifier] -> Float normalized detected, scaled to ({x}, {y})")
                                return x, y
                            print(f"   [Verifier] -> ({x}, {y})")
                            return x, y
                        except (json.JSONDecodeError, ValueError):
                            pass

                # Layer 2: simple regex for inline JSON fragments
                m = re.search(r'\\{[^}]*"[xy]"\\s*:[^}]+\\}', text)
                if m:
                    try:
                        coords = json.loads(m.group(0))
                        if 'nx' in coords and 'ny' in coords:
                            x = int(float(coords['nx']) * img_w / 1000)
                            y = int(float(coords['ny']) * img_h / 1000)
                            print(f"   [Verifier] -> Normalized ({coords['nx']}, {coords['ny']}) scaled to ({x}, {y})")
                            return x, y
                        x, y = int(coords.get('x', 0)), int(coords.get('y', 0))
                        if 0 < x < 1 and 0 < y < 1:
                            x, y = int(x * img_w), int(y * img_h)
                            print(f"   [Verifier] -> Float normalized detected, scaled to ({x}, {y})")
                            return x, y
                        print(f"   [Verifier] -> ({x}, {y})")
                        return x, y
                    except (json.JSONDecodeError, ValueError):
                        pass

                # Layer 3: extract x and y key-value pairs anywhere in text
                # "? makes the opening quote optional — handles malformed `y": 40` responses
                xm = re.search(r'"?x"?\\s*:\\s*(\\\\d+)', text)
                ym = re.search(r'"?y"?\\s*:\\s*(\\\\d+)', text)
                if xm and ym:
                    x, y = int(xm.group(1)), int(ym.group(1))
                    print(f"   [Verifier] -> ({x}, {y}) [fallback extract]")
                    return x, y

"""
    # Replace backslashes correctly for python string
    new_block = new_block.replace('\\\\', '\\')
    
    new_content = content[:start_idx] + new_block + content[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully fixed vision_analyzer.py find_coordinates indentation")
else:
    print(f"Could not find markers: start={start_idx}, end={end_idx}")
