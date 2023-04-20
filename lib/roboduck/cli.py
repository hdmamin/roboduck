import argparse
import os
from pathlib import Path
import subprocess


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='The python script to execute.')
    args = parser.parse_args()
    path = Path(args.file).resolve()
    tmp_path = Path('/tmp')/path.name
    with open(path, 'r') as f:
        src_text = f.read()
    path.rename(tmp_path)
    src_text = 'from roboduck import errors\n' + src_text

    try:
        with open(path, 'w') as f:
            f.write(src_text)
        subprocess.call(['python', str(path)])
    except Exception as e:
        raise e
    finally:
        tmp_path.rename(path)


if __name__ == '__main__':
    run()
