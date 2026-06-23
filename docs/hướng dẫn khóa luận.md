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

1. **AI Interact Mode / multi-agent (Chart Agent, News Agent, Indicator Agent):** theo bộ nhớ hội thoại đây là Phase 2/LangGraph chưa triển khai. Khác với luồng dữ liệu Lambda, đây là một lớp tính năng AI riêng — nếu anh muốn coi như đã xong tương tự 0.1, hãy nói rõ; nếu không, mục 1.4.3 vẫn nên viết ở thì định hướng.
2. **Số chỉ báo kỹ thuật:** 5 chỉ báo cơ bản (bản "Nhóm 79") hay đủ 16 chỉ báo (bản "Đại học")?
3. **Số khung thời gian hỗ trợ:** 9 khung 1s→1w hay 7 khung 1m→1w?
4. **Version cụ thể:** Flink 1.18.1 hay 1.17.1-java11; lightweight-charts v4.x hay v5.2 (v5.2 nhiều khả năng đúng hơn vì khớp với bộ nhớ hội thoại).
5. **Số LLM provider thực tế:** 4 provider hay 2 provider (mock + litellm)?
6. **Pipeline tin tức/sentiment (VADER/FinBERT/CryptoBERT):** đã hoàn thiện lưu trữ tin tức chưa, hay vẫn ở dạng khảo sát/chưa tích hợp?

Khi AI viết tới các mục liên quan mà chưa có câu trả lời, mặc định dùng phương án có độ tin cậy cao hơn (đã ghi rõ ở từng dòng) và gắn chú thích `[CẦN XÁC NHẬN: ...]` ngay trong bản nháp thay vì tự quyết âm thầm.

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
| Fama, E. F. (1970). "Efficient Capital Markets: A Review of Theory and Empirical Work." *The Journal of Finance*, 25(2), 383–417. | 1.2.1 — nền tảng EMH | Vol 25 No 2, May 1970, pp. 383–417. DOI 10.1111/j.1540-6261.1970.tb00518.x (JSTOR stable ID tương đương 10.2307/2325486 cũng hợp lệ) |
| Marz, N., & Warren, J. (2015). *Big Data: Principles and Best Practices of Scalable Realtime Data Systems*. Manning Publications. ISBN 9781617290343. | 1.3.1 — Lambda Architecture | Xuất bản 4/2015, Manning, ~328 trang. Marz là người khởi xướng Lambda Architecture, từng là kỹ sư trưởng tại BackType/Twitter |
| Armbrust, M., Ghodsi, A., Xin, R., & Zaharia, M. (2021). "Lakehouse: A New Generation of Open Platforms that Unify Data Warehousing and Advanced Analytics." *CIDR 2021*. | 1.3.2 — Data Lakehouse | CIDR (Conference on Innovative Data Systems Research) 2021, Virtual Event, Jan 11–15 2021. Tác giả đầu là Armbrust theo đúng byline gốc |
| Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *NeurIPS 2020*, 33, 9459–9474. | 1.4.2 — RAG | 12 đồng tác giả đầy đủ đã xác minh; NeurIPS 33, trang 9459–9474 |
| Malkov, Y. A., & Yashunin, D. A. (2020). "Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs." *IEEE TPAMI*, 42(4), 824–836. | 1.4.4 — HNSW | DOI 10.1109/TPAMI.2018.2889473, xuất bản online 12/2018, in chính thức 4/2020 |
| Wohlin, C., Runeson, P., Höst, M., Ohlsson, M. C., Regnell, B., & Wesslén, A. (2012). *Experimentation in Software Engineering*. Springer. | Chương 4 — phương pháp luận đánh giá / threats to validity | DOI 10.1007/978-3-642-29044-2, Springer Berlin Heidelberg |

### Đã có log xác minh từ bản "Đại học" (độ tin cậy cao, khuyến nghị re-verify nhanh trước khi khóa số liệu cuối)
- Urquhart, A. (2016). "The inefficiency of Bitcoin." *Economics Letters*, 148, 80–82. — dùng cho 1.2.1
- Tran, V. L., & Leirvik, T. (2020). "Efficiency in the markets of crypto-currencies." *Finance Research Letters*, 35, 101382. — dùng cho 1.2.1
- McNally, S., Roche, J., & Caton, S. (2018). "Predicting the price of Bitcoin using machine learning." *PDP 2018*, 339–343. — dùng cho phần liên hệ ML/dự báo giá (4.6 hướng phát triển)
- Kreps, J. (2011). "Kafka: a Distributed Messaging System for Log Processing." *NetDB Workshop*. — dùng cho 1.3.3, lưu ý đây là workshop paper, không phải hội nghị bình duyệt đầy đủ, nên ghi chú khi trích
- Vaswani, A. et al. (2017). "Attention Is All You Need." *NeurIPS*. — dùng cho 1.4.1 nếu cần nói về nền tảng Transformer

### Cần xác minh lại trước khi dùng (độ tin cậy trung bình-cao nhưng CHƯA kiểm tra sống trong phiên này)
- Murphy, J. J. (1999). *Technical Analysis of the Financial Markets*. NYIF. — 1.2.1
- Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. Trend Research. — 1.2.2 (RSI gốc)
- Nison, S. *Japanese Candlestick Charting Techniques* — 1.2.3, cần xác minh năm/ấn bản chính xác (1991 bản 1 hay 2001 bản 2)
- Liu, Y., & Tsyvinski, A. (2021). "Risks and Returns of Cryptocurrency." *Review of Financial Studies*, 34(6), 2689–2727. — 1.2.4, tác động tin tức
- Shazeer, N. et al. (2017). "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer." *ICLR*. — 1.4.3 (MoE)
- Araci, D. (2019). "FinBERT: Financial Sentiment Analysis with Pre-Trained Language Models." arXiv:1908.10063. — 1.4.3
- Devlin, J. et al. (2019). "BERT: Pre-training of Deep Bidirectional Transformers..." *NAACL*. — nếu cần nền tảng cho FinBERT/CryptoBERT
- Kirkpatrick, C. D., & Dahlquist, J. R. *Technical Analysis: The Complete Resource...* — thay thế/bổ sung cho Murphy nếu cần
- Carbone, P. et al. — trích dẫn học thuật cho Apache Flink: bản "Đại học" đã phát hiện bài "IEEE Data Engineering Bulletin 2015" KHÔNG xác minh được qua tìm kiếm; gợi ý thay bằng Carbone et al. (2017) "State Management in Apache Flink," *PVLDB*, 10(12), 1718–1729 — **bắt buộc tìm kiếm xác nhận bài PVLDB 2017 này trước khi dùng**; nếu không xác minh được, dùng Apache Flink Documentation (flink.apache.org) làm nguồn thay thế, không bịa DOI

### ĐÃ XÁC NHẬN LÀ BỊA — TUYỆT ĐỐI KHÔNG ĐƯỢC DÙNG LẠI
- "Buss et al. (2021)" về Iceberg hidden partitioning — không tồn tại, bản "Đại học" đã phát hiện và thay bằng Apache Iceberg official spec.
- "Baur and Dimpfl (2021)" về volatility của Bitcoin — không tìm thấy bài báo khớp tên/năm.
- "Dow (1902)" như một publication cụ thể cho Dow Theory — không có ấn phẩm đơn lẻ năm 1902; Dow Theory được tổng hợp từ ~255 bài editorial trên Wall Street Journal rải rác 1900–1902. Khi cần nhắc tới, diễn đạt là "được hệ thống hóa từ các bài viết của Charles Dow trên Wall Street Journal đầu thế kỷ 20" mà không gắn năm/citation cụ thể.

---

# PHẦN 3 — QUY TRÌNH VIẾT TỪNG PHẦN (dùng cho mỗi phiên với AI)

## 3.1. Quy trình 5 bước bắt buộc cho mỗi mục/tiểu mục

1. **Soạn thảo** mục đó hoàn toàn bằng văn xuôi liên tục, bám sát đề cương nội dung ở Phần 4 bên dưới và độ dài khuyến nghị.
2. **Tự kiểm văn phong**: rà từng đoạn, hỏi "đoạn này có phải là một danh sách gạch đầu dòng được nối câu lại không?" — nếu có, viết lại; "đoạn nào dưới ~80 từ và đọc như một câu tóm tắt trơ trọi?" — phát triển thêm hoặc gộp với đoạn liền kề.
3. **Tự kiểm trích dẫn**: liệt kê toàn bộ trích dẫn dùng trong mục; với trích dẫn chưa có trong "Đã xác minh trực tiếp", chạy quy trình 5 bước ở mục 2.2 trước khi giữ lại.
4. **Tự kiểm sự thật nội bộ**: liệt kê mọi con số/tên thành phần/khẳng định trạng thái về hệ thống LMView xuất hiện trong mục (ví dụ "16 chỉ báo", "3 node", "AI đã tích hợp multi-agent"); đối chiếu với Phần 0.2 — nếu thuộc danh sách xung đột chưa chốt, gắn cờ rõ ràng thay vì tự chọn một phương án.
5. **Xuất báo cáo tự kiểm** ngắn ngay sau bản nháp (mẫu ở mục 3.2) trước khi chuyển sang mục tiếp theo.

## 3.2. Mẫu "Báo cáo tự kiểm" (AI phải tự điền sau mỗi mục)

```
## Báo cáo tự kiểm — Mục [số mục]
- Số đoạn văn: ...
- Số trích dẫn sử dụng: ... (đã xác minh: ... / cần xác minh thêm: ... / mới phát hiện cần loại bỏ: ...)
- Đoạn nào còn ở dạng liệt kê/gạch ý chưa triển khai đủ: [có/không, nêu cụ thể nếu có]
- Khẳng định nào về hệ thống LMView phụ thuộc vào xung đột dữ liệu chưa chốt (Phần 0.2): [liệt kê]
- Đề xuất hành động tiếp theo: [ví dụ: "cần anh xác nhận số node thực tế trước khi viết tiếp 3.1"]
```

## 3.3. Prompt mẫu — copy nguyên văn khi bắt đầu một phiên viết mới

```
Đọc file "huong-dan-viet-khoa-luan-lmview.md" trong dự án. Viết mục [X.Y — tên mục] theo đúng:
- Văn phong học thuật ở Phần 1 (không gạch đầu dòng trong thân bài, ngôi thứ ba, đoạn văn đầy đủ)
- Quy trình trích dẫn ở Phần 2 (xác minh sống qua web_search trước khi dùng, không tái sử dụng các trích dẫn đã biết là bịa)
- Nội dung và độ dài theo đề cương ở Phần 4 cho đúng mục này
- Nếu gặp số liệu/khẳng định thuộc danh sách xung đột ở Phần 0.2 mà tôi chưa xác nhận, hãy viết một phương án mặc định hợp lý nhưng gắn chú thích rõ ràng [CẦN XÁC NHẬN: ...], không tự quyết.
Sau khi viết xong, xuất Báo cáo tự kiểm theo mẫu ở mục 3.2.
```

---

# PHẦN 4 — ĐỀ CƯƠNG CHI TIẾT NỘI DUNG TỪNG MỤC

> Với mỗi mục: **Nguồn nên dùng**, **Nội dung cốt lõi**, **Trích dẫn dự kiến**, **Độ dài khuyến nghị**, **Lưu ý/cảnh báo**.

## CHƯƠNG 1 — CƠ SỞ LÝ THUYẾT

### 1. Tiền điện tử và thị trường tiền điện tử
- **Nguồn:** khung nội dung từ bản "Nhóm 79" §1.1 (đã khá đầy đủ: định nghĩa, Bitcoin/Ethereum, đặc điểm thị trường, sàn Binance).
- **Nội dung:** định nghĩa cryptocurrency và cơ chế mật mã/sổ cái phân tán; lược sử Bitcoin (Nakamoto) và Ethereum (hợp đồng thông minh); năm đặc điểm thị trường (24/7, biến động cao, phi tập trung, toàn cầu, tương quan thấp với thị trường truyền thống) viết thành các đoạn lập luận nối tiếp, không liệt kê; vai trò của Binance (WebSocket Streams, REST API, Combined Streams) như nguồn dữ liệu chính của LMView, dẫn vào con số 671 cặp USDT.
- **Trích dẫn dự kiến:** Nakamoto whitepaper (Bitcoin) cho định nghĩa nguyên thủy; Urquhart (2016) hoặc Tran & Leirvik (2020) cho luận điểm về biến động/hiệu quả thị trường — **không dùng con số vốn hóa thị trường tuyệt đối nếu không kèm trích dẫn + thời điểm tham chiếu cụ thể**.
- **Độ dài:** 600–900 từ.

### 2. Phân tích kỹ thuật trong thị trường tiền điện tử

**2.1. Nền tảng lý thuyết phân tích kỹ thuật**
- **Nguồn:** bản "Đại học" §1.1.1 — đoạn này đã có cấu trúc lập luận rất tốt (3 tiên đề Dow Theory, liên hệ EMH của Fama, sau đó phản biện bằng 2 nguồn đối lập về hiệu quả thị trường crypto) — nên giữ cấu trúc lập luận này, không cần viết lại từ đầu, chỉ làm mới văn phong nếu cần.
- **Nội dung:** ba tiên đề Dow Theory (thị trường phản ánh mọi thông tin; giá vận động theo xu hướng; lịch sử lặp lại), liên hệ rõ ràng từng tiên đề với Efficient Market Hypothesis của Fama; sau đó trình bày tranh luận học thuật về hiệu lực TA trong crypto — dẫn Urquhart (2016) cho luận điểm thị trường gần như không hiệu quả giai đoạn đầu, đối chiếu Tran & Leirvik (2020) cho luận điểm thị trường đang tiến gần hiệu quả theo thời gian; kết đoạn bằng việc liên hệ tới lý do LMView tích hợp AI Assistant như một nguồn thông tin bổ sung.
- **Trích dẫn:** Fama (1970) [đã xác minh], Murphy (1999) [cần xác minh], Urquhart (2016), Tran & Leirvik (2020).
- **Độ dài:** 500–700 từ.

**2.2. Các chỉ báo kỹ thuật cốt lõi**
- **Nguồn:** kết hợp công thức LaTeX rõ ràng từ bản "Nhóm 79" §1.2.2 với cách phân nhóm 4 nhóm chỉ báo (xu hướng/động lượng/biến động/khối lượng) của bản "Đại học" §1.1.2.
- **⚠️ Trước khi viết:** xác nhận số chỉ báo thực sự được tính trong Flink (xem Phần 0.2 mục 5) — đề xuất bắt đầu với bộ 5 chỉ báo cốt lõi chắc chắn có thật (SMA, EMA, RSI, MACD, Bollinger Bands) làm xương sống, sau đó nêu các chỉ báo mở rộng (VWAP, Stochastic, ATR...) ở thì "hệ thống được thiết kế để mở rộng tính toán thêm..." nếu chưa chắc chắn đã triển khai đủ.
- **Nội dung:** với mỗi chỉ báo — công thức LaTeX, ý nghĩa tham số (N, k...), ngưỡng diễn giải (RSI>70 quá mua...), và một câu liên hệ cách Flink tính incremental (deque rolling window) thay vì recompute toàn bộ lịch sử.
- **Trích dẫn:** Wilder (1978) cho RSI gốc, Murphy hoặc Kirkpatrick & Dahlquist cho khung lý thuyết tổng quát.
- **Độ dài:** 900–1300 từ.

**2.3. Biểu đồ nến và dữ liệu OHLCV**
- **Nguồn:** bản "Nhóm 79" §1.2.3.
- **⚠️ Cần chốt trước:** số khung thời gian hệ thống thực sự hỗ trợ (9 khung 1s→1w hay 7 khung 1m→1w — Phần 0.2 mục 6).
- **Nội dung:** định nghĩa nến Nhật, cấu trúc OHLCV, vai trò aggregation (1s→1m→khung lớn hơn).
- **Trích dẫn:** Nison (cần xác minh năm/ấn bản).
- **Độ dài:** 300–500 từ.

**2.4. Tác động của tin tức đến thị trường tiền điện tử**
- **Nguồn:** bản "Nhóm 79" §1.2.4, viết lại theo thì định hướng cho phần liên hệ pipeline tin tức.
- **⚠️ Bắt buộc dùng thì chưa hoàn thành** cho phần liên hệ tới VADER/FinBERT/CryptoBERT, vì theo bộ nhớ hội thoại, pipeline tin tức/sentiment "chưa hoàn thiện việc lưu trữ tin tức" — ví dụ diễn đạt đúng: "khóa luận đề xuất tích hợp một pipeline phân tích cảm xúc tin tức gồm các mô hình VADER, FinBERT và CryptoBERT nhằm..." thay vì "hệ thống đã phân tích cảm xúc tin tức real-time".
- **Trích dẫn:** Liu & Tsyvinski (2021) [cần xác minh].
- **Độ dài:** 300–450 từ.

### 3. Xử lý dữ liệu lớn trong thời gian thực

**3.1. Kiến trúc Lambda (Lambda Architecture)**
- **Nguồn:** kết hợp định nghĩa 3 tầng từ cả hai bản, dùng nguyên lập luận so sánh Lambda vs Kappa của bản "Đại học" §2.1.2 (rất chặt chẽ: throughput 671 symbol × 1Hz × 365 ngày ≈ 21 tỷ message/năm khiến Kappa không khả thi vì Kafka chỉ giữ 7 ngày).
- **Nội dung:** ba tầng Speed/Batch/Serving với vai trò cụ thể trong LMView; trình bày trade-off analysis dưới dạng đoạn văn (không bảng ưu/nhược dạng liệt kê) — độ phức tạp tăng do 2 codebase song song, độ trễ giữa kết quả speed và batch, chi phí hạ tầng.
- **Trích dẫn:** Marz & Warren (2015) [đã xác minh].
- **Độ dài:** 700–1000 từ.

**3.2. Hạ tầng lưu trữ Data Lakehouse**
- **Nguồn:** bản "Đại học" §1.2.4 (đã sửa lỗi trích dẫn bịa, nội dung đáng tin cậy) + mô tả schema Bronze/Silver/Gold từ SYSTEM.md §36.
- **Nội dung:** định nghĩa Lakehouse kết hợp ưu điểm Data Lake và Data Warehouse; kiến trúc Medallion 3 tầng với lý do kỹ thuật cụ thể (BINARY cho Bronze để replay, DECIMAL(20,8) cho Silver để tránh sai số dấu phẩy động khi giá token có thể rất nhỏ hoặc rất lớn); tính năng ACID/time-travel/schema evolution của Iceberg.
- **Trích dẫn:** Armbrust et al. (2021) [đã xác minh] cho khái niệm Lakehouse tổng quát; Apache Iceberg official specification (iceberg.apache.org/spec) cho tính năng cụ thể — **không dùng "Buss et al."**.
- **Độ dài:** 700–900 từ.

**3.3. Kỹ thuật xử lý dữ liệu thời gian thực**
- **Nguồn:** SYSTEM.md §9, §13 cho chi tiết kỹ thuật Kafka/Flink, bản "Đại học" cho khung lý thuyết.
- **Nội dung:** Kafka (topic/partition/replication, vai trò "băng ghi âm" sự kiện); Flink (stateful processing, KeyedProcessFunction, incremental indicator computation so sánh với Spark Streaming micro-batch); Redis Sentinel (cơ chế quorum, failover).
- **Trích dẫn:** Kreps (2011) cho Kafka [đã có log xác minh, lưu ý là workshop paper]; cho Flink — ưu tiên xác minh Carbone et al. (2017) PVLDB, nếu không xác minh được thì dùng Apache Flink Documentation.
- **Độ dài:** 700–1000 từ.

### 4. Trí tuệ nhân tạo trong phân tích tài chính

**4.1. Mô hình ngôn ngữ lớn (LLM)**
- **Nguồn:** SYSTEM.md §40 cho số liệu provider thực tế.
- **⚠️ Cần chốt:** số provider LLM thực sự hoạt động (2 theo SYSTEM.md: mock + litellm, hay 4 theo bản "Nhóm 79" — Phần 0.2 mục 8). Khuyến nghị dùng số liệu SYSTEM.md vì cụ thể hơn, trừ khi anh xác nhận đã tích hợp thêm provider.
- **Nội dung:** định nghĩa LLM, vai trò trong phân tích tài chính (tóm tắt tin tức, hỗ trợ ra quyết định), kiến trúc provider router của LMView.
- **Trích dẫn:** Vaswani et al. (2017) nếu cần nền tảng Transformer.
- **Độ dài:** 400–600 từ.

**4.2. Retrieval-Augmented Generation (RAG)**
- **Nguồn:** bản "Đại học" §1.3.2 — đã viết rất tốt, có thể giữ gần như nguyên cấu trúc 4 bước (Embedding → Retrieval → Augmentation → Generation), chỉ cần đảm bảo trích dẫn đúng định dạng đầy đủ tác giả.
- **Nội dung:** giải thích cách RAG giải quyết 3 hạn chế của LLM thuần (knowledge cutoff, hallucination, thiếu ngữ cảnh thị trường); ứng dụng cụ thể: embedding all-MiniLM-L6-v2 (384 chiều), pgvector, HNSW, top-5 chunks.
- **Trích dẫn:** Lewis et al. (2020) [đã xác minh].
- **Độ dài:** 500–700 từ.

**4.3. DAG, MoE, Multi Agents, FinBERT**
- **Đây là mục nhạy cảm nhất — đọc kỹ trước khi viết.**
- **DAG:** có cơ sở thực tế (Dagster điều phối pipeline dữ liệu theo SYSTEM.md) — có thể viết ở thì hiện tại bình thường.
- **MoE:** trình bày như khái niệm lý thuyết, sau đó liên hệ với "provider router" của LMView bằng phép loại suy — **phải nói rõ đây là loại suy về mặt định tuyến/lựa chọn, không phải LMView triển khai kiến trúc Mixture-of-Experts ở cấp độ mạng nơ-ron**, để tránh người đọc hiểu nhầm.
- **Multi Agents:** trình bày như nền tảng lý thuyết về điều phối nhiều tác tử AI nói chung, sau đó nêu rõ đây là **hướng phát triển đã hoạch định** (Phase 2, kiến trúc LangGraph) chứ không khẳng định "Chart Agent, News Agent, Indicator Agent" đã vận hành — đây là điểm cần sửa quan trọng nhất so với bản "Nhóm 79" hiện tại, vốn đang mô tả các agent này như đã triển khai.
- **FinBERT:** mô tả là một trong các mô hình đã được khảo sát cho kế hoạch phân tích cảm xúc tương lai, đúng theo SYSTEM.md ("đã khảo sát nhưng chưa tích hợp").
- **Trích dẫn:** Shazeer et al. (2017) [cần xác minh] cho MoE; Araci (2019) [cần xác minh] cho FinBERT.
- **Độ dài:** 600–900 từ, dùng nhiều ngôn ngữ giảm nhẹ mức độ chắc chắn hơn các mục khác.

**4.4. Vector database và HNSW index**
- **Nguồn:** bản "Đại học" §1.3.3.
- **Nội dung:** vector database là gì, vai trò pgvector trên PostgreSQL; thuật toán HNSW (cấu trúc đồ thị đa tầng, độ phức tạp O(log n) so với O(n) tìm kiếm tuyến tính); cấu hình cụ thể của LMView.
- **Trích dẫn:** Malkov & Yashunin (2020) [đã xác minh].
- **Độ dài:** 400–600 từ.

---

## CHƯƠNG 2 — TỔNG QUAN VÀ KIẾN TRÚC HỆ THỐNG

### Tổng quan (chức năng, phi chức năng)
- **Nguồn:** bảng chức năng từ bản "Nhóm 79" §2.1.1 (mở rộng thành đoạn văn giới thiệu trước bảng), bảng NFR 9 mục từ bản "Đại học" §2.1.1 — đoạn phân tích "yêu cầu mâu thuẫn" (NFR1 độ trễ thấp >< NFR6 lưu trữ dài hạn; NFR7 chi phí thấp >< NFR5 nhiều chỉ báo real-time) là một đóng góp lập luận tốt, nên giữ và mở rộng.
- **Độ dài:** 800–1100 từ.

### Kiến trúc hệ thống (theo lớp)
- **Nguồn:** sơ đồ 3-Node Architecture làm xương sống, "dịch" thành Hình 2.x + đoạn văn; 4 lớp Ingestion/Processing/Storage/Serving theo bản "Nhóm 79" §2.2.2.
- **Điểm mấu chốt cần nhất quán:** mô tả rõ ràng đường ghi trực tiếp `binance-ticker-ws → Redis` là **đường dự phòng tốc độ cao** (redundant fast-path, nguyên tắc graceful degradation) song song với đường chính thống Kafka → Flink/Spark cho dữ liệu đã đóng và chỉ báo — đây là cách trình bày chính xác và học thuật nhất, theo đúng văn phong bản "Đại học" §2.2.1, tránh mô tả như hai hệ thống độc lập rời rạc.
- **Độ dài:** 1000–1400 từ.

### Phân tích thiết kế (data flow, scenario, use case, system design)
- **Nguồn:** 3 luồng dữ liệu (real-time/streaming/batch) từ bản "Nhóm 79" §2.3.1; thuật toán đối chiếu dữ liệu tại điểm biên T_boundary (reconciliation/stitching) từ bản "Đại học" §3.4.3 — đây là phần kỹ thuật có giá trị học thuật cao nhất trong toàn bộ tài liệu nguồn, nên đưa vào Chương 2 như một phần thiết kế cốt lõi (không chỉ nhắc ở Chương 3); 3 kịch bản sử dụng (xem chart, hỏi AI, Flink crash) từ bản "Nhóm 79" §2.3.2, cập nhật số node; use case diagram và component diagram cập nhật theo 3-node.
- **Độ dài:** 1300–1800 từ (mục dài nhất của Chương 2 vì nhiều nội dung kỹ thuật).

### Công nghệ sử dụng (tech stack)
- **Nguồn:** bảng tech stack bản "Nhóm 79" §2.4, đối chiếu version với SYSTEM.md trước khi chốt (xem Phần 0.2 mục 7).
- **Độ dài:** 400–600 từ giới thiệu + bảng.

---

## CHƯƠNG 3 — XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG

### Cài đặt hạ tầng hệ thống
- **Nguồn:** bản "Nhóm 79" §3.1 (đã có cấu trúc đoạn văn + code minh họa khá tốt), 3-Node Architecture cho YAML placement constraints.
- **Bắt buộc mở đầu bằng một đoạn minh bạch** nêu mức độ triển khai thực tế so với kiến trúc mục tiêu (xem khung ở Phần 0.3).
- **Độ dài:** 1200–1600 từ.

### Giao diện
- **Nguồn:** bản "Nhóm 79" §3.2, bổ sung cấu trúc frontend feature-based từ SYSTEM.md §20.
- **Lưu ý:** không mô tả công cụ vẽ kỹ thuật (drawing toolbar) như đã hoàn thiện — theo bộ nhớ hội thoại, tính năng này đang ở giai đoạn thiết kế.
- **Độ dài:** 600–900 từ.

### Kết quả triển khai
- **Nguồn:** bảng trạng thái dịch vụ bản "Nhóm 79" §3.3.1, đối chiếu và cập nhật theo trạng thái thực tế trong SYSTEM.md (Kafka/producer/indicator) và bộ nhớ hội thoại gần nhất (Iceberg gold layer rỗng, Spark Structured Streaming chưa ổn định).
- **Văn phong:** dùng câu hedging rõ ràng cho mọi cấu phần chưa ổn định hoàn toàn, theo mẫu bản "Đại học": "cần lưu ý rằng tại thời điểm thực hiện khóa luận, [cấu phần] chưa đạt được mức độ ổn định mong muốn do [nguyên nhân], và nhóm nghiên cứu đã ghi nhận đây là một hạn chế kỹ thuật cần khắc phục (xem mục 4.2.2)."
- **Độ dài:** 800–1200 từ.

---

## CHƯƠNG 4 — ĐÁNH GIÁ VÀ KẾT LUẬN

### Đánh giá hiệu năng hệ thống
**Tiêu chí đánh giá:** bảng tiêu chí (E2E Latency, API Latency p50/p99, Throughput, Availability, Redis Failover, Kafka HA) theo bản "Nhóm 79" §4.1.1, mở rộng đoạn văn giải thích phương pháp đo cho từng tiêu chí. *400–600 từ.*

**Kết quả đánh giá:** số liệu **phải đo lại** trên hạ tầng thực tế tại thời điểm hoàn thiện khóa luận, không copy nguyên số liệu từ bản nguồn nếu kiến trúc đã thay đổi. Giữ nguyên khung "Pilot Benchmarking" + "Methodology Defense" + 4 khía cạnh Threats to Validity (Internal/External/Construct validity, Reliability) của bản "Đại học" §4.4.2–4.4.3 — đây là phần thể hiện tính nghiêm túc học thuật rõ nhất trong toàn bộ tài liệu nguồn, nên giữ và phát triển thêm chứ không cắt bớt. *1200–1800 từ.*

### Kết luận
**Điểm mạnh:** dùng khung "3 cấp độ đóng góp" (kỹ thuật ứng dụng / tham khảo kiến trúc / bài học kinh nghiệm) của bản "Đại học" §4.5 — khung này có tính học thuật cao hơn cách liệt kê ưu điểm thông thường. *500–700 từ.*

**Hạn chế:** bảng hạn chế kỹ thuật (theo mẫu L1–L15 bản "Đại học" §4.4.1) cộng phần thảo luận sâu về namespace collision (đa sàn giao dịch) — đây là một đoạn lập luận tốt nên giữ. Đối chiếu lại từng dòng với trạng thái thực tế mới nhất trước khi đưa vào. *700–1000 từ.*

**Đề xuất hướng phát triển:** giữ khung 6 giai đoạn theo thời gian (ngắn/trung/dài hạn) của bản "Đại học" §4.6, viết mỗi giai đoạn thành một đoạn văn tổng hợp (không liệt kê đầu dòng) nêu mục tiêu – phạm vi – giá trị kỳ vọng. Đây cũng là nơi hợp lý để đưa nội dung "Kế hoạch khắc phục Indicator Pipeline" vào — trình bày như một giai đoạn phát triển kế tiếp đã được lên kế hoạch chi tiết, không phải kết quả đã đạt được. *800–1100 từ.*

---

# PHẦN 5 — CHECKLIST TỔNG THỂ TRƯỚC KHI NỘP

- [ ] Toàn bộ 9 xung đột dữ liệu ở Phần 0.2 đã được xác nhận hoặc gắn cờ minh bạch.
- [ ] Không còn đoạn nào trong thân bài là danh sách gạch đầu dòng đóng vai trò lập luận chính.
- [ ] Mọi trích dẫn trong danh mục tham khảo cuối cùng đã qua quy trình 5 bước ở mục 2.2, không còn trích dẫn nào ở trạng thái "cần xác minh".
- [ ] Không còn trích dẫn nào trùng với danh sách "đã xác nhận là bịa" ở mục 2.5.
- [ ] Số liệu hiệu năng ở Chương 4 khớp với hạ tầng được mô tả là đã triển khai ở Chương 3 (không lấy số liệu đo trên kiến trúc khác).
- [ ] Mục 1.4.3 (Multi Agents) không khẳng định các agent cụ thể đã vận hành nếu chưa được xác nhận.
- [ ] Mục 2.4 và 4.3 (tin tức/sentiment) dùng thì định hướng phù hợp với trạng thái pipeline thực tế.
- [ ] Đánh số lại toàn bộ trích dẫn IEEE theo đúng thứ tự xuất hiện sau khi ghép toàn bộ các chương.
