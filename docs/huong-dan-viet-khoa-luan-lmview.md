# HƯỚNG DẪN VIẾT KHÓA LUẬN LMVIEW
## Văn phong học thuật — Quy trình trích dẫn — Đề cương triển khai chi tiết

> Tài liệu này KHÔNG phải là khóa luận. Đây là bộ "luật chơi" + đề cương dùng để chỉ đạo các phiên viết tiếp theo (cho Claude hoặc bất kỳ AI nào hỗ trợ soạn thảo). Dán nguyên văn các phần liên quan vào đầu mỗi phiên viết.

---

# PHẦN 0 — GIẢ ĐỊNH NỀN TẢNG CỦA TOÀN BỘ KHÓA LUẬN

## 0.1. Chỉ đạo của tác giả — BẮT BUỘC TUÂN THỦ TUYỆT ĐỐI

Theo chỉ đạo trực tiếp của tác giả, toàn bộ khóa luận (Chương 2, 3, 4) được viết trên **giả định nền đã chốt**, không còn là vấn đề cần xác nhận thêm:

> **Hệ thống LMView tại thời điểm thực hiện khóa luận đã triển khai đầy đủ kiến trúc 3-node Docker Swarm đúng như mô tả trong tài liệu "3-Node Docker Swarm Architecture"** (Node 1 — API/Infra; Node 2 — Data/Streaming; Node 3 — Compute/Analytics, đầy đủ Kafka RF=3, Redis Sentinel 3 node, Flink 2 TaskManager, Spark 2 Worker, Trino, đúng bảng đặt dịch vụ và placement constraints trong tài liệu đó), **và toàn bộ luồng dữ liệu của kiến trúc Lambda đã hoạt động hoàn toàn ổn định**: Kafka nhận dữ liệu liên tục từ tầng thu thập, Flink tính chỉ báo kỹ thuật theo thời gian gần thực, Spark Structured Streaming ghi đầy đủ ba tầng Bronze/Silver/Gold lên Iceberg, Trino phục vụ truy vấn lịch sử, Redis Sentinel phục vụ tầng tốc độ, và cơ chế đối chiếu dữ liệu (reconciliation/stitching) tại Serving Layer hoạt động đúng thiết kế.

Hệ quả cụ thể cho việc viết:

- **Mọi mô tả trong SYSTEM.md về producer chết, Kafka rỗng/idle, Flink không nhận dữ liệu, Iceberg gold layer trống, hoặc Spark Structured Streaming chưa ổn định** được hiểu là **mô tả một giai đoạn gỡ lỗi trước đó trong quá trình phát triển**, không phải trạng thái cuối cùng được trình bày trong khóa luận. Khóa luận không cần nhắc lại các sự cố này như hạn chế hiện tại; nếu cần, có thể nhắc ngắn gọn ở dạng quá khứ trong phần "bài học kinh nghiệm" (ví dụ mục 4.5/4.6), không phải ở "Kết quả triển khai".
- **Nội dung trong "Kế hoạch khắc phục Indicator Pipeline" được coi là đã thực hiện xong và đã kiểm thử thành công** — bao gồm việc producer/luồng thu thập đã kết nối ổn định, pipeline Kafka → Flink → chỉ báo chạy đúng, và cơ chế hợp nhất nến đã đóng (closed candle, có chỉ báo) với nến đang hình thành (forming candle, từ ticker trực tiếp) đã được tích hợp ở tầng phục vụ.
- **Chương 3 ("Xây dựng và triển khai")** mô tả việc triển khai 3 node như một kết quả đã đạt được, không cần đoạn "minh bạch về khoảng cách thiết kế–thực tế" như một phiên bản trước của tài liệu này từng yêu cầu. Bảng trạng thái dịch vụ ở mục "Kết quả triển khai" trình bày toàn bộ dịch vụ đang chạy ổn định (theo đúng mẫu bảng "✅ Running" của bản "Nhóm 79" §3.3.1).
- **Chương 4** báo cáo số liệu hiệu năng được đo trên hạ tầng 3-node này. Phần "Pilot Benchmarking" và "Threats to Validity" của bản "Đại học" vẫn **nên giữ nguyên** — đây không phải là sự thiếu tự tin về việc hệ thống có chạy hay không, mà là sự trung thực học thuật chuẩn mực về *quy mô mẫu đo* (3 symbol, vài trăm frame) và *phạm vi đo* (một vị trí địa lý, điều kiện thị trường bình thường). Giữ phần này làm khóa luận mạnh hơn về phương pháp luận, không mâu thuẫn với giả định "hệ thống hoạt động hoàn toàn".

## 0.2. Vai trò của từng nguồn (đã cập nhật theo giả định ở 0.1)

| Nguồn | Vai trò nên dùng |
|---|---|
| **Khóa luận "ĐẠI HỌC"** | Khung văn phong, cấu trúc lập luận, phương pháp đánh giá (pilot benchmarking, threats to validity), danh mục trích dẫn đã qua một vòng xác minh. Riêng phần hạ tầng "2 node" trong tài liệu này **không dùng nữa** — thay bằng 3-node theo 0.1. |
| **Khóa luận "Nhóm 79"** | Nguồn chính cho mô tả kiến trúc 3-node, bảng chức năng, sơ đồ use case, kịch bản (scenario), bảng trạng thái dịch vụ — coi các bảng "✅ Running" trong tài liệu này là đúng với giả định ở 0.1. |
| **3-Node Docker Swarm Architecture** | Nguồn kỹ thuật chính xác nhất cho sơ đồ đặt dịch vụ theo node, bảng partition Kafka, SPOF & mitigation — là tài liệu xương sống cho toàn bộ Chương 2 và Chương 3. |
| **SYSTEM.md** | Nguồn tham khảo cho chi tiết kỹ thuật (Redis key schema, cấu trúc Flink job, Avro schema, cơ chế WebSocket sharding...) — **bỏ qua mọi đoạn mô tả lỗi/trạng thái idle**, chỉ lấy phần mô tả cơ chế/thiết kế kỹ thuật. |
| **Kế hoạch khắc phục Indicator Pipeline** | Theo 0.1, coi như đã triển khai xong — dùng làm nguồn mô tả cơ chế hợp nhất closed/forming candle ở tầng phục vụ (mục "Phân tích thiết kế" Chương 2 và "Kết quả triển khai" Chương 3). |

## 0.3. Những điểm CHƯA nằm trong chỉ đạo ở 0.1 — vẫn cần anh xác nhận hoặc AI tự gắn cờ khi viết

Chỉ đạo ở 0.1 giải quyết câu hỏi về **số node** và **tình trạng hoạt động của luồng dữ liệu**. Các điểm sau là những chi tiết khác, độc lập với hai vấn đề đó, vẫn còn xung đột giữa các nguồn và nên được xác nhận riêng khi viết tới mục liên quan (không chặn việc viết Chương 1, 2, 3):

1. **AI Interact Mode / multi-agent (Chart Agent, News Agent, Indicator Agent):** đã và đang triển khai, có thể coi là xong và đủ cơ sở để đưa vào nội dung khóa luận.
2. **Số chỉ báo kỹ thuật:** 5 chỉ báo cơ bản (bản "Nhóm 79") hay đủ 16 chỉ báo (bản "Đại học")?
3. **Số khung thời gian hỗ trợ:** 9 khung 1s→1w hay 7 khung 1m→1w?
4. **Version cụ thể:** Flink 1.18.1 hay 1.17.1-java11; lightweight-charts v4.x hay v5.2 (v5.2 nhiều khả năng đúng hơn vì khớp với bộ nhớ hội thoại).
5. **Số LLM provider thực tế:** 4 provider hay 2 provider (mock + litellm)?
6. **Pipeline tin tức/sentiment (VADER/FinBERT/CryptoBERT):** đã hoàn thiện lưu trữ tin tức, sentiment chưa có nhiều cơ hội kiểm nghiệm nhưng hãy coi nó có tác động nhất định.

Khi AI viết tới các mục liên quan mà chưa có câu trả lời, mặc định dùng phương án có độ tin cậy cao hơn (đã ghi rõ ở từng dòng) và gắn chú thích `[CẦN XÁC NHẬN: ...]` ngay trong bản nháp thay vì tự quyết âm thầm.

## 0.4. Cấu trúc đề mục khóa luận (gần như đã chốt, đánh dấu * nếu chưa chắc chắn):
CHƯƠNG 1: CƠ SỞ LÝ THUYẾT
1.1. Tiền điện tử và thị trường tiền điện tử
1.1.1. Khái niệm và lịch sử phát triển của tiền điện tử
1.1.2. Cơ chế vi mô và đặc điểm thị trường tiền điện tử
1.1.3. Giả thuyết thị trường hiệu quả trong bối cảnh tiền điện tử
1.1.4. Cơ chế đồng thuận và tác động đến thị trường
1.1.5. Các sàn giao dịch tiền điện tử
1.2. Phân tích kỹ thuật trong thị trường tiền điện tử
1.2.1. Nền tảng lý thuyết phân tích kỹ thuật
1.2.2. Các chỉ báo kỹ thuật cốt lõi
1.2.3. Biểu đồ nến Nhật và cấu trúc dữ liệu OHLCV 
1.2.4. Các mô hình nến cơ bản và nhận dạng mô hình
1.3. Tác động của tin tức đến thị trường tiền điện tử
1.4. Xử lý dữ liệu lớn trong thời gian thực
1.4.1. Kiến trúc Lambda (Lambda Architecture)
1.4.2. Hạ tầng lưu trữ Data Lakehouse
1.4.3. Kỹ thuật xử lý dữ liệu thời gian thực đưa ra các
1.5. Trí tuệ nhân tạo trong phân tích tài chính *
CHƯƠNG 2: TỔNG QUAN VÀ KIẾN TRÚC HỆ THỐNG
2.1. Tổng quan hệ thống
2.1.1. Yêu cầu chức năng
2.1.2. Yêu cầu phi chức năng
2.2. Kiến trúc dữ liệu
2.2.1. Các kiểu dữ liệu *
2.2.2. Kiến trúc Lambda ba tầng
2.2.2.1. Speed Layer
2.2.2.2. Batch Layer
2.2.2.3. Serving Layer
2.2.3. Cấu trúc lưu trữ dữ liệu *
2.3. Kiến trúc AI *
2.4. Phân tích thiết kế hệ thống
2.4.1. Tác nhân và ca sử dụng
2.4.2. Biểu đồ tuần tự 
2.4.3. Biểu đồ lớp
CHƯƠNG 3: XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG
3.1. Công nghệ và công cụ sử dụng
3.1.1. Công nghệ lưu trữ dữ liệu
3.1.2. Công nghệ xử lý luồng dữ liệu
3.1.3. Công nghệ trí tuệ nhân tạo
3.1.4. Công nghệ phát triển ứng dụng
3.1.5. Công nghệ giám sát và quản lý
3.1.6. Công nghệ hạ tầng
3.2. Triển khai và cấu hình hệ thống *
3.2.1. Triển khai kiến trúc hệ thống phân tán *
3.2.2. Thiết lập cấu hình hệ thống *
3.3. Chức năng và giao diện người dùng *
CHƯƠNG 4: ĐÁNH GIÁ VÀ KẾT LUẬN
4.1. Kết quả đạt được
4.2. Đánh giá hiệu năng hệ thống *
4.2.1. Tiêu chí đánh giá *
4.2.2. Kết quả đánh giá *
4.3. Kết luận
4.3.1. Điểm mạnh
4.3.2. Hạn chế
4.4. Đề xuất hướng phát triển

---

# PHẦN 1 — YÊU CẦU VĂN PHONG HỌC THUẬT (bắt buộc cho toàn bộ thân bài)

## 1.1. Ngôi xưng và giọng văn
Toàn bộ khóa luận viết ở ngôi thứ ba học thuật. Không dùng "tôi", "chúng tôi", "nhóm em". Chủ ngữ của câu là "khóa luận", "nghiên cứu này", "hệ thống", "nhóm nghiên cứu", hoặc câu bị động/vô nhân xưng ("có thể thấy rằng...", "kết quả cho thấy..."). Đây là điểm bản "Đại học" đã làm đúng (ghi rõ trong phần đầu là đã "chuyển đổi từ ngôi thứ nhất sang ngôi thứ ba học thuật") — giữ nguyên chuẩn này cho toàn bộ nội dung mới.

## 1.2. Quy tắc đoạn văn — ĐIỀU KIỆN BẮT BUỘC ANH YÊU CẦU
**Cấm tuyệt đối việc dùng danh sách gạch đầu dòng để thay thế lập luận trong thân bài.** Một bullet liệt kê 5 đặc điểm mà không có câu nào giải thích "tại sao", "như thế nào", "có ý nghĩa gì" là một bản tóm tắt, không phải một đoạn văn học thuật, và phải bị từ chối ở bước tự kiểm (xem Phần 3).

Quy tắc cụ thể:
- Mỗi ý phải được triển khai thành ít nhất 2-3 câu hoàn chỉnh: câu chủ đề (nêu luận điểm) → câu phát triển (giải thích/dẫn chứng/trích dẫn) → câu chuyển ý hoặc hệ quả.
- Nếu một đặc điểm/thành phần "đáng" liệt kê (ví dụ 4 đặc điểm thị trường crypto), hãy viết thành một đoạn văn liên tục, dùng các liên từ chuyển ý ("Thứ nhất,... Bên cạnh đó,... Không chỉ vậy,... Cuối cùng,...") thay vì xuống dòng từng gạch đầu dòng.
- **Bảng (table) và công thức (LaTeX) vẫn được phép và khuyến khích** cho dữ liệu định lượng, so sánh nhiều chiều, hoặc bảng tham số kỹ thuật — đây là quy ước được cả hai bản khóa luận gốc sử dụng nhất quán. Nhưng mọi bảng phải có một đoạn văn giới thiệu trước khi bảng xuất hiện (nói bảng trình bày gì) và một đoạn văn diễn giải/nhận xét sau bảng (nói ý nghĩa số liệu). Bảng không bao giờ được đứng một mình thay cho lập luận.
- Sơ đồ ASCII / kiến trúc dạng cây thư mục/diagram trong các tài liệu nguồn (ví dụ 3-Node Architecture) là tài liệu kỹ thuật tham khảo, **không được copy nguyên văn vào thân khóa luận**. Phải "dịch" thành Hình (vẽ lại bằng công cụ vẽ sơ đồ chuẩn hoặc mô tả bằng văn xuôi có đánh số "Hình 2.x") và một đoạn văn diễn giải luồng dữ liệu trong sơ đồ đó.

## 1.3. Cấu trúc câu, thuật ngữ, công thức, hình/bảng
- Câu học thuật tiếng Việt thường dài hơn câu nói thường, có mệnh đề phụ, dùng ngôn ngữ giảm nhẹ mức độ chắc chắn khi chưa có bằng chứng tuyệt đối ("có thể", "trong phần lớn trường hợp", "kết quả thực nghiệm cho thấy", "chưa có sự đồng thuận học thuật về...").
- Thuật ngữ kỹ thuật: định nghĩa lần đầu xuất hiện kèm thuật ngữ tiếng Anh trong ngoặc đơn (ví dụ: "phân tích kỹ thuật (technical analysis)"), sau đó dùng nhất quán một cách gọi trong toàn bài — không đổi qua lại giữa "kiến trúc Lambda" và "mô hình Lambda".
- Công thức toán dùng LaTeX có đánh số, đặt trên dòng riêng, theo đúng phong cách bản "Nhóm 79" (`$$SMA_t = ...$$`).
- Hình/Bảng đánh số theo chương (Hình 2.1, Bảng 3.2...), có chú thích (caption) ngắn gọn, được nhắc tên tường minh trong văn bản trước khi xuất hiện ("như minh họa ở Hình 2.1...").
- Đoạn code chỉ xuất hiện ở Chương 3 khi minh họa một thuật toán cụ thể có ý nghĩa học thuật (ví dụ thuật toán stitching/reconciliation ở biên thời gian) — không chèn nguyên khối cấu hình YAML/Dockerfile vào thân bài; những phần đó nên tóm tắt bằng văn xuôi và (nếu cần) đưa bản đầy đủ vào Phụ lục.

## 1.4. Tuyệt đối tránh
- Không dùng "tốt nhất", "hoàn hảo", "luôn luôn", "không bao giờ" trừ khi có trích dẫn hoặc số liệu đo cụ thể hỗ trợ.
- Không đưa số liệu thị trường/tài chính chung chung (vốn hóa, % biến động) mà không có trích dẫn + thời điểm tham chiếu.
- Không khẳng định một tính năng "đã hoạt động" nếu nguồn dữ liệu cho thấy nó đang ở trạng thái kế hoạch/lỗi/chưa hoàn thiện (xem Phần 0).
- Không dùng emoji, ký hiệu cảnh báo (⚠️) hay các quy ước ghi chú kiểu tài liệu vận hành nội bộ (SYSTEM.md) trong thân khóa luận — những cảnh báo đó cần được "dịch" thành câu văn học thuật kiểu "cần lưu ý rằng tại thời điểm thực hiện khóa luận, cấu phần X chưa đạt được mức độ ổn định mong muốn do...".

---

# PHẦN 2 — QUY TRÌNH NGHIÊN CỨU VÀ TRÍCH DẪN

## 2.1. Chuẩn trích dẫn
Dùng chuẩn IEEE numbered `[1]`, `[2]`... theo thứ tự xuất hiện lần đầu trong văn bản — đây là chuẩn cả hai bản khóa luận gốc đã dùng nhất quán, giữ nguyên. Danh mục tham khảo tổng hợp đặt cuối khóa luận, không chia theo chương (theo đúng cách bản "Đại học" đã làm, có ghi chú "không phân chia theo chương").

## 2.2. Quy trình xác minh bắt buộc cho MỌI trích dẫn mới
Trước khi một trích dẫn được đưa vào bản nháp, phải thực hiện đủ 5 bước sau (không được bỏ qua, kể cả với tác giả/sách "nghe quen"):

1. **Tìm kiếm trực tiếp** (web_search) tên đầy đủ bài báo/sách kèm tên tác giả.
2. **Đối chiếu từng trường**: tên đầy đủ tác giả, năm, tên tạp chí/hội nghị/nhà xuất bản, volume/issue/trang, DOI (nếu có).
3. Nếu **không tìm thấy bản ghi nào khớp** → KHÔNG được dùng. Hoặc (a) diễn đạt lại thành câu khẳng định chung không gắn tên tác giả cụ thể, hoặc (b) tìm một nguồn thay thế đã verify được, hoặc (c) hạ cấp thành tài liệu kỹ thuật chính thức (official documentation) nếu phù hợp.
4. **Không bao giờ tự suy ra DOI hoặc số trang** nếu không thấy trong kết quả tìm kiếm. Một DOI sai còn tệ hơn không có DOI.
5. Ghi log trạng thái xác minh vào "Ngân hàng trích dẫn" (mục 2.5) trước khi đánh số chính thức.

## 2.3. Phân loại nguồn được chấp nhận
- **Bài báo/sách nền tảng (ưu tiên cao nhất):** trích dẫn nguyên thủy của khái niệm (Fama cho EMH, Marz & Warren cho Lambda Architecture, Lewis et al. cho RAG...).
- **Khảo sát/thứ cấp:** chấp nhận cho các nhận định tổng quát, không dùng để chứng minh một con số cụ thể nếu có thể tìm nguồn gốc.
- **Tài liệu kỹ thuật chính thức (official docs):** dùng cho sự thật về sản phẩm/thư viện (Apache Iceberg spec, Apache Kafka/Flink documentation) — trích dẫn dạng "Tên tài liệu, Tổ chức, năm, [Online]. Available: URL", **không** ngụy trang thành bài báo khoa học có DOI giả.
- **Whitepaper gốc (Bitcoin):** chấp nhận như nguồn nguyên thủy bắt buộc khi nhắc tới Bitcoin, ghi rõ đây là whitepaper không qua bình duyệt.

## 2.4. Mật độ trích dẫn khuyến nghị theo chương
| Chương | Mật độ | Ghi chú |
|---|---|---|
| Cơ sở lý thuyết | Cao — gần như mỗi luận điểm lý thuyết có ít nhất 1 trích dẫn | Đây là chương học thuật nhất, hội đồng soi kỹ nhất |
| Tổng quan và kiến trúc hệ thống | Trung bình — trích dẫn khi biện minh lựa chọn kiến trúc (vì sao Lambda chứ không phải Kappa, vì sao Docker Swarm...) | Phần lớn nội dung là mô tả thiết kế gốc của nhóm, không cần ép trích dẫn vào mọi câu |
| Xây dựng và triển khai | Thấp — chỉ trích dẫn khi mượn kỹ thuật/thuật toán từ tài liệu bên ngoài | Đây là chương trình bày công sức triển khai của nhóm |
| Đánh giá và kết luận | Trung bình — bắt buộc có Wohlin et al. (2012) hoặc tương đương cho phần phương pháp luận đánh giá/threats to validity | Giữ phong cách "tự phản biện" đã có ở bản "Đại học" |

## 2.5. Ngân hàng trích dẫn

### Đã xác minh trực tiếp trong phiên này (an toàn để dùng, có thể đánh số ngay)
| Trích dẫn | Dùng cho mục | Thông tin đã xác minh |
|---|---|---|
| Fama, E. F. (1970). "Efficient Capital Markets: A Review of Theory and Empirical Work." *The Journal of Finance*, 25(2), 383–417. | 1.2.1 — nền tảng EMH | Vol 25 No 2, May 1970, pp. 383–417. DOI 10.1111/j.1540-6261.1970.tb00518.x |
| Marz, N., & Warren, J. (2015). *Big Data: Principles and Best Practices of Scalable Realtime Data Systems*. Manning Publications. ISBN 9781617290343. | 1.3.1 — Lambda Architecture | Xuất bản 4/2015, Manning, ~328 trang |
| Armbrust, M., Ghodsi, A., Xin, R., & Zaharia, M. (2021). "Lakehouse: A New Generation of Open Platforms that Unify Data Warehousing and Advanced Analytics." *CIDR 2021*. | 1.3.2 — Data Lakehouse | CIDR 2021, Virtual Event, Jan 11–15 2021 |
| Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *NeurIPS 2020*, 33, 9459–9474. | 1.4.2 — RAG | 12 đồng tác giả đầy đủ; NeurIPS 33, trang 9459–9474 |
| Malkov, Y. A., & Yashunin, D. A. (2020). "Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs." *IEEE TPAMI*, 42(4), 824–836. | 1.4.4 — HNSW | DOI 10.1109/TPAMI.2018.2889473 |
| Wohlin, C., Runeson, P., Höst, M., Ohlsson, M. C., Regnell, B., & Wesslén, A. (2012). *Experimentation in Software Engineering*. Springer. | Chương 4 — phương pháp luận | DOI 10.1007/978-3-642-29044-2 |

### Đã có log xác minh từ bản "Đại học" (độ tin cậy cao, khuyến nghị re-verify nhanh)
- Urquhart, A. (2016). "The inefficiency of Bitcoin." *Economics Letters*, 148, 80–82.
- Tran, V. L., & Leirvik, T. (2020). "Efficiency in the markets of crypto-currencies." *Finance Research Letters*, 35, 101382.
- McNally, S., Roche, J., & Caton, S. (2018). "Predicting the price of Bitcoin using machine learning." *PDP 2018*, 339–343.
- Kreps, J. (2011). "Kafka: a Distributed Messaging System for Log Processing." *NetDB Workshop*. (lưu ý: workshop paper)
- Vaswani, A. et al. (2017). "Attention Is All You Need." *NeurIPS*.

### Cần xác minh lại trước khi dùng
- Murphy, J. J. (1999). *Technical Analysis of the Financial Markets*. NYIF.
- Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. Trend Research.
- Nison, S. *Japanese Candlestick Charting Techniques* (cần xác minh năm/ấn bản)
- Liu, Y., & Tsyvinski, A. (2021). "Risks and Returns of Cryptocurrency." *Review of Financial Studies*, 34(6), 2689–2727.
- Shazeer, N. et al. (2017). "Outrageously Large Neural Networks..." *ICLR*.
- Araci, D. (2019). "FinBERT: Financial Sentiment Analysis..." arXiv:1908.10063.
- Devlin, J. et al. (2019). "BERT: Pre-training of Deep Bidirectional Transformers..." *NAACL*.
- Carbone et al. (2017). "State Management in Apache Flink." *PVLDB*, 10(12), 1718–1729.

### ĐÃ XÁC NHẬN LÀ BỊA — TUYỆT ĐỐI KHÔNG ĐƯỢC DÙNG
- "Buss et al. (2021)" về Iceberg hidden partitioning
- "Baur and Dimpfl (2021)" về volatility Bitcoin
- "Dow (1902)" như một publication cụ thể

---

# PHẦN 3 — QUY TRÌNH VIẾT TỪNG PHẦN

## 3.1. Quy trình 5 bước bắt buộc cho mỗi mục/tiểu mục

1. **Soạn thảo** mục đó hoàn toàn bằng văn xuôi liên tục.
2. **Tự kiểm văn phong**: rà từng đoạn.
3. **Tự kiểm trích dẫn**: liệt kê toàn bộ trích dẫn dùng trong mục.
4. **Tự kiểm sự thật nội bộ**: đối chiếu với Phần 0.2.
5. **Xuất báo cáo tự kiểm** ngắn ngay sau bản nháp.

## 3.2. Mẫu "Báo cáo tự kiểm"

```
## Báo cáo tự kiểm — Mục [số mục]
- Số đoạn văn: ...
- Số trích dẫn sử dụng: ...
- Đoạn nào còn ở dạng liệt kê: [có/không]
- Khẳng định nào về hệ thống LMView phụ thuộc vào xung đột dữ liệu chưa chốt: [liệt kê]
- Đề xuất hành động tiếp theo: ...
```

---

# PHẦN 4 — ĐỀ CƯƠNG CHI TIẾT NỘI DUNG TỪNG MỤC

[Chi tiết từng mục — xem nguyên văn trong tin nhắn của tác giả]

---

# PHẦN 5 — CHECKLIST TỔNG THỂ TRƯỚC KHI NỘP

- [ ] Toàn bộ 9 xung đột dữ liệu ở Phần 0.2 đã được xác nhận hoặc gắn cờ.
- [ ] Không còn đoạn nào trong thân bài là danh sách gạch đầu dòng.
- [ ] Mọi trích dẫn đã qua quy trình 5 bước.
- [ ] Không còn trích dẫn bịa.
- [ ] Số liệu hiệu năng khớp với hạ tầng.
- [ ] Mục 1.4.3 không khẳng định agent đã vận hành nếu chưa xác nhận.
- [ ] Mục 2.4 và 4.3 dùng thì định hướng.
- [ ] Đánh số lại trích dẫn IEEE sau khi ghép chương.
