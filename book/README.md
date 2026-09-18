# 中文书稿维护与出版

这里面向作者和维护者，不是读者正文。读者入口是 [`docs/book/README.md`](../docs/book/README.md)。同一份**中文简体 Markdown 母稿**现在同时支持网站与可重排 EPUB3；导出不改写正文、不自动生成英文或转换繁体。EPUB 可供离线阅读和审稿，但不代表当前简体稿具备 KDP 上架资格。

## 一份正文，两种阅读方式

知识章继续以 `docs/<topic>/.../NN-chapter.md` 为唯一源文件。网站沿模块组织，电子书依据 [`zh-CN/manifest.json`](zh-CN/manifest.json) 的显式顺序编排，不复制第二套正文。

当前共 143 章，九篇依次为：LLM 23 章、多模态 10 章、工具与协议 15 章、RAG 22 章、Agent 25 章、框架与编排 23 章、生产工程 13 章、安全与治理 10 章、FDE 2 章。篇内按原文件章号递增，每篇重新从第 1 章开始。书稿标题显示“第一篇 第1章”等完整位置，小节号和正文中原有的“第十四章”不做全局替换。

manifest 只保存篇标题、章节稳定 ID 和路径；知识章标题从源 H1 读取。`front_matter` 与 `back_matter` 指向 `docs/book/` 的扉页、前言、读法、致谢、作者与许可页。目录和站点入口由脚本生成，不手工维护另一份 143 章标题清单。

## 组装与日常维护

只需要 Python 3.10 或更新版本的标准库。从仓库根目录运行：

```bash
# 不生成文件；检查 manifest、章号、覆盖、源文件、链接、锚点与资产
python3 scripts/build_book.py --check

# 源标题或 manifest 改动后，重建并提交读者目录
python3 scripts/build_book.py --write-index

# CI 同时检查目录是否过期
python3 scripts/build_book.py --check --check-index

# 组装默认母稿及可追踪的构建记录
python3 scripts/build_book.py

# 也可指定仓库外的输出文件；资产随它放在相邻 assets/ 下
python3 scripts/build_book.py --output /tmp/ai-engineering-book/manuscript.md

python3 -m unittest discover -s scripts/tests -p 'test_build_book.py'
```

默认输出为 `book/zh-CN/generated/manuscript.md`，同目录生成 `manuscript.build.json`，必要时复制本地资产到 `assets/`。该目录由本地 `.gitignore` 忽略，不提交生成正文。输出路径不能覆盖仓库内的源文件；仓库内的输出只能位于上述生成目录。`--manifest` 接受仓库相对路径，`--check` 不与 `--output` 同用；单独执行 `--write-index` 只更新读者目录，不写母稿。

manifest 校验检查全部 `docs/**/NN-*.md` 知识章恰好出现一次；新增主题或新增章节不会被静默漏掉。漏章、重复路径/ID、非法 JSON 字段、错误篇内顺序、错误 H1 章号、越界路径、缺少资产或片段锚点都会失败。不要为了让构建通过而跳过坏文件。

新增、移动或删除章节时，同时更新 manifest、各级网站索引和 MkDocs 导航，再重建书稿目录。标题审校完成后也要重建目录。正式发布前仍需运行仓库既有的 `python3 scripts/check_docs.py`、`npm run check:mermaid` 和 `.venv/bin/mkdocs build --strict`；组装器不能替代逐章技术审校。

## 转换边界

| 输入 | 母稿中的处理 |
|---|---|
| YAML 页元数据 | 只剥离文件开头成对的 `---` 元数据块，不把描述插入正文 |
| 书内章节、前后附页链接 | 改为同一文件内的稳定锚点；原有标题片段会先校验，再映射到书稿锚点 |
| 网站总目录、主题目录链接 | 分别映射到书稿目录与对应篇；不拼接网站索引正文 |
| 模块目录或其他未收录 Markdown 页面 | 校验目标后转成 `source_url` 下的完整线上链接，保留所指模块的含义；**需要联网**，不冒充某一章 |
| 本地图片和其他非 Markdown 附件 | 校验存在且未越出仓库，复制到输出旁的 `assets/`；保留仓库相对层级，避免重名覆盖 |
| 外部资料链接、远程图片 | 保留原 URL，不下载；远程图片还不是离线出版资产 |
| 参考式链接 | 统一重写定义目标，并给引用标签加章节命名空间，避免整书重名串链 |
| 代码围栏、行内代码、数学、缩进代码 | 保留原文，不把其中的示例链接、注释或标题当作正文改写 |
| 编辑用 HTML 注释 | 不进入读者稿；代码示例里的注释仍保留 |
| 已知格式的重复作者页尾、返回网站目录行 | 只移除这些明确模式；不删除技术限定、来源说明或第三方具体出处 |

这是为本仓库维护的 Markdown 子集组装器，不是通用 CommonMark/EPUB 引擎。支持普通行内链接（含括号 URL、尖括号目标和同一行的可选标题）、常规参考式链接、带引号的 HTML `href`/`src`。脚注、源 HTML 自定义锚点、`srcset` 等尚未实现的结构会明确报错；需要时应先增加显式转换和回归用例。新增块级语法或多行链接时也应扩展测试，不能只看命令是否退出成功。

篇锚点形如 `part-agent`，章锚点形如 `agent-24`，编号小节形如 `agent-24-s24-2`。不编号的标题使用章内顺序 ID，例如 `agent-24-extra-01`。普通中文标题片段由脚本映射到这些锚点。更改标题不会改动章 ID 或编号小节 ID；调整小节编号、不编号标题的顺序时，需要重新核对交叉引用。

本轮审校已从章节源文件移除通用署名页尾；组装器保留对旧格式的兼容处理，仓库许可继续有效。遇到未识别的本章作者声明时，脚本报错而不是猜测删除范围。第三方具体署名、论文与规范出处应留在对应论证旁，通用许可声明集中在 `docs/book/colophon.md`。

## 中文冻结与后续英文

`schema_version` 表示 manifest 格式，`edition` 是内部稿件版本标识，不代表已出版的版次或 ISBN。冻结中文稿时记录 Git 提交、manifest 与源文件哈希、审校记录，以及构建记录中的 `manuscript_sha256`。同样的输入应得到同样的母稿字节；变更稿件时更新内部版本并保留上一版构建记录。

章 ID 是跨语言身份，不随译名、文件移动或展示顺序重新生成。将来的英文 manifest 应复用同一章 ID，明确对应的中文冻结提交与译稿版本，而不是复制现在的中文生成稿继续独立维护。当前脚本仅支持 `zh-CN`；英文组装需届时增加语言标签、路径和编号展示规则，不能只把语言字段改掉便当作已支持。

翻译启动前，再建立以稳定概念 ID 为键的术语表，至少记录中文写法、英文首选词、保留缩写、语义备注和首次出现的章 ID。像“记忆”“上下文”“状态”“检索”“工具执行”这些容易混用的词，要先确定语境，再统一译法。保留产品名、API 标识符和必要版本限定；不通过统一译名掩盖原本不同的概念。本阶段不生成英文章节或假装已经做完术语审定。

## EPUB 导出与下载

网站继续走 `.github/workflows/docs.yml`；电子书走独立的 [Build EPUB](https://github.com/zongyangbigpolo/awesome-ai-roadmap/actions/workflows/epub.yml)。PR、影响书稿的 main 更新和手动运行都会生成完整电子书。导出流程只有仓库读取权限，不发 Release、不部署网站、不上传 KDP；导出依赖或格式检查失败不会阻塞原有网站部署。

日常改稿仍然只改原来的 Markdown、只提一个 PR；PR 阶段检查网站并生成 EPUB 预览，合并后两个工作流各自构建。无需另开“EPUB 内容 PR”，也不手工维护或提交 `.epub`。独立的是构建流程，不是正文来源。

在成功运行的 **Artifacts** 中下载 `ai-engineering-interview-zh-CN-epub`，解压得到 `ai-engineering-interview-zh-CN.epub`、`build.json`、母稿哈希记录、静态渲染记录和 EPUBCheck 报告。GitHub 下载工件通常需要登录。保留期为 90 天（仓库或组织策略可能进一步缩短）；过期后，有 Actions 操作权限的维护者可选 **Run workflow** 重建。无需把生成文件提交进 Git。

### 本地安装与一条命令导出

完整导出支持 macOS 的 arm64、x64，以及 Linux x64；需要 Python 3.10+、Node.js 22 和单独安装的 Java 17+。安装脚本不改全局 PATH、不替用户安装 Java，不接触主工作树。Windows 可使用 x64 Linux 环境运行。虽然固定的 Pandoc 归档另含 Linux arm64，当前 Puppeteer 配套 Chromium 不支持该平台，因此不能据此宣称完整导出支持 Linux arm64；请使用 x64 runner。

```bash
# 首次安装，或固定依赖版本发生变化时运行
python3 scripts/install_epub_tools.py
npm ci --prefix book/epub

# 日常导出：包含全书组装、静态渲染、打包、链接审计和 EPUBCheck
python3 scripts/build_epub.py

# 可选：独立输出目录；只能替换本工具已有的输出，不能覆盖源文件
python3 scripts/build_epub.py --output /tmp/ai-engineering-epub
```

默认文件在 `book/zh-CN/generated/epub/ai-engineering-interview-zh-CN.epub`。目录内还保留中间母稿、`rendered/` PNG 和构建记录，便于人工审稿。只有全部检查通过才替换上次成功输出；缺工具、资源丢失、未知公式、渲染错误或写入失败都会报错，不降级成缺图版本。

Pandoc **3.6.4**、EPUBCheck **5.2.1** 下载到 `book/epub/.tools/`，按 [`epub/tools.json`](epub/tools.json) 固定的完整归档 SHA-256 校验后解包。校验值来自官方 GitHub Release 的 HTTPS 下载，不冒充上游签名。Node 依赖单独锁在 `book/epub/package-lock.json`：Mermaid **11.12.0**、MathJax **3.2.2**、Puppeteer **24.15.0**、Noto Sans SC **5.2.5**；Chromium 放在该目录的 `.cache/puppeteer/`，普通网站的 `npm ci` 不会安装它们。首次安装需要联网获取工具和字体，书稿转换不发送到任何远程渲染服务。

Linux 若缺 Chromium 系统库，按 [Puppeteer 的运行环境说明](https://pptr.dev/troubleshooting) 安装对应发行版依赖；不要用关闭沙箱掩盖缺库。本地默认启用浏览器沙箱，只有独立、可丢弃的 CI runner 显式设置 `EPUB_NO_SANDBOX=1`。

### 导出如何保留阅读内容

导出复用 `scripts/build_book.py` 的 manifest 校验、次序、稳定 ID、链接与署名处理，然后由 Pandoc 解析 Markdown AST。代码围栏、行内代码和缩进代码不是公式；示例代码中的 Mermaid 不会被当成真正插图。独立的源分段计数与 AST 图/公式计数必须一致，遇到超出当前支持子集的结构要补充转换与回归测试，不能直接放宽计数。

每个知识章、篇页和前后附页分别生成 XHTML，线性 spine 顺序来自 manifest。保留原扉页，不使用 Pandoc 自动扉页；母稿的正文目录换成单一的 EPUB 原生导航目录。篇内原章号不变，稳定章/节 ID 移交给标题；打包后按真实 XHTML ID 与资源哈希修正跨文件链接，并逐条检查目标是否存在。参考资料仍可点击联网访问，**正文、图和公式本身不依赖网络**。

Mermaid 与 LaTeX 仅在导出时转成带替代文本的 PNG，网站源继续保留原语法。本地浏览器加载隔离安装的渲染器与中文字体，禁止访问外部地址；单个浏览器批量绘制并按内容、渲染器与 lockfile 缓存。图片使用两倍像素密度和白色背景，避免深色阅读模式下透明黑字消失；行内公式按 `em` 设尺寸，随正文缩放。中文字体用于生成图片，不锁定电子书正文字体。

源文件中的普通图片目前支持本地 PNG/JPEG/GIF。远程图片、带依赖的 SVG、Mermaid 内嵌图片/图标和交互链接需要先做显式的离线静态转换；当前导出会拒绝这些输入，不替作者联网抓取或静默删除。

正文只保留概览与“查看大图与细节”链接；非线性的独立图页放完整原图与有重叠的局部图，局部按从左到右、从上到下阅读，不裁掉超出屏幕的内容。每次出现的图都有自己的详情页，返回链接精确回到正文中的此图，跨章复用的 PNG 仍只打包一份。图页不混入章目录或连续阅读 spine，局部图不重复堆在正文。超出渲染器明确尺寸/面积上限会失败，要求主动调整图，而不是悄悄丢图或缩成不可读缩略图。代码只通过 CSS 视觉换行，不向代码内容插入换行符；表格按窄屏折行，但宽表、大图和公式仍需在实际设备查看。

EPUB 专用 CSS 位于 `book/epub/epub.css`，不会覆盖站点样式。本次不生成封面、不编造 ISBN 或出版社；书目作者沿用 Polo Li，许可仍集中在书末。生成文件使用真实的 `zh-CN`，将来英文导出要先有对应英文母稿与语言支持，不能只修改 metadata。

### 回归与验收边界

```bash
# 网站也可运行：这些单元测试不需要导出工具或浏览器
python3 -B -m unittest discover -s scripts/tests -p 'test_*.py'

# EPUB 专用：实际启动浏览器，验证中文图、公式、缓存和错误路径
npm test --prefix book/epub
python3 -B scripts/tests/epub_integration.py

# 完整 143 章实际导出及格式校验，不是两页样例或跳过式测试
python3 scripts/build_epub.py
```

`build.json` 区分图/公式的**出现次数**、去重渲染数、局部图和实际打包资产数，并记录字节数、SHA-256、章数、篇数、spine、内部链接检查及工具版本。`manuscript.build.json` 记录每个源文件与资产哈希；`render.json` 可定位 PNG 及尺寸；`epubcheck.json` / `.txt` 保留官方校验结果。完整导出还检查 mimetype、OPF、语言、导航、所有内部片段、资源完整性、脚本与远程依赖。图/公式无错误、EPUBCheck 无错误和警告后才发布工件。

这些是格式与覆盖检查，不是人工排版验收。还要在电子书阅读器与 Kindle Previewer 查看中文字体、窄屏代码/表格、不同字号、横竖屏、深色模式以及全部图和公式；导出记录会明确保留“未进行 Kindle Previewer 人工验收”和“未声称 KDP 接收”。

## 出版限制与人工决策

以下是作者操作说明。EPUB 格式与语言支持核对日期为 **2026-09-18**；其他出版条款保留 **2026-09-15** 的核对记录。平台规则会变化，上架前须重新查阅原始页面。

**格式支持、预览验收与发行资格是三件事。** KDP 的 [Supported eBook Formats](https://kdp.amazon.com/en_US/help/topic/G200634390) 接受符合 Kindle Publishing Guidelines 的 EPUB，并建议上传前用 Kindle Previewer 检查。通过 EPUBCheck 只说明文件满足其检查的 EPUB 规范，不说明视觉排版已验收，更不说明 KDP 已接受该书或其语言。

**语言资格尚未满足。** KDP 的 [Book Supported Languages](https://kdp.amazon.com/en_US/help/topic/G200673300) 只列出 `Chinese (Traditional) (eBook only)`，未列简体中文。官方说明不支持语言的电子书可能被移除。因此继续维护简体母稿，但不能把本稿称为当前可直接上架的 KDP 书，也不能虚报成其他语言绕过限制。后续英文出版是另一阶段；不要未经作者决定偷偷转为繁体。

**按真实生产方式申报 AI 内容。** KDP [Content Guidelines](https://kdp.amazon.com/en_US/help/topic/G200672390) 要求申报 AI 实际生成的文字、图片或翻译，即使随后经过大量人工修改仍属 `AI-generated`。仅用 AI 对人写内容做编辑、润色、检查等辅助，才属于对应的 `AI-assisted` 情形。逐项记录真实过程，在后台按当时要求申报，不能因为人工审校过就自动改报为纯人工。

**普通 KDP 出版不等于 KDP Select。** [KDP Terms and Conditions](https://kdp.amazon.com/en_US/terms-and-conditions) 的 Optional Programs → KDP Select → Exclusivity 要求项目期间的数字独家分发。该条款页面标注更新于 2024-09-27。本项目已有 GitHub/Wiki 公开全文且已按 CC BY 4.0 授权，不应默认勾选 Select 或 Kindle Unlimited。作者需另行核对是否能够满足独家义务；删除版权声明或关闭仓库不会撤销已经授予的 CC 许可。

**保留权利边界。** 作者可以商业出版自己的原创内容，但不能撤销已授予的 CC BY 4.0 许可。第三方论文、代码、截图、商标和引用各有其权利与许可，须根据最终实际用法复核；不能因原仓库开放就把全部引用视为可任意重印。集中许可页不代替第三方要求的具体署名、通知或授权。

## 到可发行电子书还差什么

先完成全部章节审校并冻结一版。当前导出已经处理静态插图、公式、原生导航和可重排打包，但仍需人工确认图中文字、公式含义、替代文本、宽表与代码在目标设备上的阅读效果，并复核资产权利。

用 Kindle Previewer 检查不同屏幕、字号和横竖屏；公式与图表还要人工逐页看，不能仅凭结构校验成功。具备平台支持的真实语言稿、完成封面、书目资料、真实致谢和权利复核后，再根据实际出版语言及 AI 使用情况填写 KDP 后台。没有获得的 ISBN、出版社、出版年次或贡献者姓名，不应为凑齐页面而编造。
