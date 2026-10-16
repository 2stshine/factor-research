import argparse
import json
from engine.phenomenon_generation import activate


def main():
    p=argparse.ArgumentParser(description='Explicit empty-knowledge generation cutover preserving prior registry')
    p.add_argument('--repo-root',required=True);p.add_argument('--archive-manifest',required=True)
    p.add_argument('--expected-pointer-sha256',required=True);p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    result=activate(args.repo_root,archive_manifest=args.archive_manifest,
                    expected_pointer_sha256=args.expected_pointer_sha256,apply=args.apply)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
