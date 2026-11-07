"""Load one manifest per upstream repository, in a stable order."""
import json
from pathlib import Path
import argparse
import re
from urllib.parse import urlsplit

CONFIG_SUFFIXES = {'.yaml', '.yml', '.module', '.sgmodule', '.sgmodulle', '.lpx', '.plugin', '.scripts', '.snippet', '.conf'}


def initialize(root, repository, ref=None, *, author=None, files=()):
    """Create metadata only; normal builds remain the sole publication decision."""
    if urlsplit(repository).hostname == 't.me':
        if ref or files:
            raise ValueError('Telegram 来源使用频道清单，不使用 --ref 或 --file')
        return initialize_channel(root, repository, author=author)
    parsed = urlsplit(repository)
    if parsed.scheme!='https' or parsed.netloc!='github.com' or parsed.query or parsed.fragment:
        raise ValueError('请使用原作者仓库地址：https://github.com/Owner/Repo')
    parts = parsed.path.strip('/').removesuffix('.git').split('/')
    if len(parts)!=2 or not all(re.fullmatch(r'[A-Za-z0-9_.-]+',p) and p not in {'.','..'} for p in parts):
        raise ValueError('地址必须指向仓库根目录；使用 --file 目录/ 和 --ref 限定范围')
    if not ref or ref.startswith('-') or any(c.isspace() for c in ref):
        raise ValueError('请明确指定有效的 --ref 分支、标签或提交')
    repository = 'https://github.com/'+'/'.join(parts)
    root = Path(root)
    folder = root/'catalog'
    for path in sorted(folder.glob('*.json')):
        if json.loads(path.read_text())['repository'].rstrip('/').casefold()==repository.casefold():
            raise ValueError('仓库已登记，请维护同一份清单：'+str(path))
    files = sorted(set(files))
    if any(not path.endswith('/') for path in files):
        raise ValueError('catalog v2 仅按目录限定范围；--file 请传以 / 结尾的目录')
    for path in files:
        relative = path.removesuffix('/')
        if path.startswith('/') or '\\' in path or any(p in {'','..','.'} for p in relative.split('/')) or (not path.endswith('/') and Path(path).suffix.lower() not in CONFIG_SUFFIXES|{'.js','.mjs'}):
            raise ValueError('请选择仓库内安全的相对目录：'+path)
    owner,repo = parts
    data = {'version':2, 'repository':repository, 'defaults':{'license':'待核验', **({'author':author} if author else {})},
        'discovery':{'type':'repository','ref':ref, **({'select':files} if files else {})}}
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/(owner+'--'+repo).lower()
    target = target.with_name(target.name+'.json')
    if target.exists():
        raise ValueError('清单文件名已存在：'+str(target))
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return target


def initialize_channel(root, channel, *, author=None):
    parsed = urlsplit(channel)
    name = parsed.path.removeprefix('/s/').strip('/')
    if (parsed.scheme != 'https' or parsed.netloc != 't.me' or parsed.query or parsed.fragment
            or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}', name)):
        raise ValueError('请使用公开频道地址：https://t.me/ChannelName')
    channel = 'https://t.me/' + name
    DEFAULT_EXCLUDED = ['blackmatrix7/ios_rule_script','fmz200/wool_scripts','Script-Hub-Org/Script-Hub']
    root = Path(root)
    name = channel.rsplit('/',1)[1]
    folder = root/'catalog'
    for path in folder.glob('*.json'):
        if json.loads(path.read_text())['repository'].lower().rstrip('/') == channel.lower():
            raise ValueError('频道已登记，请维护同一份清单：'+str(path))
    target = folder/('telegram--'+name.lower()+'.json')
    if target.exists():
        raise ValueError('清单文件名已存在：'+str(target))
    data = {'version':2,'repository':channel,'defaults':{'author':author} if author else {},
        'discovery':{'type':'telegram','max_pages':None,'exclude_repositories':DEFAULT_EXCLUDED},
        }
    folder.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return target


def load_catalog(root):
    resources, scripts, ids, repositories = [], [], set(), set()
    files = sorted((Path(root) / 'catalog').glob('*.json'))
    if not files:
        raise ValueError('catalog/ 中没有仓库清单')
    for path in files:
        from .source_catalog import normalize
        data = normalize(json.loads(path.read_text(encoding='utf-8')))
        if data.get('version') != 1 or not isinstance(data.get('repository'), str):
            raise ValueError(f'{path.name}: 缺少 version: 1 或 repository')
        if data['repository'] in repositories:
            raise ValueError(f'{path.name}: 同一仓库只能有一个清单')
        repositories.add(data['repository'])
        defaults = data.get('defaults', {})
        if not isinstance(defaults, dict):
            raise ValueError(f'{path.name}: defaults 必须是对象')
        for key, output in [('resources', resources), ('scripts', scripts)]:
            entries = data.get(key, [])
            if not isinstance(entries, list):
                raise ValueError(f'{path.name}: {key} 必须是数组')
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError(f'{path.name}: 条目必须是对象')
                item = {**defaults, **entry, 'repository': data['repository']}
                identity = item.get('id')
                if not isinstance(identity, str) or identity in ids:
                    raise ValueError(f'{path.name}: 缺少或重复 ID {identity}')
                ids.add(identity)
                output.append(item)
    resource_ids = {item['id'] for item in resources if item.get('kind') == 'modules'}
    for item in resources:
        if item.get('module_id') and item['module_id'] not in resource_ids:
            raise ValueError(f"{item['id']}: module_id 引用了不存在的模块")
        if not set(item.get('script_map', {}).values()) <= {script['id'] for script in scripts}:
            raise ValueError(f"{item['id']}: script_map 引用了不存在的脚本")
    return resources, scripts


def main():
    parser = argparse.ArgumentParser(description='登记原作者仓库或公开 Telegram 频道；不下载、转换或提交资源')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='生成一份仓库清单与来源记录')
    init.add_argument('repository', help='https://github.com/Owner/Repo 或 https://t.me/ChannelName')
    init.add_argument('--ref', help='GitHub 必填：实际分支、标签或提交，不猜测默认分支')
    init.add_argument('--author', help='作者昵称；默认使用 GitHub 用户名')
    init.add_argument('--file', action='append', default=[], help='只纳入以 / 结尾的递归目录及配套依赖；可重复')
    args = parser.parse_args()
    try:
        path = initialize(Path(__file__).resolve().parents[2], args.repository, args.ref, author=args.author, files=args.file)
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc)+'\n')
    print(f'已生成 {path}；请核对来源与许可，然后运行 python build.py。详见 docs/adding-sources.md')


if __name__=='__main__':
    main()
