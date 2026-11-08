# 增加来源与原作者适配

一个仓库或公开频道只登记一份 `catalog/*.json`。清单只描述来源、作者信息与抓取规则；构建自动发现模块、读取依赖、提取名称说明并决定是否可以转换。不要登记具体脚本名称、文件路径、资源 ID、图标匹配、转换状态或手写资源介绍。

## 统一 JSON 格式

所有来源使用版本 2，固定四个顶层字段：

```json
{
  "version": 2,
  "repository": "https://github.com/Author/Repo",
  "defaults": {},
  "discovery": {
    "type": "repository",
    "ref": "main"
  }
}
```

完整可复制示例见 [仓库](examples/repository.json)、[Release](examples/releases.json)、[Telegram](examples/telegram.json)、[本地来源](examples/local.json)。示例不放入 `catalog/`，不会成为抓取目标。

| 字段 | 含义 |
| --- | --- |
| `version` | 固定为 `2` |
| `repository` | GitHub 仓库根地址、公开 Telegram 频道地址；本地为 `local` |
| `defaults` | 来源级可选元信息，允许空对象 |
| `discovery` | 按来源类型声明自动抓取规则 |

不使用 `resources`、`scripts`、`overrides`、`script_overrides` 或 `script_map`。旧格式仅作为读取兼容保留，仓库中的清单和初始化命令统一输出版本 2。

## 昵称与头像

这些设置均可省略：

```json
"defaults": {
  "author": "作者昵称",
  "author_avatar": "https://example.org/avatar.png",
  "license": "MIT",
  "license_url": "https://github.com/Author/Repo/blob/main/LICENSE"
}
```

GitHub 未设置昵称时使用仓库作者用户名；未设置头像时使用 `https://github.com/<owner>.png?size=96`。作者昵称不改变原始仓库身份和来源路径。同一作者跨仓库的显式头像应保持一致。

Telegram 未设置昵称时读取频道公开名称，未设置头像时读取频道声明的头像。离线构建复用缓存；尚无频道资料缓存时名称暂用频道用户名，头像不伪造。自定义 `author_avatar` 优先于默认头像。GitHub 作者也可通过已有的 `author_avatar_channel` 指定公开 Telegram 频道头像。

许可必须与上游一致；没有声明时使用“未声明许可证”，尚未核实时使用“待核验”。清单登记不表示已获得作者授权。原文中的署名、转载限制与许可仍参与构建检查。

## GitHub 仓库发现

```sh
.venv/bin/python -m tools.egern_hub.catalog init https://github.com/Author/Repo --ref main

# 仅限定目录；递归抓取，未来新增文件无需修改清单
.venv/bin/python -m tools.egern_hub.catalog init https://github.com/Author/Repo --ref main \
  --author 作者昵称 --file Loon/plugin/ --file Loon/script/
```

`--ref` 必须填写真实分支、标签或提交；不猜测分支。`--file` 为兼容命令名称，版本 2 仅接受以 `/` 结尾的目录。初始化只创建清单，不下载、构建或提交。

全仓库发现省略 `select`；限定范围时写目录：

```json
"discovery": {
  "type": "repository",
  "ref": "main",
  "select": ["Loon/plugin/", "Loon/script/"]
}
```

目录取并集，递归纳入模块及脚本候选；脚本仅作为模块依赖，不能独立发布。目录不存在、路径越界或空选择数组会报错。不要用逐文件选择冻结爬虫结果。已有仓库追加目录时修改同一份清单，不再创建第二份。

需要纳入规则集时使用通用匹配，例如 `"rule_include": ["rules/*.list"]`；`defaults.policy` 可设置规则策略。匹配规则不写具体文件名。

构建解析配套模块与 README / 注释用法，优先选择原生 Egern，再考虑 Surge、Loon、QX；原生 Egern 正文逐字保留，依赖继续指向上游。构建会先扫描本次发现范围内所有来源的原生模块，收集其 `script_url`；其他平台合集若引用同一规范化 URL，会自动省去重复条目并复用原生模块及上游依赖，不转换该脚本，也不依赖人工映射。其他脚本必须通过静态转换及完成结果传播检查，不能可靠转换的内容进入报告。任务合集按一个模块发布，不能拆成独立任务资源。

## GitHub Release 自动发现

```json
"discovery": {
  "type": "releases"
}
```

从仓库最新正式 Release 的附件索引枚举 `.yaml` / `.yml`，下载后按 Egern 模块语法识别。不是原生模块的 YAML 记录跳过原因，不猜测内容类型。清单不填写附件名称或下载地址；以后新增附件也自动纳入。附件名称来自作者的 Release 元数据，不是维护者手选。

Release 索引缓存在忽略的 `cache/releases/`，原文仍放在忽略的 `sources/`。离线发现必须已有索引及原文缓存，不能假装完成联网更新。

## Telegram 公开频道

```sh
.venv/bin/python -m tools.egern_hub.catalog init https://t.me/ChannelName
```

```json
"discovery": {
  "type": "telegram",
  "max_pages": null
}
```

`max_pages: null` 表示不人为截断历史页数。`exclude_repositories` 可排除整个仓库，`content: "widgets"` 用于频道中的小组件内容。频道发现的 GitHub 资源继续追溯原作者仓库、固定版本与许可证；频道作为发现来源，不冒充脚本作者。

## 本地原创来源

```json
"discovery": {
  "type": "local",
  "directory": "sources/Author/Repo",
  "rule_policy": "DIRECT"
}
```

递归扫描目录内的原生模块、Surge 模块、Loon 插件与行式规则，不列具体文件。目录必须位于 `sources/` 内。规则需要按内容设置不同策略时，可使用 `rule_policies` 中的 `content_pattern` 正则和 `policy`；后匹配者覆盖前者。不要用具体文件名模拟逐项资源表。

## 原作者如何适配

1. 在原仓库发布完整模块，原生 Egern 优先；其他平台提供正式配置和所引用的脚本。原文路径不需要迎合本站的输出路径。
2. 在模块声明中提供真实名称、说明、作者和图标来源；缺失说明时构建只能从代码与配置分析行为，不人工补写效果承诺。
3. 使用可访问的依赖地址，并在 LICENSE、README 或文件头声明许可及署名。跨仓库依赖也需要能追溯到原作者。
4. 定时任务提供 cron 声明及 Cookie / Token 获取入口；合集保留完整配置。仅发布孤立脚本且没有可解析用法时，不会作为页面资源展示。
5. 非原生脚本尽量保持宿主 API 调用可静态追踪，避免动态拼装 API 名称、远程执行代码、源码自检及逃逸的完成回调。普通 JavaScript 库可以保留，不需要原作者手动改成兼容层。
6. 提交一份来源级 JSON 或提供仓库根地址、分支、目录范围与可选昵称头像。后续新增内容由爬虫发现，不提交逐文件适配名单。

App 图标优先从原作者声明、App Store 与官网自动匹配，保留出处及缓存。页面分类固定为广告净化、应用增强、影音字幕、网络分流、定时脚本；不按新作者或应用扩展分类。

## 验证与提交

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_catalog_standalone.py' -q
.venv/bin/python build.py --verify
.venv/bin/python -m tools.egern_hub.serve
```

首次抓取需要联网；检查报告中的跳过、拒绝转换与未覆盖分支。动态验证规范见 [`egern-converter` 的 verification.md](https://github.com/errbin/egern-converter/blob/main/docs/verification.md)，未触发行为不能记为通过，不保证所有输入或真机效果。存在其他任务明确要求暂缓全量构建时，先完成清单与发现层定向验证，待条件满足后再全量构建。

只提交清单、工具、测试、文档及允许提交的静态素材。`sources/`、`dist/`、缓存及私人验证样例不提交，不使用强制添加绕过忽略规则。维护完成并通过验证后使用准确、简洁的英文提交说明；预览服务默认监听 `0.0.0.0:8787`，服务目录为 `dist/`。
