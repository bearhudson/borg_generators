# Borg surface generator


It runs off CADquery which is very heavy, so I recommend running this script in a virtual env.

Usage:
```bash
python3 -m venv venv
source venv/bin/activate
pip install cadquery
python3 borg.py
```

Input dimensions, wait a while, and you'll have a STEP file in the root directory. 

I do mean a _while_. It's Python, CAD, and recursion. It's very slow.
