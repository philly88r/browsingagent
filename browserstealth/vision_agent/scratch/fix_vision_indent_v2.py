import sys

file_path = r'c:\Users\info\browserstealth\vision_agent\vision_analyzer.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Target the specific problematic block
# Using a multi-line string to ensure exact matching of the broken part
broken_block = """                if m:
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
                        pass"""

fixed_block = """                if m:
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
                        pass"""

if broken_block in content:
    new_content = content.replace(broken_block, fixed_block)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully fixed vision_analyzer.py indentation via exact block replacement")
else:
    # Try a slightly fuzzy match in case of line endings
    broken_block_unix = broken_block.replace('\r\n', '\n')
    content_unix = content.replace('\r\n', '\n')
    if broken_block_unix in content_unix:
        new_content = content_unix.replace(broken_block_unix, fixed_block.replace('\r\n', '\n'))
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        print("Successfully fixed vision_analyzer.py indentation via Unix line endings")
    else:
        print("Could not find the broken block in vision_analyzer.py")
