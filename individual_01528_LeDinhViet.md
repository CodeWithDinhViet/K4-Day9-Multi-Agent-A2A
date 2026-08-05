# Báo cáo cá nhân — Day 9: Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Lê Đình Việt |
| MSSV | 2A202601528 |
| Khóa/Lớp | K4 |
| Vai trò chính | Thiết kế và triển khai toàn bộ pipeline cá nhân |
| Ngày hoàn thành | 05/08/2026 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data access và contract | `src/data_repository.py`, `src/models.py` | 9 CSV và input JSON | Index read-only, typed handoff | Hoàn thành |
| Domain agents | `src/agents/` | Claimed order ID | Customer/order/payment/delivery analysis | Hoàn thành |
| Policy và output | `policy_agent.py`, `output_builder.py` | Investigation bundle | Policy decision và output schema | Hoàn thành |
| Verification và batch | `verifier_agent.py`, `runner.py` | Output candidate | 50 JSON đã verify, trace, metadata | Hoàn thành |
| Test và tài liệu | `tests/`, `architecture.md` | Pipeline hoàn chỉnh | Test report và kiến trúc | Hoàn thành |

Đây là bài làm cá nhân nên không có dependency vào module của thành viên khác. Các dependency nội bộ được quản lý qua contract dataclass giữa Coordinator và agent.

### Việc hỗ trợ ngoài phạm vi chính

Không có; toàn bộ phạm vi được triển khai cá nhân.

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | Artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Điều tra toàn bộ input | `src/agents/`, `src/orchestrator.py` | 50/50 case được phân tích | `python -m src.main --all` |
| Sinh kết quả chấm | `output/EC_001.json` đến `EC_050.json` | Đúng 50 JSON | Đếm và parse lại toàn bộ file |
| Kiểm tra regression | `tests/test_pipeline.py` | 6 test pass | `python -m unittest discover -s tests -v` |
| Ghi audit | `logging/trace.jsonl`, `metadata.json` | 400 event, 50 case | Parse từng JSONL event |

Phân bố primary issue của 50 case:

| Primary issue | Số case |
| --- | ---: |
| `canceled_order_paid` | 8 |
| `unavailable_order_paid` | 6 |
| `late_delivery_seller` | 10 |
| `late_delivery_logistics` | 10 |
| `valid_split_payment` | 8 |
| `unsupported_late_claim` | 8 |

Có 34 case `action_required` và 16 case `no_action`.

## 4. Giải thích phần kỹ thuật

### Vấn đề cần giải quyết

Một khiếu nại không thể kết luận chỉ từ message khách hàng. Pipeline phải join nhiều bảng, tách trách nhiệm seller/carrier/platform, đối soát toàn bộ payment và chỉ phát hành evidence tồn tại trong nguồn.

### Cách triển khai

Repository đọc CSV một lần và lập index theo order/customer/product/seller. Coordinator giao claimed order cho bốn domain agent. Customer Agent tìm lịch sử bằng `customer_unique_id`; Order & Product Agent giữ thứ tự item; Payment Agent dùng `Decimal`; Delivery Agent tính chênh lệch timestamp và shipping limit sớm nhất theo seller. Policy Agent nhận bundle đã xác minh fact và áp dụng sáu rule theo đúng priority. Output Builder dựng schema; Verifier là hard gate trước khi Batch Runner ghi file.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `input/EC_001.json` đến `EC_050.json`, policy `EC_POLICY_V2` |
| Output | `output/EC_001.json` đến `EC_050.json` theo schema README |
| Module phụ thuộc | `data_repository`, domain agents, policy, output builder |
| Module sử dụng output | Verifier, runner và hệ thống chấm |
| Điều kiện lỗi | Thiếu input/order, policy không hỗ trợ, evidence giả, sai limit/schema/null |

### Cách xác minh

```powershell
python -m src.main --all
python -m unittest discover -s tests -v
```

- Kết quả mong đợi: ghi đủ 50 output và 6 test đều pass.
- Kết quả thực tế: `verified_outputs_written=50`, `Ran 6 tests ... OK`.
- Artifact/log: `output/`, `logging/trace.jsonl`, `logging/metadata.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Các phép cộng tiền và tolerance `0.10 BRL` không được sai do biểu diễn số.
- **Phương án cân nhắc:** dùng `float`; hoặc dùng `Decimal` xuyên suốt phần tính toán rồi chỉ chuyển sang JSON number khi dựng output.
- **Phương án chọn:** dùng `Decimal` với `ROUND_HALF_UP` và precision hai chữ số.
- **Lý do:** tránh lỗi nhị phân của `float`, giữ reconciliation và refund có thể tái lập.
- **Bằng chứng:** test tính lại `expected_total`, `difference` và tolerance cho toàn bộ 50 case đều pass.

## 6. Một lỗi đã xử lý

- **Triệu chứng:** CLI dùng `args.json` bên trong `inspect_case`, trong khi `args` là biến local của `main`, có thể gây `NameError` khi chạy trực tiếp.
- **Tái hiện:** `python -m src.main --case EC_001` sau khi thêm chế độ in JSON.
- **Nguyên nhân gốc:** hàm phụ thuộc ngầm vào biến ngoài scope thay vì nhận tham số.
- **Cách xử lý:** thêm tham số `show_json` và `write`, truyền tường minh từ `main`; đồng thời tách batch logic sang `runner.py`.
- **Xác minh:** CLI single-case, batch 50 case và toàn bộ unittest đều chạy thành công.
- **Bài học:** contract tường minh cần áp dụng cả giữa function CLI, không chỉ giữa agent.

## 7. Hiểu biết về luồng end-to-end

1. Input cung cấp claimed order ID. Repository tìm order rồi join customer, items, payments, products và sellers qua các khóa trong README.
2. Bốn domain agent tạo fact riêng biệt và handoff vào `InvestigationBundle`; dữ liệu lịch sử chỉ đi vào customer context.
3. Policy Agent xét rule theo thứ tự ưu tiên. Vì vậy canceled/unavailable paid luôn được xử lý trước late delivery hoặc split payment.
4. Output Builder tạo schema, root cause, responsibility, evidence, refund và actions. Verifier đối chiếu ngược với bundle/repository và chặn output sai.
5. Batch Runner chỉ ghi case đã pass, thay trace lần chạy mới nhất và tạo metadata. Test tái dựng 50 output từ input và so sánh với file đã nộp để phát hiện kết quả không tái lập.

Quality checks nằm ở nhiều lớp: input/order existence ở repository/coordinator, rule consistency ở Policy Agent, hard gate ở Verifier và regression ở unittest. Cùng 50 input được dùng cho mọi lần chạy để so sánh trực tiếp, tránh thay đổi test set làm sai lệch đánh giá.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ một module.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không sao chép báo cáo của thành viên khác.

**Họ và tên:** Lê Đình Việt

**Ngày xác nhận:** 2026-08-05
