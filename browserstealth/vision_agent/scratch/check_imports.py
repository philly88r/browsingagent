import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from vision_analyzer import VisionAnalyzer
    print("VisionAnalyzer imported successfully")
    va = VisionAnalyzer()
    print("VisionAnalyzer instance created")
    
    # Check if COORDINATOR_TEMPLATE is in globals of the module
    import vision_analyzer
    if hasattr(vision_analyzer, 'COORDINATOR_TEMPLATE'):
        print("COORDINATOR_TEMPLATE is present in vision_analyzer globals")
    else:
        print("COORDINATOR_TEMPLATE is NOT present in vision_analyzer globals")
        # List all globals starting with C
        c_globals = [g for g in dir(vision_analyzer) if g.startswith('C')]
        print(f"C-globals in vision_analyzer: {c_globals}")

except Exception as e:
    import traceback
    traceback.print_exc()
