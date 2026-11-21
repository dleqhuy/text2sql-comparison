# Lời thoại demo bốn phương pháp Text-to-SQL

**Một người trình bày. Bản chuẩn: 6 phút 30 giây. Cập nhật: 19/11/2026.**

## 1. Cách tập nói

Đọc các đoạn dưới nhãn Lời nói. Các đoạn Thao tác và Chỉ trên màn hình là chỉ dẫn để bấm UI, không đọc thành lời. Mỗi phương pháp có khoảng 70 giây, bao gồm cả thao tác.

Tài liệu này giới thiệu cả bốn phương pháp trong một buổi demo. Phần giải thích sâu để học trước nằm trong [Sổ tay demo](demo-script.md). Không đọc toàn bộ sổ tay trong 5–7 phút.

Để chuyển sang DOCX, giữ tiêu đề, đoạn ngắn và nhãn đậm. Không dồn các đoạn thành bảng; mỗi cặp Thao tác và Lời nói nên nằm gần nhau trên trang.

## 2. Chuẩn bị trước khi bấm giờ

Dùng câu số 0000, “How many singers do we have?”, trên database `concert_singer`. Mở thử phiên `e84db07f97fe` trong lịch sử, xác nhận cả bốn phương pháp có trace và đều trả 6.

Tính thử CM, EM, EX, VES trên DIN-SQL của phiên này và chụp ảnh điểm dự phòng. SELECT F1, EM, EX đã kiểm tra đều bằng 1. Không học thuộc số VES. Nếu dùng phiên khác, đối chiếu dữ liệu rồi sửa lời nói cho phù hợp.

Bắt đầu tại màn hình Lược đồ CSDL. Khi mở một bước, chọn Trace rồi lần lượt mở Input / prompt và Output / SQL / kết quả. Chỉ đoạn cần nói, không đọc toàn bộ prompt dài.

## 3. Từ 0:00 đến 0:30 — Lời chào, giới thiệu đề tài và dẫn vào demo

**Thao tác:** Mở sẵn Lược đồ CSDL với database `concert_singer`. Khi đọc lời dẫn, không thao tác thêm. Đến câu hỏi minh họa, chỉ bảng `singer`, rồi về Pipeline explorer và mở phiên lịch sử đã chuẩn bị.

**Lời nói:**

> Dạ, em chào cô. Nhóm em xin trình bày đề tài “Giao diện cơ sở dữ liệu thế hệ mới: Khảo sát các kỹ thuật chuyển đổi ngôn ngữ tự nhiên thành SQL bằng mô hình ngôn ngữ lớn”.

> Sau đây, em minh họa bốn phương pháp qua câu hỏi “Có bao nhiêu ca sĩ?”. Đây là câu hỏi có đáp án SQL tham chiếu trong tập dữ liệu Spider dev. Em sẽ chỉ rõ input và output của từng bước, sau đó giải thích bốn độ đo CM, EM, EX và VES.

**Nếu đã giới thiệu đề tài ở phần slide:** Thay hai đoạn trên bằng đoạn chuyển tiếp sau, không đọc cả hai phiên bản.

> Sau phần khảo sát, nhóm em xin minh họa cách bốn phương pháp xử lý cùng câu hỏi “Có bao nhiêu ca sĩ?”. Em dùng trace một phiên chạy thật đã lưu để chỉ input, output từng bước và giải thích các độ đo trên kết quả.

## 4. Từ 0:30 đến 1:40 — DIN-SQL

### 4.1. Bước một: Liên kết câu hỏi với schema

**Thao tác:** Chọn DIN-SQL, bấm Liên kết schema. Mở Input / prompt, rồi Output / SQL / kết quả.

**Chỉ trên màn hình:** Dòng `Schema_links: [singer.*]`.

**Lời nói:**

> Đầu tiên là phương pháp DIN-SQL. Bước một liên kết câu hỏi với schema. Input là prompt chứa câu hỏi và schema của database; output xác định bảng singer liên quan đến câu hỏi.

### 4.2. Bước hai: Phân loại câu hỏi

**Thao tác:** Bấm Phân loại câu hỏi; mở input rồi output và chỉ `Label: "EASY"`.

**Lời nói:**

> Bước hai là phân loại. Input là prompt phân loại có câu hỏi và thông tin schema. Output là nhãn EASY vì mô hình nhận định không cần JOIN hay truy vấn lồng. Nhãn này giúp chọn prompt sinh SQL ở bước tiếp theo.

### 4.3. Bước ba: Sinh SQL

**Thao tác:** Bấm Sinh SQL; mở prompt input rồi output SQL.

**Chỉ trên màn hình:** `SELECT COUNT(*) FROM singer`.

**Lời nói:**

> Bước ba là sinh SQL. Từ kết quả phân loại, hệ thống chọn mẫu prompt EASY và ghép thông tin câu hỏi, schema làm input cho LLM. Output là câu SQL dùng COUNT sao để đếm số ca sĩ trong bảng singer.

### 4.4. Bước bốn: Kiểm tra và sửa SQL

**Thao tác:** Bấm Kiểm tra & sửa SQL; mở input rồi output. Đối chiếu SQL trước và sau bước kiểm tra.

**Lời nói:**

> Bước bốn là kiểm tra và sửa SQL. Input là prompt yêu cầu LLM rà soát câu SQL vừa sinh và sửa nếu cần. Output là SQL sau kiểm tra. Trong ví dụ này, SQL được giữ nguyên nên hai câu trước và sau giống nhau.

### 4.5. Câu chuyển sang phương pháp tiếp theo

**Thao tác:** Chỉ nhanh SQL cuối hoặc kết quả 6 nếu đủ thời gian, rồi chuyển tab MAC-SQL. Không cần đọc thêm một đoạn về thực thi ở đây vì sẽ trở lại Result khi giải thích độ đo.

**Lời nói:**

> Điểm chính của DIN-SQL là tách riêng liên kết schema, chọn nhánh, sinh và kiểm tra SQL.

## 5. Từ 1:40 đến 2:50 — MAC-SQL

### 5.1. Bước một: Selector lựa chọn schema

**Thao tác:** Chọn MAC-SQL, bấm Selector · trạng thái. Mở Input / prompt rồi Output / SQL / kết quả.

**Chỉ trên màn hình:** Câu hỏi và database ở input; `pruned: false` và `send_to: Decomposer` ở output.

**Lời nói:**

> Tiếp theo là MAC-SQL. Bước một là Selector. Input là trạng thái chứa câu hỏi và thông tin database. Output cho thấy schema được giữ nguyên và chuyển sang Decomposer. Bước này quyết định có cần thu gọn schema trước khi sinh SQL hay không.

### 5.2. Bước hai: Decomposer sinh SQL

**Thao tác:** Bấm Decomposer · gọi LLM; mở prompt input rồi SQL output. Sau đó bấm Decomposer · trạng thái, chỉ `qa_pairs` và `send_to: Refiner` nếu còn thời gian.

**Chỉ trên màn hình:** `SELECT COUNT(*) FROM singer;`.

**Lời nói:**

> Bước hai là Decomposer. Input là prompt chứa câu hỏi và schema đã chuẩn bị. Output là SQL đếm ca sĩ. SQL được đưa vào trạng thái để chuyển sang Refiner. Câu này đơn giản nên agent giải trực tiếp, không cần tách nhiều câu hỏi con.

### 5.3. Bước ba: Refiner kiểm tra và sửa khi cần

**Thao tác:** Bấm Refiner · trạng thái; mở input chứa SQL rồi output.

**Chỉ trên màn hình:** `pred`, `fixed: false`, `try_times: 1` và `send_to: System`.

**Lời nói:**

> Bước ba là Refiner. Input là trạng thái có SQL vừa sinh và database. Agent kiểm tra bằng thực thi; output là SQL sau kiểm tra và trạng thái chuyển về hệ thống. Ở đây không cần sửa nên không có thêm lần gọi LLM sửa lỗi.

### 5.4. Câu chuyển sang phương pháp tiếp theo

**Thao tác:** Chuyển tab DAIL-SQL. Không mở lại các bước thực thi chung nếu sắp hết thời gian.

**Lời nói:**

> Điểm chính của MAC-SQL là phân vai lựa chọn schema, sinh SQL và kiểm tra, rồi chuyển trạng thái giữa các agent.

## 6. Từ 2:50 đến 4:00 — DAIL-SQL

### 6.1. Bước một: Chọn ví dụ lượt đầu

**Thao tác:** Chọn DAIL-SQL, bấm Lượt 1 · Chọn ví dụ. Mở input ghi script/tham số; mở output và một ví dụ đếm đối tượng.

**Chỉ trên màn hình:** Số ví dụ là 9; ví dụ “How many aircrafts do we have?” có SQL đếm máy bay. Prompt ghép nằm ở output lựa chọn, không phải toàn bộ nội dung của input script.

**Lời nói:**

> Tiếp theo là DAIL-SQL. Bước một chọn ví dụ. Input ghi tham số lựa chọn; output là danh sách ví dụ câu hỏi–SQL và prompt ghép. Ví dụ đếm máy bay giúp minh họa cách viết SQL đếm ca sĩ.

### 6.2. Bước hai: Sinh SQL sơ bộ

**Thao tác:** Bấm Lượt 1 · Sinh SQL sơ bộ; mở Input / prompt rồi Output / SQL / kết quả. Nếu prompt được lấy từ node phản hồi LLM con, chỉ dòng chú thích nguồn prompt.

**Chỉ trên màn hình:** `SELECT COUNT(*) FROM singer;`.

**Lời nói:**

> Bước hai sinh SQL sơ bộ. Input là prompt chứa câu hỏi, schema và các ví dụ đã chọn. LLM trả output là SQL đếm ca sĩ, làm dự đoán ban đầu cho lượt tiếp theo.

### 6.3. Bước ba: Chọn lại ví dụ

**Thao tác:** Bấm Lượt 2 · Chọn lại ví dụ; mở input tham số rồi output danh sách và prompt.

**Chỉ trên màn hình:** Tham số lượt hai dùng kết quả SQL sơ bộ; danh sách ví dụ trong phiên này có thể giống lượt đầu.

**Lời nói:**

> Bước ba chọn lại ví dụ. Input ghi cấu hình lượt hai, sử dụng thêm SQL sơ bộ. Output là ví dụ và prompt cho lượt sau. SQL sơ bộ cung cấp thêm thông tin về cấu trúc truy vấn cần tạo.

### 6.4. Bước bốn: Sinh SQL cuối

**Thao tác:** Bấm Lượt 2 · Sinh SQL cuối; mở input/prompt rồi output SQL. Không mở thêm node tiền xử lý trong lịch trình chính.

**Lời nói:**

> Bước bốn sinh SQL cuối. Input là prompt lượt hai; output vẫn là SQL đếm ca sĩ trong ví dụ này. Điểm chính của DAIL-SQL là chọn ví dụ qua hai lượt; ví dụ từ database khác chỉ hỗ trợ prompt, không phải truy vấn nhiều database.

## 7. Từ 4:00 đến 5:10 — Codex MCP SQL

### 7.1. Bước một: Nhận yêu cầu của phiên agent

**Thao tác:** Chọn Codex MCP SQL, bấm Phiên Codex và mở Input / prompt. Chỉ yêu cầu cùng hướng dẫn dùng công cụ. Output của phiên chỉ xem ở bước cuối bên dưới.

**Lời nói:**

> Cuối cùng là Codex MCP SQL. Bước một, agent nhận input là câu hỏi và hướng dẫn dùng công cụ. Phiên này bao quanh các lần gọi công cụ; output cuối của phiên là SQL sau quá trình tương tác.

### 7.2. Bước hai: Tìm schema bằng công cụ

**Thao tác:** Bấm Tìm bảng / cột, tên công cụ là search_objects. Mở input tham số rồi output schema.

**Chỉ trên màn hình:** Từ khóa `singer`; kết quả có `singer` và `singer_in_concert`.

**Lời nói:**

> Bước hai tìm schema. Input công cụ là từ khóa singer; output là thông tin bảng và cột thực tế. Agent dùng schema này để viết SQL, không bắt buộc dùng mọi bảng tìm thấy.

### 7.3. Bước ba: Thử SQL qua MCP

**Thao tác:** Bấm Thử SQL qua MCP, tên công cụ là execute_sql. Mở input SQL rồi output bảng dữ liệu.

**Chỉ trên màn hình:** `SELECT COUNT(*) AS singer_count FROM singer;`. Output có một dòng chứa giá trị 6.

**Lời nói:**

> Bước ba thử SQL. Input là câu SQL cần kiểm tra; output là dữ liệu SQLite trả về, ở đây là sáu. Phản hồi công cụ giúp agent kiểm tra câu lệnh và điều chỉnh nếu có lỗi.

### 7.4. Bước bốn: Trả SQL cuối

**Thao tác:** Trở lại Phiên Codex, mở output có `final_response`; nếu đủ thời gian, chỉ SQL cuối. Node SQL cuối chỉ ghi kết quả, không có input riêng thì không diễn giải như một lần gọi LLM mới.

**Lời nói:**

> Bước bốn hoàn tất phiên và trả output là SQL cuối. Điểm chính là agent khám phá schema và thử SQL bằng công cụ. App vẫn thực thi và đánh giá SQL cuối để so sánh chung với các phương pháp khác.

## 8. Từ 5:10 đến 6:10 — Bốn độ đo trên Result

### 8.1. CM và EM

**Thao tác:** Chuyển lại DIN-SQL, chọn Result. Bấm Tính CM / EM / EX / VES nếu chưa có điểm; không bấm Đo lại khi đã có kết quả. Chỉ số sau khi chúng xuất hiện.

**Chỉ trên màn hình:** CM có SELECT F1 bằng 1.00, WHERE không dùng hiện —. Nếu cần, mở Chi tiết CM theo thành phần SQL để chỉ một hàng, không đọc cả bảng.

**Lời nói:**

> Em quay lại DIN-SQL để minh họa bốn độ đo trên cùng câu SQL. CM xét từng thành phần: SELECT có F1 bằng một; dấu gạch là phần cả hai truy vấn không dùng. CM được giữ theo thành phần, không gộp tùy ý thành điểm trung bình. EM xét cấu trúc toàn câu theo Spider, ở đây bằng một.

### 8.2. EX và VES

**Thao tác:** Chỉ thẻ EX, bảng kết quả 6 và thẻ VES. Đọc VES theo số hiện tại nếu muốn minh họa, không dùng số đã học thuộc.

**Lời nói:**

> EX xét kết quả thực thi có khớp đáp án không, ở đây bằng một. VES xét hiệu suất SQL so với SQL đáp án khi kết quả hợp lệ, không tính thời gian mô hình sinh SQL. Điểm VES có thể dao động và lớn hơn một trăm. Các điểm đang xem thuộc một câu, không phải điểm toàn bộ tập dữ liệu.

## 9. Từ 6:10 đến 6:30 — Kết thúc

**Thao tác:** Giữ màn hình Result; không mở thêm phiên hoặc chạy câu hỏi mới.

**Lời nói:**

> Qua bốn phương pháp, cùng đầu vào có thể cho cùng kết quả nhưng luồng xử lý khác nhau. Trace cho phép kiểm tra input, output và sự chuyển tiếp; CM, EM, EX, VES giúp xem xét thành phần, cấu trúc, kết quả và hiệu suất. Một câu demo chưa đủ để xếp hạng phương pháp. Dạ, em xin kết thúc.

## 10. Bản rút còn 5 phút

Dành 20 giây mở đầu, 50 giây cho mỗi phương pháp, 60 giây cho bốn độ đo và 20 giây kết luận. Tổng là 5 phút. Giữ cả bốn phương pháp; rút lời giải thích, không bỏ toàn bộ phần input/output của một phương pháp.

Ở mỗi phương pháp, vẫn bấm các node chính nhưng chỉ đọc đoạn ngắn tương ứng dưới đây. Phần độ đo giữ bản đầy đủ ở mục 8.

**DIN-SQL:**

> Prompt liên kết schema chỉ ra bảng singer. Prompt phân loại trả EASY để chọn nhánh. Prompt sinh SQL trả câu đếm ca sĩ. Bước rà soát giữ nguyên SQL; thực thi cuối trả sáu. Như vậy từng bước có input, output và vai trò riêng.

**MAC-SQL:**

> Bước một, Selector nhận trạng thái câu hỏi/schema và chuyển sang Decomposer. Bước hai, Decomposer nhận prompt và trả SQL. Bước ba, Refiner nhận SQL để kiểm tra bằng thực thi; output giữ nguyên SQL trong phiên này.

**DAIL-SQL:**

> Bước một chọn ví dụ, output là ví dụ và prompt. Bước hai nhận prompt để sinh SQL sơ bộ. Bước ba dùng thêm SQL sơ bộ để chọn lại ví dụ. Bước bốn nhận prompt mới và trả SQL cuối.

**Codex MCP SQL:**

> Bước một agent nhận câu hỏi và hướng dẫn. Bước hai, công cụ nhận từ khóa và trả schema. Bước ba, công cụ nhận SQL để thử và trả dữ liệu. Bước bốn, phiên agent hoàn tất và trả SQL cuối.

Nếu có đủ 7 phút, dùng bản chính 6 phút 30 giây và dành 30 giây còn lại cho một câu hỏi. Không mở thêm một lượt chạy khó.

## 11. Lời chuyển khi có sự cố

### 11.1. API chậm khi chạy live

**Thao tác:** Mở phiên lịch sử đã chuẩn bị; tiếp tục ở phương pháp đang trình bày, không nói lại từ đầu.

**Lời nói:**

> Dịch vụ đang phản hồi chậm. Em chuyển sang trace một phiên chạy thật đã lưu để tiếp tục chỉ input và output của các bước.

### 11.2. Điểm chưa hiện hoặc báo N/A

**Thao tác:** Nếu đã chụp ảnh điểm, mở ảnh và nói rõ đó là kết quả đo trước. Nếu chưa có ảnh, chỉ giải thích ý nghĩa và trạng thái chờ, không đọc số dự kiến.

**Lời nói khi có ảnh:**

> Em dùng ảnh điểm đã đo trước trên cùng phiên để giải thích tiếp. N/A hiện tại là chưa tính được, không phải điểm không.

### 11.3. Output khác lời đã học

**Thao tác:** Đọc output thực tế, mở output gốc khi cần. Node chưa chạy hoặc không ghi input riêng thì chỉ đúng thông báo trên UI.

**Lời nói:**

> Output phiên này khác bản em đã chuẩn bị. Em sẽ giải thích theo dữ liệu đang hiển thị, thay vì đọc lại một kết quả chưa xuất hiện.

### 11.4. EX bằng 1 nhưng CM hoặc EM thấp

**Thao tác:** Mở Chi tiết tính điểm. Nếu là lỗi parser, chỉ đúng lý do; nếu SQL khác cấu trúc thì đối chiếu SQL dự đoán và tham chiếu.

**Lời nói:**

> Hai câu SQL có thể khác cấu trúc nhưng cùng dữ liệu. Bộ chấm Spider cũng có giới hạn cú pháp; lỗi parser được ghi riêng. Vì vậy em xem cả cấu trúc lẫn kết quả, không kết luận SQL chạy sai chỉ từ EM.
