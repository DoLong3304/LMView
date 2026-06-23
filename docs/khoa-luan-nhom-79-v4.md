# KHÓA LUẬN TỐT NGHIỆP NHÓM 79

## XÂY DỰNG HỆ THỐNG PHÂN TÍCH KỸ THUẬT TIỀN ĐIỆN TỬ THỜI GIAN THỰC
### NỀN TẢNG LMVIEW — KIẾN TRÚC LAMBDA TRÊN DOCKER SWARM 3 NODE

---

**Ngành học:** Khoa học Máy tính / Công nghệ Phần mềm

**Giảng viên hướng dẫn:** ...

**Sinh viên thực hiện - Nhóm 79:** ...

**Niên khóa:** 2025–2026

---

# MỞ ĐẦU

## 1. Bối cảnh và vấn đề nghiên cứu

Thị trường tiền điện tử (cryptocurrency market) đã trải qua một cuộc chuyển mình ngoạn mục trong thập kỷ qua, từ một thử nghiệm công nghệ biên trở thành một kênh đầu tư toàn cầu với tổng vốn hóa thị trường đạt hơn hai nghìn tỷ đô-la Mỹ vào đầu năm 2025. Không giống như các thị trường tài chính truyền thống vốn chỉ hoạt động trong những khung giờ nhất định và đóng cửa vào cuối tuần cũng như ngày lễ, thị trường tiền điện tử vận hành 24 giờ một ngày, 7 ngày một tuần, 365 ngày một năm. Đặc điểm này, kết hợp với biến động giá cực kỳ nhanh và mạnh — một đồng tiền có thể thay đổi giá từ 5 đến 20 phần trăm chỉ trong vài giờ — tạo ra một môi trường giao dịch đầy thách thức, nơi tốc độ truy cập thông tin chính xác và kịp thời trở thành yếu tố sống còn đối với nhà đầu tư.

Phân tích kỹ thuật (technical analysis), với tư cách là phương pháp dự đoán biến động giá dựa trên dữ liệu lịch sử về giá và khối lượng giao dịch, đã trở thành công cụ trung tâm trong quyết định giao dịch của phần lớn nhà đầu tư tiền điện tử. Các nền tảng như TradingView, CoinMarketCap hay Binance cung cấp biểu đồ nến Nhật (Japanese candlestick chart), các chỉ báo kỹ thuật (RSI, MACD, Bollinger Bands), và dữ liệu thị trường theo thời gian thực. Tuy nhiên, những nền tảng thương mại này tồn tại một số hạn chế đáng kể về mặt chi phí, khả năng tùy biến, và tích hợp trí tuệ nhân tạo:

- **Chi phí:** TradingView Pro có giá từ 15 đến 60 đô-la Mỹ mỗi tháng cho dữ liệu thời gian thực và các chỉ báo nâng cao, một mức giá không nhỏ đối với nhà đầu tư cá nhân tại các thị trường mới nổi.
- **Khả năng tùy biến:** người dùng không thể mở rộng hoặc tích hợp các mô hình trí tuệ nhân tạo riêng vào nền tảng, cũng như không thể kiểm tra thuật toán phân tích do mã nguồn đóng.
- **Tích hợp trí tuệ nhân tạo:** hầu hết các nền tảng hiện tại chưa có trợ lý thông minh có khả năng phân tích ngữ cảnh thị trường và giải thích biến động giá bằng ngôn ngữ tự nhiên, buộc nhà đầu tư phải tự tổng hợp thông tin từ nhiều nguồn khác nhau.

Từ những phân tích trên, vấn đề cốt lõi mà nghiên cứu này đặt ra là: làm thế nào để xây dựng một nền tảng phân tích kỹ thuật tiền điện tử thời gian thực với chi phí vận hành thấp, khả năng mở rộng linh hoạt, và tích hợp trí tuệ nhân tạo — mà vẫn đảm bảo độ trễ dưới 500 mili-giây từ thời điểm lệnh được khớp trên sàn giao dịch cho đến khi hiển thị trên trình duyệt người dùng? Bài toán này đặt ra những thách thức không nhỏ về kiến trúc hệ thống, khả năng chịu lỗi, lưu trữ đa tầng, và tích hợp AI, đòi hỏi một giải pháp tổng thể có cơ sở lý thuyết vững chắc và khả năng triển khai thực tế.

## 2. Phương pháp nghiên cứu

Khóa luận này áp dụng Phương pháp luận Nghiên cứu Khoa học Thiết kế (Design Science Research Methodology — DSRM) do Peffers và cộng sự đề xuất (Peffers et al., 2007) làm khung phương pháp luận chính. DSRM là một quy trình gồm sáu bước: xác định vấn đề và động cơ nghiên cứu, xác định mục tiêu của giải pháp, thiết kế và phát triển, trưng bày (demonstration), đánh giá (evaluation), và truyền thông (communication). Khung này đặc biệt phù hợp cho các nghiên cứu trong lĩnh vực hệ thống thông tin và kỹ thuật phần mềm, nơi sản phẩm đầu ra là một artifact (hệ thống phần mềm) cùng với kiến thức kiến trúc đi kèm.

Ánh xạ sáu bước DSRM vào cấu trúc khóa luận:

- **Bước 1 (xác định vấn đề):** trình bày trong Chương 1 thông qua tổng quan về thị trường tiền điện tử, phân tích kỹ thuật, các thách thức về xử lý dữ liệu thời gian thực, và kiến trúc AI.
- **Bước 2 (xác định mục tiêu giải pháp):** thông qua việc xây dựng năm câu hỏi nghiên cứu CN1–CN5 với các chỉ số mục tiêu cụ thể (E2E latency p50 < 200ms, failover < 30s, chi phí < 300 USD/tháng production).
- **Bước 3 (thiết kế và phát triển):** trình bày trong Chương 2 và Chương 3: kiến trúc Lambda ba tầng, ba node Docker Swarm, Flink streaming job, RAG pipeline.
- **Bước 4 (trưng bày):** thông qua bảng trạng thái 23 dịch vụ, kết quả vận hành, và các sơ đồ kiến trúc trong Chương 3.
- **Bước 5 (đánh giá):** khung đánh giá GQM với sáu tiêu chí E1–E6 và phân tích threats to validity trong Chương 4.
- **Bước 6 (truyền thông):** chính khóa luận này, với mã nguồn được publish trên GitHub dưới dạng open-source.

## 3. Phát biểu bài toán và các câu hỏi nghiên cứu

Bài toán của khóa luận này được phát biểu một cách hình thức như sau: xây dựng một nền tảng phần mềm có tên gọi LMView, có khả năng thu thập dữ liệu thị trường tiền điện tử theo thời gian thực từ sàn giao dịch Binance, xử lý và lưu trữ dữ liệu với độ trễ tối thiểu, hiển thị biểu đồ phân tích kỹ thuật trực quan trên trình duyệt web, và tích hợp trợ lý trí tuệ nhân tạo có khả năng trả lời các câu hỏi phân tích thị trường dựa trên ngữ cảnh dữ liệu thời gian thực.

Bài toán này được phân rã thành bốn bài toán con:

- **Thu thập dữ liệu (data ingestion):** duy trì kết nối ổn định với Binance WebSocket cho 671 symbol, xử lý ngắt kết nối và auto-reconnect, parse dữ liệu từ định dạng Binance JSON thành cấu trúc dữ liệu nội bộ.
- **Xử lý streaming (stream processing):** tổng hợp nến 1 giây thành nến 1 phút, tính toán chỉ báo kỹ thuật trên luồng dữ liệu vô hạn, đảm bảo tính nhất quán trong môi trường phân tán.
- **Lưu trữ đa tầng (multi-tier storage):** phân bổ dữ liệu vào các tầng lưu trữ khác nhau (Redis, InfluxDB, Iceberg) dựa trên tần suất truy xuất và yêu cầu về độ trễ, đồng bộ nhất quán giữa các tầng.
- **Tích hợp AI (AI integration):** xây dựng trợ lý AI có khả năng truy xuất thông tin thị trường thời gian thực, kết hợp với cơ sở tri thức có cấu trúc, sinh câu trả lời chính xác, an toàn, kịp thời.

Từ bài toán tổng quát, năm câu hỏi nghiên cứu cụ thể được đặt ra theo khuôn mẫu GQM (Goal-Question-Metric) của Wohlin và cộng sự (Wohlin et al., 2012):

- **CN1 (kiến trúc hệ thống):** làm thế nào để thiết kế một kiến trúc xử lý dữ liệu thời gian thực đáp ứng yêu cầu độ trễ dưới 500ms với hơn 600 cặp giao dịch đồng thời, đồng thời đảm bảo lưu trữ dữ liệu lịch sử lâu dài? *Mục tiêu đánh giá:* E2E latency p50 < 200ms, p99 < 500ms.
- **CN2 (khả năng chịu lỗi):** làm thế nào để thiết kế cơ chế đảm bảo hệ thống vẫn hoạt động liên tục khi có sự cố ở một hoặc nhiều thành phần? *Mục tiêu đánh giá:* Redis failover < 30s, Kafka 0 data loss khi mất 1 broker.
- **CN3 (chiến lược lưu trữ đa tầng):** làm thế nào để kết hợp hiệu quả giữa lưu trữ nóng (Redis), ấm (InfluxDB), và lạnh (Iceberg/MinIO) nhằm cân bằng tốc độ truy xuất và chi phí? *Mục tiêu đánh giá:* chi phí lưu trữ < 1 USD/tháng cho toàn bộ dữ liệu lịch sử.
- **CN4 (tích hợp trí tuệ nhân tạo):** làm thế nào để xây dựng trợ lý AI sử dụng kiến trúc RAG có khả năng phân tích dựa trên dữ liệu thời gian thực kết hợp cơ sở tri thức, đồng thời đảm bảo an toàn và chính xác? *Mục tiêu đánh giá:* RAG retrieval precision > 80%, LLM hallucination rate < 10%.
- **CN5 (triển khai thực tế):** làm thế nào để triển khai trên hạ tầng Docker Swarm ba node EC2 với chi phí vận hành tối ưu? *Mục tiêu đánh giá:* tổng chi phí < 300 USD/tháng production (c5.2xlarge spot), < 50 USD/tháng staging (t3.medium spot).

## 4. Đóng góp chính của khóa luận

Khóa luận này đóng góp bốn kết quả chính, mỗi kết quả tương ứng với một hoặc nhiều câu hỏi nghiên cứu đã nêu:

- **Đóng góp 1 — Kiến trúc Lambda ba tầng hoàn chỉnh:** được thiết kế riêng cho phân tích kỹ thuật tiền điện tử thời gian thực, xử lý 671 cặp USDT từ Binance, kèm cơ chế đối chiếu dữ liệu (reconciliation/stitching) tại tầng phục vụ giúp dung hòa kết quả giữa luồng thời gian thực và luồng batch — giải quyết thách thức kinh điển của kiến trúc Lambda (CN1).
- **Đóng góp 2 — Thiết kế phân bổ tối ưu trên ba node Docker Swarm:** Node 1 (API/Infra), Node 2 (Data/Streaming), Node 3 (Compute/Analytics), đảm bảo tổng RAM mỗi node không vượt 12 GB, chi phí < 300 USD/tháng production và < 50 USD/tháng staging (CN5).
- **Đóng góp 3 — Cơ chế chịu lỗi đa tầng:** Kafka RF=3 (chịu mất 1 broker), Redis Sentinel quorum 2/3 (phục hồi < 30s), Flink checkpoint (exactly-once), và đường dự phòng tốc độ cao (direct Redis bypass) duy trì cập nhật ngay cả khi pipeline chính gặp sự cố (CN2).
- **Đóng góp 4 — Hệ thống trợ lý AI tích hợp với RAG:** scope gate, prompt builder, provider router, output guard; vận hành trên cùng hạ tầng với backend, tận dụng PostgreSQL + pgvector lưu vector embeddings và lịch sử hội thoại (CN4).

## 5. Phạm vi nghiên cứu

Phạm vi của khóa luận được xác định trên bốn khía cạnh:

- **Phạm vi chức năng:** biểu đồ nến thời gian thực (chín khung thời gian từ 1s đến 1w), sổ lệnh 50 mức giá mua/bán, lịch sử giao dịch 50 lệnh gần nhất, chỉ báo kỹ thuật cốt lõi (SMA, EMA, RSI, MACD, Bollinger Bands), trợ lý AI chat, bảng tổng quan thị trường, tab tin tức tổng hợp từ CoinDesk, CoinTelegraph, CryptoPanic.
- **Phạm vi dữ liệu:** 671 cặp USDT từ Binance (chọn lọc theo khối lượng 24h), dữ liệu lịch sử 90 ngày qua InfluxDB, lưu trữ vô thời hạn qua Iceberg/MinIO.
- **Phạm vi công nghệ:** Docker Swarm trên ba máy AWS EC2, backend Python FastAPI, frontend React 19 + TypeScript, pipeline Apache Kafka, Flink, Spark.
- **Phạm vi không bao gồm:** giao dịch tự động, bot trading, sentiment analysis từ mạng xã hội (Twitter/Reddit), hỗ trợ đa sàn ngoài Binance.

## 6. Kết cấu của khóa luận

Khóa luận gồm bốn chương. **Chương 1 (Cơ sở lý thuyết)** trình bày nền tảng lý thuyết bốn lĩnh vực cốt lõi: tiền điện tử và thị trường, phân tích kỹ thuật, xử lý dữ liệu lớn thời gian thực (kiến trúc Lambda và Data Lakehouse), và trí tuệ nhân tạo trong phân tích tài chính (LLM, RAG, vector database). **Chương 2 (Tổng quan và kiến trúc hệ thống)** phân tích yêu cầu chức năng và phi chức năng, đề xuất kiến trúc Lambda ba tầng trên Docker Swarm ba node, trình bày chi tiết các luồng dữ liệu, kịch bản sử dụng, bảng công nghệ áp dụng. **Chương 3 (Xây dựng và triển khai)** mô tả cài đặt hạ tầng AWS, phân tích chi tiết kiến trúc ba node, giao diện người dùng, kết quả vận hành. **Chương 4 (Đánh giá và kết luận)** thiết lập khung tiêu chí đánh giá, trình bày bảng số liệu đo lường, thảo luận điểm mạnh, hạn chế và đề xuất hướng phát triển.

---

# CHƯƠNG 1 — CƠ SỞ LÝ THUYẾT

## 1.1. Tiền điện tử và thị trường tiền điện tử

### 1.1.1. Khái niệm và lịch sử phát triển của tiền điện tử

Tiền điện tử (cryptocurrency) là một loại tài sản kỹ thuật số sử dụng mật mã học (cryptography) nhằm đảm bảo an toàn cho các giao dịch, kiểm soát việc tạo ra các đơn vị mới, và xác minh việc chuyển giao tài sản mà không cần đến sự hiện diện của các trung gian tài chính truyền thống. Khác với tiền pháp định (fiat currency) do chính phủ các quốc gia phát hành và kiểm soát thông qua ngân hàng trung ương, tiền điện tử hoạt động dựa trên công nghệ blockchain — một loại sổ cái phân tán (distributed ledger) phi tập trung, nơi mọi giao dịch được ghi nhận một cách công khai, minh bạch và không thể thay đổi sau khi đã được xác nhận.

Bitcoin (BTC), ra mắt lần đầu vào năm 2009 bởi một cá nhân hoặc nhóm ẩn danh dưới bút danh Satoshi Nakamoto, là đồng tiền điện tử đầu tiên trong lịch sử và vẫn duy trì vị thế thống trị về vốn hóa thị trường cho đến ngày nay. Trong whitepaper gốc của mình (Nakamoto, 2008), Nakamoto đã đề xuất một hệ thống tiền mặt điện tử peer-to-peer cho phép thực hiện các giao dịch trực tuyến mà không cần thông qua một tổ chức tài chính trung gian. Bitcoin giới thiệu khái niệm bằng chứng công việc (proof-of-work — PoW) như một cơ chế đồng thuận phân tán, và đặt ra giới hạn cung ứng tối đa 21 triệu đơn vị, tạo nên tính khan hiếm số học mà nhiều người ví như "vàng kỹ thuật số".

Ethereum (ETH), ra mắt vào năm 2015 bởi Vitalik Buterin và cộng sự, đã mở rộng đáng kể khái niệm về blockchain thông qua việc giới thiệu hợp đồng thông minh (smart contract) (Buterin, 2013). Không giống như Bitcoin vốn chỉ tập trung vào chức năng chuyển tiền, Ethereum cho phép lập trình các ứng dụng phi tập trung (decentralized applications — dApps) trên nền tảng của nó, mở ra một hệ sinh thái phong phú bao gồm tài chính phi tập trung (DeFi), token không thể thay thế (NFT), và các tổ chức tự trị phi tập trung (DAO). Các altcoin khác như Binance Coin (BNB), Solana (SOL), Cardano (ADA), và Ripple (XRP) tiếp tục mở rộng hệ sinh thái này với những cải tiến về khả năng mở rộng, tốc độ giao dịch, và mô hình đồng thuận khác nhau (Wood, 2014).

### 1.1.2. Giả thuyết thị trường hiệu quả trong bối cảnh tiền điện tử

Giả thuyết thị trường hiệu quả (Efficient Market Hypothesis — EMH) của Fama (Fama, 1970) là một trong những lý thuyết nền tảng của tài chính hiện đại. EMH phát biểu rằng giá thị trường phản ánh toàn bộ thông tin có sẵn, do đó không thể đạt được lợi nhuận vượt trội một cách nhất quán thông qua phân tích kỹ thuật hoặc phân tích cơ bản. EMH tồn tại ở ba dạng: dạng yếu (weak form) — giá phản ánh toàn bộ thông tin lịch sử; dạng trung bình (semi-strong form) — giá phản ánh toàn bộ thông tin công khai; dạng mạnh (strong form) — giá phản ánh cả thông tin nội bộ.

Urquhart (Urquhart, 2016) đã tiến hành nghiên cứu thực nghiệm về tính hiệu quả của thị trường Bitcoin và phát hiện bằng chứng cho thấy thị trường Bitcoin là không hiệu quả (inefficient) trong giai đoạn đầu (2010–2013) nhưng dần trở nên hiệu quả hơn theo thời gian. Kết quả này phù hợp với giả thuyết rằng thị trường tiền điện tử đang trong quá trình trưởng thành và hiệu quả hóa. Tran và Leirvik (Tran & Leirvik, 2020) mở rộng nghiên cứu ra 15 loại tiền điện tử và kết luận rằng không có đồng tiền nào đạt hiệu quả dạng yếu trong toàn bộ thời gian nghiên cứu, nhưng các đồng tiền vốn hóa lớn (Bitcoin, Ethereum) cho thấy xu hướng tiến tới hiệu quả rõ rệt.

Ý nghĩa của EMH đối với LMView mang tính hai mặt:

- Nếu thị trường tiền điện tử không hiệu quả hoàn toàn, phân tích kỹ thuật (soi biểu đồ, tính chỉ báo) có thể mang lại lợi thế thông tin cho nhà đầu tư — biện minh cho tính hữu ích của nền tảng.
- Nếu thị trường đang tiến tới hiệu quả hơn, nền tảng cần cung cấp thông tin thời gian thực với độ trễ tối thiểu để người dùng tận dụng lợi thế thông tin trước khi thị trường điều chỉnh — chính xác là mục tiêu latency dưới 500ms của LMView.

### 1.1.3. Các cơ chế đồng thuận và tác động đến thị trường

Các cơ chế đồng thuận của blockchain có ảnh hưởng trực tiếp đến cấu trúc thị trường và do đó đến thiết kế nền tảng phân tích kỹ thuật. Các cơ chế phổ biến bao gồm:

- **Proof-of-Work (PoW):** Bitcoin sử dụng PoW, nơi thợ đào (miners) cạnh tranh giải bài toán hash (SHA-256) để tạo block mới. Hash rate (~600 EH/s đầu 2026) là thước đo trực tiếp cho sức mạnh tính toán và bảo mật của mạng lưới.
- **Proof-of-Stake (PoS):** Ethereum chuyển từ PoW sang PoS vào tháng 9/2022 (sự kiện The Merge), nơi validator stake ETH để xác nhận giao dịch thay vì tiêu tốn điện năng cho đào coin (Buterin, 2013).
- **Proof-of-History (PoH) kết hợp PoS:** Solana đạt throughput lên tới 65,000 TPS.

Các sự kiện nâng cấp giao thức như Bitcoin halving (giảm một nửa phần thưởng block mỗi 210,000 block, ~4 năm một lần) thường tạo ra biến động giá đáng kể và là nguồn sự kiện quan trọng cần phản ánh kịp thời trên nền tảng phân tích.

### 1.1.4. Cấu trúc vi mô và đặc điểm thị trường tiền điện tử

Cấu trúc vi mô thị trường (market microstructure) nghiên cứu quá trình hình thành giá trong ngắn hạn dưới tác động của các yếu tố như dòng lệnh, chi phí giao dịch, và hành vi của các nhà tạo lập thị trường (Carbone et al., 2015). Trong thị trường tiền điện tử, cấu trúc vi mô có các đặc thù quan trọng:

- **Order book** hiển thị tập trung tất cả lệnh mua và bán còn hiệu lực, với bid (giá mua) và ask (giá bán) sắp xếp theo thứ tự giá. Chênh lệch giữa giá ask thấp nhất và bid cao nhất gọi là bid-ask spread — chỉ số quan trọng đánh giá tính thanh khoản.
- **Depth của thị trường** (tổng khối lượng lệnh ở các mức giá gần giá hiện tại) phản ánh khả năng hấp thụ lệnh lớn mà không gây trượt giá (slippage) đáng kể.
- **Giao dịch khớp lệnh** (taker order) được ghi nhận dưới dạng trade — mỗi trade bao gồm giá, khối lượng, thời gian, và chiều giao dịch (buyer/seller).

Thị trường tiền điện tử sở hữu ba đặc điểm khác biệt cơ bản so với thị trường tài chính truyền thống:

- **Tính liên tục 24/7:** thị trường không bao giờ đóng cửa, không có phiên giao dịch (Makarov & Schoar, 2020), dữ liệu giá sinh ra liên tục, không có gap giữa các phiên.
- **Tính phân mảnh của thị trường:** hàng trăm sàn giao dịch hoạt động song song, mỗi sàn có liquidity pool, phí giao dịch, và cơ chế khớp lệnh riêng. Giá BTC trên Binance có thể chênh lệch 0.1–0.5% so với Coinbase, tạo cơ hội arbitrage (CoinMarketCap, 2025).
- **Tính biến động cực cao:** độ lệch chuẩn lợi suất hàng ngày của Bitcoin (3–5%) cao gấp 5–10 lần so với S&P 500 (0.5–1%), thường xuyên xuất hiện biến động giá đột ngột (flash crash, spike) do tính thanh khoản phân tán (Makarov & Schoar, 2020).

Ngoài ra, tiền điện tử có tính thanh khoản cao đối với các đồng tiền chủ chốt (Bitcoin, Ethereum) với khối lượng giao dịch hàng ngày thường xuyên vượt mức hàng chục tỷ đô-la Mỹ, đảm bảo dữ liệu giá luôn cập nhật liên tục. Tuy nhiên, tiền điện tử cũng có tương quan thấp với thị trường tài chính truyền thống, khiến chúng trở thành kênh đa dạng hóa danh mục hấp dẫn nhưng đồng thời đặt ra thách thức cho các mô hình phân tích vốn được phát triển chủ yếu cho thị trường chứng khoán.

### 1.1.5. Sàn giao dịch Binance và API thời gian thực

Binance là sàn giao dịch tiền điện tử lớn nhất thế giới tính theo khối lượng giao dịch, xử lý khối lượng hàng ngày thường xuyên vượt quá 50 tỷ đô-la Mỹ theo dữ liệu từ CoinMarketCap (CoinMarketCap, 2025). Binance cung cấp hai giao thức truy cập chính (Binance, 2026):

**WebSocket Streams** — giao thức push dữ liệu thời gian thực, cho phép Binance chủ động gửi dữ liệu khi có sự kiện mới:

- `@ticker` stream: cập nhật thông tin giá 24 giờ cho mỗi symbol, tần suất ~1 giây.
- `@kline` stream: push dữ liệu nến mới ngay khi nến đóng cửa.
- `@depth` stream: cập nhật sổ lệnh theo thời gian thực.
- `@aggTrade` stream: thông báo giao dịch khớp mới.
- **Combined Streams:** gộp nhiều stream của nhiều symbol vào một kết nối duy nhất, giảm số lượng kết nối cần duy trì.

**REST API** — cung cấp endpoint truy vấn dữ liệu lịch sử và snapshot:

- `/api/v3/klines`: dữ liệu nến lịch sử.
- `/api/v3/depth`: snapshot sổ lệnh hiện tại.
- `/api/v3/aggTrades`: lịch sử giao dịch gần nhất.

Trong LMView, Binance được chọn làm nguồn dữ liệu duy nhất dựa trên ba tiêu chí: khối lượng giao dịch lớn nhất đảm bảo dữ liệu phong phú, tài liệu API đầy đủ chi tiết, và độ ổn định cao của hệ thống WebSocket. 671 cặp USDT hàng đầu được chọn lọc tự động dựa trên khối lượng giao dịch 24 giờ, đảm bảo hệ thống chỉ xử lý các cặp có thanh khoản tốt nhất.

## 1.2. Phân tích kỹ thuật trong thị trường tiền điện tử

### 1.2.1. Nền tảng lý thuyết của phân tích kỹ thuật

Phân tích kỹ thuật (technical analysis — TA) là phương pháp đánh giá và dự đoán biến động giá của tài sản tài chính dựa trên việc nghiên cứu dữ liệu thị trường quá khứ, chủ yếu là giá và khối lượng giao dịch. Về mặt triết học, phân tích kỹ thuật dựa trên ba nguyên lý cốt lõi được hệ thống hóa từ các bài viết của Charles Dow — người sáng lập Wall Street Journal và cha đẻ của lý thuyết Dow — sau này được Murphy tổng hợp trong tác phẩm kinh điển "Technical Analysis of the Financial Markets" (Murphy, 1999):

- **Thị trường phản ánh tất cả thông tin (market discounts everything):** giá hiện tại đã tích hợp mọi yếu tố (cơ bản, tin tức, tâm lý nhà đầu tư), do đó nghiên cứu diễn biến giá đủ để đưa ra quyết định giao dịch mà không cần phân tích từng yếu tố cơ bản.
- **Giá vận động theo xu hướng (prices move in trends):** giá không biến động ngẫu nhiên mà tuân theo xu hướng tăng (uptrend), giảm (downtrend), hoặc đi ngang (sideways). Một khi xu hướng đã thiết lập, nó có xu hướng tiếp diễn cho đến khi có tín hiệu đảo chiều rõ ràng.
- **Lịch sử có tính lặp lại (history repeats itself):** các mô hình giá và hành vi tâm lý nhà đầu tư có xu hướng lặp lại theo thời gian do tâm lý đám đông mang tính chu kỳ.

Ba nguyên lý này có mối quan hệ mật thiết với Giả thuyết thị trường hiệu quả EMH (Fama, 1970). Phân tích kỹ thuật hoạt động dựa trên giả định thị trường chỉ hiệu quả ở mức yếu — giá phản ánh thông tin quá khứ nhưng chưa phản ánh thông tin hiện tại và tương lai, tạo ra cơ hội cho các nhà phân tích kỹ thuật. Sự thiếu vắng đồng thuận học thuật rõ ràng về mức độ hiệu quả của thị trường tiền điện tử (Urquhart, 2016; Tran & Leirvik, 2020) chính là lý do khiến LMView tích hợp trợ lý AI như một nguồn thông tin bổ sung, giúp nhà đầu tư có góc nhìn đa chiều trước khi đưa ra quyết định.

### 1.2.2. Các chỉ báo kỹ thuật cốt lõi

Các chỉ báo kỹ thuật triển khai trong LMView được phân loại thành bốn nhóm theo Murphy (Murphy, 1999) và Kirkpatrick cùng Dahlquist (Kirkpatrick & Dahlquist, 2015). Việc phân nhóm này có ý nghĩa quan trọng về cả lý thuyết lẫn triển khai kỹ thuật, bởi mỗi nhóm chỉ báo đòi hỏi phương pháp tính toán incremental khác nhau trong môi trường xử lý streaming.

**Nhóm chỉ báo xu hướng (trend indicators):**

- **SMA (Simple Moving Average)** tính bằng trung bình cộng giá đóng cửa trong N phiên gần nhất:

$$SMA_t(N) = \frac{1}{N} \sum_{i=0}^{N-1} P_{t-i}$$

- **EMA (Exponential Moving Average)** gán trọng số giảm dần theo thời gian, ưu tiên giá trị gần nhất:

$$EMA_t = P_t \times \alpha + EMA_{t-1} \times (1 - \alpha), \quad \alpha = \frac{2}{N+1}$$

Trong LMView, các chỉ báo xu hướng được tính toán trực tiếp trên luồng dữ liệu Flink thông qua cơ chế cửa sổ trượt (sliding window) với kỹ thuật incremental update — giá trị SMA/EMA mới được cập nhật dựa trên giá trị cũ và dữ liệu mới nhất, giảm chi phí tính toán.

**Nhóm chỉ báo động lượng (momentum indicators):**

- **RSI (Relative Strength Index)** do Wilder giới thiệu năm 1978 (Wilder, 1978), đo dao động trên thang 0–100:

$$RSI = 100 - \frac{100}{1 + RS}$$

RS là tỷ lệ giữa trung bình tăng giá và trung bình giảm giá trong N phiên. Ngưỡng kinh điển: RSI > 70 = quá mua (overbought), RSI < 30 = quá bán (oversold).

- **MACD (Moving Average Convergence Divergence):** hiệu giữa EMA 12 phiên và EMA 26 phiên; đường tín hiệu là EMA 9 phiên của chính MACD. Khi MACD cắt lên đường tín hiệu = tín hiệu mua; cắt xuống = tín hiệu bán.

**Nhóm chỉ báo biến động (volatility indicators):**

- **Bollinger Bands** gồm ba đường: đường giữa là SMA 20 phiên, dải trên = SMA(20) + 2σ, dải dưới = SMA(20) − 2σ, với σ là độ lệch chuẩn giá đóng cửa trong 20 phiên. Các chỉ báo phái sinh: Bandwidth (BW) = (Upper − Lower)/Middle phản ánh biến động tương đối; %B = (Close − Lower)/(Upper − Lower) cho biết vị trí giá trong dải. Dải mở rộng = biến động tăng, dải thu hẹp = biến động giảm (thường báo hiệu biến động lớn sắp xảy ra — squeeze setup).

**Nhóm chỉ báo khối lượng (volume indicators):** VWAP, OBV, ATR. Mặc dù hiện chưa triển khai, kiến trúc plugin cho phép mở rộng dễ dàng trong tương lai.

### 1.2.3. Các mô hình nến cơ bản và nhận dạng mô hình

Bên cạnh các chỉ báo định lượng, mô hình nến (candlestick pattern) đóng vai trò quan trọng nhờ khả năng cung cấp tín hiệu đảo chiều sớm trước khi các chỉ báo trễ kịp phản ứng. Nison (Nison, 2001) đã hệ thống hóa hàng trăm mô hình nến:

- **Mô hình một nến:** doji (giá mở/đóng gần bằng nhau, thể hiện sự do dự), hammer (thân trên nhỏ, bấc dưới dài — tín hiệu đảo chiều tăng), shooting star (thân dưới nhỏ, bấc trên dài — tín hiệu đảo chiều giảm).
- **Mô hình hai nến:** bullish engulfing (nến xanh bao trùm nến đỏ trước đó), bearish engulfing (nến đỏ bao trùm nến xanh).
- **Mô hình ba nến:** morning star (nến đỏ dài, doji, nến xanh dài — đáy), evening star (xanh dài, doji, đỏ dài — đỉnh), three white soldiers (ba nến xanh tăng dần).

Trong LMView, nhận dạng mô hình nến hiện được thực hiện thủ công bởi người dùng trên biểu đồ. Kiến trúc plugin cho phép tích hợp thư viện nhận dạng tự động trong tương lai. Khi người dùng hỏi AI Assistant, Prompt Builder thêm yêu cầu kiểm tra 10 mô hình nến cơ bản vào prompt; LLM trả lời dựa trên mô tả 6 nến 1h gần nhất từ ngữ cảnh thời gian thực. Hướng phát triển tương lai là triển khai custom indicator trong Flink để nhận dạng tự động.

### 1.2.4. Phân tích kỹ thuật trên dữ liệu streaming: thách thức và cơ hội

Tính toán chỉ báo kỹ thuật trên luồng dữ liệu streaming (infinite stream) đặt ra ba thách thức mà các nền tảng batch-based (TradingView, Binance) không gặp phải:

- **Out-of-order data:** dữ liệu Binance WebSocket không đến theo thứ tự thời gian tuyệt đối do network latency và load balancing. LMView giải quyết bằng watermark mechanism của Flink với maxOutOfOrderness=5000ms — cho phép 5 giây out-of-order trước khi nến được đóng.
- **Sliding window state:** tính toán RSI 14 yêu cầu duy trì cửa sổ 14 phiên, mỗi khi nến mới đến, nến cũ nhất phải được loại bỏ. LMView sử dụng RocksDB state backend với TTL 30 phút và sliding window logic.
- **Consistency giữa streaming và batch:** giá trị RSI trên streaming path có thể khác RSI trên batch path do khác biệt về thời gian snapshot. Cơ chế reconciliation giải quyết: khi nến đã đóng hoàn toàn và Flink đã tính xong RSI, giá trị streaming được ghi đè lên giá trị real-time tạm thời, đảm bảo dữ liệu lịch sử luôn chính xác.

### 1.2.5. Biểu đồ nến Nhật và cấu trúc dữ liệu OHLCV

Biểu đồ nến Nhật (Japanese Candlestick Chart) là phương pháp trực quan hóa dữ liệu giá phổ biến nhất, được Nison giới thiệu rộng rãi trong giới giao dịch phương Tây (Nison, 2001). Phương pháp này có nguồn gốc từ Nhật Bản thế kỷ 18, phát triển bởi Munehisa Homma — thương nhân gạo tại Osaka, được coi là hình thức phân tích kỹ thuật sớm nhất trong lịch sử.

Mỗi nến (candlestick) đại diện cho một khoảng thời gian giao dịch cụ thể và chứa bốn giá trị cốt lõi: Open (O) — giá mở cửa, High (H) — giá cao nhất, Low (L) — giá thấp nhất, Close (C) — giá đóng cửa, cùng với Volume (V). Cấu trúc OHLCV tạo thành đơn vị dữ liệu cơ bản:

$$\text{Candle}_t = \{O_t, H_t, L_t, C_t, V_t\}$$

Thân nến (real body) biểu diễn khoảng cách giữa giá mở và đóng cửa: xanh (bullish) nếu đóng > mở, đỏ (bearish) nếu ngược lại. Bấc nến (wick/shadow) biểu diễn giá cao/thấp nhất trong phiên. Một nến có bấc trên dài và thân nhỏ ở phía dưới gọi là "hammer" (búa) — tín hiệu đảo chiều tăng sau xu hướng giảm.

Trong LMView, dữ liệu nến được tổng hợp ở chín khung thời gian (1s, 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w). Quá trình aggregation theo cấu trúc phân cấp: nến 1s được Flink tổng hợp thành nến 1m thông qua KeyedProcessFunction với watermark, các khung lớn hơn tổng hợp từ nến 1m. Cơ chế phân cấp có hai ưu điểm: giảm khối lượng tính toán (Flink chỉ duy trì cửa sổ 1 phút), và dễ mở rộng (thêm khung mới chỉ cần thêm aggregation query).

Cơ chế hợp nhất (stitching) nến đã đóng (có chỉ báo kỹ thuật) với nến đang hình thành (từ dữ liệu ticker thời gian thực) được thực hiện tại tầng phục vụ FastAPI. Thuật toán stitching hoạt động như sau:

- FastAPI nhận request klines với limit=200.
- Đọc 200 nến gần nhất từ Redis (Sorted Set candle:1m:binance:BTCUSDT).
- Nếu Redis trả về đủ 200 nến, kiểm tra nến cuối: nếu là forming candle (timestamp < current_time), thay bằng nến từ Real-time Path.
- Nếu Redis không đủ, fallback sang InfluxDB (90 ngày), merge với nến mới nhất từ Redis.
- Nếu cả Redis và InfluxDB đều không đủ, fallback sang Trino/Iceberg.

### 1.2.6. Tác động của tin tức đến thị trường tiền điện tử

Thị trường tiền điện tử được ghi nhận là đặc biệt nhạy cảm với các sự kiện tin tức so với thị trường tài chính truyền thống. Các sự kiện có tác động mạnh bao gồm:

- Thay đổi quy định pháp lý từ SEC (Mỹ), MiCA (EU).
- Tuyên bố từ nhân vật có tầm ảnh hưởng (Elon Musk, quan chức FED).
- Sự cố bảo mật, hack sàn giao dịch.
- Sự kiện nâng cấp giao thức (Bitcoin halving, Ethereum Merge).
- Biến động kinh tế vĩ mô (lạm phát, lãi suất).

Liu và Tsyvinski (Liu & Tsyvinski, 2021) đã tiến hành nghiên cứu định lượng quy mô lớn về các yếu tố tác động đến lợi suất tiền điện tử và phát hiện rằng các yếu tố phi truyền thống (tin tức, tâm lý mạng xã hội) có tương quan mạnh hơn đáng kể so với các yếu tố truyền thống (chỉ số chứng khoán, tỷ giá hối đoái). Kết quả này củng cố nhu cầu tích hợp nguồn thông tin thị trường có cấu trúc và khả năng tổng hợp thông minh vào nền tảng phân tích kỹ thuật.

Trong LMView, khả năng phân tích tin tức được hiện thực hóa thông qua trợ lý AI với kiến trúc RAG — truy xuất thông tin thị trường mới nhất từ cơ sở tri thức kết hợp dữ liệu thời gian thực. Pipeline tin tức tự động và phân tích cảm xúc vẫn đang trong giai đoạn khảo sát kỹ thuật và chưa được tích hợp vào pipeline production (xem phần Hạn chế 4.2).

## 1.3. Xử lý dữ liệu lớn trong thời gian thực

### 1.3.1. Kiến trúc Lambda

Kiến trúc Lambda (Lambda Architecture) là mô hình kiến trúc xử lý dữ liệu lớn được Nathan Marz giới thiệu lần đầu năm 2013 và trình bày chi tiết trong cuốn sách "Big Data: Principles and Best Practices of Scalable Realtime Data Systems" (Marz & Warren, 2015). Marz, người từng là kỹ sư trưởng tại BackType (được Twitter mua lại năm 2011), đã phát triển kiến trúc này dựa trên kinh nghiệm thực tế trong xây dựng hệ thống xử lý dữ liệu lớn tại Twitter.

Kiến trúc Lambda giải quyết một bài toán cốt lõi: làm thế nào để xây dựng hệ thống vừa có độ trễ cực thấp (dưới 1 giây) vừa có khả năng tính toán lại toàn bộ lịch sử một cách chính xác. Không có công nghệ xử lý dữ liệu đơn lẻ nào đáp ứng đồng thời cả hai yêu cầu: hệ thống thời gian thực (Storm, Flink) có độ trễ thấp nhưng không thể tính toán lại lịch sử hiệu quả; hệ thống batch (Hadoop, Spark) có độ chính xác cao nhưng độ trễ tính bằng phút hoặc giờ.

Kiến trúc Lambda gồm ba tầng vận hành song song:

- **Speed Layer:** xử lý dữ liệu theo thời gian thực với độ trễ từ vài chục mili-giây đến vài giây. Dữ liệu được xử lý ngay khi đến, kết quả lưu vào bộ nhớ đệm nóng (Redis), cung cấp kết quả tức thời nhưng có thể chưa hoàn toàn chính xác.
- **Batch Layer:** xử lý toàn bộ dữ liệu lịch sử, đảm bảo độ chính xác tuyệt đối. Lưu trữ dữ liệu gốc bất biến (immutable), thực hiện tính toán phức tạp định kỳ. Kết quả có độ trễ cao (phút đến giờ) nhưng hoàn toàn chính xác và reproducible.
- **Serving Layer:** kết hợp và đối chiếu kết quả từ hai tầng trên, cung cấp giao diện thống nhất. Đây là tầng phức tạp nhất, phải giải quyết dung hòa giữa kết quả tạm thời từ speed layer và kết quả chính xác từ batch layer.

Quyết định lựa chọn Lambda thay vì Kappa (chỉ một luồng xử lý thời gian thực duy nhất) trong LMView dựa trên phân tích định lượng. Với 671 symbol × 86,400 giây/ngày × 365 ngày ≈ 21 tỷ sự kiện mỗi năm, Kappa đòi hỏi lưu trữ toàn bộ trong Kafka, dẫn đến chi phí rất lớn (Kafka tối ưu throughput, không phải lưu trữ dài hạn). Lambda giải quyết bằng cách chỉ dùng Kafka cho speed layer (retention 48 giờ), trong khi batch layer lưu vô thời hạn trên Iceberg/MinIO với chi phí thấp hơn nhiều (dữ liệu nén Parquet, lưu trên object storage).

Tuy nhiên, Lambda cũng có hạn chế:

- Độ phức tạp tăng do phải duy trì hai codebase xử lý song song (Flink cho speed layer, Spark cho batch layer).
- Độ trễ giữa speed layer và batch layer có thể dẫn đến không nhất quán dữ liệu tạm thời.
- Chi phí bảo trì cao hơn.

Những hạn chế này là đối tượng của cơ chế đối chiếu dữ liệu (reconciliation/stitching) được trình bày chi tiết trong Chương 2.

### 1.3.2. Hạ tầng lưu trữ Data Lakehouse

Data Lakehouse là mô hình kiến trúc lưu trữ kết hợp ưu điểm của Data Warehouse (ACID, schema enforcement, SQL) và Data Lake (lưu trữ linh hoạt, chi phí thấp). Armbrust và cộng sự (Armbrust et al., 2021), trong bài báo tại hội nghị CIDR 2021, định nghĩa Data Lakehouse là "thế hệ nền tảng dữ liệu mới kết hợp khả năng lưu trữ linh hoạt, chi phí thấp của Data Lake với khả năng quản lý giao dịch ACID, hỗ trợ schema enforcement, và truy vấn SQL hiệu quả của Data Warehouse".

LMView triển khai Data Lakehouse trên Apache Iceberg — định dạng bảng mã nguồn mở phát triển bởi Netflix, chuyển giao cho Apache Software Foundation (Armbrust et al., 2021; Apache Iceberg, 2021). Iceberg cung cấp ba tính năng quan trọng:

- **ACID transactions:** cho phép nhiều luồng ghi đồng thời (từ Spark streaming và job batch) mà không gây xung đột.
- **Time travel:** truy vấn dữ liệu tại bất kỳ thời điểm nào trong quá khứ, hữu ích cho tái tạo kết quả và gỡ lỗi.
- **Schema evolution:** thêm, xóa, hoặc thay đổi kiểu dữ liệu cột mà không cần viết lại toàn bộ bảng.

Hạ tầng lưu trữ tổ chức theo kiến trúc Medallion ba tầng:

- **Bronze (đồng):** lưu dữ liệu thô nguyên bản từ Kafka, định dạng BINARY cho phép replay toàn bộ pipeline khi cần.
- **Silver (bạc):** làm sạch dữ liệu — loại bỏ trùng lặp dựa trên key (exchange, symbol, timestamp), chuẩn hóa kiểu dữ liệu (DECIMAL(20,8) thay vì DOUBLE để tránh sai số dấu phẩy động, đặc biệt quan trọng với token có giá rất nhỏ hoặc rất lớn), chuẩn hóa múi giờ về UTC.
- **Gold (vàng):** dữ liệu tổng hợp ở mức độ cao, sẵn sàng cho truy vấn API (market overview, top gainers/losers, news feed), tính toán từ Silver qua các job Spark định kỳ.

MinIO — hệ thống lưu trữ đối tượng mã nguồn mở tương thích S3 — đóng vai trì tầng lưu trữ vật lý cho Iceberg. MinIO chạy trên Node 1 với volume dữ liệu riêng, cung cấp port 9000 (S3 API) và port 9001 (web console). Trino — engine truy vấn SQL phân tán mã nguồn mở — chạy trên Node 3, cho phép truy vấn trực tiếp trên Iceberg qua JDBC catalog kết nối PostgreSQL.

### 1.3.3. Các kỹ thuật xử lý dữ liệu thời gian thực

Xử lý dữ liệu thời gian thực trong LMView dựa trên ba công nghệ cốt lõi, mỗi công nghệ đảm nhiệm một vai trò riêng biệt:

**Apache Kafka** — nền tảng streaming phân tán được phát triển tại LinkedIn bởi Kreps và cộng sự (Kreps, 2011), với kiến trúc publish-subscribe cho phép lưu trữ và phát lại luồng sự kiện. Kafka hoạt động như "băng ghi âm" (immutable log): producer ghi message vào cuối log, consumer đọc từ đầu log theo thứ tự. Mỗi message lưu trên ổ cứng và có thể đọc lại nhiều lần (fan-out).

Trong LMView, Kafka cluster gồm ba broker trên ba node khác nhau. Số partition là 12 cho topic chính (crypto_ticker, crypto_klines), tương ứng với số luồng xử lý song song của Flink. Replication factor 3 đảm bảo mỗi message được sao chép sang ít nhất hai broker khác trước khi coi là đã ghi thành công. Cấu hình min.insync.replicas=2 đảm bảo producer chỉ nhận ack khi có ít nhất hai broker đã ghi thành công, ngăn chặn mất dữ liệu khi một broker gặp sự cố.

**Apache Flink** — framework xử lý streaming mã nguồn mở phát triển từ dự án Stratosphere tại Đại học Kỹ thuật Berlin (Carbone et al., 2015; Apache Flink, 2023). Flink có khả năng stateful processing ở độ trễ cực thấp. Khác với Spark Streaming sử dụng mô hình micro-batch (xử lý theo lô nhỏ 500ms–2s), Flink sử dụng mô hình event-by-event processing thông qua pipeline — mỗi bản ghi được xử lý ngay khi đến mà không cần đợi lô tiếp theo (Carbone et al., 2015). Điều này đặc biệt quan trọng với chỉ báo kỹ thuật yêu cầu tính toán incremental (EMA, RSI).

Flink JobManager chạy trên Node 2 điều phối job, quản lý checkpoint, phục hồi sau sự cố. Hai Flink TaskManager trên Node 2 và Node 3, mỗi cái xử lý 6 task, tổng parallelism 12 — tương ứng với số partition Kafka. Mỗi task thực hiện KeyedProcessFunction với key là cặp (exchange, symbol), đảm bảo mọi dữ liệu cùng symbol được xử lý bởi cùng task, duy trì thứ tự thời gian. Các xử lý chính: aggregation nến 1s→1m thông qua watermark, tính toán chỉ báo incremental qua cửa sổ trượt, ghi kết quả vào Redis (hot cache) và InfluxDB (warm storage) với batch flush 500ms.

**Redis Sentinel Cluster** — cung cấp khả năng chịu lỗi tự động (auto-failover) cho Redis, bộ nhớ đệm trong RAM chứa dữ liệu thời gian thực (Redis Ltd., 2024). Cấu hình gồm một master (Node 2), một replica (Node 3), ba sentinel (mỗi node một sentinel) giám sát cluster. Cơ chế quorum 2/3 đảm bảo quyết định failover chỉ được đưa ra khi ít nhất hai trong ba sentinel đồng thuận rằng master đã mất kết nối, tránh failover giả do sự cố mạng tạm thời.

## 1.4. Trí tuệ nhân tạo trong phân tích tài chính

### 1.4.1. Mô hình ngôn ngữ lớn (Large Language Model — LLM)

Mô hình ngôn ngữ lớn (LLM) là lớp mô hình deep learning được huấn luyện trên khối lượng văn bản khổng lồ (hàng nghìn tỷ token), có khả năng hiểu và sinh văn bản tự nhiên. Nền tảng kiến trúc là mô hình Transformer do Vaswani và cộng sự giới thiệu tại NeurIPS 2017 (Vaswani et al., 2017), với cơ chế self-attention cho phép mô hình học các mối quan hệ ngữ nghĩa phức tạp trong văn bản dài mà không bị giới hạn bởi độ dài context window như RNN/LSTM.

Các mô hình tiêu biểu qua từng giai đoạn phát triển:

- **GPT-1 (OpenAI, 2018)** với 117 triệu tham số chứng minh generative pre-training trên văn bản không gán nhãn có thể học được các mẫu ngôn ngữ phong phú (Radford et al., 2018).
- **BERT (Google, 2019)** với 340 triệu tham số giới thiệu masked language modeling và next-sentence prediction, đạt state-of-the-art trên 11 bài NLP tasks (Devlin et al., 2019).
- **GPT-3 (OpenAI, 2020)** với 175 tỷ tham số chứng minh scaling law: tăng quy mô mô hình dẫn đến sự xuất hiện của các khả năng mới (in-context learning, few-shot reasoning) mà không cần fine-tuning (Brown et al., 2020).
- **Llama (Meta, 2023)** tiếp tục đẩy giới hạn với kiến trúc optimized transformer trên dữ liệu huấn luyện chất lượng cao (Touvron et al., 2023).

Trong lĩnh vực tài chính, LLM được ứng dụng vào nhiều bài toán:

- Phân tích tin tức và báo cáo tài chính, trích xuất thông tin quan trọng từ hàng trăm trang báo cáo mỗi ngày.
- Tổng hợp thông tin thị trường từ nhiều nguồn (Twitter, Reddit, CoinDesk, Reuters) thành bức tranh tổng thể.
- Hỗ trợ ra quyết định đầu tư thông qua hội thoại tương tác.
- Tạo báo cáo phân tích kỹ thuật tự động dựa trên dữ liệu thời gian thực và chỉ báo kỹ thuật.

Trong LMView, LLM được tích hợp thông qua kiến trúc provider router — tầng trung gian cho phép lựa chọn linh hoạt giữa các nhà cung cấp mô hình, dễ dàng mở rộng sang provider mới (OpenAI, Anthropic) khi có nhu cầu.

### 1.4.2. Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation (RAG) là kiến trúc AI kết hợp truy xuất thông tin và sinh văn bản, được Lewis và cộng sự giới thiệu tại NeurIPS 2020 (Lewis et al., 2020). RAG giải quyết ba hạn chế cốt hữu của LLM thuần túy:

- **Knowledge cutoff:** LLM chỉ biết dữ liệu đến thời điểm huấn luyện (vài tháng đến vài năm trước), không thể cập nhật tin tức hay sự kiện mới.
- **Hallucination:** LLM có thể sinh thông tin không chính xác hoặc bịa đặt nhưng trình bày thuyết phục, gây nguy hiểm trong lĩnh vực tài chính.
- **Thiếu ngữ cảnh thị trường cụ thể:** LLM không biết trạng thái hiện tại của thị trường, dẫn đến câu trả lời chung chung, thiếu tính ứng dụng thực tế.

Kiến trúc RAG trong LMView gồm bốn bước tuần tự:

- **Embedding:** câu hỏi của người dùng chuyển thành vector 384 chiều bằng mô hình all-MiniLM-L6-v2 (mô hình sentence transformer nhẹ 80 MB nhưng đủ mạnh cho bài toán truy xuất kiến thức thị trường).
- **Retrieval:** vector câu hỏi truy vấn pgvector (extension vector của PostgreSQL) với HNSW index, tìm top-5 knowledge chunks có cosine similarity > 0.7.
- **Augmentation:** knowledge chunks ghép vào prompt template cùng ngữ cảnh thị trường thời gian thực (giá hiện tại, chỉ báo kỹ thuật, tin tức gần nhất).
- **Generation:** prompt hoàn chỉnh gửi đến LLM provider (mock hoặc litellm) sinh câu trả lời. Kết quả kiểm tra bởi output guard trước khi gửi về client.

### 1.4.3. Các kiến trúc AI liên quan

Bốn khái niệm trong mục này phản ánh các mức độ áp dụng khác nhau trong LMView, từ đã triển khai (DAG) đến đang nghiên cứu (MoE, Multi Agents, FinBERT).

**DAG (Directed Acyclic Graph):** cấu trúc toán học trong đó các tác vụ được tổ chức thành đồ thị có hướng không chu trình. Là nền tảng cho hầu hết nền tảng điều phối pipeline hiện đại như Apache Airflow, Dagster, Prefect. LMView sử dụng Dagster để quản lý pipeline batch, cho phép định nghĩa rõ ràng thứ tự thực thi và phụ thuộc giữa các tác vụ bronze-to-silver, silver-to-gold, compaction.

**MoE (Mixture of Experts):** kiến trúc mạng nơ-ron trong đó nhiều mô hình chuyên gia (experts) huấn luyện song song và router học cách chọn một hoặc kết hợp nhiều chuyên gia phù hợp cho từng đầu vào (Shazeer et al., 2017). Mặc dù LMView không triển khai MoE ở cấp độ mạng nơ-ron, khái niệm định tuyến thông minh được áp dụng ở cấp độ hệ thống thông qua provider router, nơi lựa chọn nhà cung cấp LLM phù hợp dựa trên độ phức tạp câu hỏi và yêu cầu tốc độ.

**Multi Agents:** hướng tiếp cận trong đó nhiều tác tử AI chuyên biệt phối hợp giải quyết vấn đề phức tạp (Chart Agent, News Agent, Indicator Agent). Đây là hướng phát triển đã hoạch định cho Phase 2 của LMView (dựa trên LangGraph) và chưa được triển khai ở giai đoạn hiện tại.

**FinBERT:** mô hình BERT được Araci (Araci, 2019) fine-tune trên dữ liệu tài chính, đạt độ chính xác cao trong phân tích cảm xúc (sentiment analysis) trên văn bản tin tức tài chính. LMView đã khảo sát FinBERT cùng VADER và CryptoBERT cho kế hoạch phân tích cảm xúc thị trường trong tương lai.

### 1.4.4. Vector database và thuật toán HNSW

Vector database là cơ sở dữ liệu chuyên biệt được thiết kế để lưu trữ và truy vấn các vector embeddings — biểu diễn số học của văn bản, hình ảnh, hoặc âm thanh trong không gian đa chiều. Trong hệ thống RAG, vector database đóng vai trò then chốt cho phép tìm kiếm đoạn văn bản có ngữ nghĩa tương tự câu hỏi của người dùng dựa trên cosine similarity hoặc Euclidean distance.

LMView sử dụng pgvector — extension mã nguồn mở cho PostgreSQL — làm vector database vì hai lý do:

- Lưu trữ vector embeddings trực tiếp trong cùng cơ sở dữ liệu quan hệ với người dùng, lịch sử hội thoại, và knowledge chunks, loại bỏ nhu cầu vận hành vector database riêng biệt (Pinecone, Weaviate).
- Hỗ trợ xây dựng HNSW index — một trong những thuật toán tìm kiếm láng giềng gần nhất (approximate nearest neighbor — ANN) hiệu quả nhất hiện nay.

Thuật toán HNSW (Hierarchical Navigable Small World Graphs), do Malkov và Yashunin đề xuất năm 2020 (Malkov & Yashunin, 2020), xây dựng cấu trúc đồ thị đa tầng (multi-layer graph):

- Tầng trên cùng có ít node nhất với kết nối dài nhất, cho phép tìm kiếm nhanh ở mức thô.
- Các tầng dưới có nhiều node hơn với kết nối ngắn hơn, cho phép tinh chỉnh kết quả.

Cơ chế phân cấp giảm độ phức tạp tìm kiếm từ O(n) (tìm kiếm tuyến tính) xuống O(log n), cho phép truy vấn top-5 knowledge chunks trong vài mili-giây ngay cả khi cơ sở tri thức chứa hàng chục nghìn đoạn văn bản. Trong LMView, HNSW index được cấu hình với m=16 (số kết nối tối đa trên mỗi node) và ef_construction=200 (độ chính xác khi xây dựng index).

---

# CHƯƠNG 2 — TỔNG QUAN VÀ KIẾN TRÚC HỆ THỐNG

Chương này trình bày tổng quan và kiến trúc hệ thống LMView theo bốn trục: tổng quan hệ thống (yêu cầu chức năng, phi chức năng), kiến trúc dữ liệu (Lambda ba tầng, Iceberg lakehouse, Kafka-Flink-Redis), kiến trúc AI (RAG pipeline, AI Service), và phân tích thiết kế chi tiết (luồng dữ liệu, kịch bản sử dụng, công nghệ sử dụng).

## 2.1. Tổng quan hệ thống

### 2.1.1. Yêu cầu chức năng

Hệ thống LMView được thiết kế nhằm cung cấp một nền tảng phân tích kỹ thuật tiền điện tử thời gian thực, với các chức năng được phân loại thành năm nhóm:

- **Hiển thị dữ liệu thị trường:**
  - Biểu đồ nến OHLCV với chín khung thời gian (1s, 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w), cập nhật qua WebSocket. Sử dụng lightweight-charts (TradingView-compatible), hỗ trợ zoom, pan, di chuyển qua vùng dữ liệu lịch sử.
  - Sổ lệnh 50 mức giá mua (bids) và bán (asks) tốt nhất, tổng khối lượng và depth thị trường cập nhật mỗi giây.
  - Lịch sử giao dịch tối đa 50 giao dịch khớp gần nhất, màu xanh cho buy market, đỏ cho sell market.
  - Ticker 24 giờ cho 671 cặp giao dịch.
- **Phân tích kỹ thuật:** chỉ báo SMA, EMA, RSI, MACD, Bollinger Bands tính toán trên luồng Flink, hiển thị trực tiếp trên biểu đồ nến, tùy chỉnh tham số (độ dài cửa sổ, màu sắc, độ dày đường).
- **Tổng quan thị trường:** top 20 tăng/giảm trong 24h, vốn hóa, chỉ số thống kê tổng thể.
- **Tin tức:** feed tổng hợp bài báo từ CoinDesk, CoinTelegraph, CryptoPanic cập nhật theo thời gian thực.
- **Trợ lý AI:** giao diện chat tiếng Việt/Anh, trích xuất và phân tích snapshot biểu đồ, giải thích chỉ báo kỹ thuật, tổng hợp xu hướng, cảnh báo sự kiện quan trọng.
- **Quản lý người dùng:** đăng ký, đăng nhập (JWT, session 24 giờ), cài đặt cá nhân hóa (giao diện sáng/tối, ngôn ngữ, danh sách theo dõi), bảng quản trị (quản lý người dùng, kiểm tra trạng thái hệ thống, xem log).

Hệ thống phục vụ ba nhóm người dùng:

- **Khách (guest):** xem biểu đồ nến, ticker, sổ lệnh, lịch sử giao dịch với tính năng giới hạn.
- **Người dùng đã đăng nhập (user):** toàn quyền tính năng bao gồm trợ lý AI, tùy chỉnh chỉ báo, chuyển đổi khung thời gian, dữ liệu lịch sử đầy đủ, tùy chỉnh giao diện.
- **Quản trị viên (admin):** thêm quyền quản lý người dùng, xem health check hệ thống, khởi động lại dịch vụ qua API, xem log vận hành.

### 2.1.2. Yêu cầu phi chức năng

Bảng 2.1. Yêu cầu phi chức năng của hệ thống

| ID | Yêu cầu | Mục tiêu | Ràng buộc / Mâu thuẫn |
|---|---|---|---|
| NFR1 | Độ trễ end-to-end | < 500ms từ Binance đến browser | Ghi vào bộ nhớ vĩnh viễn (SSD) chậm hơn RAM ≥ 100 lần |
| NFR2 | Thông lượng ticker | 671 ticker/giây | CPU Flink và băng thông Kafka có hạn trên 8 vCPU |
| NFR3 | Khả dụng hệ thống | 99.9% (≤ 8.76 giờ downtime/năm) | Replica và HA → tăng gấp đôi chi phí (NFR7) |
| NFR4 | Toàn vẹn dữ liệu | Không mất message khi mất 1 node | Kafka RF=3 và minISR=2 → latency +10-20ms |
| NFR5 | Khả năng mở rộng | Scale ngang (thêm symbol/exchange) | Kiến trúc microservices → độ phức tạp vận hành tăng |
| NFR6 | Lưu trữ dài hạn | Dữ liệu lịch sử vô thời hạn | Lakehouse lạnh → query chậm hơn 100 lần so với RAM |
| NFR7 | Chi phí vận hành (production) | < 300 USD/tháng (c5.2xlarge spot) | Hạn chế số replica, không dùng Kubernetes (EKS ~73 USD/tháng) |

Hai mâu thuẫn cốt lõi giữa các yêu cầu:

- **NFR1 vs NFR6 (độ trễ thấp vs lưu trữ dài hạn):** nếu ưu tiên độ trễ, mọi dữ liệu lưu trong Redis và mất khi mất điện; nếu ưu tiên lưu trữ, mọi ghi nhận đồng bộ xuống MinIO gây độ trễ vài trăm mili-giây. Kiến trúc Lambda (Marz & Warren, 2015) giải quyết bằng hai luồng song song: luồng tốc độ cao (Redis) dùng RAM cho truy xuất nhanh, luồng batch (Iceberg/MinIO) dùng ổ cứng cho lưu trữ lâu dài, với cơ chế đối chiếu định kỳ.
- **NFR3 vs NFR7 (khả dụng cao vs chi phí thấp):** để đạt 99.9% availability với chi phí < 300 USD/tháng production, LMView không thể triển khai giải pháp HA đắt tiền như Kubernetes multi-AZ (EKS ~73 USD/tháng) hay PostgreSQL streaming replica (cần thêm 1 node). Hệ thống tập trung HA vào thành phần quan trọng nhất (Kafka, Redis) bằng cách tận dụng ba node đã có, chấp nhận single point of failure cho thành phần ít quan trọng hơn (PostgreSQL, MinIO, InfluxDB). Môi trường staging có thể giảm xuống < 50 USD/tháng bằng t3.medium spot.

## 2.2. Kiến trúc dữ liệu

Mục này trình bày kiến trúc dữ liệu tổng thể của LMView, từ Lambda ba tầng, kiến trúc phân tầng lưu trữ, đến phân tích các lựa chọn kiến trúc và so sánh với phương án thay thế.

### 2.2.1. Kiến trúc tổng thể — Lambda ba tầng

Mô hình kiến trúc tổng thể của LMView kế thừa nguyên lý cốt lõi của kiến trúc Lambda được đề xuất bởi Marz và Warren (2015) và được Kiran và cộng sự (2015) phân tích định lượng cho các hệ thống big data chi phí thấp. Theo Kiran và cộng sự (2015), kiến trúc Lambda cho phép tách biệt Speed Layer và Batch Layer nhằm giải quyết mâu thuẫn kinh điển giữa độ trễ xử lý và dung lượng lưu trữ — vấn đề cốt yếu trong hệ thống xử lý dữ liệu thời gian thực quy mô lớn. Đối với đặc thù biến động cao của thị trường tiền điện tử, việc thiết kế hệ thống tuân theo mô hình phân tầng luồng dữ liệu song song cho phép dung hòa ba ràng buộc của Định lý CAP (Gilbert & Lynch, 2002): hệ thống ưu tiên Tính khả dụng (Availability) và Tính chịu vách ngăn mạng (Partition Tolerance) ở tầng lưu trữ lạnh (Iceberg/MinIO), trong khi chấp nhận Tính nhất quán nhất thời (Eventual Consistency) ở tầng tốc độ (Redis) để đảm bảo độ trễ dưới 500ms.

Ba tầng của kiến trúc Lambda trong LMView:

- **Tầng tốc độ (Speed Layer):** áp dụng mô hình xử lý tính toán có trạng thái (Stateful Stream Processing) giúp tính toán các chỉ báo kỹ thuật liên tục trên luồng dữ liệu vô hạn mà không cấu trúc lại toàn bộ cơ sở dữ liệu (Carbone et al., 2015). Dữ liệu ticker từ Binance WebSocket được thu thập bởi binance-ticker-ws (Node 1) với tám shard kết nối song song, parse thành 24 field Redis và ghi trực tiếp vào Redis Master (Node 2) thông qua buffer 50ms. Song song, dữ liệu nến 1s từ Binance REST được thu thập bởi binance-kline-rest (Node 1), Avro-serialize và publish vào Kafka với replication factor 3. Flink (Node 2 và Node 3) đọc Kafka, thực hiện aggregation nến 1s→1m bằng cơ chế watermark xử lý sự kiện đến trễ, tính toán chỉ báo kỹ thuật incremental (EMA, RSI, MACD) thông qua cửa sổ trượt, và ghi kết quả vào Redis cùng InfluxDB.

- **Tầng batch (Batch Layer):** sử dụng Apache Spark với mô hình RDD (Resilient Distributed Datasets) do Zaharia và cộng sự (2012) đề xuất, cho phép tái tính toán dữ liệu lịch sử trên bộ nhớ RAM hiệu năng cao với cơ chế chịu lỗi dựa trên lineage. Spark Structured Streaming (Node 2 và Node 3) đọc dữ liệu từ Kafka và ghi vào Iceberg Bronze (dữ liệu thô). Job Spark bronze-to-silver (chạy định kỳ mỗi giờ) thực hiện làm sạch dữ liệu: loại bỏ trùng lặp dựa trên key (exchange, symbol, event_time), chuẩn hóa kiểu dữ liệu, ghi vào Iceberg Silver. Job Spark silver-to-gold tổng hợp dữ liệu từ Silver thành các bảng Gold (market_overview, top_gainers_losers) sẵn sàng cho truy vấn.

- **Tầng phục vụ (Serving Layer):** đóng vai trò cầu nối giữa dữ liệu và người dùng, thực hiện cơ chế đối chiếu (reconciliation) giữa kết quả tạm thời từ Speed Layer và kết quả chính xác từ Batch Layer — thách thức đã được Marz và Warren (2015) xác định là điểm yếu cốt hữu của kiến trúc Lambda. FastAPI (Node 1) cung cấp REST API và WebSocket, đọc dữ liệu theo thứ tự ưu tiên độ trễ: Redis (hot, 1ms) → InfluxDB (warm, 10-50ms) → Trino/Iceberg (cold, 50-500ms). Cơ chế đối chiếu dữ liệu tại biên thời gian đảm bảo tính nhất quán: nến từ luồng thời gian thực được thay thế bằng nến từ luồng streaming khi nến đã đóng và có chỉ báo kỹ thuật.

Hình 2.1 dưới đây minh họa kiến trúc tổng thể với ba tầng xử lý và ba node vật lý:

```
Hình 2.1. Kiến trúc Lambda ba tầng trên Docker Swarm ba node

                                  ┌─────────────────────┐
                                  │  Binance WSS + REST │
                                  │  671 USDT pairs     │
                                  │  8 shards @ticker   │
                                  └──────────┬──────────┘
                                             │ WS 1Hz + REST 30s
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  NODE 1 (Manager - role=api)      8vCPU / 32GB / EFS / Docker Registry    │
│                                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────┐  ┌──────────────┐  │
│  │   INGESTION SERVICES     │  │   SERVING LAYER      │  │   STORAGE    │  │
│  │  binance-ticker-ws       │  │  FastAPI REST+WS     │  │  PostgreSQL  │  │
│  │  (8 shards → Redis)      │  │  /api/klines, /stream│  │  InfluxDB   │  │
│  │  binance-kline-rest      │  │  Auth, AI, Admin     │  │  MinIO      │  │
│  │  (Avro → Kafka)          │  │  WebSocket 50ms push │  │  Kafka-1    │  │
│  │  binance-depth-rest      │  │  Reconciliation      │  │  Sentinel-1 │  │
│  │  (REST → Redis)          │  │                      │  │  Nginx :443 │  │
│  └──────────────────────────┘  └──────────────────────┘  └──────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
         │                          │
         │ Kafka RF=3              │ Kafka RF=3
         ▼                          ▼
┌──────────────────────────┐ ┌──────────────────────────┐
│ NODE 2 (Worker - data)   │ │ NODE 3 (Worker - compute)│
│ 8vCPU / 32GB             │ │ 8vCPU / 32GB             │
│ ┌────────────────────┐   │ │ ┌────────────────────┐   │
│ │ SPEED LAYER        │   │ │ │ SPEED LAYER        │   │
│ │ Zookeeper          │   │ │ │ Kafka-3            │   │
│ │ Kafka-2            │   │ │ │ Flink TaskManager 2│   │
│ │ Schema Registry    │   │ │ │ Redis REPLICA      │   │
│ │ Redis MASTER       │   │ │ │ Spark Worker 2     │   │
│ │ Flink JobManager   │   │ │ │ Trino :8083        │   │
│ │ Flink TaskManager 1│   │ │ │ Sentinel-3         │   │
│ │ Spark Master       │   │ │ │                    │   │
│ │ Spark Worker 1     │   │ │ │ BATCH LAYER        │   │
│ │ Sentinel-2         │   │ │ │ Iceberg via Trino  │   │
│ │ BATCH LAYER        │   │ │ │ Spark Silver/Gold  │   │
│ │ Spark Bronze       │   │ │ │ Loki + Promtail    │   │
│ └────────────────────┘   │ │ └────────────────────┘   │
└──────────────────────────┘ └──────────────────────────┘
```

### 2.2.2. Kiến trúc theo lớp (Layer Architecture)

Bên cạnh kiến trúc ba tầng dọc theo thời gian xử lý (Lambda), hệ thống được tổ chức thành bốn lớp ngang theo chức năng, mỗi lớp có vai trò và ranh giới rõ ràng:

- **Lớp thu thập dữ liệu (Ingestion Layer):** kết nối với Binance và thu thập ba luồng dữ liệu chính.
  - binance-ticker-ws: duy trì tám kết nối WebSocket song song, mỗi kết nối quản lý ~84 symbol. Cơ chế tám shard vượt qua giới hạn Binance (tối đa 200 stream/kết nối) và tăng khả năng chịu lỗi (một shard mất, bảy còn lại vẫn hoạt động).
  - binance-kline-rest: poll REST API `/api/v3/klines` mỗi 30 giây lấy nến 1 giây đã đóng, Avro-serialize và publish lên Kafka.
  - binance-depth-trades-rest: poll REST API `/api/v3/depth` và `/api/v3/aggTrades` cho top 30 symbol, ghi trực tiếp vào Redis.

- **Lớp xử lý (Processing Layer):** nhận dữ liệu từ lớp thu thập và thực hiện các biến đổi phức tạp.
  - Kafka cluster ba broker với 12 partition/topic và RF=3 cung cấp khả năng lưu trữ và phát lại luồng sự kiện.
  - Flink cluster (JobManager + hai TaskManager) thực hiện streaming (aggregation nến, chỉ báo) với độ trễ 100-500ms.
  - Spark cluster (Master + hai Worker) thực hiện batch (bronze-to-silver-to-gold) trên Iceberg.

- **Lớp lưu trữ (Storage Layer):** bốn hệ thống lưu trữ với đặc điểm hiệu năng khác nhau.
  - Redis Sentinel (Master N2, Replica N3): truy xuất dưới 1ms cho dữ liệu thời gian thực.
  - InfluxDB (N1): nến 90 ngày, truy vấn 10-50ms.
  - MinIO (N1): Iceberg vô thời hạn, truy vấn qua Trino 50-500ms.
  - PostgreSQL (N1): dữ liệu quan hệ, ~500MB, hỗ trợ pgvector.

- **Lớp phục vụ (Serving Layer):** gồm FastAPI và Nginx.
  - FastAPI cung cấp 18 API router (REST + WebSocket), cơ chế đọc dữ liệu ưu tiên theo độ trễ.
  - Nginx reverse proxy, TLS termination (Let's Encrypt), rate limiting, HSTS, gzip, serve static files.

### 2.2.3. Phân tích chi tiết tầng phục vụ (Serving Layer) và kiến trúc API

Tầng phục vụ là nơi hội tụ của mọi luồng dữ liệu, đóng vai trò trung gian giữa dữ liệu đã xử lý (từ speed layer và batch layer) và người dùng cuối. FastAPI với kiến trúc ASGI (Asynchronous Server Gateway Interface) cho phép xử lý hàng nghìn kết nối WebSocket đồng thời mà không bị block bởi I/O. Bốn worker Uvicorn (gunicorn với workers=4, worker_class=uvicorn.workers.UvicornWorker) cung cấp khả năng xử lý song song trên bốn CPU core, mỗi worker độc lập về event loop và connection pool.

Kiến trúc API gồm 18 router, mỗi router nhóm các endpoint liên quan:

- **klines:** `GET /api/klines` (dữ liệu nến lịch sử + real-time), `GET /api/klines/latest` (nến mới nhất).
- **ticker:** `GET /api/ticker/{symbol}` (ticker một symbol), `GET /api/ticker/all` (671 symbol).
- **orderbook:** `GET /api/orderbook/{symbol}` với tham số depth (mặc định 50).
- **trades:** `GET /api/trades/{symbol}` (recent trades), `GET /api/trades/summary/{symbol}` (thống kê).
- **ai:** `chat`, `snapshot`, `history`, `knowledge`, `feedback`.
- **auth:** `login`, `register`, `refresh token`, `logout`.
- **admin:** `user management`, `health check`, `system status`.
- **settings:** `user preferences`, `display settings`.

Mỗi router gọi service layer tương ứng thông qua dependency injection pattern. Router không chứa business logic — chỉ parse request parameters, gọi service, format response. Service layer (backend/services/) chứa toàn bộ business logic: CandleService, TickerService, OrderBookService, TradeService, AIService, AuthService, SettingsService. Mỗi service sử dụng repository pattern để truy cập dữ liệu — CandleService đọc từ RedisRepository, InfluxDBRepository, hoặc TrinoRepository tùy fallback chain. Repository layer (backend/core/) quản lý kết nối và query đến từng storage backend: Redis Sentinel, InfluxDB, PostgreSQL (asyncpg), Trino (trino dbapi). Dependency injection thông qua FastAPI Depends() — `CandleService` inject qua `async def get_candle_service(request: Request)`, mỗi request nhận instance service mới.

### 2.2.4. Phân tích chiến lược Kafka partition và consumer group

Chiến lược partition trong Kafka đóng vai trò then chốt trong đảm bảo hiệu năng và khả năng mở rộng. LMView sử dụng 12 partition cho mỗi topic chính (crypto_ticker, crypto_klines), tương ứng với số core CPU khả dụng trên hai Flink TaskManager (mỗi TM có 6 slots, tổng 12 slots). Số partition được chọn dựa trên quy tắc thực nghiệm: số partition ≤ số consumer thread × số core mỗi thread.

Key partition strategy sử dụng hash của (exchange:symbol) để đảm mọi message của cùng symbol đi vào cùng partition, do đó được xử lý bởi cùng Flink task. Điều này rất quan trọng cho stateful processing: Flink task cần duy trì sliding window (20-26 phiên) cho SMA/EMA/RSI/MACD, nếu message cùng symbol bị phân tán sang nhiều task, state sẽ bị phân mảnh và kết quả chỉ báo sai. Công thức hash: `partition = abs(hash(key)) % num_partitions` với key = "binance:BTCUSDT".

Cơ chế consumer rebalancing và offset management. Khi Flink TaskManager gặp sự cố, Kafka group coordinator phát hiện mất heartbeat sau session.timeout.ms=30s và trigger rebalance. Trong quá trình rebalance, tất cả consumer tạm dừng, partition được reassign, consumer tiếp tục đọc từ offset cuối cùng đã commit. Thời gian rebalance ~5-15 giây. LMView cấu hình Flink với partition.assignment.strategy=CooperativeStickyAssignor thay vì range assignor mặc định — Cooperative Sticky giảm số lần rebalance (chỉ reassign partition bị ảnh hưởng) và giảm "stop-the-world" từ 15 giây xuống 2-5 giây.

Offset commit strategy: LMView sử dụng checkpoint-based commit (enable.auto.commit=false). Mỗi 30 giây, Flink checkpoint barrier đánh dấu trạng thái xử lý, offset commit lên Kafka khi checkpoint hoàn tất. Nếu Flink crash trước checkpoint, offset chưa commit, consumer đọc lại từ offset cũ (reprocessing). Cơ chế đảm bảo exactly-once semantics: mỗi message được xử lý đúng một lần. Lưu ý: reprocessing gây duplicate write Redis/InfluxDB, được giải quyết bằng idempotent write (ZREMRANGEBYSCORE trước ZADD cho candle, UPSERT cho InfluxDB).

### 2.2.5. Phân tích chiến lược Flink state backend và checkpoint

Flink sử dụng RocksDB state backend (so với HashMap state backend) để lưu trạng thái xử lý streaming. RocksDB là key-value store embedded trong JVM (dựa trên LevelDB của Google), tối ưu cho lưu trữ trên ổ cứng với khả năng spill-to-disk khi memory đầy. Lựa chọn RocksDB dựa trên hai yếu tố:

- **Dung lượng state:** mỗi task quản lý state cho ~56 symbol (671/12) × 26 phiên (cửa sổ SMA/EMA) × 4 field OHLC = ~5,824 giá trị. Với HashMap, toàn bộ state (~50MB) phải nằm trong heap (1.5GB), không scale được khi số symbol tăng. Với RocksDB, state lưu trên SSD và chỉ cache hot data trong block cache (128MB).
- **Checkpoint:** RocksDB hỗ trợ incremental checkpoint (chỉ ghi diff từ checkpoint trước) thay vì full snapshot, giảm thời gian checkpoint từ ~10s xuống ~2s.

Checkpoint strategy sử dụng interval=30s với exactly-once semantics. Checkpoint lưu trên MinIO (bucket flink-checkpoints/) với đường dẫn s3://flink-checkpoints/cryptoprice-kline-job/. Khi Flink JobManager restart, đọc checkpoint cuối cùng và yêu cầu TaskManager khôi phục state. Nếu checkpoint quá cũ (5 phút trước), Flink phải đọc lại 5 phút dữ liệu Kafka để bắt kịp real-time — lý do checkpoint interval không nên quá dài (> 5 phút). Ngược lại, nếu checkpoint quá thường xuyên (< 10 giây), overhead I/O cho RocksDB checkpoint có thể ảnh hưởng latency xử lý.

### 2.2.6. Chiến lược Redis persistence và backup

Mặc dù Redis được sử dụng chủ yếu như hot cache (dữ liệu có thể tái tạo từ Kafka/InfluxDB nếu mất), việc cấu hình persistence cho Redis Master là cần thiết để tránh mất dữ liệu ticker và candle khi Redis restart. LMView sử dụng Redis AOF (Append-Only File) persistence với policy `appendfsync everysec` — ghi log mỗi giây một lần, cân bằng giữa durability (mất tối đa 1 giây dữ liệu nếu crash) và performance. RDB snapshot (save 900 1, save 300 10) được bật làm backup phụ. AOF file và RDB snapshot lưu trong volume redis_data, mount từ EBS volume. Khi Redis Master trên Node 2 mất, Redis Replica trên Node 3 có AOF và RDB riêng, sẵn sàng được promote lên Master mới bởi Sentinel mà không mất dữ liệu.

Backup strategy: Redis AOF và RDB backup tự động mỗi 24 giờ qua cron job (`docker exec redis-master redis-cli --rdb /backup/redis-$(date +%Y%m%d).rdb`). Backup lưu trên EFS (/mnt/efs/LMView/backups/redis/). Retention: 7 ngày (local, EBS) và 30 ngày (EFS). Trong disaster recovery, Redis có thể restore từ RDB file bằng lệnh: `docker exec -i redis-master redis-cli --pipe < /backup/redis-20260621.rdb` (mất ~5-10 giây cho 200MB dữ liệu). Lưu ý: restore từ RDB sẽ mất dữ liệu giữa lần snapshot cuối và thời điểm crash, nhưng dữ liệu này có thể tái tạo từ Kafka (24-48 giờ) và InfluxDB (90 ngày).

### 2.2.7. Phân tích chiến lược Redis key design và memory optimization

Redis key design đóng vai trò quan trọng trong hiệu năng truy xuất dữ liệu thời gian thực. LMView sử dụng năm loại key chính với cấu trúc được tối ưu cho từng use case:

- **Ticker data:** key `ticker:latest:{exchange}:{symbol}` (ví dụ ticker:latest:binance:BTCUSDT) lưu toàn bộ 24 field ticker trong một Redis Hash (HSET). Hash giảm số lượng network round-trip: một lệnh HGETALL trả về tất cả 24 field, trong khi key-value riêng lẻ cần 24 lệnh GET. Memory overhead: Hash tiết kiệm ~40% memory so với String riêng lẻ.
- **Candle data:** key `candle:1m:{exchange}:{symbol}` lưu trong Redis Sorted Set (ZADD) với score là timestamp (epoch milliseconds) và member là JSON string chứa OHLCV. Sorted Set cho phép truy vấn range (ZRANGEBYSCORE) với độ phức tạp O(log n), lý tưởng cho "lấy 200 nến gần nhất". Không đặt TTL. Tổng memory cho candle keys: 671 symbol × 200 nến × ~108 bytes ≈ 14.5 MB.
- **Order book data:** key `orderbook:{exchange}:{symbol}` lưu Hash với 100 field (50 bids + 50 asks), mỗi field name "b:{price}" hoặc "a:{price}" và field value là quantity. Hash cho phép cập nhật từng field riêng lẻ (HSET) khi giá thay đổi, thay vì ghi lại toàn bộ snapshot.
- **Trade data:** key `trade:latest:{exchange}:{symbol}` lưu List (RPUSH + LTRIM) với tối đa 200 giao dịch gần nhất, mỗi phần tử JSON string ~150 bytes.

### 2.2.8. Cơ chế xử lý lỗi và đảm bảo chất lượng dữ liệu trong streaming pipeline

Pipeline streaming của LMView phải xử lý nhiều loại lỗi khác nhau. Bốn loại lỗi chính được xác định và có cơ chế xử lý riêng:

- **Lỗi dữ liệu (data error):** Binance đôi khi gửi dữ liệu không hợp lệ (null field, NaN price, timestamp quá khứ). Xử lý: mỗi producer thực hiện validation ngay sau parse — kiểm tra price > 0, volume >= 0, timestamp trong vòng 5 phút so với server time. Dữ liệu không hợp lệ ghi vào Kafka topic riêng (crypto_errors) với nguyên nhân lỗi, không làm gián đoạn pipeline chính.
- **Lỗi kết nối (connection error):** Binance WebSocket đột ngột đóng kết nối. Xử lý: auto-reconnect với exponential backoff (1s → 30s), tối đa 10 lần. Sau 10 lần thất bại, service log fatal và chờ can thiệp thủ công.
- **Lỗi schema (schema error):** Avro schema thay đổi mà consumer chưa kịp cập nhật. Xử lý: Schema Registry với schema evolution policy (FORWARD: chỉ cho phép thêm field, không cho phép xóa). Consumer tự động fetch schema mới từ Schema Registry khi phát hiện schema ID mới.
- **Lỗi backpressure (backpressure error):** Flink xử lý chậm hơn tốc độ Kafka produce, dẫn đến consumer lag tăng. Xử lý: Flink tự động áp dụng backpressure (dựa trên network buffer utilization) và checkpoint barrier stall. Nếu backpressure kéo dài > 5 phút, cần tăng parallelism (hiện 12, có thể tăng lên 24).

Chất lượng dữ liệu được đảm bảo thông qua ba cơ chế:

- **Exactly-once semantics cho Flink sink:** mỗi bản ghi chỉ được ghi vào Redis/InfluxDB đúng một lần nhờ Kafka transaction và two-phase commit protocol.
- **Idempotent write cho Redis Sorted Set:** trước khi ZADD member mới (candle OHLCV), Flink xóa member cũ có cùng score (timestamp) bằng ZREMRANGEBYSCORE.
- **Periodic data quality check:** Spark job chạy mỗi 6 giờ kiểm tra dữ liệu Iceberg — số lượng record, null rate, outlier detection (giá thay đổi > 50% trong 1 phút), ghi report vào PostgreSQL.

## 2.3. Kiến trúc AI

Mục này trình bày kiến trúc AI Service — một trong những thành phần phức tạp nhất của hệ thống, với kiến trúc multi-layer gồm năm tầng xử lý tuần tự, cùng pipeline RAG chi tiết (chunking, embedding, indexing).

### 2.3.1. Kiến trúc tổng thể AI Service

AI Service gồm năm tầng xử lý tuần tự:

- **Tầng Scope Gate** (backend/services/ai/scope_gate.py) kiểm tra câu hỏi đầu vào có thuộc phạm vi thị trường tiền điện tử không, sử dụng classification model nhẹ (Logistic Regression trên TF-IDF features) với ngưỡng confidence 0.7. Nếu câu hỏi nằm ngoài phạm vi (ví dụ "cách nấu phở", "dự đoán số đề"), scope gate từ chối ngay với message "Xin lỗi, tôi chỉ có thể trả lời các câu hỏi về thị trường tiền điện tử". Cơ chế này đảm bảo AI không bị lạm dụng cho mục đích ngoài phạm vi.

- **Tầng Prompt Builder** (backend/services/ai/prompt_builder.py) xây dựng prompt hoàn chỉnh bằng cách kết hợp ba nguồn thông tin:
  - Ngữ cảnh thị trường thời gian thực: giá hiện tại, RSI 14, MACD, Bollinger Bands, volume 24h, tin tức gần nhất từ knowledge base.
  - Lịch sử hội thoại của phiên hiện tại (tối đa 10 turns gần nhất).
  - System prompt định nghĩa vai trò AI như "chuyên gia phân tích kỹ thuật tiền điện tử".

  Prompt template có cấu trúc JSON: `{"system": "...", "context": {market data}, "history": [...], "query": "..."}`. Cấu trúc hóa prompt thay vì free-form text giúp LLM xử lý chính xác hơn.

- **Tầng RAG Retrieval** (backend/services/ai/rag.py) truy vấn pgvector với HNSW index để tìm top-5 knowledge chunks có cosine similarity > 0.7. Knowledge chunks nhúng bằng mô hình all-MiniLM-L6-v2 (384 chiều) và lưu trong PostgreSQL với HNSW index (m=16, ef_construction=200). Cấu trúc bảng ai_knowledge: id, title, content, source_url, embedding vector(384), created_at, updated_at. Vector search query: `SELECT id, content, 1 - (embedding <=> $query_embedding) AS similarity FROM ai_knowledge WHERE 1 - (embedding <=> $query_embedding) > 0.7 ORDER BY similarity DESC LIMIT 5`. Index HNSW: `CREATE INDEX ON ai_knowledge USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200)`.

- **Tầng Provider Router** (backend/services/ai/provider_router.py) lựa chọn LLM provider dựa trên cấu hình và độ phức tạp câu hỏi. Hệ thống hiện có hai provider:
  - **Mock provider:** template-based response, không gọi network, dùng cho phát triển và demo.
  - **Litellm provider:** gọi đến LiteLLM gateway có thể route đến OpenAI, Anthropic, hoặc local model, dùng cho production.
  
  Provider router kiểm tra biến môi trường AI_MODE — nếu "mock", dùng mock provider; nếu không, dùng litellm provider.

- **Tầng Output Guard** (backend/services/ai/output_guard.py) kiểm tra output từ LLM trước khi gửi về client. Output guard sử dụng regex pattern để phát hiện nội dung nhạy cảm (số điện thoại, địa chỉ, thông tin cá nhân) và lời khuyên tài chính cụ thể ("mua BTC ngay", "bán hết ETH"). Nếu phát hiện vi phạm, output guard thêm disclaimer "Đây không phải lời khuyên tài chính. Vui lòng tự nghiên cứu trước khi đưa ra quyết định đầu tư."

### 2.3.2. Phân tích chi tiết RAG pipeline: chunking, embedding, indexing

Pipeline RAG gồm bốn giai đoạn xử lý tuần tự, từ dữ liệu thô đến câu trả lời cuối cùng.

**Giai đoạn 1 — Knowledge ingestion (nạp dữ liệu tri thức):** diễn ra không đồng bộ với luồng chat. Dữ liệu tri thức thu thập từ ba nguồn chính:

- Tài liệu API và documentation của Binance (từ Binance API Docs).
- Bài viết phân tích kỹ thuật từ CoinDesk và CoinTelegraph (dạng RSS feed).
- Dữ liệu về các cặp giao dịch (symbol metadata) từ Binance Exchange Info API.

Mỗi nguồn có adapter riêng: BinanceDocsAdapter parse HTML và extract section content, RSSFeedAdapter parse XML feed và download full article content, ExchangeInfoAdapter parse JSON response từ API và tạo structured metadata.

**Giai đoạn 2 — Chunking (phân đoạn dữ liệu):** dữ liệu thô chia thành các chunk nhỏ phù hợp cho embedding và retrieval. Chiến lược chunking sử dụng recursive character text splitter với chunk_size=512 tokens, chunk_overlap=128 tokens (25% overlap). Văn bản chia theo cấu trúc phân cấp: trước tiên theo section headers (##, ###), sau đó theo paragraph, cuối cùng theo câu. Overlap 128 tokens giữa các chunk liền kề đảm bảo không mất ngữ cảnh quan trọng ở biên. Metadata mỗi chunk: source_url, chunk_index, chunk_count, title, created_at.

**Giai đoạn 3 — Embedding (tạo vector nhúng):** mỗi chunk chuyển thành vector 384 chiều bằng mô hình all-MiniLM-L6-v2. Lý do chọn mô hình này:

- Kích thước 384 chiều đủ cho use case phân tích kỹ thuật với lượng tri thức ~500 chunks (tỷ lệ 500:384 = 1.3, không gây overfitting).
- Tốc độ embedding nhanh trên CPU (~50 chunks/giây trên c5.2xlarge) cho phép embedding toàn bộ knowledge base (~500 chunks) trong 10 giây.
- Triển khai local không cần API key, phù hợp với kiến trúc offline-first.

Quy trình embedding trong backend service (backend/services/ai/embedding_service.py) với batch size=32 và auto-detect device (CPU nếu không có GPU). Chi phí embedding: ~500 chunks × 384 floats × 4 bytes = ~768KB cho toàn bộ knowledge base.

**Giai đoạn 4 — Indexing (xây dựng chỉ mục vector):** vector lưu vào PostgreSQL với pgvector extension. HNSW index với m=16 và ef_construction=200. So với IVFFlat, HNSW cho recall cao hơn (99% vs 95% ở top-10) với chi phí memory tương tự (~1.5x kích thước vector gốc). Thời gian xây dựng HNSW index cho 500 vectors: ~0.1 giây. Query time cho top-5 với HNSW: ~2ms (so với ~50ms của full scan).

Khi người dùng gửi câu hỏi, quy trình retrieval: câu hỏi được embedding bằng cùng mô hình all-MiniLM-L6-v2, tạo query vector 384 chiều. Vector search: `SELECT id, content, source_url, chunk_index, 1 - (embedding <=> $query_vec) AS similarity FROM ai_knowledge WHERE 1 - (embedding <=> $query_vec) > 0.7 ORDER BY similarity DESC LIMIT 5`. Cosine similarity threshold 0.7 được chọn dựa trên thực nghiệm: threshold thấp hơn (0.5) trả về nhiều kết quả không liên quan (precision giảm), threshold cao hơn (0.85) trả về quá ít kết quả (recall giảm). Top-5 kết quả được kết hợp vào prompt thông qua Prompt Builder, mỗi chunk format dưới dạng: `{"source": "CoinDesk", "title": "Bitcoin Halving 2024", "content": "..."}`.

## 2.4. Phân tích và thiết kế hệ thống

Mục này trình bày phân tích chi tiết các luồng dữ liệu, cơ chế đối chiếu, các kịch bản sử dụng chính, use case, công nghệ áp dụng, và so sánh với các nghiên cứu liên quan.

### 2.4.1. Các luồng dữ liệu và cơ chế đối chiếu

LMView vận hành với ba luồng dữ liệu chính, mỗi luồng có đặc điểm về độ trễ và mục đích sử dụng khác nhau.

```
Hình 2.2. Ba luồng dữ liệu chính và cơ chế đối chiếu tại tầng phục vụ

LUỒNG THỜI GIAN THỰC (REAL-TIME PATH) — Độ trễ: 100-500ms
┌──────────┐    ┌─────────────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────────┐
│ Binance  │───►│ binance-ticker- │───►│  Redis       │───►│ FastAPI  │───►│ Browser WS   │
│ WSS      │    │ ws (N1)         │    │  Master (N2) │    │ (N1)     │    │ 50ms poll    │
│ @ticker  │    │ 8 shards × 84s  │    │  HSET 24     │    │ WS push  │    │ lightweight  │
│ 1Hz/sym  │    │ parse + buffer  │    │  fields/sym  │    │ 50ms     │    │ -charts      │
└──────────┘    │ 50ms/2000 items │    │  TTL 300s    │    │ loop     │    └──────────────┘
                └─────────────────┘    └──────────────┘    └──────────┘
    Điểm mạnh: Độ trễ cực thấy (p50 ~100ms), không phụ thuộc Kafka/Flink
    Sử dụng cho: Giá ticker, cập nhật nến real-time

LUỒNG STREAMING (STREAMING PATH) — Độ trễ: 500ms-5s
┌──────────┐    ┌──────────────────┐    ┌──────────┐    ┌──────────────────┐    ┌──────────────┐
│ Binance  │───►│ binance-kline    │───►│  Kafka   │───►│  Flink (N2,N3)  │───►│  Redis       │
│ REST     │    │ -rest (N1)       │    │  3 nodes │    │  KeyedProcessFn │    │  Master (N2) │
│ /klines  │    │ poll 30s        │    │ RF=3     │    │  1s→1m agg      │    │  candles +   │
│ 1s đóng  │    │ Avro serialize   │    │ 12 part  │    │  indicator calc │    │  indicators  │
└──────────┘    └──────────────────┘    └──────────┘    │  batch flush    │    └──────┬───────┘
                                                         │  500ms          │           │
                                                         └──────────────────┘    ┌──────▼───────┐
                                                                                 │  InfluxDB    │
                                                                                 │  (N1)        │
                                                                                 │  90 days     │
                                                                                 └──────────────┘
    Điểm mạnh: Chỉ báo kỹ thuật chính xác, persistence qua Kafka
    Sử dụng cho: Nến 1m+ đã đóng, chỉ báo (SMA/EMA/RSI/MACD/Bollinger)

LUỒNG BATCH (BATCH PATH) — Độ trễ: phút-giờ
┌──────────┐    ┌──────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Kafka   │───►│  Spark   │───►│  Iceberg Bronze  │───►│  Iceberg Silver  │───►│  Iceberg Gold    │
│  (N1-N3) │    │ (N2,N3)  │    │  (MinIO N1)      │    │  (MinIO N1)      │    │  (MinIO N1)      │
│  48h ret │    │ 2 worker │    │ raw Kafka data   │    │ cleaned + dedup  │    │ aggregated view  │
│  replay  │    │ 2GB heap │    │ BINARY format    │    │ DECIMAL(20,8)    │    │ for API queries  │
└──────────┘    └──────────┘    │ replay-capable   │    │ UTC normalized   │    └────────┬─────────┘
                                └──────────────────┘    └──────────────────┘             │
                                                                                   ┌──────▼──────────┐
                                                                                   │  Trino (N3)     │
                                                                                   │  SQL via JDBC   │
                                                                                   │  market_overview│
                                                                                   │  top_gainers    │
                                                                                   │  news_feed      │
                                                                                   └────────┬─────────┘
                                                                                            │
                                                                                   ┌────────▼─────────┐
                                                                                   │  FastAPI (N1)    │
                                                                                   │  /api/market/*   │
                                                                                   └──────────────────┘
    Điểm mạnh: Dữ liệu lịch sử vô hạn, có thể tính toán lại
    Sử dụng cho: Tổng quan thị trường, tin tức, dữ liệu >90 ngày

CƠ CHẾ ĐỐI CHIẾU (RECONCILIATION) TẠI TẦNG PHỤC VỤ:

Tại biên thời gian T_boundary (ví dụ: đầu mỗi phút mới):
  - Nến forming từ Real-time Path ──► được thay bằng nến đã đóng từ Streaming Path
  - Chỉ báo từ Streaming Path ──► được ghép vào nến đã đóng
  - Nếu Streaming Path chưa kịp cập nhật ──► dùng tạm Real-time Path, retry sau 5s
  - Đảm bảo: Người dùng luôn thấy giá mới nhất (real-time) và chỉ báo chính xác (streaming)
```

Chi tiết từng luồng:

- **Luồng thời gian thực (Real-time Path):** thiết kế với độ trễ là ưu tiên hàng đầu. binance-ticker-ws sử dụng cơ chế buffer hai tầng: mỗi shard buffer riêng (100 items), và TickerRedisWriter gộp tất cả buffer và flush xuống Redis Master mỗi 50ms hoặc khi buffer đạt 2000 items. Cơ chế này giảm số lượng kết nối Redis từ 8 × 84 × 1Hz = 672 write/s xuống còn 20 flush/s, giảm tải đáng kể cho Redis. Độ trễ p50 ~100ms, bao gồm: thời gian mạng từ Binance (~50ms), xử lý parse (~10ms), buffer đợi (~25ms), ghi Redis (~1ms), push WebSocket (~15ms).

- **Luồng streaming (Streaming Path):** đảm bảo tính chính xác của chỉ báo kỹ thuật thông qua xử lý có trạng thái của Flink. Flink duy trì state backend (RocksDB) lưu trữ cửa sổ trượt 20-26 phiên cho tính toán SMA/EMA/RSI/MACD, và cửa sổ 1 phút cho aggregation nến. Khi watermark vượt biên thời gian, nến 1 phút được đóng, chỉ báo tính toán, kết quả ghi vào Redis và InfluxDB qua batch flush 500ms — đánh đổi giữa độ trễ (500ms) và số lượng write (giảm từ 12 write/s xuống 2 flush/s).

- **Cơ chế đối chiếu dữ liệu (reconciliation/stitching) tại tầng phục vụ:** đóng góp thiết kế quan trọng của LMView. Tại mỗi biên thời gian (T_boundary = đầu mỗi phút), FastAPI kiểm tra xem nến đã đóng từ Flink (Streaming Path) đã có trong Redis chưa. Nếu có, nến từ Real-time Path (chỉ có giá, không có chỉ báo) thay thế bằng nến từ Streaming Path (đã có chỉ báo đầy đủ). Nếu chưa (Flink đang chậm), FastAPI tạm thời dùng nến từ Real-time Path và lên lịch retry sau 5 giây. Cơ chế này đảm bảo người dùng luôn thấy giá mới nhất (từ Real-time Path) mà không mất thông tin chỉ báo kỹ thuật (vốn chỉ có trên Streaming Path).

### 2.4.2. Phân tích lựa chọn kiến trúc và so sánh với phương án thay thế

Việc lựa chọn kiến trúc Lambda không phải là quyết định hiển nhiên và cần biện minh thông qua so sánh có hệ thống với các phương án thay thế. Bốn phương án được xem xét:

- **Kiến trúc monolithic (nguyên khối):** tất cả logic xử lý từ thu thập dữ liệu đến phục vụ API nằm trong một ứng dụng duy nhất. Ưu điểm: đơn giản về vận hành và triển khai. Hạn chế: không thể scale khi khối lượng dữ liệu tăng. Với 21 tỷ sự kiện mỗi năm, monolithic nhanh chóng đạt giới hạn về bộ nhớ, CPU, và I/O. Hơn nữa, monolithic không cho phép scale riêng từng thành phần — nếu chỉ cần tăng throughput Flink, vẫn phải scale toàn bộ ứng dụng, gây lãng phí tài nguyên.

- **Kiến trúc microservices thuần túy:** mỗi service là ứng dụng độc lập giao tiếp qua network. Ưu điểm: scale riêng từng thành phần, công nghệ đa dạng. LMView áp dụng một phần (mỗi service là Docker container riêng). Hạn chế: chi phí vận hành cao (cần service mesh, API gateway, distributed tracing), độ phức tạp triển khai lớn, không phù hợp với ngân sách hạn chế.

- **Kiến trúc Kappa:** Kreps đề xuất như phiên bản đơn giản hóa của Lambda với chỉ một luồng xử lý streaming duy nhất (Kreps, 2011), loại bỏ tầng batch layer, chỉ dùng Kafka lưu trữ toàn bộ dữ liệu. Ưu điểm: chỉ cần duy trì một codebase xử lý, không gặp vấn đề đối chiếu giữa speed và batch layer. Hạn chế: yêu cầu rất lớn về khả năng lưu trữ Kafka — 21 tỷ sự kiện × 200 bytes = 4.2 TB mỗi năm, vượt xa ngân sách. Với RF=3, tổng cộng ~12.6 TB.

- **Kiến trúc Lambda (lựa chọn):** giải quyết hạn chế của cả ba phương án trên. So với monolithic, cho phép scale riêng speed layer và batch layer. So với microservices thuần túy, cung cấp cấu trúc tổ chức rõ ràng (ba tầng) giảm độ phức tạp thiết kế. So với Kappa, tách rời lưu trữ ngắn hạn (Kafka 48 giờ) và lưu trữ dài hạn (Iceberg/MinIO vô thời hạn), giảm chi phí từ 4.2 TB/năm (Kappa) xuống còn ~200 GB/năm Kafka và ~5.6 GB/năm Iceberg (đã nén Parquet).

Lựa chọn Docker Swarm thay vì Kubernetes dựa trên ba yếu tố định lượng:

- **Chi phí vận hành:** Swarm tích hợp sẵn trong Docker Engine (không mất phí), Amazon EKS có chi phí cố định 73 USD/tháng cho cluster control plane, chiếm ~25% tổng ngân sách production (~300 USD/tháng).
- **Độ phức tạp:** Swarm sử dụng cú pháp docker-compose.yml quen thuộc, Kubernetes yêu cầu học nhiều khái niệm mới (Pod, Deployment, Service, Ingress, ConfigMap, Secret, RBAC).
- **Quy mô:** với ba node và ~23 service, các tính năng nâng cao Kubernetes (auto-scaling, service mesh, canary deployment, custom resource definition) là không cần thiết. Swarm cung cấp đầy đủ auto-restart, rolling update, service discovery nội bộ, overlay network cho quy mô này.

### 2.4.3. So sánh LMView với các giải pháp thương mại hiện có

Để định vị LMView trong bối cảnh các nền tảng phân tích kỹ thuật hiện có, một so sánh có hệ thống với ba giải pháp phổ biến nhất (TradingView, CoinMarketCap, và Binance Chart) được thực hiện dựa trên bảy tiêu chí: độ trễ dữ liệu real-time, số lượng indicator, khả năng tùy biến, tích hợp AI, chi phí, mã nguồn mở, và khả năng đa sàn giao dịch.

- **TradingView:** nền tảng dẫn đầu với hơn 50 triệu người dùng. Độ trễ real-time ~1-2 giây (tùy gói), gói Pro (15 USD/tháng) và Premium (60 USD/tháng) cần cho dữ liệu thời gian thực. Hỗ trợ hơn 100 indicator và 10+ khung thời gian — vượt trội so với LMView (5 indicator, 9 khung thời gian). Tuy nhiên, TradingView là nền tảng mã nguồn đóng, không cho phép tùy biến backend hay tích hợp AI. LMView vượt trội ở hai khía cạnh: mã nguồn mở hoàn toàn và tích hợp AI (RAG pipeline với LLM).

- **CoinMarketCap và CoinGecko:** tập trung vào dữ liệu tổng hợp (market cap, volume, supply) hơn là phân tích kỹ thuật. CoinMarketCap API giới hạn 333 request/ngày (gói free) và 10,000 request/ngày (gói Starter, 79 USD/tháng). Cả hai không hỗ trợ WebSocket real-time, không có indicator kỹ thuật hay trợ lý AI. LMView vượt trội ở real-time (WebSocket 50ms push) và số lượng symbol (671 USDT pairs so với ~100 symbol của CoinMarketCap free API).

- **Binance Chart:** nền tảng tích hợp trong sàn Binance, cung cấp biểu đồ TradingView-compatible (cùng thư viện lightweight-charts). Dữ liệu độ trễ thấp (~100-200ms) và miễn phí. Hạn chế: chỉ hỗ trợ symbol Binance (không Coinbase, Kraken) và không có trợ lý AI. LMView bổ sung hai tính năng: tích hợp AI (RAG pipeline với market context) và kiến trúc mã nguồn mở có thể mở rộng.

LMView không cạnh tranh trực tiếp với TradingView về số lượng indicator hay độ tinh vi giao diện, mà tập trung vào ba điểm khác biệt chiến lược: mã nguồn mở, tích hợp AI, và chi phí vận hành thấp. Đây là phân khúc thị trường mà cả TradingView (đóng, đắt) và Binance Chart (đóng, không AI) đều không phục vụ.

### 2.4.4. Phân tích tính khả thi về mặt kỹ thuật và kinh tế

Phân tích tính khả thi (feasibility analysis) là bước quan trọng trong Design Science Research (Peffers et al., 2007), nhằm đánh giá liệu giải pháp đề xuất có thể triển khai được trong thực tế với các ràng buộc về kỹ thuật, tài nguyên, và chi phí.

**Về mặt kỹ thuật:** LMView sử dụng các công nghệ đã được kiểm chứng trong môi trường production quy mô lớn: Kafka xử lý hàng triệu message/giây tại LinkedIn, Flink xử lý streaming tại Alibaba (tảng lên tới 2 tỷ bản ghi/ngày), Spark xử lý batch tại Netflix và Uber, Docker Swarm quản lý container tại Docker Inc. Rủi ro kỹ thuật chính nằm ở việc tích hợp các công nghệ này trên hạ tầng 3 node với tài nguyên hạn chế (32 GB RAM mỗi node). Cụ thể, chạy Kafka (1GB heap), Flink (1.5GB heap), Spark (2GB heap), và Redis (2GB) đồng thời trên Node 2 và Node 3 có thể gây xung đột tài nguyên nếu không cấu hình memory limits chính xác. Biện pháp giảm thiểu: cấu hình memory limits trong docker-compose.yml và sử dụng cgroups.

**Về mặt kinh tế:** ba kịch bản chi phí được phân tích:

- **Kịch bản tiết kiệm (development/staging):** t3.medium (2 vCPU, 4 GB RAM) spot instances ~0.02 USD/giờ × 3 instances × 730 giờ = ~44 USD/tháng, cộng EFS (3 USD/tháng) = ~47 USD/tháng.
- **Kịch bản cân bằng (staging mở rộng):** c5.xlarge (4 vCPU, 8 GB RAM) spot ~0.06 USD/giờ × 3 × 730 = ~131 USD/tháng.
- **Kịch bản production:** c5.2xlarge (8 vCPU, 32 GB RAM) spot ~0.12 USD/giờ × 3 × 730 = ~263 USD/tháng.

So sánh với TradingView Pro (15 USD/người dùng/tháng) và CoinMarketCap API (79 USD/tháng cho 10,000 request/ngày), LMView có chi phí cạnh tranh cho môi trường team (3-5 người dùng) và vượt trội về khả năng tùy biến và tích hợp AI. Mục tiêu chi phí: < 50 USD/tháng cho staging (t3.medium spot) và < 300 USD/tháng cho production (c5.2xlarge spot).

Sử dụng Spot Instances cho phép giảm 60-70% chi phí EC2 so với On-Demand (0.12 USD/giờ so với 0.34 USD/giờ cho c5.2xlarge). Tuy nhiên, Spot Instances có thể bị thu hồi (terminate) bất kỳ lúc nào khi AWS cần lấy lại tài nguyên (Agmon Ben-Yehuda et al., 2014). Với xác suất thu hồi trung bình 5-10% mỗi tháng cho instance type c5.2xlarge tại us-east-1 (Agmon Ben-Yehuda et al., 2014), rủi ro này là nguyên nhân thiết kế kiến trúc chịu lỗi đa tầng (Mục 3.1.3).

**Về mặt nhân sự:** triển khai và vận hành LMView yêu cầu kiến thức về Docker (Swarm, Compose), Kafka (topic, partition, consumer group), Flink (streaming job, checkpoint, state backend), Spark (batch job, Iceberg, catalog), Python (FastAPI, async programming), React (TypeScript, hooks, lightweight-charts). Đây là stack kỹ thuật khá rộng, đòi hỏi ít nhất 2-3 kỹ sư có kinh nghiệm 2-3 năm trong data engineering và full-stack development. Tuy nhiên, kiến trúc module hóa (mỗi service là Docker container riêng) cho phép phân chia công việc theo chiều ngang: kỹ sư A phụ trách backend/data pipeline, kỹ sư B phụ trách frontend, kỹ sư C phụ trách infrastructure/deployment.

### 2.4.5. Kiến trúc ba node Docker Swarm

Docker Swarm được lựa chọn làm nền tảng orchestration cho LMView dựa trên ba lý do: tích hợp sẵn trong Docker Engine (không cần cài đặt thêm như Kubernetes); cung cấp đầy đủ tính năng cần thiết cho hệ thống quy mô vừa (tự động khởi động lại container, rolling update không gián đoạn, service discovery nội bộ, load balancing); sử dụng cùng cú pháp docker-compose.yml, cho phép dễ dàng chuyển đổi giữa môi trường phát triển và production.

Bảng 2.2. Phân bổ chi tiết dịch vụ trên ba node Docker Swarm

| Node | Vai trò | Thành phần | RAM (GB) |
|---|---|---|---|
| Node 1 (api) | Serving + Storage | Nginx, FastAPI, PostgreSQL, InfluxDB, MinIO, Kafka-1, binance-ticker-ws, binance-kline-rest, binance-depth-rest, Prometheus+Grafana, Registry, Certbot, DuckDNS, Sentinel-1 | 11.9 |
| Node 2 (data) | Streaming + Messaging | Zookeeper, Kafka-2, Schema Registry, Redis Master, Flink JobManager, Flink TaskManager 1, Spark Master, Spark Worker 1, Kafka Exporter, Sentinel-2 | 10.9 |
| Node 3 (compute) | Batch + Analytics | Kafka-3, Flink TaskManager 2, Spark Worker 2, Trino, Redis Replica, Loki+Promtail, Dagster (opt-in), Sentinel-3 | 11.5 |

Phân bổ này dựa trên ba nguyên tắc:

- **Affinity:** các dịch vụ có tương tác dữ liệu cao đặt trên cùng node hoặc node gần nhau — Redis Master trên Node 2 (cùng node với Flink, writer chính), MinIO trên Node 1 (cùng node với FastAPI, reader chính).
- **HA:** các thành phần quan trọng phân tán — Kafka ba broker trên ba node, Redis Sentinel ba node, Flink hai TaskManager trên hai node, Spark hai Worker trên hai node.
- **Tài nguyên:** tổng RAM mỗi node không vượt quá 12 GB, tận dụng tối đa 32 GB RAM có sẵn.

### 2.4.6. Các kịch bản sử dụng chính

Để minh họa cách hệ thống vận hành trong các tình huống thực tế, ba kịch bản sử dụng chính được phân tích chi tiết dưới đây, bao gồm cả trường hợp hoạt động bình thường và trường hợp khắc phục sự cố.

**Kịch bản 1: Người dùng xem biểu đồ nến BTCUSDT khung 1 phút.** Khi người dùng mở trình duyệt tại https://lmview.duckdns.org, React SPA được tải từ Nginx (Node 1). Người dùng chọn cặp BTCUSDT và khung thời gian 1 phút. Component `CandlestickChart` gọi `marketDataService.getKlines("binance", "BTCUSDT", "1m")`, gửi request `GET /api/klines?exchange=binance&symbol=BTCUSDT&interval=1m` đến FastAPI qua HTTPS. FastAPI đọc theo thứ tự ưu tiên: Redis (vài trăm nến gần nhất, 1-2ms) → InfluxDB (90 ngày, 10-50ms) → Trino/Iceberg (vô thời hạn, 50-500ms). Phản hồi JSON chứa mảng nến OHLCV được trả về và render bởi lightweight-charts. Sau khi biểu đồ hiển thị, trình duyệt mở WebSocket `wss://lmview.duckdns.org/api/stream/all?symbol=BTCUSDT`. FastAPI bắt đầu push cập nhật nến mới mỗi 50ms từ Redis poll loop. Chart cập nhật real-time mà không cần F5.

**Kịch bản 2: Người dùng hỏi AI "Tại sao BTC giảm hôm nay?".** Người dùng mở panel AI Assistant và gõ câu hỏi. Frontend gửi `POST /api/ai/chat` với payload `{"message": "Tại sao BTC giảm hôm nay?", "snapshot": "base64_chart_image"}`. FastAPI AI router nhận request và thực hiện năm bước:

- Scope Gate kiểm tra câu hỏi thuộc phạm vi crypto không — nếu không, từ chối ngay.
- Prompt Builder xây dựng prompt với ngữ cảnh gồm giá hiện tại, RSI 14, MACD, Bollinger Bands, tin tức gần nhất từ knowledge base.
- RAG Retrieval truy vấn pgvector với HNSW index, tìm top-5 knowledge chunks có cosine similarity > 0.7.
- Provider Router gọi LLM (mock nếu không có key, litellm nếu có).
- Output Guard kiểm tra output — nếu có nội dung nhạy cảm hoặc lời khuyên tài chính cụ thể, thêm disclaimer.

Response markdown được trả về và render trong panel chat.

**Kịch bản 3: Flink JobManager crash và phục hồi.** Khi Flink JobManager gặp sự cố (OOM, network partition), Docker Swarm phát hiện qua health check (interval: 30s, retries: 3). Swarm tự động kill container cũ và start container mới. Trong thời gian Flink restart (30-60 giây), dữ liệu ticker vẫn được cập nhật qua đường binance-ticker-ws → Redis Master (Real-time Path). Kafka lưu tất cả message chưa được Flink consume (offset không tăng), đảm bảo không mất dữ liệu. Flink JobManager mới đọc checkpoint cuối cùng từ MinIO (flink-checkpoints bucket) và yêu cầu TaskManager kết nối lại. TaskManager đọc lại state từ checkpoint và tiếp tục xử lý Kafka từ offset đã lưu. Người dùng chỉ bị ảnh hưởng nhẹ: thiếu chỉ báo mới trong khoảng 1 phút, nhưng giá vẫn cập nhật bình thường.

### 2.4.7. Sơ đồ use case và sơ đồ thành phần

Hệ thống LMView phục vụ ba nhóm người dùng:

- **Khách (guest):** xem biểu đồ nến, ticker, sổ lệnh, lịch sử giao dịch với tính năng giới hạn.
- **Người dùng đã đăng nhập (user):** toàn quyền tính năng bao gồm trợ lý AI, tùy chỉnh chỉ báo, chuyển đổi khung thời gian, dữ liệu lịch sử đầy đủ, tùy chỉnh giao diện.
- **Quản trị viên (admin):** thêm quyền quản lý người dùng, xem health check, khởi động lại dịch vụ qua API, xem log vận hành.

Sơ đồ thành phần gồm năm thành phần chính:

- **Frontend (React SPA):** giao tiếp với Nginx qua HTTPS/WS.
- **Nginx (Node 1):** reverse proxy đến FastAPI, serve static files, SSL termination.
- **FastAPI backend (Node 1):** kết nối đến bốn hệ thống lưu trữ: Redis, InfluxDB, PostgreSQL, Trino.
- **Flink và Spark:** chạy độc lập dưới dạng Swarm services, đọc từ Kafka, ghi vào Redis/InfluxDB/Iceberg.

### 2.4.8. Công nghệ sử dụng (Tech Stack)

Công nghệ được lựa chọn cho LMView dựa trên bốn tiêu chí: mã nguồn mở, tài liệu phong phú, cộng đồng lớn, và khả năng tương thích giữa các thành phần.

**Lựa chọn ngôn ngữ lập trình:** Python cho backend và pipeline dữ liệu vì:

- Ngôn ngữ thống trị trong AI và data science, hệ sinh thái thư viện phong phú (litellm, sentence-transformers, PyFlink, PySpark, fastavro).
- FastAPI là một trong những web framework Python nhanh nhất nhờ async/await, hiệu năng tương đương Node.js và Go trong bài toán I/O-bound.
- Python cho phép dùng chung mã nguồn giữa backend và pipeline — cùng class `RedisClient` có thể dùng trong FastAPI và Flink mà không duplicate code.

TypeScript cho frontend nhờ khả năng phát hiện lỗi tại compile time thông qua strict mode, giảm bug runtime.

**Lựa chọn cơ sở dữ liệu:** mỗi hệ thống lưu trữ được chọn dựa trên đặc điểm truy xuất cụ thể:

- **Redis** cho hot cache: kiểu Hash cho phép lưu 24 field ticker trong một key duy nhất, giảm network round-trip.
- **InfluxDB** cho warm storage: tối ưu truy vấn time-series range scan — nhanh hơn 5-10 lần PostgreSQL có time index.
- **PostgreSQL** cho relational data: extension pgvector cho phép lưu vector embeddings cùng bảng với knowledge chunks.
- **MinIO** cho object storage: tương thích S3 API, dễ mở rộng lên AWS S3 nếu cần.

Bảng 2.3. Bảng công nghệ chi tiết

| Lớp | Công nghệ | Phiên bản | Mục đích |
|---|---|---|---|
| Frontend | React | 19 | UI framework |
| | TypeScript | 5.x | Ngôn ngữ type-safe |
| | lightweight-charts | 4.x | Biểu đồ nến TradingView-compatible |
| | TailwindCSS | 3.x | CSS utility framework |
| | shadcn/ui | latest | UI component library |
| | Vite | 5.x | Build tool, HMR |
| Backend | Python | 3.11 | Ngôn ngữ lập trình chính |
| | FastAPI | 0.111+ | REST + WebSocket framework |
| | Uvicorn | latest | ASGI server (production) |
| | asyncpg | latest | PostgreSQL async driver |
| | redis-py (aioredis) | latest | Redis async client |
| | influxdb-client | latest | InfluxDB client |
| | trino (dbapi) | latest | Trino SQL client |
| | litellm | latest | LLM provider router |
| | sentence-transformers | latest | Text embeddings (384d) |
| Streaming | Apache Kafka | 3.9.0 | Event streaming platform |
| | Apache Flink | 1.18.1 | Stream processing (stateful) |
| | Apache Spark | 3.5.5 | Batch processing (Iceberg) |
| | Apicurio SR | 2.6.2 | Avro schema registry |
| Storage | Redis | 7.2-alpine | Hot cache (Sentinel HA) |
| | InfluxDB | 2.7 | Time-series database |
| | PostgreSQL | 16 + pgvector | Relational + vector DB |
| | MinIO | latest | S3-compatible object store |
| | Apache Iceberg | latest | Table format (ACID) |
| | Trino | 442 | Distributed SQL engine |
| Infra | Docker | 24+ | Container runtime |
| | Docker Swarm | built-in | Orchestration |
| | AWS EC2 | c5.2xlarge | Cloud compute (×3) |
| | EFS | — | Shared file system |
| | Nginx | 1.31-alpine | Reverse proxy, SSL, HSTS |
| | Let's Encrypt | certbot | SSL certificates |
| Monitoring | Prometheus | v2.45 | Metrics collection |
| | Grafana | 10.2 | Dashboard + alerting |
| | Loki | 2.9 | Log aggregation |
| AI | LiteLLM | latest | Multi-provider LLM gateway |
| | pgvector | latest | Vector storage + HNSW index |
| | all-MiniLM-L6-v2 | latest | Sentence embeddings (384d) |

### 2.4.9. Phân tích các mẫu thiết kế (Design Patterns) sử dụng trong LMView

Kiến trúc của LMView áp dụng bảy mẫu thiết kế phổ biến trong kỹ thuật phần mềm:

- **Repository Pattern:** trong tầng data access (backend/core/), nơi CandleRepository, TickerRepository, OrderBookRepository, TradeRepository là các lớp trừu tượng hóa việc truy cập dữ liệu, ẩn chi tiết implementation của từng storage backend.
- **Strategy Pattern:** trong AI provider router — AIProvider là interface, MockProvider và LiteLLMProvider là concrete strategy, ProviderRouter lựa chọn strategy dựa trên biến môi trường AI_MODE.
- **Observer Pattern:** trong WebSocket push — FastAPI WebSocket endpoint là Subject broadcast dữ liệu đến tất cả browser client (Observer) thông qua websocket.send_json().
- **Chain of Responsibility:** trong fallback chain của CandleService — service thử Redis trước, nếu không đủ chuyển sang InfluxDB, nếu vẫn không đủ chuyển sang Trino.
- **Factory Method:** trong exchange adapter (src/exchanges/base.py) — BaseExchange định nghĩa factory method create_ws_connection() và create_rest_client(), các exchange cụ thể override để tạo connection phù hợp với API của từng sàn.
- **Singleton:** cho các client kết nối resource tốn kém (Redis connection pool, PostgreSQL async pool, Kafka producer), khởi tạo một lần duy nhất và reuse cho mọi request.
- **Adapter:** trong frontend mock data layer (frontend/src/data/mock/), nơi MockKlinesAdapter implement interface giống API response thật cho phép phát triển frontend độc lập với backend.

### 2.4.10. So sánh với các nghiên cứu liên quan

Phần này định vị LMView trong bối cảnh các nghiên cứu và hệ thống liên quan đến phân tích kỹ thuật thời gian thực, kiến trúc Lambda, và tích hợp AI trong lĩnh vực tài chính. Bốn nhóm nghiên cứu liên quan:

- **Nền tảng phân tích kỹ thuật thương mại (commercial platforms):** TradingView là nền tảng dẫn đầu với hơn 50 triệu người dùng, sử dụng backend độc quyền và WebSocket-based real-time data push. LMView khác biệt ở ba điểm: mã nguồn mở, kiến trúc Lambda có tài liệu thiết kế đầy đủ, và tích hợp RAG-based AI assistant. CoinMarketCap và CoinGecko tập trung vào dữ liệu tổng hợp thị trường hơn là phân tích kỹ thuật — LMView bổ sung khả năng real-time chart và indicator.

- **Kiến trúc Lambda cho dữ liệu tài chính (Lambda Architecture for financial data):** Marz và Warren (2015) đã thiết lập nền tảng lý thuyết nhưng không cung cấp triển khai cụ thể cho lĩnh vực tài chính. Hausenblas và NÄ®gaard (2015) triển khai Lambda Architecture trên Kafka và Spark cho dữ liệu chứng khoán, với batch layer xử lý 10 năm lịch sử và speed layer real-time ticks, nhưng không đề cập cơ chế reconciliation giữa speed và batch layer — thách thức trung tâm của Lambda. LMView giải quyết bằng stitching candle và fallback chain. Villarroel và cộng sự (2019) đề xuất Lambda Architecture cho hệ thống giao dịch thuật toán với Flink cho speed layer và Spark cho batch layer, nhưng không tích hợp AI hay RAG.

- **Tích hợp LLM trong phân tích tài chính (LLM for financial analysis):** Araci (2019) giới thiệu FinBERT, mô hình ngôn ngữ fine-tune trên dữ liệu tài chính cho sentiment analysis, đạt accuracy 85% trên Financial PhraseBank. Lopez-Lira và Tang (2023) sử dụng ChatGPT dự đoán hướng giá chứng khoán dựa trên tin tức và phát hiện ChatGPT có khả năng dự đoán tốt hơn random baseline đáng kể. Tuy nhiên, các nghiên cứu này sử dụng LLM như công cụ độc lập, không tích hợp vào kiến trúc streaming real-time. LMView khác biệt ở chỗ tích hợp LLM trực tiếp vào pipeline xử lý dữ liệu thời gian thực qua RAG architecture, với scope gate, prompt builder, và output guard.

- **Nền tảng mã nguồn mở cho phân tích thị trường (open-source trading platforms):** Freqtrade (Python, 25k+ GitHub stars) là trading bot hỗ trợ backtesting và chiến lược tùy chỉnh, nhưng không có real-time chart hay AI assistant. Julia (node.js) cung cấp real-time dashboard cho chứng khoán nhưng không hỗ trợ tiền điện tử. Hummingbot (Python, 7k+ stars) tập trung vào market making và arbitrage. LMView khác biệt ở chỗ tập trung vào phân tích kỹ thuật và AI assistant thay vì giao dịch tự động, phù hợp với nhà đầu tư cá nhân muốn hiểu thị trường.

---
