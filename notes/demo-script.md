# Sổ tay demo bốn phương pháp Text-to-SQL

**Người trình bày:** Một người vừa thao tác vừa diễn giải.

**Thời lượng phần trình bày:** 5–7 phút; lịch trình chuẩn là 6 phút 30 giây.

**Cập nhật:** 18/11/2026.

## 1. Cách sử dụng hai tài liệu

Tài liệu này dùng để học kỹ trước buổi demo. Mỗi phương pháp có phần giải thích input, output, vai trò của từng bước và điểm cần chỉ trên UI. Không đọc toàn bộ tài liệu trong phần trình bày 5–7 phút.

File [Lời thoại demo](demo-talk-track.md) là bản để tập nói theo. Bản đó giới thiệu cả bốn phương pháp với thời gian tương đương, có chỉ dẫn bấm và chỉ vào dữ liệu. Khi bị hỏi sâu, dùng phần tương ứng trong sổ tay này.

Mỗi bước cần trả lời được bốn câu: nhận dữ liệu gì, trả dữ liệu gì, vì sao cần bước đó và dữ liệu được chuyển tiếp thế nào. Ưu tiên bằng chứng trong trace; không diễn giải một bước chưa chạy như thể đã có kết quả.

## 2. Chuẩn bị dữ liệu và UI

### 2.1. Câu hỏi dùng chung

- Database: `concert_singer`.
- Câu hỏi mẫu: số 0000, “How many singers do we have?”.
- Nghĩa tiếng Việt: “Có bao nhiêu ca sĩ?”.
- Độ khó trên bộ lọc Spider: Dễ.
- SQL tham chiếu: `SELECT COUNT(*) FROM singer`.
- Kết quả trên dữ liệu đã kiểm tra: 6.

Database có bốn bảng: `singer`, `concert`, `singer_in_concert` và `stadium`. Câu hỏi này chỉ dùng bảng `singer`. Việc một database có nhiều bảng không có nghĩa phải dùng tất cả các bảng cho mọi câu hỏi.

### 2.2. Phiên dự phòng

Phiên `e84db07f97fe` đã được kiểm tra trong workspace: đủ bốn phương pháp, đều trả kết quả 6. Các output cụ thể trong tài liệu được đối chiếu với phiên này. Mã phiên chỉ là dữ liệu tham khảo của workspace, không phải phiên có sẵn trên mọi máy.

Trước buổi demo, kiểm tra lại lịch sử còn mở được phiên đó. Nếu dùng phiên khác, đối chiếu SQL và output trước khi tập nói; lần chạy mới có thể có phản hồi khác.

Chuẩn bị ba việc:

1. Mở đúng phiên và xác nhận cả bốn tab đều có trace.
2. Chọn DIN-SQL, mở Result, bấm Tính CM / EM / EX / VES và chụp ảnh điểm dự phòng.
3. Tải JSON của phiên để lưu bằng chứng. Nút JSON dùng để xuất, không phải nút nhập hoặc khôi phục phiên.

Ở DIN-SQL của phiên đã kiểm tra, SELECT có CM F1 = 1, EM = 1 và EX = 1. Không học thuộc VES vì kết quả đo thay đổi theo tải máy và từng lần thực thi.

### 2.3. Quy ước thao tác

Trong mỗi phương pháp, chọn node cần xem, chọn Trace, rồi mở hai tab Input / prompt và Output / SQL / kết quả. Chỉ đoạn liên quan; không đọc hết prompt dài.

- Trace là chi tiết của bước đang chọn.
- Result là SQL, dữ liệu và độ đo cuối của phương pháp đang chọn.
- Lược đồ CSDL là màn hình xem bảng, cột, PK/FK và DDL gốc.
- Lịch sử và Phát lại dùng trace đã lưu, không gọi mô hình lại.

Nếu dùng lịch sử, nói rõ “đây là trace của một lần chạy thật đã lưu”. Nếu cần chạy live, bấm Chạy pipeline trước khi giới thiệu schema; chuẩn bị chuyển sang lịch sử khi phải chờ. Các phương pháp được runner xử lý lần lượt, không chạy song song.

## 3. Lịch trình cân đối cho cả bốn phương pháp

- 0:00–0:30: giới thiệu schema, câu hỏi và phiên demo.
- 0:30–1:40: DIN-SQL, 70 giây.
- 1:40–2:50: MAC-SQL, 70 giây.
- 2:50–4:00: DAIL-SQL, 70 giây.
- 4:00–5:10: Codex MCP SQL, 70 giây.
- 5:10–6:10: giải thích CM, EM, EX, VES, 60 giây.
- 6:10–6:30: kết luận, 20 giây.

Phần 4–7 dưới đây là kiến thức để học kỹ. Trong lúc trình bày, đi theo các điểm bấm chính của từng phương pháp và lời thoại ngắn ở file còn lại. Các node đầu vào, SQL cuối và thực thi đều cần hiểu, nhưng không phải mở lại cả ba node ở tất cả các phương pháp.

## 4. DIN-SQL: xác định schema, chọn nhánh và sinh SQL

### 4.1. Ý tưởng và điểm bấm chính

DIN-SQL chia công việc thành các bước tường minh: liên kết schema, phân loại câu hỏi, sinh SQL và tự kiểm tra. Đầu ra của các bước trước hỗ trợ xây dựng prompt cho bước sau.

Trong 70 giây, ưu tiên bấm bốn node: Liên kết schema, Phân loại câu hỏi, Sinh SQL, Kiểm tra & sửa SQL. Chỉ nhanh kết quả thực thi ở cuối nếu còn thời gian.

### 4.2. Câu hỏi đầu vào

**Thao tác:** Chọn Câu hỏi đầu vào; mở input rồi output.

**Input:** Câu hỏi đếm ca sĩ và `db_id` là `concert_singer`.

**Output:** Bản ghi đầu vào được runner nhận. Đây chưa phải SQL hoặc kết quả truy vấn.

**Vai trò:** Xác định yêu cầu và database cần truy vấn. SQL tham chiếu không được gửi cho phương pháp để tạo câu trả lời; nó được dùng khi đánh giá.

### 4.3. Liên kết schema

**Thao tác:** Chọn Liên kết schema; chỉ câu hỏi/schema trong input và dòng liên kết trong output.

**Input:** Prompt chứa câu hỏi, cấu trúc schema và hướng dẫn liên kết.

**Output đã quan sát:** `Schema_links: [singer.*]`.

**Vì sao:** Từ “singers” cần được gắn với đối tượng trong database. Phản hồi chỉ ra bảng `singer` liên quan đến phép đếm. Ký hiệu `singer.*` ở bước này là thông tin liên kết; không có nghĩa SQL cuối sẽ dùng `SELECT *`.

**Chuyển tiếp:** Thông tin liên kết được dùng trong các prompt xử lý tiếp theo để hỗ trợ lựa chọn cấu trúc truy vấn.

### 4.4. Phân loại câu hỏi

**Thao tác:** Chọn Phân loại câu hỏi; mở input và chỉ `Label: "EASY"` trong output.

**Input:** Prompt phân loại với câu hỏi, schema và thông tin liên kết.

**Output đã quan sát:** Nhận định không cần JOIN, không cần truy vấn lồng; nhãn EASY.

**Vì sao:** Mỗi nhánh có cách hướng dẫn sinh SQL phù hợp. Đếm dòng của một bảng là tình huống đơn giản trong phiên này.

**Điểm cần phân biệt:** Nhãn EASY, NON-NESTED, NESTED là dự đoán của DIN-SQL. Bộ lọc Dễ, Trung bình, Khó, Rất khó trên UI lấy từ SQL đáp án theo Spider. Hai loại phân loại không đồng nhất, và dự đoán DIN-SQL có thể sai.

### 4.5. Sinh SQL

**Thao tác:** Chọn Sinh SQL; chỉ prompt input và câu SQL output.

**Input:** Prompt của nhánh được chọn, sử dụng câu hỏi và thông tin schema liên quan.

**Output đã quan sát:** `SELECT COUNT(*) FROM singer`.

**Vì sao:** COUNT(*) đếm số dòng của bảng ca sĩ. Không có điều kiện lọc nên không cần WHERE; không cần thông tin bảng khác nên không cần JOIN.

### 4.6. Kiểm tra & sửa SQL

**Thao tác:** Chọn Kiểm tra & sửa SQL; đối chiếu SQL trong input với output.

**Input:** Prompt yêu cầu rà soát SQL vừa sinh trong bối cảnh câu hỏi và schema.

**Output đã quan sát:** SQL đếm ca sĩ được giữ nguyên.

**Vì sao:** Bước này cho mô hình cơ hội rà soát và sửa SQL. Trong phiên này không có thay đổi. Không nói “hệ thống đã sửa được lỗi” nếu input và output không cho thấy một lỗi được sửa.

**Giới hạn cần nhớ:** Tự rà soát của DIN-SQL không đồng nghĩa với việc nhận thông báo lỗi SQLite như Refiner hoặc công cụ execute_sql. Chỉ nói có phản hồi thực thi nếu trace thực sự ghi điều đó.

### 4.7. SQL cuối và thực thi

**Thao tác:** Nếu cần, mở SQL cuối rồi Thực thi & đánh giá.

**Input thực thi:** SQL cuối được runner chọn.

**Output:** Giá trị 6 và đánh giá SQLite EX khớp đáp án.

**Vai trò:** Node SQL cuối ghi lại câu lệnh kết thúc; có thể không có input riêng và không phải lần gọi LLM mới. Node thực thi mới cho thấy SQL chạy trên SQLite thật và trả dữ liệu.

**Câu chốt DIN-SQL:** Điểm khác biệt nằm ở chuỗi liên kết schema, chọn nhánh, sinh và rà soát SQL.

## 5. MAC-SQL: điều phối trạng thái giữa các agent

### 5.1. Ý tưởng và điểm bấm chính

MAC-SQL tổ chức công việc quanh Selector, Decomposer và Refiner. Các agent nhận và cập nhật một trạng thái chung, rồi chuyển việc cho thành phần tiếp theo.

Trong 70 giây, ưu tiên Selector · trạng thái, Decomposer · gọi LLM, Decomposer · trạng thái và Refiner · trạng thái. Không coi mọi node trạng thái là một lần gọi LLM.

### 5.2. Selector và lựa chọn schema

**Thao tác:** Chọn Selector · trạng thái; mở input và output.

**Input:** Trạng thái có câu hỏi, database và các trường phục vụ điều phối. Trường `query` ở đây chứa câu hỏi tự nhiên; không mặc định là một câu SQL. `ground_truth` trong trạng thái runner là chuỗi rỗng.

**Output đã quan sát:** `pruned: false`, `send_to: Decomposer`, `extracted_schema: {}`. Trạng thái còn có mô tả schema được chuyển tiếp cho agent sau.

**Vì sao:** Selector quyết định có cần thu gọn schema trước khi giải hay không. Phiên này giữ schema và chuyển sang Decomposer. Đối tượng extracted_schema rỗng không có nghĩa database không có bảng.

**Khi câu khác phức tạp hơn:** Có thể xuất hiện thêm lời gọi Selector để chọn schema. Không hứa node này luôn xuất hiện.

### 5.3. Decomposer sinh lời giải và SQL

**Thao tác:** Chọn Decomposer · gọi LLM; chỉ prompt input rồi SQL output.

**Input:** Prompt chứa câu hỏi, mô tả schema và các hướng dẫn giải bài toán.

**Output đã quan sát:** Phản hồi chứa `SELECT COUNT(*) FROM singer;`.

**Vì sao:** Decomposer tạo lời giải và SQL. Với bài toán phức tạp, phản hồi có thể thể hiện các câu hỏi con; với phép đếm đơn giản này, agent có thể giải trực tiếp. Không nói mọi câu đều phải được tách thành nhiều bài toán con.

### 5.4. Decomposer chuyển trạng thái

**Thao tác:** Chọn Decomposer · trạng thái; tìm `qa_pairs` và `send_to` trong output.

**Input:** Trạng thái trước khi Decomposer xử lý, gồm câu hỏi/schema đã chuẩn bị.

**Output đã quan sát:** Phản hồi SQL trong qa_pairs, `send_to: Refiner` và `fixed: false`.

**Vì sao:** Lần gọi LLM trả nội dung; node trạng thái cho thấy nội dung đó được đưa vào luồng điều phối ra sao. Hai node có liên hệ nhưng không phải hai lần sinh SQL độc lập.

### 5.5. Refiner kiểm tra và quyết định sửa

**Thao tác:** Chọn Refiner · trạng thái; mở input có SQL, rồi chỉ `pred`, `try_times`, `fixed` và `send_to` ở output.

**Input:** Trạng thái chứa SQL ứng viên và thông tin database.

**Output đã quan sát:** SQL trong pred, `try_times: 1`, `fixed: false`, `send_to: System`.

**Vì sao:** Refiner kiểm tra bằng thực thi và có thể gọi LLM sửa khi cần. Phiên này không cần sửa nên không có lời gọi Refiner · gọi LLM riêng. Các cờ trạng thái cho thấy quyết định chuyển tiếp, không phải bảng dữ liệu trả về.

**Giới hạn:** SQL chạy được chưa bảo đảm trả lời đúng. Kiểm tra thực thi của Refiner không thay thế đánh giá EX với đáp án.

### 5.6. SQL cuối và thực thi chung

**Output cuối đã quan sát:** `SELECT COUNT(*) FROM singer;`, trả kết quả 6 ở bước Thực thi & đánh giá của app.

**Câu chốt MAC-SQL:** Điểm khác biệt là sự chuyển giao trạng thái và vai trò riêng của các agent; chỉ xuất hiện lời gọi LLM khi nhánh thực tế cần đến nó.

## 6. DAIL-SQL: chọn ví dụ và sinh SQL qua hai lượt

### 6.1. Ý tưởng và điểm bấm chính

DAIL-SQL đưa ví dụ câu hỏi–SQL vào prompt để hỗ trợ câu hỏi mới. Runner hiện tại có hai lượt: lượt đầu tạo SQL sơ bộ, lượt sau dùng thêm thông tin SQL sơ bộ khi lựa chọn ví dụ để tạo SQL cuối.

Trong 70 giây, ưu tiên Chọn ví dụ lượt 1, Sinh SQL sơ bộ, Chọn lại ví dụ lượt 2 và Sinh SQL cuối. Chỉ tiền xử lý hoặc node phản hồi LLM nếu cô hỏi sâu.

### 6.2. Tiền xử lý

**Thao tác:** Khi cần giải thích thêm, mở Tiền xử lý.

**Input:** Bản ghi script và tham số chạy tiền xử lý.

**Output đã quan sát:** `examples: 1`, `training_cache_reused: true`, nguồn train là Spider train và train_others.

**Vì sao:** Dữ liệu và biểu diễn phục vụ chọn ví dụ cần được chuẩn bị. Cache cho phép dùng lại phần train đã xử lý. Giá trị examples bằng 1 ở node này chỉ số mẫu đầu vào đang xử lý; không phải chỉ có một ví dụ train được chọn.

### 6.3. Chọn ví dụ lượt 1

**Thao tác:** Chọn Lượt 1 · Chọn ví dụ; mở output và mở một ví dụ cụ thể.

**Input được ghi:** Script và tham số lựa chọn. Không gọi danh sách tham số đó là toàn bộ prompt gửi LLM.

**Output đã quan sát:** 9 ví dụ, số ví dụ trong n_examples, database mục tiêu và prompt ghép. Ví dụ đầu có câu “How many aircrafts do we have?” với SQL `SELECT count(*) FROM Aircraft`.

**Vì sao:** Câu đếm máy bay và câu đếm ca sĩ có cùng dạng phép đếm. Ví dụ giúp mô hình nhận dạng cách viết SQL phù hợp, dù nội dung và database khác nhau.

**Chuyển tiếp:** Prompt ghép được dùng cho lần sinh SQL lượt đầu. Ví dụ từ database khác không có nghĩa SQL cuối truy vấn nhiều database.

### 6.4. Sinh SQL sơ bộ và phản hồi LLM lượt 1

**Thao tác:** Chọn Lượt 1 · Sinh SQL sơ bộ; mở Input / prompt rồi output SQL.

**Input:** Prompt ghép từ câu hỏi, schema và các ví dụ. UI có thể lấy prompt từ node con Lượt 1 · Phản hồi LLM; dòng chú thích cho biết prompt được ghi ở đâu.

**Output đã quan sát:** `SELECT COUNT(*) FROM singer;`.

**Vì sao:** Mô hình dùng ví dụ và schema để tạo dự đoán đầu tiên. Node phản hồi LLM ghi phản hồi công khai và thông tin token; node sinh SQL ghi câu SQL runner đã lấy ra. Không coi hai node là hai lượt suy luận độc lập.

### 6.5. Chọn lại ví dụ lượt 2

**Thao tác:** Chọn Lượt 2 · Chọn lại ví dụ; chỉ danh sách ví dụ và prompt trong output.

**Input được ghi:** Cấu hình/script lượt hai; luồng lựa chọn sử dụng thêm kết quả SQL sơ bộ.

**Output đã quan sát:** Vẫn là 9 ví dụ; trong phiên đơn giản này danh sách có thể trùng lượt đầu.

**Vì sao:** SQL sơ bộ cung cấp thêm tín hiệu về cấu trúc truy vấn. Chọn lại không có nghĩa bắt buộc phải đổi toàn bộ ví dụ; quyết định phụ thuộc câu hỏi và kết quả lựa chọn thực tế.

### 6.6. Sinh SQL cuối lượt 2

**Thao tác:** Chọn Lượt 2 · Sinh SQL cuối; mở input/prompt rồi output.

**Input:** Prompt đã ghép cho lượt hai.

**Output đã quan sát:** SQL đếm ca sĩ, giống SQL sơ bộ trong phiên này.

**Vì sao:** Đây là lượt sinh dự đoán cuối theo cấu hình hai lượt. Không gọi lượt hai là tự sửa dựa trên lỗi SQLite: việc chọn ví dụ lại không đồng nghĩa nhận phản hồi thực thi từ database.

### 6.7. SQL cuối và thực thi chung

**Output:** SQL cuối trả kết quả 6; app đánh giá SQLite EX với đáp án.

**Câu chốt DAIL-SQL:** Điểm khác biệt là ví dụ được lựa chọn và prompt qua hai lượt; ở mỗi lượt phải chỉ được ví dụ hoặc prompt nào dẫn đến SQL nào.

## 7. Codex MCP SQL: agent tương tác với công cụ

### 7.1. Ý tưởng và điểm bấm chính

Agent có thể chủ động tìm schema và thử SQL qua công cụ SQLite MCP. Số lần gọi công cụ tùy thuộc quá trình giải, không phải câu nào cũng có số lần gọi giống nhau.

Trong 70 giây, ưu tiên Tìm bảng / cột, Thử SQL qua MCP và SQL cuối. Chỉ thêm Phiên Codex để giải thích yêu cầu và phản hồi của phiên khi có thời gian.

### 7.2. Phiên Codex

**Thao tác:** Chọn Phiên Codex; mở input và output.

**Input:** Prompt yêu cầu, hướng dẫn, khuôn dạng output và cấu hình phiên. Trong bản ghi có các trường prompt, instructions, output_schema và config_overrides.

**Output đã quan sát:** Trạng thái hoàn tất, final_response chứa SQL, thông tin usage và không có lỗi phiên.

**Vì sao:** Node này bao quanh quá trình agent giải bài toán và gọi công cụ. Nó không phải một bước độc lập chỉ chạy trước hoặc chỉ chạy sau toàn bộ công cụ. Không cộng thời gian node bao ngoài với thời gian node con để tính tổng.

**Phạm vi quan sát:** UI ghi yêu cầu, phản hồi công khai và audit công cụ; không hiển thị toàn bộ suy luận nội bộ của mô hình.

### 7.3. Tìm bảng và cột

**Thao tác:** Chọn Tìm bảng / cột, tên stage là search_objects; mở input rồi output.

**Input đã quan sát:** Từ khóa `singer`, loại đối tượng all, giới hạn 20 và offset 0.

**Output đã quan sát:** Schema của singer và singer_in_concert, kèm cột và metadata liên quan.

**Vì sao:** Agent kiểm tra đối tượng có thật trong database trước khi viết SQL. Kết quả tìm thấy nhiều bảng không có nghĩa SQL cuối phải dùng cả hai; câu đếm ca sĩ vẫn chỉ cần singer.

### 7.4. Thử SQL qua MCP

**Thao tác:** Chọn Thử SQL qua MCP, tên stage là execute_sql; mở input SQL rồi output bảng dữ liệu.

**Input đã quan sát:** `SELECT COUNT(*) AS singer_count FROM singer;`.

**Output đã quan sát:** Cột singer_count, giá trị 6 và một dòng kết quả.

**Vì sao:** Đây là kết quả thực thi từ công cụ, giúp agent kiểm tra câu SQL. Một dòng kết quả không có nghĩa có một ca sĩ; dòng đó chứa giá trị đếm là 6.

**Khi có lỗi:** Agent có thể dùng phản hồi lỗi để điều chỉnh và gọi lại. Không nói đã sửa lỗi nếu phiên đang xem không có lần sửa nào được ghi.

### 7.5. SQL cuối và đánh giá của app

**Output cuối đã quan sát:** SQL đếm ca sĩ có alias singer_count; bước Thực thi & đánh giá của app cũng trả 6 và EX khớp.

**Vì sao có hai lần thực thi:** Lần thử qua MCP là một phần quá trình agent tạo câu trả lời. Lần thực thi cuối của app phục vụ hiển thị và đánh giá chung giữa các phương pháp.

**Điểm cần lưu ý về EM:** SQL có alias này chạy được trong SQLite nhưng parser Spider gốc có thể từ chối. Trong phiên đã kiểm tra, EX bằng 1 trong khi EM bằng 0 do giới hạn parser, và CM dùng dự đoán rỗng theo evaluator gốc. Mở Chi tiết tính điểm để nói đúng nguyên nhân.

**Câu chốt Codex MCP SQL:** Điểm khác biệt là vòng tương tác với schema và kết quả thực thi qua công cụ.

## 8. Giải thích bốn độ đo trên Result

### 8.1. Thao tác và điểm minh họa

Chuyển lại DIN-SQL của phiên dự phòng, chọn Result và bấm Tính CM / EM / EX / VES. Nếu đã có kết quả thì dùng kết quả hiện tại; không đo lại để tìm số đẹp hơn. Cache có thể hết khi reload hoặc sau một thời gian không xem, nên giữ ảnh điểm dự phòng.

Chỉ SELECT F1=1, EM=1 và EX=1 trên DIN-SQL đã chuẩn bị. Không đọc các điểm đó khi còn đang đứng ở Codex hoặc một phiên khác. VES phải đọc theo số thực sự hiện ra.

### 8.2. CM: Component Matching

CM chỉ mức khớp từng thành phần SQL bằng F1 theo evaluator Spider. Thẻ chính gồm SELECT, WHERE, GROUP BY, ORDER BY và KEYWORDS. GROUP BY ở thẻ chính bao gồm kiểm tra HAVING; bảng mở rộng thể hiện chi tiết hơn.

Trong câu đếm ca sĩ, SELECT khớp có F1 bằng 1. Dấu — nghĩa là cả dự đoán và đáp án không dùng thành phần đó. Nếu đáp án có WHERE nhưng dự đoán thiếu, WHERE được chấm 0, không phải —.

Bảng Chi tiết CM theo thành phần SQL có Precision, Recall, F1 và số phần tử dự đoán/đáp án. UI không tự lấy trung bình các thành phần thành một điểm CM chung.

### 8.3. EM: Exact Matching

EM xét mức khớp cấu trúc toàn câu theo bộ chấm Spider, không so từng ký tự SQL. Trong một câu, điểm là 0 hoặc 1.

Evaluator có các quy tắc xử lý cấu trúc, có thể bỏ qua literal, và có giới hạn parser. Prediction không được parser hỗ trợ bị chấm với AST rỗng, kèm lý do; lỗi môi trường hoặc gold khiến điểm chưa tính được.

### 8.4. EX: Execution Accuracy

EX xét kết quả chạy SQL có khớp SQL tham chiếu hay không. Trong một câu, điểm là 0 hoặc 1. SQL khác cấu trúc có thể cùng kết quả nên EX=1 chưa kéo theo EM=1.

EX của dự án dùng toàn bộ kết quả, không chỉ bảng preview tối đa 100 dòng. Quy tắc có xét số lần lặp, thứ tự khi đáp án có ORDER BY và hoán vị cột nhất quán. SQL chạy được chỉ xác nhận thực thi thành công, không tự bảo đảm trả lời đúng.

### 8.5. VES: Valid Efficiency Score

VES đánh giá hiệu suất thực thi SQL dự đoán so với SQL tham chiếu khi kết quả hợp lệ. Không gồm thời gian mô hình sinh SQL hoặc gọi API.

UI hiện đo 10 cặp thời gian, lọc tỷ số ngoài ngưỡng 3σ và tính điểm theo 100 nhân căn bậc hai trung bình tỷ số thời gian SQL đáp án trên SQL dự đoán. Đo execute, fetch và close; không tính thời gian mở kết nối.

VES có thể lớn hơn 100, không phải phần trăm chính xác bị chặn ở 100. Số có thể dao động theo tải máy. Điều kiện khớp của VES theo tập hợp BIRD khác quy tắc EX của dự án, nên cần đọc đúng từng độ đo. Prediction lỗi hoặc không khớp theo điều kiện VES có điểm 0; lỗi đo hoặc thiếu tài nguyên có thể là N/A.

### 8.6. Kết luận được phép rút ra

Điểm trên UI là của câu đang xem, không phải kết quả toàn bộ benchmark. CM/EM trong demo chấm SQL gốc chưa chuẩn hóa cho parser, nên không đọc trực tiếp như điểm sau chuẩn hóa trong báo cáo.

Có thể nói bốn phương pháp cùng trả 6 trong phiên này nhưng có quy trình tạo SQL khác nhau. Không dùng một câu hoặc một lần đo VES để kết luận phương pháp nào tốt nhất.

## 9. Tình huống dự phòng

**API chậm:** Mở lịch sử và Phát lại. Nói rõ đang xem trace đã lưu; không giới thiệu như phản hồi live vừa chạy xong.

**Điểm chưa hiện:** Nếu có ảnh điểm đã đo trước, mở ảnh và nói rõ nguồn. Nếu chưa có, chỉ giải thích ý nghĩa; không đọc số dự kiến như điểm đã tính.

**N/A, 0 và —:** N/A là chưa tính được; 0 là kết quả chấm không đạt theo quy tắc; — ở CM là thành phần không có trong cả hai truy vấn. Không đổi lẫn ý nghĩa.

**Node không có input/output riêng:** Chỉ thông báo trên UI. Dữ liệu có thể nằm ở lời gọi con hoặc output của node khác; mở đúng nơi ghi nhận, không dựng thêm prompt.

**Output khác tài liệu:** Đọc theo phiên thực tế. Dấu chấm phẩy, alias hoặc cách viết SQL có thể khác; giải thích ảnh hưởng dựa trên parser và kết quả thực thi.

**Tại sao không thấy Selector hoặc Refiner gọi LLM:** Nhánh xử lý không cần thu gọn hoặc sửa thì có thể chỉ có node trạng thái. Không tạo lời gọi giả để đủ một sơ đồ cố định.

**Dữ liệu có ground_truth trong trạng thái MAC-SQL:** Trong runner live, giá trị đó là rỗng. Không suy luận mô hình được cung cấp SQL đáp án chỉ từ tên trường.

**Câu hỏi tự nhập không có điểm:** Không có SQL tham chiếu nên chỉ xem thực thi, không tự gắn điểm đúng/sai.

## 10. Giữ thời lượng và kiểm tra trước buổi nói

Bản chuẩn 6 phút 30 giây dành 70 giây cho mỗi phương pháp. Nếu chỉ có 5 phút, dùng 20 giây mở đầu, 50 giây cho mỗi phương pháp, 60 giây cho độ đo và 20 giây kết luận. Tổng là 5 phút. Có đủ 7 phút thì dùng bản chuẩn và dành tối đa 30 giây cho một câu hỏi.

Không mở hết phần giải thích chi tiết của sổ tay trong lúc demo. Không chèn thêm câu hỏi khó khi chưa chạy thử. Giữ thứ tự bốn phương pháp và chỉ các input/output có tính phân biệt.

Trước buổi trình bày, kiểm tra:

1. Lịch sử, bốn phương pháp và câu hỏi đều đúng.
2. Mở được input và output của các node chính ở từng phương pháp.
3. Tính được bốn độ đo trên DIN-SQL; có ảnh dự phòng.
4. Phân biệt node trạng thái, lần gọi LLM và lời gọi công cụ.
5. Tập một lần có đồng hồ và một lần chuyển sang lịch sử khi API chậm.

## 11. Quy ước để chuyển sang DOCX dễ đọc

Hai file dùng tiêu đề phân cấp tối đa ba cấp, đoạn ngắn và danh sách một cấp. Không dùng bảng rộng, Mermaid, HTML hoặc khối JSON/prompt dài trong nội dung chính.

Khi chuyển bằng Pandoc hoặc công cụ tương đương, giữ Heading 1–3, chữ đậm và danh sách. Chọn trang A4, lề khoảng 2 cm, cỡ chữ 11–12, giãn dòng khoảng 1,15 và giữ tiêu đề cùng đoạn tiếp theo. Không ép cả một mục phương pháp thành một đoạn hoặc một hàng bảng.

Trong bản lời thoại, giữ nhãn Thao tác riêng với Lời nói. Đoạn thoại có thể dùng style Block Text hoặc Quote trong Word. SQL và tên trường dùng chữ đơn cách; các tên dài được tách ra khỏi câu thoại để hạn chế tràn dòng.
