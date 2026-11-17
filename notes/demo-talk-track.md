# Lời thoại demo Text-to-SQL — một người, khoảng 5–7 phút

**Cập nhật:** 17/11/2026.\
**Cách tập:** Đọc liền các đoạn trích dẫn. Phần **[Bấm trên UI]** là chỉ dẫn thao tác, không đọc thành lời. Các mốc giờ là mục tiêu để tập, không phải thời gian chờ hệ thống.

Bản này đi cùng [kịch bản chi tiết và câu trả lời dự phòng](demo-script.md).

## Chuẩn bị trước khi bấm giờ

- Dùng màn hình desktop, mở app và kiểm tra lịch sử.
- Chuẩn bị phiên **`e84db07f97fe`**, câu **How many singers do we have?**, database **`concert_singer`**. Phiên này đã chạy đủ bốn phương pháp và đều trả **6**.
- Nếu lịch sử có nhiều câu trùng tên, mở trước đúng phiên và xác nhận cả bốn phương pháp có trace. Không dành thời gian trình bày để tìm phiên.
- Trước buổi tập, trên phiên đó chọn **DIN-SQL → Result → Tính CM / EM / EX / VES** để kiểm tra SELECT F1=1, EM=1 và EX=1; chụp ảnh kết quả dự phòng. Số VES dao động, không học thuộc. Cache điểm có thể hết khi reload hoặc sau vài phút không xem, nên dành vài giây để tính lại nếu cần.
- Bắt đầu tại màn hình **Lược đồ CSDL**, chọn `concert_singer`.
- Với mỗi node, nếu inspector đang ở Result thì bấm **Trace**, rồi mở **Input / prompt** và **Output / SQL / kết quả** theo chỉ dẫn.
- Output trong lời thoại thuộc phiên đã lưu nói trên. Nếu dùng phiên khác, đối chiếu bản ghi trước khi đọc; không gọi output chưa xuất hiện là kết quả thực tế.

## 0:00–0:40 — Giới thiệu dữ liệu và cách demo

**[Bấm trên UI]** Tại **Lược đồ CSDL**, chỉ bảng `singer` và các đường nối giữa bảng. Không cần kéo hoặc zoom nếu đã nhìn rõ.

> Dạ, em demo cách chuyển câu hỏi tự nhiên thành SQL trên database concert singer. Database có bốn bảng, nhưng câu hỏi “Có bao nhiêu ca sĩ?” chỉ cần bảng singer.

**[Bấm trên UI]** Về **Pipeline explorer**, mở phiên lịch sử đã chuẩn bị. Chỉ câu hỏi ở phần **Database & câu hỏi**, rồi chọn **DIN-SQL**.

> Đây là trace một phiên chạy thật đã lưu, với cùng đầu vào cho bốn phương pháp. Em sẽ chỉ input, output từng bước, rồi giải thích bốn độ đo ở phần cuối.

## 0:40–3:10 — DIN-SQL: đi đầy đủ chuỗi xử lý

**[Bấm trên UI]** Chọn **Câu hỏi đầu vào** → **Trace** → **Input / prompt**; chỉ `question` và `db_id`. Mở **Output / SQL / kết quả**.

> Đầu vào xác định câu hỏi và database cần truy vấn. Ở đây là câu đếm ca sĩ trên concert singer. SQL đáp án không được đưa vào cho phương pháp sinh câu trả lời; đáp án được dùng ở phần đánh giá cuối.

**[Bấm trên UI]** Chọn **Liên kết schema** → mở input, chỉ phần câu hỏi/schema → mở output, chỉ `Schema_links: [singer.*]`.

> Bước đầu là liên kết schema. Input là prompt có câu hỏi và cấu trúc dữ liệu. Output xác định bảng singer liên quan đến từ “singers”. Bước này giúp mô hình biết cần dùng dữ liệu nào trước khi viết SQL.

**[Bấm trên UI]** Chọn **Phân loại câu hỏi** → mở input → mở output, chỉ `Label: "EASY"`.

> Tiếp theo, mô hình phân loại câu hỏi để chọn nhánh xử lý. Trong phiên này, output là EASY vì chỉ cần một bảng, không cần JOIN hay truy vấn lồng. Đây là nhãn dự đoán của DIN-SQL, khác với bộ lọc độ khó Spider trên UI.

**[Bấm trên UI]** Chọn **Sinh SQL** → mở **Input / prompt**, chỉ prompt của bước → mở output, chỉ SQL.

> Bước sinh SQL nhận prompt của nhánh đã chọn và trả về SELECT COUNT sao FROM singer. COUNT sao đếm số dòng trong bảng ca sĩ. Câu hỏi không có điều kiện lọc nên không cần WHERE, và không cần nối thêm bảng khác.

**[Bấm trên UI]** Chọn **Kiểm tra & sửa SQL** → mở input → mở output.

> SQL vừa sinh được đưa vào bước rà soát. Output ở đây vẫn là câu SQL đếm ca sĩ. Như vậy, bước kiểm tra không nhất thiết phải thay đổi SQL; trong phiên này, câu SQL được giữ nguyên.

**[Bấm trên UI]** Chọn **SQL cuối** → mở output. Nếu thử mở input và thấy thông báo không có input riêng, chỉ thông báo đó.

> Node SQL cuối ghi nhận câu lệnh runner trả về, không phải một lần gọi mô hình mới. Node này có thể không có input riêng được ghi lại; em chỉ diễn giải dữ liệu thực sự có trong trace.

**[Bấm trên UI]** Chọn **Thực thi & đánh giá** → input là SQL → output là bảng kết quả **6** và nhãn khớp đáp án.

> Cuối cùng, app chạy SQL trên SQLite thật. Output là sáu ca sĩ. Với câu hỏi mẫu, app còn so sánh kết quả với SQL tham chiếu. Đến đây mình đã kiểm tra được từ câu hỏi đầu vào đến dữ liệu trả về.

## 3:10–3:50 — MAC-SQL: chuyển giao giữa các agent

**[Bấm trên UI]** Chọn **MAC-SQL** → **Selector · trạng thái** → mở input rồi output. Chỉ `send_to: Decomposer` và `pruned: false`.

> MAC-SQL chuyển trạng thái giữa các agent. Selector nhận câu hỏi và database; output cho thấy không cần thu gọn schema và chuyển sang Decomposer.

**[Bấm trên UI]** Chọn **Decomposer · gọi LLM** → mở input/prompt rồi output SQL.

> Decomposer nhận prompt chứa câu hỏi và schema để sinh SQL. Với câu đơn giản, agent giải trực tiếp và trả SQL đếm ca sĩ.

**[Bấm trên UI]** Chọn **Refiner · trạng thái** → mở input rồi output; chỉ `pred`, `fixed: false`, `send_to: System`.

> Refiner nhận trạng thái có SQL để kiểm tra bằng thực thi. Output cho thấy không cần sửa và chuyển về hệ thống. Vì vậy phiên này không có thêm lần gọi LLM sửa lỗi riêng.

## 3:50–4:40 — DAIL-SQL: chọn ví dụ qua hai lượt

**[Bấm trên UI]** Chọn **DAIL-SQL** → **Lượt 1 · Chọn ví dụ** → mở output → mở một ví dụ có câu hỏi “How many aircrafts do we have?”.

> DAIL-SQL chọn ví dụ câu hỏi và SQL để hướng dẫn mô hình. Ví dụ đếm máy bay cũng dùng COUNT sao như câu đếm ca sĩ. Đây là ví dụ trong prompt, không phải truy vấn nhiều database.

**[Bấm trên UI]** Chọn **Lượt 1 · Sinh SQL sơ bộ** → mở input/prompt → mở output SQL.

> Lượt đầu nhận prompt ghép từ schema, câu hỏi và các ví dụ, rồi trả SQL sơ bộ.

**[Bấm trên UI]** Chọn **Lượt 2 · Chọn lại ví dụ** → mở output ví dụ/prompt. Sau đó chọn **Lượt 2 · Sinh SQL cuối** → mở input rồi output.

> Lượt hai sử dụng thêm SQL sơ bộ trong quá trình chọn ví dụ, rồi sinh SQL cuối từ prompt mới. Trong phiên này SQL cuối vẫn là đếm ca sĩ. Hai lượt không nhất thiết phải cho hai câu SQL khác nhau.

## 4:40–5:30 — Codex MCP SQL: tương tác với công cụ

**[Bấm trên UI]** Chọn **Codex MCP SQL** → **Tìm bảng / cột** — stage `search_objects` → mở input rồi output schema.

> Codex dùng công cụ để kiểm tra dữ liệu. Search objects nhận tham số tìm kiếm, trả về schema bảng và cột thực tế để agent viết SQL.

**[Bấm trên UI]** Chọn **Thử SQL qua MCP** — stage `execute_sql` → mở input SQL → output có giá trị **6**.

> Execute SQL nhận SQL cần thử và trả dữ liệu từ SQLite, ở đây là sáu. Phản hồi công cụ giúp agent kiểm tra và điều chỉnh khi có lỗi.

**[Bấm trên UI]** Chọn **SQL cuối** → mở output.

> Agent trả SQL cuối sau tương tác. App vẫn thực thi và đánh giá SQL đó theo cơ chế chung như các phương pháp khác.

## 5:30–6:15 — Giải thích CM, EM, EX, VES

**[Bấm trên UI]** Chuyển lại **DIN-SQL** → **Result** → **Tính CM / EM / EX / VES**. Nếu đã có kết quả thì không bấm **Đo lại**. Chờ số hiện rồi mới diễn giải. Chỉ thẻ CM và các hàng SELECT, WHERE; nếu đủ thời gian, mở **Chi tiết CM theo thành phần SQL**. Không đọc hết bảng.

> Em quay lại DIN-SQL để xem bốn độ đo. CM kiểm tra từng thành phần: SELECT có F1 bằng một; dấu gạch là phần cả hai truy vấn không dùng. EM xét cấu trúc toàn câu theo Spider; EX xét kết quả thực thi. Ở đây cả hai bằng một. VES so tốc độ SQL dự đoán với SQL đáp án khi kết quả hợp lệ, không gồm thời gian mô hình. Đây là điểm của một câu; VES có thể dao động giữa các lần đo.

**[Chỉ trên UI khi nói]** CM → SELECT **1.00**, WHERE **—**; EM **1**; EX **1**; cuối cùng chỉ số VES đang hiển thị, không đọc số đã chuẩn bị sẵn. Dùng điểm của **DIN-SQL** để khớp lời thoại; không đọc “EM=1” nếu còn đang đứng ở Codex hoặc phương pháp khác.

## 6:15–6:30 — Chốt kết quả

**[Bấm trên UI]** Giữ màn hình Result và bốn độ đo, không mở phiên mới.

> Bốn phương pháp có thể ra cùng kết quả nhưng đi qua các bước khác nhau. Trace giúp kiểm tra input và output; bốn độ đo cho xem thành phần, cấu trúc, kết quả và tốc độ SQL. Dạ, em xin kết thúc phần demo.

## Cách rút xuống khoảng 5 phút

Tập theo phân bổ: **30 giây mở đầu + 2 phút DIN-SQL + 30 giây MAC-SQL + 35 giây DAIL-SQL + 35 giây Codex + 40 giây độ đo + 10 giây kết luận = 5 phút**.

Giữ thao tác chỉ input/output, rút lời thoại như sau:

- Mở đầu: “Em demo câu đếm ca sĩ trên concert singer bằng trace một phiên chạy thật đã lưu, cùng đầu vào cho bốn phương pháp.”
- DIN-SQL: bỏ câu so sánh nhãn phân loại với bộ lọc Spider; mỗi node chỉ nói một câu về input, output và mục đích.
- MAC-SQL: “Selector nhận câu hỏi/schema và chuyển sang Decomposer; Decomposer sinh SQL; Refiner kiểm tra và phiên này không cần sửa.” Vẫn chỉ dữ liệu ở ba node.
- DAIL-SQL: không mở rộng ví dụ. Chỉ danh sách, prompt và SQL hai lượt: “Lượt một chọn ví dụ để sinh SQL sơ bộ; lượt hai dùng thêm SQL sơ bộ để chọn lại ví dụ và sinh SQL cuối.”
- Codex: “Search objects trả schema thực tế; execute SQL nhận SQL và trả dữ liệu để agent kiểm tra.”
- Bốn độ đo: vẫn chuyển lại **DIN-SQL → Result** và nói đủ: “CM xét từng phần SQL, EM xét cấu trúc toàn câu, EX xét kết quả, VES xét tốc độ SQL khi kết quả hợp lệ. SELECT F1, EM, EX ở đây đều bằng một; dấu gạch là phần không dùng. Đây là điểm một câu, không phải toàn bộ tập dữ liệu.” Không cần mở bảng chi tiết CM.
- Kết thúc: “Trace cho xem input/output; bốn độ đo giúp đánh giá SQL từ nhiều góc độ. Dạ, em xin kết thúc.”

Nếu có đủ 7 phút, giữ bản chính 6 phút 30 giây và dành **30 giây** còn lại cho một câu hỏi ngắn hoặc mở chi tiết CM; không khởi động thêm phiên khó.

## Nếu có sự cố trong lúc nói

**API chậm khi chạy trực tiếp:**

> “Dịch vụ đang phản hồi chậm. Em chuyển sang trace của phiên chạy thật đã lưu để trình bày tiếp input và output từng bước.”

**[Bấm trên UI]** Chọn phiên dự phòng trong lịch sử. Không đọc lại từ đầu; tiếp tục ở phương pháp/bước đang giải thích.

**Output khác lời thoại đã tập:**

> “Output của lần chạy này có khác phiên em đã chuẩn bị. Em sẽ giải thích theo bản ghi đang hiển thị.”

**[Bấm trên UI]** Mở output gốc nếu cần. Nếu bước chưa xong hoặc không có input riêng, nói đúng trạng thái trên màn hình, không đọc kết quả dự kiến như thể đã xuất hiện.

**Điểm chưa tính xong hoặc báo N/A:**

> “Em đã đo trước trên cùng phiên và có ảnh kết quả lưu lại. Em dùng ảnh đó để giải thích tiếp; N/A trên màn hình hiện tại là chưa tính được, không phải điểm không.”

**[Thao tác]** Mở ảnh điểm đã chuẩn bị, nói rõ là kết quả đo trước. Nếu chưa có ảnh thì chỉ giải thích ý nghĩa độ đo và thông báo đang chờ; không đọc điểm dự kiến như số đã đo.

## Ghi nhớ để trả lời khi cô hỏi — không đọc hết trong phần chính

- **CM** giữ F1 theo từng thành phần, không gộp thành điểm trung bình. Dấu **—** là cả hai truy vấn không có thành phần; thiếu WHERE so với đáp án thì là **0**, không phải —.
- **EM** không so chuỗi từng ký tự. Bộ chấm Spider có bước xử lý cấu trúc và có giới hạn parser; giá trị literal có thể không được xét như khi thực thi.
- **EX** kiểm tra dữ liệu trả về. Vì vậy SQL khác cấu trúc có thể EX=1 dù EM=0.
- **CM/EM khi lỗi parser prediction:** evaluator chấm AST dự đoán rỗng và UI ghi rõ lý do. Trong phiên Codex có alias cột, có thể EX=1 nhưng EM=0; không kết luận SQL chạy sai chỉ từ EM.
- **VES** không phải số mili giây, tỷ lệ đúng hay tổng thời gian sinh SQL. Điểm có thể hơn 100 và dao động theo tải máy. UI đo 10 cặp, lọc tỷ số ngoại lệ 3σ rồi tính `100 × sqrt(mean(t_gold / t_pred))`; không khớp theo điều kiện hợp lệ của VES hoặc prediction lỗi thì VES=0.
- **EX và VES có quy tắc hợp lệ khác nhau:** VES dùng so tập hợp của BIRD; EX của dự án còn xét dòng trùng, thứ tự khi cần và hoán vị cột.
- **Điểm đang trình bày là của một câu trên SQL gốc**, không phải điểm trung bình toàn bộ benchmark hoặc EM/CM sau chuẩn hóa trong báo cáo.
