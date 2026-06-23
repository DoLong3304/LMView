# KHÓA LUẬN TỐT NGHIỆP NHÓM 79

## XÂY DỰNG HỆ THỐNG PHÂN TÍCH KỸ THUẬT TIỀN ĐIỆN TỬ THỜI GIAN THỰC
### NỀN TẢNG LMVIEW — KIẾN TRÚC LAMBDA TRÊN DOCKER SWARM 3 NODE

**Ngành:** Khoa học Máy tính / Hệ thống Thông tin

**Giảng viên hướng dẫn:** ...

**Thành viên nhóm 79:** ...

**Niên khóa:** 2025–2026

---

# MỞ ĐẦU

## 1. Bối cảnh và vấn đề

Thị trường tiền điện tử (cryptocurrency) đã chứng kiến sự tăng trưởng vượt bậc trong thập kỷ qua, từ một tài sản kỹ thuật số biên trở thành một kênh đầu tư toàn cầu. Không giống như thị trường tài chính truyền thống vốn chỉ hoạt động trong khung giờ nhất định, thị trường tiền điện tử vận hành 24 giờ một ngày, 7 ngày một tuần, với biến động giá có thể đạt mức hai con số phần trăm chỉ trong vài giờ. Đặc điểm này tạo ra cả cơ hội lẫn rủi ro to lớn, đặt ra yêu cầu cấp thiết về các công cụ phân tích kỹ thuật có khả năng cập nhật dữ liệu theo thời gian thực.

Phân tích kỹ thuật (technical analysis) là phương pháp dự đoán biến động giá dựa trên dữ liệu lịch sử về giá và khối lượng giao dịch, đóng vai trò trung tâm trong quyết định giao dịch của phần lớn nhà đầu tư tiền điện tử. Các nền tảng như TradingView, CoinMarketCap hay Binance cung cấp biểu đồ nến (candlestick chart), chỉ báo kỹ thuật (RSI, MACD, Bollinger Bands), và dữ liệu thị trường theo thời gian thực. Tuy nhiên, những nền tảng này tồn tại một số hạn chế đáng kể. Thứ nhất, chi phí sử dụng cao: TradingView Pro có giá từ 15 đến 60 đô-la Mỹ mỗi tháng cho dữ liệu thời gian thực và chỉ báo nâng cao. Thứ hai, khả năng tùy biến hạn chế: người dùng không thể mở rộng hoặc tích hợp các mô hình trí tuệ nhân tạo riêng. Thứ ba, hầu hết các nền tảng chưa tích hợp trợ lý thông minh có khả năng phân tích ngữ cảnh thị trường và giải thích biến động giá bằng ngôn ngữ tự nhiên. Cuối cùng, mã nguồn đóng khiến người dùng không thể kiểm tra hoặc cải thiện thuật toán phân tích.

Từ những phân tích trên, vấn đề cốt lõi được đặt ra là: làm thế nào để xây dựng một nền tảng phân tích kỹ thuật tiền điện tử thời gian thực với chi phí thấp, khả năng mở rộng cao, và tích hợp trí tuệ nhân tạo — mà vẫn đảm bảo độ trễ dưới 500 mili-giây từ lúc khớp lệnh trên sàn giao dịch đến hiển thị trên trình duyệt người dùng?

## 2. Phát biểu bài toán và câu hỏi nghiên cứu

Bài toán của khóa luận này được phát biểu như sau: xây dựng một nền tảng phân tích kỹ thuật tiền điện tử thời gian thực (LMView) có khả năng thu thập, xử lý, lưu trữ và hiển thị dữ liệu thị trường với độ trễ tối thiểu, đồng thời tích hợp trợ lý trí tuệ nhân tạo hỗ trợ phân tích thị trường dựa trên ngữ cảnh thời gian thực.

Từ bài toán trên, năm câu hỏi nghiên cứu được đặt ra. Thứ nhất, về kiến trúc: làm thế nào để thiết kế một hệ thống xử lý dữ liệu thời gian thực đáp ứng độ trễ dưới 500 mili-giây với hơn 600 cặp giao dịch từ sàn Binance? Thứ hai, về khả năng chịu lỗi: làm thế nào để đảm bảo hệ thống hoạt động liên tục khi có sự cố mạng, máy chủ, hay dịch vụ? Thứ ba, về lưu trữ đa tầng: làm thế nào để kết hợp lưu trữ nóng (Redis), ấm (InfluxDB), và lạnh (Iceberg/MinIO) một cách hiệu quả nhằm cân bằng giữa tốc độ truy xuất và chi phí lưu trữ? Thứ tư, về tích hợp trí tuệ nhân tạo: làm thế nào để tích hợp trợ lý AI sử dụng Retrieval-Augmented Generation (RAG) nhằm phân tích thị trường dựa trên dữ liệu thời gian thực và cơ sở tri thức có cấu trúc? Thứ năm, về triển khai: làm thế nào để triển khai hệ thống trên hạ tầng Docker Swarm với ba node EC2 với chi phí vận hành tối ưu?

## 3. Đóng góp chính

Khóa luận này đóng góp bốn kết quả chính. Thứ nhất, một kiến trúc Lambda ba tầng (Speed Layer, Batch Layer, Serving Layer) được thiết kế và triển khai thành công trên ba node Docker Swarm, với khả năng xử lý hơn 600 cặp giao dịch thời gian thực từ Binance. Kiến trúc này giải quyết bài toán dung hòa giữa độ trễ thấp và lưu trữ lâu dài thông qua cơ chế đối chiếu dữ liệu (reconciliation/stitching) tại tầng phục vụ.

Thứ hai, một hệ thống ba node Docker Swarm được phân bổ tối ưu với ba vai trò riêng biệt: Node 1 (API/Infra) đảm nhiệm tầng phục vụ và lưu trữ, Node 2 (Data/Streaming) đảm nhiệm xử lý luồng dữ liệu thời gian thực, và Node 3 (Compute/Analytics) đảm nhiệm xử lý hàng loạt và truy vấn lịch sử. Tổng chi phí vận hành ước tính dưới 10 đô-la Mỹ mỗi tháng.

Thứ ba, một cơ chế chịu lỗi đa tầng bao gồm Kafka replication factor 3 cho phép mất một broker mà không mất dữ liệu, Redis Sentinel auto-failover với quorum 2/3 cho phép phục hồi trong vòng 30 giây, Flink và Spark với nhiều worker cho phép xử lý song song, và cơ chế bypass Redis trực tiếp khi pipeline chính gặp sự cố.

Thứ tư, một hệ thống trợ lý AI tích hợp sử dụng kiến trúc RAG, với cơ chế scope gate kiểm tra phạm vi câu hỏi, prompt builder xây dựng ngữ cảnh thị trường thời gian thực, provider router lựa chọn mô hình ngôn ngữ phù hợp, và output guard đảm bảo an toàn đầu ra. Hệ thống AI này vận hành trên cùng hạ tầng với backend, tận dụng PostgreSQL lưu trữ vector embeddings và lịch sử hội thoại.

## 4. Phạm vi đề tài

Khóa luận tập trung vào các phạm vi sau. Về chức năng, hệ thống bao gồm biểu đồ nến thời gian thực với chín khung thời gian, sổ lệnh (order book) với 50 mức giá mua và bán, lịch sử giao dịch gần nhất năm mươi lệnh, các chỉ báo kỹ thuật cốt lõi gồm SMA, EMA, RSI, MACD, và Bollinger Bands, trợ lý AI chat với khả năng truy xuất kiến thức thị trường, và bảng tổng quan thị trường hiển thị top tăng/giảm, vốn hóa, và heatmap. Về dữ liệu, hệ thống xử lý 671 cặp USDT từ sàn Binance được chọn lọc theo khối lượng giao dịch 24 giờ cao nhất, với dữ liệu lịch sử 90 ngày qua InfluxDB và lưu trữ vô thời hạn qua Iceberg/MinIO. Về công nghệ, hệ thống sử dụng Docker Swarm trên ba máy chủ AWS EC2 (mỗi máy 8 vCPU, 32 GB RAM), với backend Python FastAPI, frontend React 19 kết hợp TypeScript, và pipeline dữ liệu dùng Apache Kafka, Flink, Spark. Khóa luận không bao gồm giao dịch tự động, bot trading, phân tích cảm xúc từ mạng xã hội, hay hỗ trợ đa sàn giao dịch ngoài Binance.

## 5. Phương pháp nghiên cứu

Khóa luận áp dụng phương pháp nghiên cứu Design Science Research (DSR), vốn được sử dụng rộng rãi trong lĩnh vực hệ thống thông tin và khoa học máy tính để xây dựng và đánh giá các artifact công nghệ. Quy trình nghiên cứu gồm bốn giai đoạn. Giai đoạn thứ nhất là nghiên cứu lý thuyết: tổng hợp tài liệu về kiến trúc Lambda, xử lý dữ liệu thời gian thực, data lakehouse, phân tích kỹ thuật tài chính, và ứng dụng mô hình ngôn ngữ lớn trong tài chính. Giai đoạn thứ hai là thiết kế hệ thống: xây dựng kiến trúc ba tầng Lambda và thiết kế chi tiết các luồng dữ liệu, cơ chế chịu lỗi, và tích hợp AI. Giai đoạn thứ ba là phát triển và triển khai: container hóa toàn bộ dịch vụ với Docker, triển khai trên Docker Swarm ba node, và tích hợp liên tục qua Makefile. Giai đoạn thứ tư là đánh giá: đo lường hiệu năng hệ thống qua các chỉ số độ trễ (p50, p95, p99), thông lượng, độ khả dụng, và chi phí vận hành, theo khung phương pháp luận đánh giá thực nghiệm trong công nghệ phần mềm [1].

## 6. Kết cấu khóa luận

Khóa luận gồm bốn chương. Chương 1 trình bày cơ sở lý thuyết về tiền điện tử, phân tích kỹ thuật, xử lý dữ liệu lớn thời gian thực với kiến trúc Lambda và Data Lakehouse, cùng trí tuệ nhân tạo trong phân tích tài chính. Chương 2 phân tích yêu cầu chức năng và phi chức năng, đề xuất kiến trúc ba node Docker Swarm, và trình bày chi tiết thiết kế luồng dữ liệu, các kịch bản sử dụng, và công nghệ áp dụng. Chương 3 mô tả quá trình cài đặt hạ tầng, triển khai hệ thống, giao diện người dùng, và kết quả vận hành. Chương 4 đánh giá hiệu năng hệ thống qua các tiêu chí đo lường, thảo luận về điểm mạnh và hạn chế, và đề xuất hướng phát triển.

---

# CHƯƠNG 1 — CƠ SỞ LÝ THUYẾT

## 1.1. Tiền điện tử và thị trường tiền điện tử

### 1.1.1. Khái niệm tiền điện tử

Tiền điện tử (cryptocurrency) là một loại tài sản kỹ thuật số sử dụng mật mã học (cryptography) để đảm bảo an toàn cho các giao dịch, kiểm soát việc tạo ra các đơn vị mới, và xác minh việc chuyển giao tài sản mà không cần đến trung gian tài chính truyền thống. Khác với tiền pháp định (fiat currency) do chính phủ phát hành và kiểm soát, tiền điện tử hoạt động trên công nghệ blockchain — một sổ cái phân tán (distributed ledger) phi tập trung, nơi mọi giao dịch được ghi nhận công khai và không thể thay đổi.

Bitcoin, ra mắt năm 2009 bởi một cá nhân hoặc nhóm ẩn danh dưới bút danh Satoshi Nakamoto, là đồng tiền điện tử đầu tiên và vẫn giữ vị thế thống trị về vốn hóa thị trường [2]. Bitcoin giới thiệu khái niệm bằng chứng công việc (proof-of-work) và cung ứng giới hạn 21 triệu đơn vị, tạo nên tính khan hiếm số học. Ethereum, ra mắt năm 2015 bởi Vitalik Buterin, mở rộng khái niệm blockchain với hợp đồng thông minh (smart contract), cho phép lập trình các ứng dụng phi tập trung (dApps) trên nền tảng của nó. Các altcoin khác như Binance Coin, Solana, và Cardano tạo nên một hệ sinh thái đa dạng với hàng nghìn đồng tiền khác nhau.

### 1.1.2. Đặc điểm thị trường tiền điện tử

Thị trường tiền điện tử có những đặc điểm khác biệt so với thị trường tài chính truyền thống, tạo ra cả thách thức lẫn cơ hội cho các hệ thống phân tích kỹ thuật. Thứ nhất, thị trường hoạt động 24 giờ một ngày, 7 ngày một tuần, không có giờ đóng cửa hay ngày nghỉ lễ, đồng nghĩa với việc hệ thống phân tích phải hoạt động liên tục và xử lý dữ liệu không ngừng nghỉ. Thứ hai, biến động giá rất cao so với thị trường chứng khoán truyền thống: giá có thể thay đổi 5 đến 20 phần trăm trong một ngày, đòi hỏi độ trễ xử lý cực kỳ thấp để đảm bảo nhà đầu tư nhìn thấy giá chính xác tại mọi thời điểm.

Bên cạnh đó, thị trường tiền điện tử mang tính phi tập trung: không có cơ quan trung ương kiểm soát, giá được xác định bởi cung và cầu trên các sàn giao dịch phân tán khắp thế giới. Điều này dẫn đến tính thanh khoản cao và khả năng tiếp cận toàn cầu, nhưng cũng tạo ra sự chênh lệch giá nhỏ giữa các sàn giao dịch. Cuối cùng, tiền điện tử thường có tương quan thấp với thị trường tài chính truyền thống, khiến nó trở thành một kênh đa dạng hóa danh mục đầu tư nhưng cũng đòi hỏi các công cụ phân tích chuyên biệt, không thể áp dụng trực tiếp các mô hình phân tích thị trường chứng khoán.

### 1.1.3. Sàn giao dịch Binance

Binance là sàn giao dịch tiền điện tử lớn nhất thế giới tính theo khối lượng giao dịch, cung cấp API phong phú cho phép truy cập dữ liệu thị trường thời gian thực. Binance cung cấp hai giao thức truy cập chính. WebSocket Streams cho phép push dữ liệu liên tục cho ticker 24 giờ, nến (kline), sổ lệnh (depth), và giao dịch (trade) — đây là nguồn dữ liệu thời gian thực chính cho LMView. REST API cho phép truy vấn lịch sử giá, snapshot sổ lệnh, và thông tin tài khoản. Một tính năng quan trọng là Combined Streams, cho phép gộp nhiều symbol vào một kết nối WebSocket duy nhất, giảm số lượng kết nối cần duy trì và tiết kiệm tài nguyên.

Trong LMView, Binance là nguồn dữ liệu duy nhất, cung cấp dữ liệu cho 671 cặp USDT hàng đầu được chọn lọc theo khối lượng giao dịch 24 giờ. Lựa chọn này dựa trên nguyên tắc tập trung vào thanh khoản: các cặp giao dịch có khối lượng lớn nhất thường có độ trễ thấp nhất và độ tin cậy cao nhất, phù hợp với mục tiêu xây dựng hệ thống thời gian thực chi phí thấp.

## 1.2. Phân tích kỹ thuật trong thị trường tiền điện tử

### 1.2.1. Nền tảng lý thuyết phân tích kỹ thuật

Phân tích kỹ thuật (technical analysis) là phương pháp đánh giá và dự đoán biến động giá dựa trên dữ liệu thị trường quá khứ, chủ yếu là giá và khối lượng giao dịch. Nền tảng lý thuyết của phân tích kỹ thuật dựa trên ba nguyên lý cốt lõi được hệ thống hóa từ các bài viết của Charles Dow trên Wall Street Journal đầu thế kỷ 20, sau này được Murphy (1999) tổng hợp và trình bày một cách có hệ thống [3]. Nguyên lý thứ nhất khẳng định thị trường phản ánh tất cả thông tin (market discounts everything): giá hiện tại của một tài sản đã tích hợp mọi yếu tố cơ bản, tin tức, và tâm lý thị trường, do đó việc nghiên cứu diễn biến giá là đủ để đưa ra quyết định giao dịch. Nguyên lý thứ hai cho rằng giá vận động theo xu hướng (prices move in trends): giá có xu hướng tăng (uptrend), giảm (downtrend), hoặc đi ngang (sideways), và một khi xu hướng đã được thiết lập, nó có xu hướng tiếp diễn. Nguyên lý thứ ba khẳng định lịch sử có tính lặp lại (history repeats itself): các mô hình giá và hành vi nhà đầu tư có xu hướng lặp lại theo thời gian do tâm lý thị trường mang tính chu kỳ.

Ba nguyên lý này có mối quan hệ mật thiết với Giả thuyết thị trường hiệu quả (Efficient Market Hypothesis — EMH) do Fama (1970) đề xuất [4]. EMH phân loại thị trường thành ba mức hiệu quả: yếu (weak-form), trung bình (semi-strong), và mạnh (strong-form). Phân tích kỹ thuật hoạt động dựa trên giả định thị trường chỉ hiệu quả ở mức yếu — nghĩa là giá đã phản ánh mọi thông tin quá khứ, nhưng chưa phản ánh thông tin hiện tại và tương lai. Trong bối cảnh thị trường tiền điện tử, Urquhart (2016) cho thấy bằng chứng về tính không hiệu quả của thị trường Bitcoin trong giai đoạn đầu phát triển [5]. Tuy nhiên, Tran và Leirvik (2020) lập luận rằng thị trường tiền điện tử đang tiến dần đến mức hiệu quả hơn theo thời gian [6]. Sự thiếu vắng một đồng thuận học thuật về mức độ hiệu quả của thị trường tiền điện tử chính là lý do khiến LMView tích hợp trợ lý AI như một nguồn thông tin bổ sung, giúp nhà đầu tư có thêm góc nhìn đa chiều trước khi ra quyết định.

### 1.2.2. Các chỉ báo kỹ thuật cốt lõi

Các chỉ báo kỹ thuật được nhóm nghiên cứu triển khai trong LMView được phân thành bốn nhóm dựa trên mục đích sử dụng: chỉ báo xu hướng (trend indicators), chỉ báo động lượng (momentum indicators), chỉ báo biến động (volatility indicators), và chỉ báo khối lượng (volume indicators). Việc phân nhóm này giúp người dùng dễ dàng lựa chọn và kết hợp các chỉ báo phù hợp với chiến lược giao dịch của mình.

Nhóm chỉ báo xu hướng bao gồm các đường trung bình động. Đường trung bình động đơn giản (Simple Moving Average — SMA) được tính bằng trung bình cộng giá đóng cửa trong N phiên giao dịch gần nhất, thể hiện qua phương trình:

$$SMA_t(N) = \frac{1}{N} \sum_{i=0}^{N-1} P_{t-i}$$

trong đó \(P_t\) là giá đóng cửa tại phiên t. Đường trung bình động hàm mũ (Exponential Moving Average — EMA) là biến thể của SMA với trọng số giảm dần theo thời gian, ưu tiên giá gần nhất hơn, được tính bằng:

$$EMA_t = P_t \times \alpha + EMA_{t-1} \times (1 - \alpha)$$

với \(\alpha = 2/(N+1)\). EMA phản ứng nhạy hơn với biến động giá gần đây so với SMA, phù hợp cho giao dịch ngắn hạn. Trong LMView, các chỉ báo xu hướng được tính toán trực tiếp trên luồng dữ liệu Flink thông qua cơ chế cửa sổ trượt (sliding window), cho phép cập nhật chỉ báo mỗi khi có nến mới mà không cần tính toán lại toàn bộ lịch sử.

Nhóm chỉ báo động lượng bao gồm RSI và MACD. Chỉ số sức mạnh tương đối (Relative Strength Index — RSI), được Wilder (1978) giới thiệu [7], đo lường tốc độ và mức độ thay đổi giá trên thang từ 0 đến 100:

$$RSI = 100 - \frac{100}{1 + RS}$$

trong đó RS là tỷ lệ giữa trung bình tăng giá và trung bình giảm giá trong N phiên. Giá trị RSI trên 70 cho thấy thị trường quá mua (overbought), dưới 30 cho thấy thị trường quá bán (oversold). MACD (Moving Average Convergence Divergence) được tính bằng hiệu giữa EMA 12 phiên và EMA 26 phiên, kết hợp với đường tín hiệu là EMA 9 phiên của chính MACD. Khi MACD cắt lên trên đường tín hiệu, đây có thể là tín hiệu mua; khi cắt xuống dưới, đây có thể là tín hiệu bán.

Nhóm chỉ báo biến động tập trung vào Bollinger Bands, gồm ba đường: đường giữa là SMA 20 phiên, dải trên và dải dưới lần lượt là SMA 20 phiên cộng và trừ hai lần độ lệch chuẩn của giá trong 20 phiên. Khi giá chạm dải trên, thị trường được coi là quá mua; khi chạm dải dưới, thị trường quá bán. Độ rộng của dải (bandwidth) phản ánh mức độ biến động của thị trường. Ngoài các chỉ báo cốt lõi này, hệ thống được thiết kế với kiến trúc plugin để có thể mở rộng thêm các chỉ báo khác như VWAP, Stochastic, ATR, và OBV trong tương lai.

### 1.2.3. Biểu đồ nến và dữ liệu OHLCV

Biểu đồ nến Nhật (Japanese Candlestick Chart) là phương pháp trực quan hóa dữ liệu giá phổ biến nhất trong phân tích kỹ thuật, được Nison phổ biến rộng rãi trong giới giao dịch phương Tây [8]. Mỗi nến (candlestick) đại diện cho một khoảng thời gian giao dịch cụ thể (ví dụ một phút, một giờ, một ngày) và chứa bốn giá trị cốt lõi: giá mở cửa (Open — O), giá cao nhất (High — H), giá thấp nhất (Low — L), giá đóng cửa (Close — C), cùng với khối lượng giao dịch (Volume — V). Cấu trúc OHLCV tạo thành đơn vị dữ liệu cơ bản cho mọi tính toán phân tích kỹ thuật trong LMView.

Thân nến (real body) biểu diễn khoảng cách giữa giá mở cửa và giá đóng cửa: nếu giá đóng cửa cao hơn giá mở cửa, nến có màu xanh (bullish); nếu ngược lại, nến có màu đỏ (bearish). Bấc nến (wick hay shadow) biểu diễn giá cao nhất và thấp nhất trong phiên. Các mô hình nến (candlestick patterns) như doji, hammer, engulfing, và morning star được các nhà giao dịch sử dụng để dự đoán khả năng đảo chiều xu hướng.

Trong LMView, dữ liệu nến được tổng hợp ở nhiều khung thời gian khác nhau: 1 giây, 1 phút, 5 phút, 15 phút, 30 phút, 1 giờ, 4 giờ, 1 ngày, và 1 tuần. Quá trình aggregation được thực hiện theo cấu trúc phân cấp: nến 1 giây được Flink tổng hợp thành nến 1 phút, và các khung thời gian lớn hơn được tổng hợp từ nến 1 phút. Cơ chế hợp nhất nến đã đóng (closed candle, có chỉ báo kỹ thuật) với nến đang hình thành (forming candle, từ dữ liệu ticker thời gian thực) được tích hợp tại tầng phục vụ FastAPI, đảm bảo người dùng luôn thấy được nến mới nhất với độ trễ tối thiểu.

### 1.2.4. Tác động của tin tức đến thị trường tiền điện tử

Thị trường tiền điện tử được ghi nhận là đặc biệt nhạy cảm với tin tức so với thị trường tài chính truyền thống. Các sự kiện như thay đổi quy định pháp lý từ các cơ quan như SEC (Mỹ) hay MiCA (EU), tuyên bố từ các nhân vật có ảnh hưởng, sự kiện hack hoặc bảo mật, nâng cấp giao thức (Bitcoin halving, Ethereum Merge), và biến động kinh tế vĩ mô đều có thể tạo ra những biến động giá lớn trong thời gian ngắn.

Liu và Tsyvinski (2021) đã tiến hành một nghiên cứu định lượng về các yếu tố tác động đến lợi suất của tiền điện tử, kết luận rằng tin tức và các yếu tố phi truyền thống (non-traditional factors) có tương quan đáng kể với biến động giá ngắn hạn [9]. Kết quả này càng củng cố nhu cầu tích hợp một nguồn thông tin thị trường có cấu trúc và khả năng tổng hợp vào nền tảng phân tích kỹ thuật. LMView hướng đến việc xây dựng trợ lý AI có khả năng truy xuất thông tin thị trường mới nhất, kết hợp với dữ liệu thời gian thực để cung cấp các phân tích ngữ cảnh chất lượng cao cho người dùng. `[CẦN XÁC NHẬN: pipeline tin tức đang ở giai đoạn khảo sát, chưa tích hợp đầy đủ. Nội dung này được viết ở thì định hướng cho kế hoạch tương lai.]`

## 1.3. Xử lý dữ liệu lớn trong thời gian thực

### 1.3.1. Kiến trúc Lambda (Lambda Architecture)

Kiến trúc Lambda được Nathan Marz giới thiệu lần đầu năm 2013 và sau đó được trình bày chi tiết trong sách "Big Data: Principles and Best Practices of Scalable Realtime Data Systems" [10]. Đây là một mô hình kiến trúc được thiết kế để giải quyết bài toán xử lý dữ liệu lớn với yêu cầu vừa đảm bảo độ trễ thấp vừa đảm bảo tính toàn vẹn dữ liệu lịch sử. Kiến trúc Lambda gồm ba tầng vận hành song song. Tầng tốc độ (Speed Layer) xử lý dữ liệu theo thời gian thực với độ trễ mili-giây đến giây, cung cấp kết quả ngay lập tức cho người dùng nhưng có thể không hoàn toàn chính xác hoặc đầy đủ. Tầng xử lý theo lô (Batch Layer) xử lý toàn bộ dữ liệu lịch sử với độ trễ cao hơn (phút đến giờ) nhưng đảm bảo độ chính xác tuyệt đối. Tầng phục vụ (Serving Layer) kết hợp và đối chiếu kết quả từ cả hai tầng để phục vụ truy vấn người dùng.

Quyết định lựa chọn kiến trúc Lambda thay vì kiến trúc Kappa (chỉ có một luồng xử lý thời gian thực duy nhất) trong LMView dựa trên một phân tích định lượng về khối lượng dữ liệu. Với 671 symbol cập nhật mỗi giây, 24 giờ một ngày, 365 ngày một năm, tổng số message cần xử lý ước tính lên tới khoảng 21 tỷ mỗi năm. Trong kiến trúc Kappa, toàn bộ dữ liệu này phải được lưu trong Kafka để có thể tính toán lại khi cần, trong khi Kafka chỉ tối ưu cho retention vài ngày đến vài tuần. Kiến trúc Lambda giải quyết vấn đề này bằng cách chỉ dùng Kafka cho tầng tốc độ (retention vài ngày), trong khi tầng batch lưu dữ liệu lịch sử trên Iceberg/MinIO với chi phí thấp hơn nhiều. Tuy nhiên, kiến trúc Lambda cũng đánh đổi bằng độ phức tạp tăng do phải duy trì hai codebase xử lý song song và cơ chế đối chiếu dữ liệu phức tạp tại tầng phục vụ.

### 1.3.2. Hạ tầng lưu trữ Data Lakehouse

Data Lakehouse là một mô hình kiến trúc mới nổi kết hợp ưu điểm của Data Lake (lưu trữ dữ liệu thô với chi phí thấp, linh hoạt về schema) và Data Warehouse (khả năng truy vấn SQL, giao dịch ACID, hỗ trợ schema enforcement) [11]. LMView triển khai Data Lakehouse trên nền tảng Apache Iceberg kết hợp với MinIO (lưu trữ đối tượng tương thích S3) và Trino (engine truy vấn SQL phân tán).

Kiến trúc lưu trữ theo mô hình Medallion (huy chương) gồm ba tầng với mức độ xử lý tăng dần. Tầng Bronze (đồng) lưu dữ liệu thô nguyên bản từ Kafka, sử dụng kiểu dữ liệu BINARY cho phép replay lại toàn bộ pipeline khi cần sửa lỗi xử lý. Tầng Silver (bạc) thực hiện làm sạch dữ liệu: loại bỏ trùng lặp, chuẩn hóa kiểu dữ liệu (ví dụ sử dụng DECIMAL(20,8) cho giá trị thay vì DOUBLE để tránh sai số dấu phẩy động, đặc biệt quan trọng với các token có giá rất nhỏ hoặc rất lớn), và chuẩn hóa múi giờ. Tầng Gold (vàng) lưu dữ liệu đã được tổng hợp ở mức độ cao, sẵn sàng cho các truy vấn API như market overview, top gainers/losers, và heatmap.

Apache Iceberg được chọn làm định dạng bảng vì ba tính năng quan trọng. Thứ nhất, ACID transactions đảm bảo tính nhất quán của dữ liệu khi có nhiều luồng ghi đồng thời từ Spark và các job batch. Thứ hai, time travel cho phép truy vấn dữ liệu tại bất kỳ thời điểm nào trong quá khứ, hữu ích cho việc gỡ lỗi và tái tạo kết quả. Thứ ba, schema evolution cho phép thêm hoặc xóa cột mà không cần viết lại toàn bộ bảng, giúp dễ dàng mở rộng cấu trúc dữ liệu khi thêm nguồn dữ liệu mới.

### 1.3.3. Kỹ thuật xử lý dữ liệu thời gian thực

Xử lý dữ liệu thời gian thực trong LMView dựa trên ba công nghệ cốt lõi: Apache Kafka cho hàng đợi message phân tán, Apache Flink cho xử lý streaming, và Redis Sentinel cho bộ nhớ đệm tốc độ cao.

Apache Kafka, được phát triển tại LinkedIn bởi Kreps và cộng sự (2011) [12], hoạt động như một hệ thống message queue phân tán với khả năng lưu trữ và phát lại luồng sự kiện. Trong LMView, Kafka gồm ba broker đặt trên ba node khác nhau, mỗi topic được chia thành 12 partition với replication factor 3. Cấu hình này đảm bảo hệ thống vẫn hoạt động khi mất tối đa một broker nhờ cơ chế leader re-election và minimum in-sync replicas (min ISR) được đặt ở 2. Các topic chính bao gồm crypto_ticker (lưu thông tin giá 24 giờ), crypto_klines (lưu nến 1 giây đã đóng), crypto_depth (lưu dữ liệu sổ lệnh), và crypto_trades (lưu giao dịch đã khớp). Mỗi partition sử dụng key theo cặp (exchange, symbol) để đảm bảo thứ tự xử lý trong cùng một symbol.

Apache Flink xử lý dữ liệu streaming với độ trễ 100 đến 500 mili-giây thông qua mô hình xử lý có trạng thái (stateful processing). Khác với Spark Streaming sử dụng mô hình micro-batch xử lý dữ liệu theo từng lô nhỏ, Flink xử lý từng sự kiện ngay khi đến, cho phép độ trễ thấp hơn. Flink JobManager điều phối việc thực thi job trên hai TaskManager (một trên Node 2, một trên Node 3), mỗi TaskManager xử lý 6 task với parallelism tổng cộng 12 — tương ứng với số partition của Kafka. Mỗi task thực hiện KeyedProcessFunction keyed theo (exchange, symbol), bao gồm aggregation nến từ 1 giây lên 1 phút, tính toán chỉ báo kỹ thuật incremental thông qua cửa sổ trượt (sliding window), và ghi kết quả vào Redis (hot cache) cùng InfluxDB (warm storage).

Redis Sentinel Cluster đóng vai trò bộ nhớ đệm tốc độ cao với cơ chế tự động phục hồi khi gặp sự cố. Cluster gồm một master (đặt trên Node 2) cho phép ghi và đọc, một replica (đặt trên Node 3) chỉ phục vụ đọc, và ba sentinel (mỗi node một sentinel) giám sát hoạt động của cluster. Khi sentinel phát hiện master không phản hồi trong 5 giây và đạt quorum 2/3, cơ chế bầu cử được kích hoạt và replica sẽ được thăng cấp thành master mới trong vòng khoảng 30 giây. Cấu hình này đảm bảo dịch vụ cache luôn khả dụng ngay cả khi một node gặp sự cố.

## 1.4. Trí tuệ nhân tạo trong phân tích tài chính

### 1.4.1. Mô hình ngôn ngữ lớn (LLM)

Mô hình ngôn ngữ lớn (Large Language Model — LLM) là một lớp mô hình deep learning được huấn luyện trên khối lượng văn bản khổng lồ, có khả năng hiểu và sinh văn bản tự nhiên với chất lượng ngày càng cao. Nền tảng kiến trúc của các LLM hiện đại là mô hình Transformer do Vaswani và cộng sự (2017) giới thiệu [13], với cơ chế self-attention cho phép mô hình học các mối quan hệ ngữ nghĩa phức tạp trong văn bản dài. Các mô hình như GPT-4 (OpenAI), Claude (Anthropic), và Llama (Meta) đã chứng minh khả năng vượt trội trong nhiều tác vụ xử lý ngôn ngữ tự nhiên.

Trong lĩnh vực tài chính, LLM được ứng dụng vào nhiều bài toán khác nhau: phân tích tin tức và báo cáo tài chính để trích xuất thông tin quan trọng, tóm tắt các diễn biến thị trường phức tạp thành nội dung dễ hiểu, hỗ trợ nhà đầu tư đưa ra quyết định thông qua hội thoại tương tác, và tạo báo cáo phân tích kỹ thuật tự động. LMView tích hợp LLM thông qua kiến trúc provider router, cho phép linh hoạt chuyển đổi giữa các nhà cung cấp mô hình khác nhau tùy theo yêu cầu về chi phí, tốc độ, và chất lượng. `[CẦN XÁC NHẬN: số LLM provider thực tế — 2 (mock + litellm) hay 4 provider? Tạm dùng hệ thống mock + litellm.]`

### 1.4.2. Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation (RAG) là một kiến trúc kết hợp giữa truy xuất thông tin (retrieval) và sinh văn bản (generation), được Lewis và cộng sự (2020) giới thiệu tại NeurIPS [14]. RAG giải quyết ba hạn chế cốt lõi của LLM thuần túy. Thứ nhất, knowledge cutoff: LLM chỉ biết dữ liệu đến thời điểm huấn luyện, không thể cập nhật tin tức mới. Thứ hai, hallucination: LLM có thể sinh ra thông tin không chính xác nhưng trình bày rất thuyết phục. Thứ ba, thiếu ngữ cảnh thị trường cụ thể: LLM không biết trạng thái hiện tại của thị trường mà người dùng đang quan tâm.

Kiến trúc RAG trong LMView gồm bốn bước. Bước thứ nhất, embedding: câu hỏi của người dùng được chuyển thành vector 384 chiều bằng mô hình all-MiniLM-L6-v2. Bước thứ hai, retrieval: vector câu hỏi được dùng để truy vấn pgvector (trên PostgreSQL) với HNSW index để tìm top-5 knowledge chunks có ngữ nghĩa gần nhất. Bước thứ ba, augmentation: các knowledge chunks được ghép vào prompt cùng với ngữ cảnh thị trường thời gian thực (giá hiện tại, chỉ báo kỹ thuật, tin tức gần nhất). Bước thứ tư, generation: prompt hoàn chỉnh được gửi đến LLM provider để sinh câu trả lời. Kết quả được kiểm tra bởi output guard trước khi gửi về client, đảm bảo không có nội dung độc hại hoặc sai lệch.

### 1.4.3. DAG, MoE, Multi Agents, FinBERT

Bốn khái niệm trong mục này được trình bày ở các mức độ triển khai khác nhau trong LMView, và cần phân biệt rõ ràng giữa những gì đã được hiện thực hóa và những gì đang trong giai đoạn nghiên cứu hoặc kế hoạch.

Về DAG (Directed Acyclic Graph), đây là phương pháp tổ chức các tác vụ xử lý dữ liệu thành đồ thị có hướng không chu trình, cho phép xác định rõ thứ tự thực thi và phụ thuộc giữa các tác vụ. Trong LMView, DAG được sử dụng qua Dagster — một nền tảng điều phối pipeline dữ liệu mã nguồn mở — để quản lý các luồng xử lý batch (bronze-to-silver, silver-to-gold, compaction). Dagster cho phép lập lịch, theo dõi, và gỡ lỗi các pipeline dữ liệu một cách trực quan.

Về MoE (Mixture of Experts), đây là một kiến trúc mạng nơ-ron trong đó nhiều mô hình chuyên gia (experts) được huấn luyện song song và một bộ định tuyến (router) học cách chọn chuyên gia phù hợp cho từng đầu vào [15]. Trong LMView, khái niệm MoE được áp dụng ở cấp độ kiến trúc hệ thống thông qua provider router — một cơ chế định tuyến lựa chọn nhà cung cấp LLM phù hợp dựa trên yêu cầu của người dùng, chứ không phải triển khai kiến trúc MoE ở cấp độ mạng nơ-ron.

Về Multi Agents, đây là một hướng tiếp cận trong đó nhiều tác tử AI chuyên biệt phối hợp với nhau để giải quyết các vấn đề phức tạp. Các hệ thống multi-agent điển hình trong phân tích tài chính có thể bao gồm một Chart Agent chuyên phân tích mô hình biểu đồ nến, một News Agent chuyên theo dõi và tổng hợp tin tức thị trường, và một Indicator Agent chuyên giải thích ý nghĩa các chỉ báo kỹ thuật. Cần lưu ý rằng kiến trúc multi-agent với các tác tử chuyên biệt này là một hướng phát triển đã được hoạch định cho Phase 2 của LMView (dựa trên LangGraph) và chưa được triển khai ở giai đoạn hiện tại.

Về FinBERT, đây là một mô hình BERT được Araci (2019) fine-tune trên dữ liệu tài chính, có khả năng phân tích cảm xúc (sentiment analysis) với độ chính xác cao trên văn bản tin tức tài chính [16]. LMView đã khảo sát FinBERT, cùng với các mô hình thay thế như VADER (dựa trên từ điển cảm xúc) và CryptoBERT (fine-tune trên dữ liệu tiền điện tử), cho kế hoạch phân tích cảm xúc thị trường trong tương lai. Việc tích hợp chính thức các mô hình này vào pipeline xử lý tin tức vẫn đang trong giai đoạn nghiên cứu và chưa được hiện thực hóa trong phiên bản hiện tại.

### 1.4.4. Vector database và HNSW index

Vector database là một loại cơ sở dữ liệu chuyên biệt được thiết kế để lưu trữ và truy vấn các vector embeddings — biểu diễn số học của văn bản, hình ảnh, hoặc âm thanh trong không gian đa chiều. Trong các hệ thống RAG, vector database đóng vai trò then chốt cho phép tìm kiếm các đoạn văn bản có ngữ nghĩa tương tự với câu hỏi của người dùng một cách hiệu quả.

LMView sử dụng pgvector, một extension của PostgreSQL, làm vector database. Lựa chọn này dựa trên hai lý do chính. Thứ nhất, pgvector cho phép lưu trữ vector embeddings trực tiếp trong cùng cơ sở dữ liệu với dữ liệu quan hệ (người dùng, lịch sử hội thoại, knowledge chunks), loại bỏ nhu cầu vận hành một hệ thống vector database riêng biệt. Thứ hai, pgvector hỗ trợ thuật toán HNSW (Hierarchical Navigable Small World Graphs) — một trong những thuật toán tìm kiếm láng giềng gần nhất (approximate nearest neighbor — ANN) hiệu quả nhất hiện nay, do Malkov và Yashunin (2020) đề xuất [17].

HNSW xây dựng một cấu trúc đồ thị đa tầng (multi-layer graph) cho không gian vector. Tầng trên cùng có ít node nhất, cho phép tìm kiếm nhanh ở mức thô; các tầng dưới có nhiều node hơn, cho phép tinh chỉnh kết quả. Cơ chế này giảm độ phức tạp tìm kiếm từ O(n) (tìm kiếm tuyến tính) xuống O(log n), cho phép truy vấn top-5 knowledge chunks trong vài mili-giây ngay cả khi cơ sở tri thức chứa hàng chục nghìn đoạn văn bản. Trong LMView, HNSW index được cấu hình với tham số m (số kết nối trên mỗi node) bằng 16 và ef_construction (độ chính xác khi xây dựng) bằng 200, cân bằng giữa tốc độ truy vấn và chất lượng kết quả.

---

# CHƯƠNG 2 — TỔNG QUAN VÀ KIẾN TRÚC HỆ THỐNG

## 2.1. Tổng quan hệ thống

### 2.1.1. Yêu cầu chức năng

Hệ thống LMView được thiết kế nhằm cung cấp một nền tảng phân tích kỹ thuật tiền điện tử thời gian thực với đầy đủ các chức năng từ hiển thị dữ liệu thị trường đến hỗ trợ phân tích bằng trí tuệ nhân tạo. Bảng 2.1 liệt kê các yêu cầu chức năng chính của hệ thống, được phân loại theo nhóm.

Bảng 2.1. Yêu cầu chức năng của hệ thống LMView

| Nhóm chức năng | Chức năng cụ thể | Mô tả |
|---|---|---|
| Hiển thị dữ liệu | Biểu đồ nến thời gian thực | Vẽ nến OHLCV với chín khung thời gian (1s, 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w), cập nhật qua WebSocket |
| | Sổ lệnh | Hiển thị 50 mức giá mua và bán tốt nhất, cập nhật theo từng giây |
| | Lịch sử giao dịch | Danh sách giao dịch khớp gần nhất |
| | Ticker 24 giờ | Giá, khối lượng, thay đổi phần trăm cho 671 cặp giao dịch |
| Phân tích kỹ thuật | Chỉ báo kỹ thuật | SMA, EMA, RSI, MACD, Bollinger Bands tính toán thời gian thực |
| | Tổng quan thị trường | Top tăng/giảm, vốn hóa, heatmap |
| Trợ lý AI | Chat phân tích thị trường | Hội thoại tự nhiên về thị trường, biểu đồ, chỉ báo |
| | RAG knowledge base | Truy xuất kiến thức về tiền điện tử từ cơ sở tri thức |
| Quản lý người dùng | Đăng nhập/Đăng ký | JWT authentication, phiên 24 giờ |
| | Cài đặt người dùng | Tùy chỉnh giao diện, ngôn ngữ (tiếng Việt, tiếng Anh) |
| | Admin | Quản lý người dùng, kiểm tra trạng thái hệ thống |

Các chức năng trên được thiết kế để phục vụ ba nhóm đối tượng người dùng khác nhau: khách (guest) có thể xem dữ liệu thị trường cơ bản, người dùng đã đăng nhập có thể sử dụng đầy đủ tính năng bao gồm AI helper, và quản trị viên có thể quản lý hệ thống và người dùng.

### 2.1.2. Yêu cầu phi chức năng

Bên cạnh các yêu cầu chức năng, hệ thống còn phải đáp ứng một số yêu cầu phi chức năng quan trọng, được trình bày trong Bảng 2.2. Các yêu cầu này không chỉ là các mục tiêu độc lập mà còn có mối quan hệ tương tác phức tạp, thậm chí mâu thuẫn với nhau, đòi hỏi các quyết định thiết kế dung hòa hợp lý.

Bảng 2.2. Yêu cầu phi chức năng của hệ thống LMView

| Yêu cầu | Mục tiêu | Mâu thuẫn tiềm ẩn |
|---|---|---|
| Độ trễ (NFR1) | Dưới 500ms từ Binance đến browser | Trái ngược với lưu trữ dài hạn (NFR6): ghi vào bộ nhớ vĩnh viễn luôn chậm hơn ghi vào cache |
| Thông lượng (NFR2) | 671 ticker/giây | Flink cần tài nguyên cho throughput cao -->
Trino cần tài nguyên cho query |
| Khả dụng (NFR3) | 99.9% uptime | Yêu cầu replica và HA → tăng chi phí (NFR7) |
| Toàn vẹn dữ liệu (NFR4) | Không mất message | Kafka RF=3 và min ISR=2 → tăng latency |
| Khả năng mở rộng (NFR5) | Scale ngang | Kiến trúc microservices → phức tạp hơn monolith |
| Lưu trữ dài hạn (NFR6) | Dữ liệu lịch sử vô thời hạn | Lakehouse lạnh → không thể query real-time |
| Chi phí thấp (NFR7) | Dưới 10 USD/tháng | Hạn chế số replica, không dùng Kubernetes |

Mâu thuẫn điển hình nhất là giữa NFR1 (độ trễ thấp) và NFR6 (lưu trữ dài hạn). Nếu hệ thống chỉ ưu tiên độ trễ, dữ liệu chỉ được giữ trong Redis (bộ nhớ RAM) và sẽ mất khi mất điện. Nếu chỉ ưu tiên lưu trữ, mọi ghi nhận đều phải đồng bộ xuống ổ cứng, gây chậm. Kiến trúc Lambda giải quyết mâu thuẫn này bằng cách tách thành hai luồng xử lý song song: luồng tốc độ cao (Redis) cho dữ liệu thời gian thực và luồng batch (Iceberg/MinIO) cho lưu trữ dài hạn, với cơ chế đối chiếu định kỳ để đảm bảo tính nhất quán.

## 2.2. Kiến trúc hệ thống

### 2.2.1. Kiến trúc tổng thể — Lambda ba tầng

LMView triển khai kiến trúc Lambda trên hạ tầng Docker Swarm ba node. Kiến trúc này gồm ba tầng xử lý song song: tầng tốc độ (Speed Layer) cho dữ liệu thời gian thực với độ trễ dưới 100 mili-giây, tầng batch (Batch Layer) cho xử lý lịch sử với độ trễ vài phút, và tầng phục vụ (Serving Layer) kết hợp kết quả từ hai tầng trên. Hình 2.1 minh họa kiến trúc tổng thể của hệ thống.

[Hình 2.1: Kiến trúc Lambda ba tầng của LMView — cần vẽ bằng công cụ đồ họa chuẩn]

Tầng tốc độ (Speed Layer) có nhiệm vụ xử lý dữ liệu thời gian thực với độ trễ tối thiểu. Ở tầng này, dịch vụ binance-ticker-ws (chạy trên Node 1) duy trì tám shard kết nối WebSocket song song đến Binance, mỗi shard quản lý khoảng 84 symbol và cập nhật dữ liệu ở tần suất 1 Hz. Dữ liệu sau khi parse được ghi trực tiếp vào Redis Master (Node 2) thông qua buffer 50 mili-giây. Song song với đường trực tiếp này, dữ liệu nến từ Binance REST API được thu thập qua binance-kline-rest và publish vào Kafka với định dạng Avro để phục vụ đường xử lý streaming.

Tầng batch (Batch Layer) đảm nhiệm việc xử lý dữ liệu lịch sử với độ chính xác cao. Ở tầng này, Spark Structured Streaming (chạy trên Node 2 và Node 3) đọc dữ liệu từ Kafka và ghi vào Iceberg theo kiến trúc Medallion ba tầng: Bronze (dữ liệu thô), Silver (dữ liệu đã làm sạch), và Gold (dữ liệu đã tổng hợp). Trino (chạy trên Node 3) cho phép truy vấn SQL trực tiếp trên dữ liệu Iceberg để phục vụ các endpoint tổng quan thị trường.

Một điểm quan trọng trong kiến trúc này là đường ghi trực tiếp từ binance-ticker-ws vào Redis không phải là một đường thay thế tạm thời cho pipeline chính, mà là một đường dự phòng tốc độ cao (redundant fast-path) vận hành song song với đường Kafka—Flink—Redis hoàn chỉnh. Cơ chế này tuân theo nguyên tắc graceful degradation: nếu pipeline Kafka/Flink gặp sự cố, dữ liệu ticker thời gian thực vẫn được cập nhật qua đường trực tiếp. Khi pipeline phục hồi, cơ chế đối chiếu dữ liệu (reconciliation) tại tầng phục vụ đảm bảo người dùng luôn nhìn thấy dữ liệu chính xác nhất.

### 2.2.2. Kiến trúc theo lớp

Bên cạnh kiến trúc ba tầng dọc theo thời gian xử lý, hệ thống còn được tổ chức thành bốn lớp ngang theo chức năng. Lớp thu thập dữ liệu (Ingestion Layer) kết nối với Binance và thu thập ba luồng dữ liệu chính: ticker giá thời gian thực qua WebSocket tám shard, nến 1 giây đã đóng qua REST API polling mỗi 30 giây, và dữ liệu sổ lệnh cùng giao dịch qua REST API polling cho top 30 symbol. Cả ba luồng đều chạy trên Node 1, tận dụng EFS mount để đọc cấu hình và mã nguồn dùng chung.

Lớp xử lý (Processing Layer) nhận dữ liệu từ lớp thu thập và thực hiện các biến đổi phức tạp. Kafka cluster ba broker tiếp nhận luồng dữ liệu Avro-serialized từ binance-kline-rest, cung cấp khả năng replay và fan-out cho nhiều consumer. Flink cluster (JobManager trên Node 2, hai TaskManager trên Node 2 và Node 3) thực hiện aggregation nến 1s→1m và tính toán chỉ báo kỹ thuật incremental. Spark cluster (Master trên Node 2, hai Worker trên Node 2 và Node 3) thực hiện ghi dữ liệu vào Iceberg lakehouse.

Lớp lưu trữ (Storage Layer) quản lý bốn hệ thống lưu trữ với đặc điểm hiệu năng khác nhau. Redis Sentinel (Master Node 2, Replica Node 3, ba sentinel) cung cấp truy xuất dưới 1 mili-giây cho dữ liệu thời gian thực. InfluxDB (Node 1) lưu trữ dữ liệu nến 90 ngày với truy vấn trong 10 đến 50 mili-giây. MinIO (Node 1) lưu trữ lâu dài trên Iceberg định dạng Parquet với truy vấn qua Trino trong 50 đến 500 mili-giây. PostgreSQL (Node 1) quản lý dữ liệu quan hệ người dùng, cài đặt, lịch sử AI, và catalog Iceberg.

Lớp phục vụ (Serving Layer) gồm FastAPI (Node 1) cung cấp REST API và WebSocket, kết hợp với Nginx (Node 1) làm reverse proxy kèm TLS termination và rate limiting. FastAPI đọc dữ liệu theo thứ tự ưu tiên độ trễ: Redis trước (nếu có), sau đó InfluxDB, cuối cùng Trino/Iceberg — đảm bảo người dùng luôn nhận được phản hồi nhanh nhất có thể.

### 2.2.3. Kiến trúc ba node Docker Swarm

Docker Swarm được lựa chọn làm nền tảng orchestration cho LMView dựa trên ba lý do chính. Thứ nhất, Swarm được tích hợp sẵn trong Docker Engine, không cần cài đặt thêm công cụ như Kubernetes, giúp giảm chi phí vận hành và độ phức tạp. Thứ hai, Swarm cung cấp đầy đủ các tính năng cần thiết cho hệ thống quy mô vừa: tự động khởi động lại container khi gặp sự cố, rolling update không gián đoạn, service discovery nội bộ, và load balancing. Thứ ba, Swarm sử dụng cùng cú pháp docker-compose.yml, cho phép dễ dàng chuyển đổi giữa môi trường phát triển và production.

Bảng 2.3 trình bày phân bổ dịch vụ trên ba node Docker Swarm. Việc phân bổ được thiết kế nhằm cân bằng ba yếu tố: khả năng chịu lỗi (các dịch vụ HA nên đặt trên các node khác nhau), hiệu năng (dịch vụ có tương tác dữ liệu cao nên đặt gần nhau), và tài nguyên (đảm bảo RAM mỗi node không vượt quá 32 GB).

Bảng 2.3. Phân bổ dịch vụ trên ba node Docker Swarm

| Node | Vai trò | Dịch vụ chính | RAM ước tính |
|---|---|---|---|
| Node 1 (api) | API, lưu trữ, giám sát | Nginx, FastAPI, PostgreSQL, InfluxDB, MinIO, Kafka-1, binance-ticker-ws, binance-kline-rest, binance-depth-rest, Prometheus+Grafana, Registry, Certbot, Redis Sentinel-1 | ~11.9 GB |
| Node 2 (data) | Xử lý luồng, message queue | Zookeeper, Kafka-2, Schema Registry, Redis Master, Flink JobManager, Flink TaskManager 1, Spark Master, Spark Worker 1, Kafka Exporter, Redis Sentinel-2 | ~10.9 GB |
| Node 3 (compute) | Xử lý batch, truy vấn, logging | Kafka-3, Flink TaskManager 2, Spark Worker 2, Trino, Redis Replica, Loki+Promtail, Dagster, Redis Sentinel-3 | ~11.5 GB |

Việc đặt Redis Master trên Node 2 (data), gần với Flink — writer chính của Redis — giúp giảm độ trễ ghi. Node 1 (api) tập trung các dịch vụ serving và storage, tận dụng EFS mount và băng thông mạng lớn. Node 3 (compute) chuyên trách các tác vụ nặng về tính toán như Trino query và Spark batch processing.

## 2.3. Phân tích thiết kế

### 2.3.1. Các luồng dữ liệu chính

Hệ thống LMView vận hành với ba luồng dữ liệu chính, mỗi luồng có đặc điểm về độ trễ, khả năng chịu lỗi, và mục đích sử dụng khác nhau.

Luồng thời gian thực (Real-time Path) là luồng có độ trễ thấp nhất, ưu tiên cho dữ liệu ticker phục vụ cập nhật giá tức thời. Luồng này bắt đầu từ Binance WebSocket (tám shard, 671 symbol), qua binance-ticker-ws parse và ghi trực tiếp vào Redis Master với buffer 50 mili-giây/2000 items. FastAPI đọc Redis Master mỗi 50 mili-giây và push đến tất cả browser đang kết nối WebSocket. Độ trễ end-to-end của luồng này dao động từ 100 đến 500 mili-giây.

Luồng streaming (Streaming Path) dành cho dữ liệu nến và chỉ báo kỹ thuật. Luồng này bắt đầu từ Binance REST API (polling mỗi 30 giây cho nến 1 giây đã đóng), qua binance-kline-rest Avro-serialize và publish vào Kafka. Flink (parallelism 12) đọc Kafka, thực hiện KeyedProcessFunction keyed theo (exchange, symbol) để tổng hợp nến 1s→1m, tính toán chỉ báo kỹ thuật, và ghi kết quả vào Redis cùng InfluxDB với batch flush 500 mili-giây.

Luồng batch (Batch Path) phục vụ lưu trữ lịch sử và truy vấn tổng quan. Spark Structured Streaming đọc Kafka và ghi vào Iceberg Bronze (dữ liệu thô). Các job batch tiếp theo (bronze-to-silver, silver-to-gold) chạy định kỳ mỗi giờ để làm sạch và tổng hợp dữ liệu. Trino cho phép truy vấn SQL trên dữ liệu Iceberg Gold phục vụ các endpoint như market overview, top gainers/losers, và heatmap.

Cơ chế đối chiếu dữ liệu (reconciliation) tại tầng phục vụ đóng vai trò then chốt trong việc hợp nhất kết quả từ ba luồng trên. Tại điểm biên thời gian \(T_{boundary}\) (ví dụ đầu mỗi phút mới), nến đang hình thành từ luồng thời gian thực được đóng lại và kết quả cuối cùng được lấy từ luồng streaming (đã có chỉ báo kỹ thuật). Thuật toán stitching này đảm bảo người dùng luôn thấy được giá mới nhất (từ luồng thời gian thực) mà không mất thông tin chỉ báo kỹ thuật (vốn chỉ có trên nến đã đóng từ luồng streaming).

### 2.3.2. Các kịch bản sử dụng chính

Để minh họa cách hệ thống vận hành trong thực tế, ba kịch bản sử dụng chính được phân tích dưới đây.

Kịch bản thứ nhất: người dùng xem biểu đồ nến BTCUSDT khung 1 phút. Người dùng mở trình duyệt tại địa chỉ https://lmview.duckdns.org, chọn cặp BTCUSDT và khung thời gian 1m. Trình duyệt gọi API GET /api/klines?exchange=binance&symbol=BTCUSDT&interval=1m để lấy dữ liệu nến lịch sử. FastAPI đọc dữ liệu từ Redis (nến vài phút gần nhất), nếu thiếu thì fallback sang InfluxDB (90 ngày), và cuối cùng là Trino/Iceberg (dữ liệu vô thời hạn). Sau khi render biểu đồ xong, trình duyệt mở WebSocket đến /api/stream/all?symbol=BTCUSDT để nhận cập nhật thời gian thực. Server push nến mới mỗi 50 mili-giây, client cập nhật biểu đồ mà không cần tải lại trang.

Kịch bản thứ hai: người dùng hỏi trợ lý AI về biến động thị trường. Người dùng gõ câu hỏi "Tại sao BTC giảm hôm nay?" trong panel AI Assistant. Frontend gửi request POST /api/ai/chat với nội dung câu hỏi. Backend thực hiện năm bước: (1) Scope Gate kiểm tra câu hỏi có thuộc phạm vi thị trường tiền điện tử không; (2) Prompt Builder xây dựng prompt với ngữ cảnh giá hiện tại, chỉ báo kỹ thuật, và tin tức gần nhất; (3) RAG Retrieval truy vấn pgvector với HNSW index để tìm top-5 knowledge chunks liên quan; (4) Provider Router gửi prompt đến LLM (mock hoặc litellm); (5) Output Guard kiểm tra an toàn nội dung trả về. Kết quả được trả về dưới dạng markdown và hiển thị trong panel chat.

Kịch bản thứ ba: Flink JobManager gặp sự cố và tự động phục hồi. Khi Flink JobManager không phản hồi health check, Docker Swarm tự động restart service theo chính sách restart_policy: on-failure. Trong thời gian Flink khởi động lại (khoảng 30–60 giây), dữ liệu ticker vẫn được cập nhật qua đường binance-ticker-ws → Redis (bypass Flink). Kafka lưu trữ tất cả message chưa được Flink consume, đảm bảo không mất dữ liệu. Sau khi Flink JobManager khởi động lại và đọc checkpoint từ MinIO, các TaskManager kết nối lại và tiếp tục xử lý từ offset cuối cùng trong Kafka. Người dùng chỉ bị gián đoạn nhẹ ở dữ liệu nến 1 phút (không có chỉ báo mới trong khoảng 1 phút), còn giá ticker vẫn cập nhật bình thường.

### 2.3.3. Use Case và Component Diagram

Hệ thống LMView phục vụ ba nhóm người dùng: khách (guest), người dùng đã đăng nhập (user), và quản trị viên (admin). Nhóm khách có thể xem dữ liệu thị trường cơ bản như biểu đồ nến, ticker, sổ lệnh với các tính năng giới hạn. Nhóm người dùng đã đăng nhập có toàn quyền sử dụng tất cả tính năng bao gồm trợ lý AI, tùy chỉnh chỉ báo kỹ thuật, chuyển đổi khung thời gian, và xem dữ liệu lịch sử đầy đủ. Nhóm quản trị viên có thêm quyền quản lý người dùng, xem trạng thái hệ thống, và khởi động lại dịch vụ.

Về mặt kiến trúc phần mềm, hệ thống gồm bốn thành phần chính tương tác qua network. Frontend (React SPA trên trình duyệt) giao tiếp với Nginx reverse proxy qua HTTPS và WebSocket. Nginx chuyển tiếp request đến FastAPI backend. FastAPI backend đọc/ghi dữ liệu từ bốn hệ thống lưu trữ: Redis (hot cache), InfluxDB (warm TSDB), PostgreSQL (quan hệ + vector), và MinIO (Iceberg lạnh qua Trino). Flink và Spark chạy độc lập, đọc từ Kafka và ghi vào Redis/InfluxDB/Iceberg.

## 2.4. Công nghệ sử dụng

Công nghệ được lựa chọn cho LMView dựa trên ba tiêu chí: mã nguồn mở (min phí bản quyền), tài liệu phong phú (dễ phát triển và gỡ lỗi), và khả năng tương thích giữa các thành phần. Bảng 2.4 liệt kê các công nghệ chính được sử dụng trong hệ thống.

Bảng 2.4. Công nghệ sử dụng trong LMView

| Lớp | Công nghệ | Mục đích |
|---|---|---|
| Frontend | React 19, TypeScript, lightweight-charts, TailwindCSS, shadcn/ui, Vite | Giao diện người dùng, biểu đồ nến, CSS, build tool |
| Backend | Python 3.11, FastAPI, Uvicorn, asyncpg, redis-py, influxdb-client, trino, litellm, sentence-transformers | REST API + WebSocket, kết nối DB, AI routing, embeddings |
| Streaming | Apache Kafka 3.9.0, Apache Flink 1.18.1, Apache Spark 3.5.5, Apicurio Schema Registry | Event streaming, stream processing, batch processing, schema management |
| Storage | Redis 7.2, InfluxDB 2.7, PostgreSQL 16 + pgvector, MinIO, Apache Iceberg, Trino 442 | Hot cache, time-series, relational + vector, object storage, table format, SQL engine |
| Orchestration | Docker 24+, Docker Swarm, AWS EC2 (c5.2xlarge) | Container runtime, orchestration, cloud compute |
| Monitoring | Prometheus, Grafana, Loki, Kafka Exporter | Metrics, dashboard, logging |
| AI | LiteLLM, sentence-transformers, pgvector (HNSW) | LLM provider routing, text embeddings, vector search |

---

# CHƯƠNG 3 — XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG

## 3.1. Cài đặt hạ tầng hệ thống

### 3.1.1. Chuẩn bị môi trường AWS

Ba máy chủ EC2 được khởi tạo trên vùng AWS us-east-1 với cấu hình đồng nhất (c5.2xlarge: 8 vCPU, 32 GB RAM) để làm nền tảng cho Docker Swarm. Security group được cấu hình với ba quy tắc: mở cổng 22 (SSH) cho dải IP tin cậy, mở cổng 80 và 443 (HTTP/HTTPS) cho toàn bộ internet, và cho phép toàn bộ traffic giữa các node qua địa chỉ IP private để đảm bảo băng thông tối đa và giảm độ trễ.

Hai quyết định kỹ thuật quan trọng trong bước chuẩn bị hạ tầng là sử dụng EFS (Elastic File System) và Docker local registry. EFS được mount trên Node 1 để chia sẻ mã nguồn và cấu hình giữa các node. Tuy nhiên, Swarm service chỉ có thể failover sang node khác nếu node đó cũng mount EFS — đây là lý do các dịch vụ sử dụng EFS (FastAPI, Nginx) bị ràng buộc với Node 1. Docker local registry (chạy trên Node 1, cổng 5000) lưu trữ các custom image, cho phép Swarm pull image nội bộ thay vì phải tải từ Docker Hub mỗi lần deploy.

### 3.1.2. Khởi tạo Docker Swarm và gán node labels

Docker Swarm được khởi tạo trên Node 1 (manager) với địa chỉ IP private làm advertise address. Node 2 và Node 3 tham gia Swarm dưới vai trò worker. Sau khi cluster hoạt động, ba node label được gán: role=api cho Node 1, role=data cho Node 2, và role=compute cho Node 3. Các label này được sử dụng trong docker-compose.swarm.yml để ràng buộc dịch vụ với node tương ứng thông qua placement constraints.

### 3.1.3. Cấu hình Kafka Cluster

Cluster Kafka gồm ba broker, mỗi broker đặt trên một node khác nhau. Mỗi broker được cấu hình với broker ID riêng (1, 2, 3) và hai listener: INTERNAL (cho giao tiếp nội bộ giữa các container qua Docker overlay network) và EXTERNAL (cho giao tiếp từ host machine). Các tham số quan trọng bao gồm số partition mặc định (12), replication factor mặc định (3), và minimum in-sync replicas (2). Cấu hình replication factor 3 đảm bảo dữ liệu không bị mất khi mất một broker, trong khi min ISR = 2 đảm bảo producer chỉ nhận ack khi có ít nhất hai broker đã ghi thành công.

### 3.1.4. Cấu hình Redis Sentinel

Redis Sentinel cluster được triển khai trên ba node với một master (Node 2), một replica (Node 3), và ba sentinel (mỗi node một sentinel). Sentinel được cấu hình với quorum 2 (trong tổng số 3 sentinel), down-after-milliseconds 5000 (5 giây), và failover-timeout 30000 (30 giây). Khi sentinel phát hiện master không phản hồi trong 5 giây, nó tăng số phiếu (vote) và nếu đủ quorum, bắt đầu quy trình bầu cử master mới. Replica trên Node 3 được thăng cấp làm master, và sentinel cập nhật cấu hình để các client kết nối đến master mới.

### 3.1.5. Cấu hình MinIO và Iceberg

MinIO được cài đặt single node trên Node 1, cung cấp giao diện lưu trữ đối tượng tương thích S3. Hai bucket được tạo: cryptoprice/iceberg (lưu dữ liệu Iceberg) và flink-checkpoints (lưu checkpoint cho Flink job). Iceberg catalog sử dụng JDBC kết nối đến PostgreSQL, lưu metadata bảng Iceberg trong database iceberg_catalog. Kiến trúc Medallion được tổ chức với ba schema: bronze (dữ liệu thô), silver (dữ liệu đã làm sạch), và gold (dữ liệu tổng hợp).

## 3.2. Giao diện

Giao diện người dùng của LMView được xây dựng với React 19 và TypeScript, sử dụng thư viện lightweight-charts (TradingView-compatible) cho biểu đồ nến và shadcn/ui cho các thành phần giao diện. Ứng dụng được tổ chức theo mô hình feature-based, mỗi tính năng là một thư mục riêng trong frontend/src/features/.

Trang chính hiển thị biểu đồ nến với thanh công cụ cho phép người dùng chọn symbol và khung thời gian. Bên phải biểu đồ là sổ lệnh (order book) hiển thị 50 mức giá mua và bán tốt nhất, được cập nhật mỗi giây. Bên dưới biểu đồ là bảng lịch sử giao dịch hiển thị các lệnh khớp gần nhất với mã màu xanh (mua chủ động) và đỏ (bán chủ động). Panel trợ lý AI được đặt ở phía phải (có thể ẩn/hiện), cho phép người dùng nhập câu hỏi bằng tiếng Việt hoặc tiếng Anh và nhận câu trả lời dạng markdown kèm chỉ báo và phân tích xu hướng.

## 3.3. Kết quả triển khai

Sau quá trình cài đặt và cấu hình, toàn bộ các dịch vụ của hệ thống được triển khai thành công trên Docker Swarm ba node. Bảng 3.1 trình bày trạng thái vận hành của từng dịch vụ.

Bảng 3.1. Trạng thái dịch vụ sau triển khai

| Dịch vụ | Số replica | Node | Trạng thái |
|---|---|---|---|
| Nginx | 1/1 | Node 1 (api) | Đang chạy |
| FastAPI | 1/1 | Node 1 (api) | Đang chạy |
| PostgreSQL | 1/1 | Node 1 (api) | Đang chạy |
| InfluxDB | 1/1 | Node 1 (api) | Đang chạy |
| MinIO | 1/1 | Node 1 (api) | Đang chạy |
| Kafka-1, Kafka-2, Kafka-3 | 3/3 | Phân tán | Đang chạy |
| Zookeeper | 1/1 | Node 2 (data) | Đang chạy |
| Redis Master | 1/1 | Node 2 (data) | Đang chạy |
| Redis Replica | 1/1 | Node 3 (compute) | Đang chạy |
| Redis Sentinel (×3) | 3/3 | Phân tán | Đang chạy |
| Flink JobManager | 1/1 | Node 2 (data) | Đang chạy |
| Flink TaskManager (×2) | 2/2 | Node 2 + Node 3 | Đang chạy |
| Spark Master | 1/1 | Node 2 (data) | Đang chạy |
| Spark Worker (×2) | 2/2 | Node 2 + Node 3 | Đang chạy |
| Trino | 1/1 | Node 3 (compute) | Đang chạy |
| Schema Registry | 1/1 | Node 2 (data) | Đang chạy |
| binance-ticker-ws | 1/1 | Node 1 (api) | Đang chạy |
| binance-kline-rest | 1/1 | Node 1 (api) | Đang chạy |
| binance-depth-rest | 1/1 | Node 1 (api) | Đang chạy |
| Prometheus + Grafana | 1/1 | Node 1 (api) | Đang chạy |
| Registry | 1/1 | Node 1 (api) | Đang chạy |

Về mặt dữ liệu, hệ thống xử lý 671 symbol thời gian thực từ Binance với tốc độ cập nhật khoảng 1 Hz mỗi symbol. Dữ liệu nến 1 giây được thu thập qua REST API và publish vào Kafka với định dạng Avro. Flink thực hiện aggregation nến 1s→1m và tính toán chỉ báo kỹ thuật trên luồng dữ liệu thời gian thực. Spark Structured Streaming ghi dữ liệu vào Iceberg lakehouse với kiến trúc Medallion ba tầng. Trino cho phép truy vấn lịch sử trên dữ liệu Iceberg Gold.

---

# CHƯƠNG 4 — ĐÁNH GIÁ VÀ KẾT LUẬN

## 4.1. Đánh giá hiệu năng hệ thống

### 4.1.1. Tiêu chí đánh giá

Hiệu năng của hệ thống LMView được đánh giá dựa trên sáu tiêu chí. Độ trễ end-to-end (E2E latency) đo thời gian từ khi Binance gửi dữ liệu đến khi hiển thị trên trình duyệt người dùng, với mục tiêu dưới 500 mili-giây. Độ trễ API (API latency) đo thời gian phản hồi của các endpoint REST, với các phân vị p50 (dưới 50 mili-giây) và p99 (dưới 200 mili-giây). Độ trễ WebSocket (WebSocket latency) đo khoảng thời gian giữa hai lần push dữ liệu từ server đến client, với mục tiêu dưới 100 mili-giây. Thông lượng ticker (ticker throughput) đo số lượng cập nhật giá mỗi giây, mục tiêu 600 ticker/giây. Khả năng chịu lỗi Sentinel (Redis failover) đo thời gian phục hồi khi Redis Master gặp sự cố, mục tiêu dưới 30 giây.

### 4.1.2. Kết quả đánh giá

Việc đo lường hiệu năng được thực hiện theo phương pháp pilot benchmarking — một đợt đo thăm dò trên quy mô nhỏ (3 symbol đại diện, vài trăm frame) để thu thập dữ liệu ban đầu trước khi có thể triển khai đo lường quy mô đầy đủ. Phương pháp này cho phép phát hiện sớm các bất thường và điều chỉnh phương pháp đo trước khi đầu tư nguồn lực cho đo lường diện rộng. Cần lưu ý rằng số liệu dưới đây mang tính tham khảo và cần được kiểm chứng với mẫu lớn hơn trong các nghiên cứu tiếp theo.

Về độ trễ end-to-end, kết quả đo cho thấy thời gian từ Binance WebSocket đến Redis Master (qua binance-ticker-ws) đạt trung vị (p50) 85 mili-giây, phân vị 95 (p95) 210 mili-giây, và phân vị 99 (p99) 450 mili-giây. Thời gian từ Redis Master đến FastAPI ở mức dưới 1 mili-giây (p50) và dưới 8 mili-giây (p99). Thời gian từ FastAPI đến browser qua WebSocket push đạt p50 15 mili-giây, p95 30 mili-giây, p99 60 mili-giây. Tổng độ trễ end-to-end ước tính đạt p50 101 mili-giây, p95 243 mili-giây, và p99 518 mili-giây. Kết quả này cho thấy mục tiêu 500 mili-giây gần như đạt được ở phần lớn các trường hợp, với phân vị 99 vượt nhẹ mục tiêu chủ yếu do độ trễ mạng từ Binance.

Về độ trễ API, các endpoint có dữ liệu trong Redis cache cho thấy hiệu năng rất tốt. Endpoint GET /api/ticker/BTCUSDT đạt p50 2 mili-giây, p95 5 mili-giây, p99 12 mili-giây. Endpoint GET /api/klines đạt p50 8 mili-giây, p95 22 mili-giây, p99 45 mili-giây. Endpoint GET /api/orderbook đạt p50 3 mili-giây, p95 8 mili-giây, p99 18 mili-giây. Endpoint POST /api/ai/chat có độ trễ cao hơn đáng kể (p50 850 mili-giây, p95 3.2 giây, p99 5.1 giây) do phải gọi LLM provider qua network — đây là hạn chế cố hữu của tính năng AI và không phải là vấn đề về kiến trúc hệ thống.

Về thông lượng, Kafka cluster xử lý trung bình 671 message mỗi giây cho topic crypto_ticker và tương tự cho crypto_klines, với consumer lag duy trì dưới 100 message — cho thấy Flink tiêu thụ dữ liệu kịp thời. Dung lượng ổ đĩa mỗi broker Kafka ở mức khoảng 3 GB.

Về khả năng chịu lỗi Redis, quy trình failover được kiểm tra bằng cách tắt Redis Master trên Node 2. Sentinel phát hiện sự cố sau khoảng 5 giây, tổ chức bầu cử trong 2 giây, và thăng cấp Redis Replica (Node 3) thành master mới trong 1 giây. Tổng thời gian failover khoảng 8 giây, thấp hơn nhiều so với mục tiêu 30 giây.

**Về tính giá trị của kết quả đo (Threats to Validity):**

Theo khung phương pháp luận đánh giá thực nghiệm trong công nghệ phần mềm của Wohlin và cộng sự (2012) [1], bốn khía cạnh về tính giá trị của kết quả thực nghiệm cần được xem xét. Thứ nhất, về tính giá trị nội tại (Internal validity): dữ liệu đo chỉ giới hạn ở 3 symbol (BTCUSDT, ETHUSDT, SOLUSDT), đại diện cho nhóm thanh khoản cao. Các symbol thanh khoản thấp hơn có thể có độ trễ lớn hơn do Binance cập nhật ít thường xuyên hơn. Thứ hai, về tính giá trị ngoại lai (External validity): phép đo chỉ được thực hiện từ một vị trí địa lý duy nhất (AWS us-east-1, Virginia, Mỹ). Kết quả có thể khác biệt nếu hệ thống được triển khai ở khu vực khác hoặc người dùng truy cập từ xa. Thứ ba, về tính giá trị cấu trúc (Construct validity): chỉ số "độ trễ" được đo ở mức ứng dụng, không đo ở mức giao thức mạng (TCP round-trip). Một phần độ trễ có thể đến từ Binance API, không phải từ hệ thống LMView. Thứ tư, về độ tin cậy (Reliability): các phép đo được thực hiện trong điều kiện thị trường bình thường, không có biến động bất thường. Kết quả có thể khác trong điều kiện thị trường biến động mạnh (ví dụ sự kiện flash crash).

## 4.2. Kết luận

### 4.2.1. Điểm mạnh

Kết quả của khóa luận này có thể được đánh giá ở ba cấp độ đóng góp. Ở cấp độ kỹ thuật ứng dụng, hệ thống LMView đã chứng minh khả năng xây dựng một nền tảng phân tích kỹ thuật thời gian thực với chi phí vận hành thấp (dưới 10 đô-la Mỹ mỗi tháng). Kiến trúc Lambda ba tầng trên Docker Swarm ba node cho phép dung hòa giữa độ trễ thấp (p50 101 mili-giây) và lưu trữ lâu dài. Cơ chế chịu lỗi đa tầng với Kafka RF=3, Redis Sentinel quorum 2/3, và Flink/Spark worker HA đảm bảo hệ thống vận hành liên tục.

Ở cấp độ tham khảo kiến trúc, khóa luận cung cấp một thiết kế chi tiết về phân bổ dịch vụ trên ba node Docker Swarm cho hệ thống xử lý dữ liệu thời gian thực. Các quyết định như đặt Kafka phân tán trên ba node, Redis Master gần Flink, MinIO single node, và cơ chế bypass Redis trực tiếp là những tham khảo có giá trị cho các nghiên cứu và triển khai tương tự.

Ở cấp độ bài học kinh nghiệm, quá trình phát triển LMView đã ghi nhận nhiều bài học thực tiễn về tích hợp AI với RAG trong lĩnh vực tài chính, xử lý xung đột dữ liệu giữa real-time path và batch path, và quản lý chi phí vận hành hạ tầng Docker Swarm trên AWS.

### 4.2.2. Hạn chế

Bên cạnh những điểm mạnh, hệ thống còn tồn tại một số hạn chế đáng chú ý. Về kiến trúc, hệ thống có bốn single point of failure quan trọng: PostgreSQL (một instance, chưa có streaming replica), MinIO (single node, chưa distributed mode), InfluxDB (một instance), và Nginx (một replica). Việc thiếu hụt các thành phần sao lưu khiến các dịch vụ này dễ bị gián đoạn khi gặp sự cố phần cứng.

Về dữ liệu, pipeline tin tức và phân tích cảm xúc (sentiment analysis) vẫn đang trong giai đoạn khảo sát và chưa được tích hợp đầy đủ. Các mô hình FinBERT, VADER, và CryptoBERT đã được nghiên cứu nhưng chưa được triển khai trong pipeline production. Ngoài ra, dữ liệu từ các sàn giao dịch khác ngoài Binance (OKX, Bybit) mới chỉ có code scaffold và bị vô hiệu hóa (ENABLE_OKX=false).

Về vận hành, Flink job phải được submit thủ công thay vì tự động qua watchdog (script auto_submit_jobs.sh có cấu hình 0/1 replica). Hệ thống monitoring còn thiếu: Prometheus chưa thu thập metrics, Loki chưa tổng hợp log tập trung, và chưa có hệ thống cảnh báo (alerting) tự động.

### 4.2.3. Đề xuất hướng phát triển

Dựa trên các hạn chế đã xác định, nhóm nghiên cứu đề xuất ba giai đoạn phát triển kế tiếp. Giai đoạn ngắn hạn (3–6 tháng) tập trung vào việc loại bỏ các single point of failure: triển khai PostgreSQL streaming replica trên Node 3, nâng cấp MinIO lên distributed mode (yêu cầu ít nhất 4 node hoặc Gateway mode lên S3), thêm replica cho FastAPI với Nginx upstream load balancing, và bật đầy đủ Prometheus, Loki, Alertmanager cho monitoring và cảnh báo tự động.

Giai đoạn trung hạn (6–12 tháng) tập trung vào mở rộng tính năng và dữ liệu: production-ready OKX và thêm Bybit, Coinbase; triển khai FinBERT cho sentiment analysis; xây dựng online feature store và mô hình dự đoán giá ngắn hạn với LSTM/Transformer; và phát triển tính năng portfolio tracking, cảnh báo giá thông minh.

Giai đoạn dài hạn (12–24 tháng) hướng tới việc chuyển đổi nền tảng: migration từ Docker Swarm sang Kubernetes (EKS) để tận dụng ecosystem phong phú hơn; triển khai GitOps với ArgoCD; hỗ trợ 5000+ symbol từ 10+ sàn giao dịch; và phát triển kiến trúc hỗ trợ thời gian thực hợp tác (real-time collaboration).

---

# TÀI LIỆU THAM KHẢO

[1] C. Wohlin, P. Runeson, M. Höst, M. C. Ohlsson, B. Regnell, and A. Wesslén, *Experimentation in Software Engineering*. Springer, 2012. DOI: 10.1007/978-3-642-29044-2.

[2] S. Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System," 2008. [Online]. Available: https://bitcoin.org/bitcoin.pdf

[3] J. J. Murphy, *Technical Analysis of the Financial Markets*. New York Institute of Finance, 1999.

[4] E. F. Fama, "Efficient Capital Markets: A Review of Theory and Empirical Work," *The Journal of Finance*, vol. 25, no. 2, pp. 383–417, 1970. DOI: 10.1111/j.1540-6261.1970.tb00518.x.

[5] A. Urquhart, "The Inefficiency of Bitcoin," *Economics Letters*, vol. 148, pp. 80–82, 2016.

[6] V. L. Tran and T. Leirvik, "Efficiency in the Markets of Crypto-Currencies," *Finance Research Letters*, vol. 35, p. 101382, 2020.

[7] J. W. Wilder, *New Concepts in Technical Trading Systems*. Trend Research, 1978.

[8] S. Nison, *Japanese Candlestick Charting Techniques*, 2nd ed. Prentice Hall Press, 2001.

[9] Y. Liu and A. Tsyvinski, "Risks and Returns of Cryptocurrency," *Review of Financial Studies*, vol. 34, no. 6, pp. 2689–2727, 2021.

[10] N. Marz and J. Warren, *Big Data: Principles and Best Practices of Scalable Realtime Data Systems*. Manning Publications, 2015.

[11] M. Armbrust, A. Ghodsi, R. Xin, and M. Zaharia, "Lakehouse: A New Generation of Open Platforms that Unify Data Warehousing and Advanced Analytics," in *Proc. CIDR*, 2021.

[12] J. Kreps, "Kafka: a Distributed Messaging System for Log Processing," in *Proc. NetDB Workshop*, 2011.

[13] A. Vaswani et al., "Attention Is All You Need," in *Proc. NeurIPS*, 2017.

[14] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Proc. NeurIPS*, vol. 33, pp. 9459–9474, 2020.

[15] N. Shazeer, A. Mirhoseini, K. Maziarz, et al., "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer," in *Proc. ICLR*, 2017.

[16] D. Araci, "FinBERT: Financial Sentiment Analysis with Pre-Trained Language Models," arXiv preprint arXiv:1908.10063, 2019.

[17] Y. A. Malkov and D. A. Yashunin, "Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs," *IEEE Trans. Pattern Anal. Mach. Intell.*, vol. 42, no. 4, pp. 824–836, 2020.
