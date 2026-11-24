# Hướng dẫn sử dụng Kiro Agent Harness (tiếng Việt)

Tài liệu này hướng dẫn cách cài đặt, cấu hình và vận hành Harness trong một dự án thực tế. Nội dung bám theo [README.md](../README.md), [Customization Guide](CUSTOMIZING.md) và [Command reference](reference/cli.md); khi có khác biệt, các tài liệu tiếng Anh đó và mã nguồn là chuẩn.

## 1. Harness là gì

Kiro Agent Harness là một bộ cấu hình dùng lại được cho Kiro IDE (và tùy chọn cho Claude Code, Cursor, Copilot). Repository này không chứa mã ứng dụng. Thứ bạn nhận được là:

- **Steering:** các file Markdown cung cấp bối cảnh dự án cho agent (sản phẩm, công nghệ, cấu trúc, bảo mật, quy tắc code, test, API, phát hành).
- **Hook an toàn và chất lượng:** chặn lệnh shell nguy hiểm, hỏi xác nhận trước khi dùng công cụ rủi ro, bảo vệ file nhạy cảm, quét secret trong prompt, chạy lint/test khi lưu file.
- **Cấu hình MCP:** các MCP server mẫu (AWS docs, fetch, git) với phiên bản ghim chính xác và danh sách auto-approve chỉ gồm công cụ đọc.
- **Validator offline:** kiểm tra toàn bộ cấu hình trên, chỉ dùng thư viện chuẩn Python, không cần mạng.
- **Bộ test:** unit test, property test (Hypothesis), eval và test tích hợp MCP (tùy chọn).

## 2. Yêu cầu

| Thành phần | Dùng cho |
|---|---|
| Python 3.10 trở lên | Validator, hook, test, lệnh `scripts/harness` |
| POSIX `sh` | Các wrapper của hook và script trong `scripts/` |
| `uv` / `uvx` | Khởi chạy MCP server mẫu |
| Hypothesis (trong `requirements-dev.txt`) | Chỉ cần cho property test |
| Kiro IDE | Đã kiểm chứng trên Kiro 1.5.11 (xem `docs/verification/kiro/1.5.11/`) |

Kiểm tra nhanh máy của bạn:

```sh
scripts/harness doctor
```

Lệnh in phiên bản Harness, Python, `sh`, `git`, `uvx`, các Agent đang bật và tình trạng drift. Mã thoát 1 nghĩa là thiếu Python 3.10 hoặc `sh`.

## 3. Cài đặt

Có hai cách.

### Cách A: cài vào một repository có sẵn (khuyến nghị)

Từ một bản checkout của Harness, chạy:

```sh
scripts/harness init ../my-project --agents kiro,claude-code
```

Lệnh này sao chép Harness, tạo `harness/manifest.json` chỉ với các Agent bạn chọn (`kiro`, `claude-code`, `cursor`, `copilot`; mặc định `kiro`), sinh các file cho từng Agent, rồi chạy validator. Nếu file đã tồn tại, lệnh dừng mà không thay đổi gì, trừ khi bạn thêm `--force`.

Sau đó commit toàn bộ kết quả, kể cả các file được sinh ra và `harness/release.lock.json`.

### Cách B: dùng repository này làm điểm khởi đầu

Clone repository và làm việc trực tiếp trên đó.

### Các bước sau khi cài

1. Tạo file biến môi trường cục bộ:

   ```sh
   cp .env.example .env
   ```

   `.env` chứa giá trị thật và đã nằm trong `.gitignore`. Không bao giờ commit file này.

2. Thay các placeholder dự án (tên dự án, ngôn ngữ chính, thư mục nguồn, framework test...). Danh sách đầy đủ và file chứa từng placeholder nằm ở mục **Placeholders** trong [README.md](../README.md#placeholders). Placeholder viết dạng chữ in hoa đặt trong cặp ngoặc nhọn kép.
3. Cấu hình lệnh lint và test (xem mục 7).
4. Tắt các MCP server không dùng (xem mục 6).
5. Chạy validator:

   ```sh
   scripts/validate.sh
   ```

   Kết quả mong đợi: mã thoát 0 và `0 errors`.

6. (Tùy chọn) Bật Git hook cho bản clone này:

   ```sh
   scripts/install-git-hooks.sh
   ```

   Lệnh chỉ đặt `core.hooksPath=.githooks` cục bộ, không đụng cấu hình Git toàn cục. Đọc [GIT_HOOKS.md](GIT_HOOKS.md) trước nếu bạn đã dùng một trình quản lý hook khác.

## 4. Nguyên tắc quan trọng nhất: sửa nguồn, không sửa file sinh ra

Harness dùng một nguồn duy nhất để sinh cấu hình cho nhiều Agent:

| Nguồn (bạn sửa ở đây) | File được sinh ra (không sửa tay) |
|---|---|
| `harness/guidance/*.md` | `.kiro/steering/`, `AGENTS.md`, `CLAUDE.md`, `.claude/rules`, `.cursor/rules`, `.github/copilot-instructions.md` |
| `harness/kiro/hooks/*.json` | `.kiro/hooks/<id>.json` |
| `harness/manifest.json` | `.kiro/settings/mcp.json`, `.claude/settings.json`, `.mcp.json` |

Sau mỗi lần sửa nguồn:

```sh
scripts/harness sync          # sinh lại file
scripts/harness sync --check  # chỉ kiểm tra, không ghi; mã thoát 1 kèm diff nếu có drift
```

Nếu bạn sửa tay một file sinh ra, validator sẽ báo lỗi **DRIFT** và `sync` sẽ từ chối ghi đè (bảo vệ bằng `harness/generated.lock.json`). Chuyển nội dung đó về file nguồn rồi chạy `scripts/harness sync --force` một lần.

## 5. Steering (bối cảnh cho agent)

Mỗi file steering là Markdown có front matter. Viết trong `harness/guidance/`, sau đó chạy `scripts/harness sync`. Trường `inclusion` quyết định khi nào Kiro nạp file:

| `inclusion` | Khi nào được nạp | Trường bắt buộc thêm |
|---|---|---|
| `always` | Mọi phiên làm việc | không |
| `fileMatch` | Khi có file khớp mẫu glob trong ngữ cảnh | `fileMatchPattern` (một glob hoặc danh sách glob) |
| `manual` | Khi bạn gọi `#<tên file>` trong chat | không |
| `auto` | Khi Kiro thấy yêu cầu khớp mô tả | `name` (1 đến 64 ký tự), `description` (1 đến 200 ký tự) |

Ví dụ một file `harness/guidance/sql-style.md`:

```markdown
---
inclusion: fileMatch
fileMatchPattern: ["**/*.sql", "migrations/**"]
---

# SQL Style

- Viết từ khóa SQL bằng chữ in hoa.
- Mọi migration phải đảo ngược được.
```

Validator chỉ hỗ trợ một tập con YAML: dòng `key: value` (giá trị trơn, nháy đơn hoặc nháy kép), `true`/`false`, danh sách dạng `[a, b]` hoặc dòng `- a`, và chú thích `#`. Mapping lồng nhau, anchor, tag, giá trị nhiều dòng và thụt lề bằng tab sẽ bị báo lỗi.

## 6. Cấu hình MCP server

MCP server được khai báo trong `harness/manifest.json` và sinh ra `.kiro/settings/mcp.json`. Bản mẫu có ba server: `aws-docs`, `fetch`, `git`.

Quy tắc bắt buộc (validator kiểm tra):

- Ghim phiên bản chính xác dạng `X.Y.Z` (ví dụ `mcp-server-git@2026.11.18`). Không dùng `@latest` hay khoảng phiên bản.
- `autoApprove` chỉ chứa công cụ chỉ-đọc.
- Thông tin xác thực chỉ ghi dưới dạng tham chiếu biến môi trường, ví dụ `${EXAMPLE_SERVICE_TOKEN}`. Không bao giờ ghi giá trị thật vào JSON hay Markdown được theo dõi bởi Git.
- Mỗi biến như vậy phải được khai báo trong `.env.example` với dòng chú thích ngay phía trên:

  ```sh
  # Used by MCP server: example-service
  EXAMPLE_SERVICE_TOKEN=replace-me
  ```

  Giá trị thật đặt trong `.env`.

Muốn tắt một server, đặt `"disabled": true` cho server đó trong Manifest rồi chạy `scripts/harness sync`.

So sánh phiên bản đang ghim với PyPI (cần mạng, không sửa file):

```sh
scripts/check-mcp-updates.sh
```

Đọc release note và cảnh báo bảo mật trước khi nâng phiên bản.

## 7. Cấu hình lệnh lint và test của dự án

Sửa `scripts/project-commands.env`:

```sh
LINT_FILE_COMMAND="ruff check"
TEST_FILE_COMMAND="python3 -m pytest -q"
TEST_COMMAND="python3 -m pytest -q"
```

- `LINT_FILE_COMMAND`: lint một file. Harness tự nối đường dẫn file vào cuối lệnh.
- `TEST_FILE_COMMAND`: chạy một file test, một lần (không chạy chế độ watch).
- `TEST_COMMAND`: chạy toàn bộ test suite một lần.

File này được đọc như dữ liệu dạng `KEY="value"`, không bao giờ bị `source`. Để trống một giá trị nếu muốn bỏ qua bước đó. Khi một giá trị còn trống hoặc vẫn là placeholder, `scripts/lint.sh` và `scripts/test.sh` thoát với mã 3 và thông báo `not configured: <KEY>`.

Hook lưu file chỉ áp dụng cho các phần mở rộng `ts`, `tsx`, `js`, `jsx`, `py`, `go` (xem `matcher` trong hook `quality-on-save`). Mẫu tên file test nằm trong `.kiro/hooks/scripts/quality-hook.conf`.

## 8. Các hook Kiro

Định nghĩa hook nằm trong `.kiro/hooks/` (sinh từ `harness/kiro/hooks/`).

| Hook | Trigger | Hành vi |
|---|---|---|
| `destructive-command-guard` | PreToolUse | Chặn lệnh shell khớp `harness/policy/destructive-commands.txt` |
| `risky-tool-guard` | PreToolUse | Hỏi xác nhận với công cụ và tham số rủi ro trong `harness/policy/risky-tools.conf` |
| `protected-path-guard` | PreToolUse | Chặn đọc, ghi, xóa các đường dẫn trong `harness/policy/protected-paths.txt` (ví dụ `.env`) |
| `quality-on-save` | PostFileSave | Chạy lint cho file nguồn vừa lưu; chạy test nếu đó là file test |
| `session-start-context` | SessionStart | Thêm nhánh Git hiện tại và số file đang thay đổi vào ngữ cảnh |
| `prompt-secret-scan` | UserPromptSubmit | Chặn prompt chứa giá trị trông giống secret |
| `post-task-tests` | PostTaskExec | Chạy toàn bộ test một lần sau mỗi task của spec |
| `stop-validate` | Stop | Nhắc agent chạy `scripts/validate.sh` trước khi kết thúc |

Hai ví dụ đang tắt nằm trong `.kiro/hooks/examples/`: nhắc viết test cho file mới và chụp trạng thái repository trước khi nén ngữ cảnh.

### Cơ chế khi lỗi (cố ý, đừng thay đổi)

- **Guard lệnh nguy hiểm, guard đường dẫn bảo vệ và quét secret trong prompt "fail closed":** nếu khớp mẫu, input hỏng, thiếu file policy hoặc thiếu `python3`, hook thoát mã 2 và chặn lệnh.
- **Guard công cụ rủi ro "fail to ask":** nếu input hoặc policy không dùng được, hook yêu cầu người dùng xác nhận thay vì cho phép hay chặn.

### Thử một guard bằng tay

```sh
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push --force"}}' \
  | harness/bin/guard claude-code pre_tool; echo "exit=$?"
```

Mã thoát 2 kèm thông báo trên stderr nghĩa là lệnh đã bị chặn.

### Thêm một hook

Tạo file JSON trong `harness/kiro/hooks/` với `"version": "v1"` và mảng `hooks`. Ví dụ hook nhắc cập nhật tài liệu API khi lưu file trong `src/api/`:

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "docs-reminder",
      "trigger": "PostFileSave",
      "matcher": "^src/api/",
      "action": {
        "type": "agent",
        "prompt": "An API source file changed. Check whether the API documentation needs the same change."
      }
    }
  ]
}
```

Lưu ý:

- Tên file chỉ dùng chữ thường, chữ số và dấu gạch ngang đơn.
- Các trigger `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostFileCreate`, `PostFileSave`, `PostFileDelete` cần `matcher` (regex trên ID công cụ hoặc đường dẫn file). Tránh `*` và `?` trong matcher.
- Action dạng `command` cần `timeout` là số nguyên từ 1 đến 300 giây, và script phải tồn tại, có quyền thực thi.

Chi tiết đầy đủ ở [Customization Guide](CUSTOMIZING.md).

## 9. Chỉnh sửa policy

Các file policy trong `harness/policy/` được đọc lúc chạy, nên đổi policy không cần sửa mã. Dòng trống và dòng bắt đầu bằng `#` bị bỏ qua.

| File | Định dạng |
|---|---|
| `destructive-commands.txt` | Mỗi dòng một mẫu gồm các từ literal (tối đa 200 mẫu). Lệnh khớp khi các từ xuất hiện theo thứ tự trong cùng một đoạn lệnh (tách bởi `&&`, `\|\|`, `;`, `\|`, xuống dòng). Không phân biệt hoa thường. |
| `risky-tools.conf` | Mỗi dòng `tool \| reason \| predicate`. Cột tool là `category:<tên>`, `<agent>:<tool-id>` hoặc ID công cụ Kiro. Predicate là `*`, `regex <field> <pattern>` hoặc `host-not-in <field> @<file>`. |
| `protected-paths.txt` | Mẫu glob cho file agent không được đọc, ghi, xóa. Dòng bắt đầu bằng `!` để loại trừ lại. |
| `egress-allowlist.txt` | Mỗi dòng một host. Gọi web tới host không có trong danh sách sẽ phải xác nhận. |

Ví dụ thêm một lệnh nguy hiểm cần chặn, nối vào cuối `destructive-commands.txt`:

```text
docker system prune
```

Khi thêm công cụ Kiro mới vào `risky-tools.conf`, nhớ thêm ID đó vào regex `matcher` của hook `risky-tool-guard` (dạng `^(...)$`). Validator kiểm tra hai nơi này luôn khớp nhau.

Xem đầy đủ ở [Policy_File formats](reference/policy-files.md).

## 10. Bật thêm Agent khác

Sửa `harness/manifest.json`, ví dụ bật Claude Code:

```json
"claude-code": {"enabled": true}
```

Rồi chạy:

```sh
scripts/harness sync
scripts/harness sync --check
scripts/validate.sh
```

Claude Code nhận `CLAUDE.md`, `.claude/rules`, `.claude/settings.json` (quyền deny/ask/allow suy ra từ policy) và `.mcp.json`. Cursor và Copilot chỉ nhận guidance, không có hook. Xem [Enable another Agent](how-to/enable-an-agent.md) và [Capability matrix](reference/capabilities.md).

## 11. Kiểm tra và test

Chạy từ thư mục gốc của repository.

| Lệnh | Mục đích | Mạng |
|---|---|---|
| `scripts/validate.sh` | Validator cấu hình và toàn bộ unit test. Chạy trước khi hoàn thành mọi thay đổi. | Không |
| `scripts/validate-config.sh` | Chỉ validator (mã thoát 0 ổn, 1 có lỗi, 2 lỗi nội bộ) | Không |
| `scripts/test-properties.sh` | Property test bằng Hypothesis (dùng `uv`, hoặc tự tạo `.venv`) | Có thể cần để cài gói |
| `HARNESS_OFFLINE=1 scripts/test-properties.sh` | Property test với Hypothesis đã cài sẵn | Không |
| `HYPOTHESIS_PROFILE=ci scripts/test-properties.sh` | 300 ví dụ mỗi test thay vì 100 | Như trên |
| `scripts/coverage.sh` | Cổng coverage: 90% dòng, 80% nhánh | Không |
| `python3 -I evals/run.py [--corpus]` | Chạy lại kịch bản eval hoặc Bypass_Corpus qua mọi Adapter | Không |
| `scripts/harness trace` | Báo cáo truy vết yêu cầu, ghi `build/traceability.json` | Không |
| `HARNESS_INTEGRATION=1 python3 -m unittest tests.integration.test_mcp_servers` | Khởi động MCP server thật và kiểm tra công cụ | Có |

Chạy một module hoặc một test đơn lẻ:

```sh
python3 -m unittest tests.hooks.test_destructive_guard
.venv/bin/python -m unittest tests.property.test_p01_hook_roundtrip
```

Git hook tùy chọn: `pre-commit` chạy `scripts/validate.sh`; `commit-msg` yêu cầu dòng tiêu đề không trống, tối đa 72 ký tự, không có khoảng trắng cuối dòng; `pre-push` chạy property test ở chế độ offline. CI (`.github/workflows/ci.yml`) chạy các kiểm tra tương tự trên mỗi push và pull request.

## 12. Nâng cấp Harness

```sh
scripts/harness upgrade --from ../harness-new
```

File bạn chưa sửa sẽ được cập nhật. File bạn đã sửa được giữ nguyên. Nếu file bạn sửa cũng thay đổi ở bản mới, lệnh báo xung đột kèm diff và để nguyên file; hãy gộp bằng tay rồi chạy lại. Manifest không bao giờ bị thay thế. Sau đó chạy `scripts/validate.sh` và đọc [CHANGELOG](../CHANGELOG.md). Đổi phiên bản major nghĩa là cơ chế khi lỗi của guard, định dạng policy hoặc schema sự kiện đã thay đổi.

## 13. Giới hạn cần biết

Các guard là **lưới an toàn, không phải sandbox**. Chúng so khớp mẫu trên văn bản lệnh, nên bắt được lỗi thông thường (force push, đọc `.env`, dán nhầm key) nhưng không ngăn được một agent cố tình né tránh bằng cách viết lệnh theo dạng khác. Với workload không tin cậy, hãy dùng cô lập ở mức hệ điều hành (container hoặc VM không có credential và không có mạng ngoài ý muốn). Xem [Why the guards are a safety net, not a sandbox](explanation/limits-and-threat-model.md).

Hành vi payload và chế độ `ask` của Kiro có thể khác nhau giữa các phiên bản IDE. Khi nâng cấp Kiro hoặc đổi hook, chạy checklist kiểm tra thủ công trong [Customization Guide](CUSTOMIZING.md) và runbook ở [docs/verification/kiro/RUNBOOK.md](verification/kiro/RUNBOOK.md).

## 14. Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân và cách xử lý |
|---|---|
| Validator báo `DRIFT` | Bạn đã sửa tay file sinh ra. Chuyển thay đổi về file nguồn trong `harness/`, chạy `scripts/harness sync`. |
| `sync` từ chối ghi đè `CLAUDE.md` hoặc file khác | File đó được viết tay. Chuyển nội dung vào `harness/guidance/`, chạy `scripts/harness sync --force` một lần. |
| Validator báo placeholder chưa liệt kê | Thêm placeholder đó vào mục Placeholders của `README.md`, kèm danh sách file chứa nó. |
| `scripts/lint.sh` hoặc `scripts/test.sh` thoát mã 3 | Lệnh tương ứng trong `scripts/project-commands.env` chưa được cấu hình. |
| Mọi lệnh shell đều bị chặn | Có thể thiếu `python3` hoặc file policy không đọc được (guard fail closed). Chạy `scripts/harness doctor`. |
| Validator báo thiếu biến trong `.env.example` | Thêm biến kèm dòng `# Used by MCP server: <tên>` ngay phía trên. |
| Validator báo MCP pin không hợp lệ | Đổi `@latest` hoặc khoảng phiên bản thành phiên bản chính xác `X.Y.Z`. |

## Tài liệu liên quan

- [Chỉ mục tài liệu](README.md)
- [Tutorial: cài đặt và xem guard chặn lệnh](tutorials/getting-started.md)
- [Customization Guide](CUSTOMIZING.md)
- [Command reference](reference/cli.md)
- [Architecture](explanation/architecture.md)
- [Implementation status](IMPLEMENTATION_STATUS.md)
