#!/usr/bin/env python3
"""Create a NEW private GitHub repository using the user's local gh login.

No embedded credentials. No force push. Refuses an existing origin or remote repo.
A dry run does not authenticate, initialize Git, or contact GitHub.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def run(*args, check=True):
    return subprocess.run(args,cwd=ROOT,text=True,encoding='utf-8',capture_output=True,check=check)


def main() -> int:
    parser=argparse.ArgumentParser(description='在本人 GitHub 账号创建全新仓库并推送，默认私有')
    parser.add_argument('--owner',default='curealb')
    parser.add_argument('--name',default='tonkatsu-me')
    parser.add_argument('--public',action='store_true',help='明确选择公开；默认创建私有仓库')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*',args.owner) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',args.name):
        parser.error('无效的 owner 或仓库名。')
    repository=f'{args.owner}/{args.name}'
    visibility='--public' if args.public else '--private'
    command=['gh','repo','create',repository,visibility,'--source',str(ROOT),'--remote','origin','--push',
             '--description','Tonkatsu.(me) — Temari’s tonkatsu daydream, an ASCII fan music video.']
    if args.dry_run:
        print('Dry run only. No GitHub repository has been created.\n'+' '.join(command))
        return 0
    try:
        if not shutil.which('gh') or not shutil.which('git'):
            raise RuntimeError('请先安装 Git 和 GitHub CLI，然后运行 gh auth login。无需把令牌发给任何人。')
        run('gh','auth','status')
        login=run('gh','api','user','--jq','.login').stdout.strip()
        if login.lower()!=args.owner.lower():
            raise RuntimeError(f'当前 gh 登录的是 {login}，目标是 {args.owner}。已停止，未创建仓库。')
        if run('gh','repo','view',repository,'--json','name',check=False).returncode==0:
            raise RuntimeError(f'{repository} 已存在。为避免覆盖，此脚本只创建全新仓库。')
        root=run('git','rev-parse','--show-toplevel',check=False)
        if root.returncode==0 and Path(root.stdout.strip()).resolve()!=ROOT.resolve():
            raise RuntimeError('项目位于另一个 Git 仓库中。请移出后再发布，避免提交无关文件。')
        if not (ROOT/'.git').exists():
            run('git','init','-b','main')
        if run('git','remote','get-url','origin',check=False).returncode==0:
            raise RuntimeError('已存在 origin。脚本不会改写远程地址或自动推送到已有仓库。')
        # Only the repository's own source is staged. Music, raw artwork and secrets are ignored.
        run('git','add','--all','--','.')
        staged=run('git','diff','--cached','--name-only').stdout.splitlines()
        forbidden={'.mp3','.wav','.m4a','.flac','.ogg','.aac','.mp4','.mov','.pem','.key'}
        if any(Path(p).suffix.lower() in forbidden or Path(p).name.startswith('.env') for p in staged):
            raise RuntimeError('暂存区出现音频或敏感文件，已停止发布。请检查 git diff --cached --name-only。')
        if run('git','rev-parse','--verify','HEAD',check=False).returncode!=0 or staged:
            identity=run('git','var','GIT_AUTHOR_IDENT',check=False)
            if identity.returncode!=0:
                raise RuntimeError('请先设置本地 Git user.name 和 user.email，然后重新运行。')
            run('git','commit','-m','Initialize Tonkatsu.(me) playable ASCII MV prototype')
        result=run(*command)
        print(result.stdout.strip())
        print(run('gh','repo','view',repository,'--json','url','--jq','.url').stdout.strip())
        return 0
    except subprocess.CalledProcessError as exc:
        print('发布未完成：'+(exc.stderr or exc.stdout or str(exc)),file=sys.stderr)
        print('若建仓已成功但推送失败，请检查 gh repo view 与 git remote -v；本脚本不会覆盖已创建的仓库。',file=sys.stderr)
        return 1
    except (OSError,RuntimeError) as exc:
        print(f'发布未完成：{exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
