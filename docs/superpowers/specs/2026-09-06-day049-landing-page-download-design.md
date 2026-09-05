# Day049 Landing Page 下载设计

## 目标

让用户把当前结果或历史完成记录中的 Landing Page 下载为 ZIP 压缩包。

## 范围

- 在现有交付区域增加一个下载操作。
- 支持当前结果和历史完成记录。
- 每次请求时在内存中生成 ZIP。
- 复用现有工作流记录和 `LandingPagePackage` 契约。
- 不新增依赖、数据库字段或持久化压缩包。

## 架构

浏览器通过工作流编号发起下载请求。现有 HTTP 服务使用 `get_workflow_run()` 重新读取该工作流，验证状态和 Landing Page 文件包，再使用 Python 标准库 `io.BytesIO` 与 `zipfile.ZipFile` 返回压缩包。

下载接口：

```text
GET /api/workflows/{workflow_id}/download
```

压缩包名称：

```text
landing-page-{workflow_id}.zip
```

## 压缩包契约

ZIP 根目录必须且只能包含：

```text
index.html
styles.css
script.js
```

文件名来自固定的 `REQUIRED_FILES` 白名单，不允许把用户提供的路径写入压缩包。

## 数据流

1. `renderRun()` 接收当前或历史工作流结果。
2. 只有状态为完成且存在有效 `landing_page` 时，页面才显示下载按钮。
3. 用户点击下载按钮。
4. 浏览器使用该记录的工作流编号请求下载接口。
5. 服务端重新读取权威工作流记录。
6. 服务端拒绝不存在、未完成或网页包无效的记录。
7. 服务端在内存中生成 ZIP，并作为附件返回。
8. 浏览器保存压缩包；服务端不保留 ZIP 文件。

## HTTP 行为

成功响应：

```text
200 OK
Content-Type: application/zip
Content-Disposition: attachment; filename="landing-page-{workflow_id}.zip"
Cache-Control: no-store
```

错误继续使用现有 JSON 格式：

- 工作流不存在时返回 `404`。
- 工作流未完成或没有有效 Landing Page 文件包时返回 `409`。
- 压缩过程出现意外错误时返回 `500` 和通用错误信息。

## 用户界面

现有交付区域在预览附近增加一个“下载网站 ZIP”按钮。选中的结果无法下载时隐藏按钮。切换到失败或无网页包的历史记录时，必须清除旧的可下载工作流编号，避免下载上一条记录。

浏览器使用简短的请求与 Blob 下载流程，使 JSON 错误可以显示在当前状态区域，而不是跳离操作台页面。

## 安全要求

- 只从固定的三文件契约生成压缩包。
- 服务端重新读取工作流，不信任浏览器提交的文件内容。
- 压缩包仅存在于内存，并返回 `Cache-Control: no-store`。
- 保留工作流写入历史前已有的敏感数据检查。
- HTTP 错误不得暴露服务器路径或异常细节。

## 验证

扩展 `test_web_app.py`，验证：

- 完成记录返回可打开的 ZIP，且三个文件及内容完全正确。
- 不存在的工作流返回 `404` JSON。
- 失败或无网页包的工作流返回 `409` JSON。
- 页面包含下载控件并连接正确接口。
- 不可下载记录会隐藏控件。

最后运行完整项目验证，并在浏览器中分别检查当前结果和历史记录下载。

## 实施时修改的文件

- `web_app.py`
- `web/index.html`
- `test_web_app.py`
- `PROGRESS.md`

## 不在本次范围

- 永久保存 ZIP 文件。
- 在浏览器内编辑网页包。
- 支持其他压缩格式。
- 部署或云端存储。
- 修改工作流数据库结构。
