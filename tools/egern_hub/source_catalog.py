"""Expand source-level discovery rules; never store per-script decisions."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urljoin, unquote


class ReleaseLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fragments = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'include-fragment' and attrs.get('src'):
            self.fragments.append(attrs['src'])
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])


def release_assets(repository, download, key):
    """Enumerate public release attachments without authenticated endpoints."""
    _, body = download({'id':'release-index-'+key, 'url':repository+'/releases/latest'})
    page = ReleaseLinks()
    page.feed(body)
    prefix = repository+'/releases/expanded_assets/'
    fragments = list(dict.fromkeys(urljoin(repository+'/', src) for src in page.fragments
        if urljoin(repository+'/', src).startswith(prefix)))
    if len(fragments) != 1:
        raise ValueError('Release 页面缺少唯一附件列表：'+repository)
    _, body = download({'id':'release-assets-'+key, 'url':fragments[0]})
    assets = ReleaseLinks()
    assets.feed(body)
    links = list(dict.fromkeys(urljoin(repository+'/', href) for href in assets.links))
    return {'assets':[{'name':unquote(urlsplit(url).path.rsplit('/',1)[-1]),
                       'browser_download_url':url} for url in links
        if url.startswith(repository+'/releases/download/')]}


def normalize(data):
    if data.get('version') != 2:
        return data
    if set(data)-{'version','repository','defaults','discovery'}:
        raise ValueError('catalog v2 仅允许 version、repository、defaults、discovery；不登记逐文件资源')
    repository=data.get('repository')
    if not isinstance(repository,str) or not repository:raise ValueError('repository 必须是来源地址')
    if not isinstance(data.get('defaults'),dict):raise ValueError('defaults 必须是对象')
    defaults=dict(data['defaults'])
    defaults.setdefault('license','未声明许可证')
    if set(defaults)-{'author','author_avatar','author_avatar_channel','source','author_homepage','homepage','license','license_url','category','content_policy','policy'}:
        raise ValueError('defaults 仅允许来源级作者、许可、分类及规则策略信息')
    avatar=defaults.get('author_avatar')
    if avatar and (not isinstance(avatar,str) or urlsplit(avatar).scheme!='https' or not urlsplit(avatar).hostname):
        raise ValueError('author_avatar 必须是 HTTPS 图片地址')
    if not isinstance(data.get('discovery'),dict):
        raise ValueError('discovery 必须是对象')
    spec=dict(data['discovery'])
    kind=spec.get('type','repository')
    if kind not in {'repository','releases','telegram','local'}:
        raise ValueError('未知 discovery.type：'+str(kind))
    allowed={'repository':{'type','ref','select','include','rule_include'},'releases':{'type'},
        'telegram':{'type','max_pages','exclude_repositories','content'},
        'local':{'type','directory','rule_policy','rule_policies'}}
    if set(spec)-allowed[kind]:raise ValueError('discovery 包含不支持的字段')
    if kind=='repository':
        if 'select' in spec and (not isinstance(spec['select'],list) or not spec['select']):
            raise ValueError('select 必须是非空目录数组')
        for field in ['include','rule_include']:
            if any(not any(c in pattern for c in '*?[') for pattern in spec.get(field,[])):
                raise ValueError(field+' 必须使用通用 glob，不能逐文件登记')
        if not spec.get('ref'):
            raise ValueError('仓库发现必须指定 ref')
        if any(not p.endswith('/') for p in spec.get('select',[])):
            raise ValueError('catalog v2 select 只允许目录，不登记具体脚本路径')
    if kind in {'repository','releases'}:
        match=re.fullmatch(r'https://github.com/([\w.-]+)/([\w.-]+)',repository)
        if not match:
            raise ValueError('需要 GitHub 仓库根地址')
        owner=match[1]
        defaults.setdefault('author',owner)
        defaults.setdefault('source',defaults['author'])
        defaults.setdefault('author_homepage','https://github.com/'+owner)
        defaults.setdefault('homepage',repository)
    if kind=='local':
        defaults.setdefault('author','ErrBin')
        defaults.setdefault('source',defaults['author'])
    return {**data,'version':1,'defaults':defaults,'discovery':spec,'resources':[],'scripts':[]}


def read_manifests(root):
    return [normalize(json.loads(p.read_text())) for p in sorted((Path(root)/'catalog').glob('*.json'))]


def expand_sources(root, manifests, *, offline, download):
    from .layout import ascii_slug
    root=Path(root).resolve()
    remaining,resources,report=[],[],[]
    for data in manifests:
        spec=data.get('discovery') or {}
        kind=spec.get('type')
        if kind not in {'local','releases'}:
            remaining.append(data)
            continue
        defaults=data.get('defaults',{})
        repository=data['repository']
        if kind=='local':
            folder=(Path(root)/spec['directory']).resolve()
            if not folder.is_relative_to(Path(root).resolve()/'sources'):
                raise ValueError('本地来源目录必须位于 sources/ 内')
            for path in sorted(folder.rglob('*')):
                if not path.is_file():continue
                if not path.resolve().is_relative_to(folder):raise ValueError('本地来源文件越界')
                suffix=path.suffix.lower()
                formats={'.yaml':'egern','.yml':'egern','.sgmodule':'surge','.plugin':'loon','.list':'surge'}
                if suffix not in formats:continue
                body=path.read_text()
                rule=suffix=='.list'
                policy=spec.get('rule_policy','DIRECT')
                for setting in spec.get('rule_policies',[]):
                    if re.search(setting['content_pattern'],body,re.M):policy=setting['policy']
                resources.append({**defaults,'repository':repository,'id':ascii_slug(path.stem),
                    'path':path.relative_to(root).as_posix(),'format':formats[suffix],
                    'kind':'rules' if rule else 'modules','category':defaults.get('category','网络分流' if rule else '应用增强'),**({'policy':policy} if rule else {})})
        else:
            key=hashlib.sha256(repository.encode()).hexdigest()[:20]
            cache=Path(root)/'cache/releases'/f'{key}.json'
            if offline:
                if not cache.is_file():raise ValueError('缺少 Release 索引缓存，请先联网发现：'+repository)
                release=json.loads(cache.read_text())
            else:
                release=release_assets(repository,download,key)
                cache.parent.mkdir(parents=True,exist_ok=True)
                cache.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
            from .convert import convert_module
            for asset in release.get('assets',[]):
                name=asset.get('name','')
                if Path(name).suffix.lower() not in {'.yaml','.yml'}:continue
                url=asset['browser_download_url']
                if urlsplit(url).hostname!='github.com' or not url.startswith(repository+'/releases/download/'):
                    raise ValueError('Release 附件地址不属于来源仓库')
                item={**defaults,'repository':repository,'id':ascii_slug(repository.split('/')[-2]+'-'+repository.split('/')[-1]+'-'+Path(name).stem),
                    'url':url,'kind':'modules','format':'egern','category':defaults.get('category','应用增强')}
                from .layout import read_source,write_source
                try:
                    body=read_source(root,item) if offline else download(item)[1]
                    if not offline:write_source(root,item,body)
                    convert_module(body,'egern')
                except ValueError as exc:
                    report.append({'repository':repository,'path':name,'decision':'skipped','reason':str(exc)})
                    continue
                resources.append(item)
        report.append({'repository':repository,'decision':'source-discovery','method':kind})
    return remaining,resources,report
