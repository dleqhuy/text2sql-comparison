# Kịch bản demo Text-to-SQL — một người, 5–7 phút

**Người trình bày:** Một người vừa thao tác UI vừa diễn giải.\
**Thời lượng mục tiêu:** 6 phút 30 giây; có thể rút còn 5 phút hoặc mở rộng đến 7 phút.\
**Cập nhật:** 17/11/2026.

**Mục tiêu:** Cho cô thấy mỗi bước nhận input gì, trả output gì và vì sao cần bước đó. Trình bày đầy đủ chuỗi DIN-SQL; ba phương pháp còn lại tập trung vào bước thể hiện khác biệt. Dành 45 giây giải thích CM, EM, EX, VES và 15 giây kết luận.

**Bản để tập nói:** [Lời thoại liền mạch 5–7 phút, kèm chỗ bấm trên UI](demo-talk-track.md).

## Chuẩn bị trước khi bắt đầu tính giờ

- Mở app và chọn sẵn database `concert_singer`.
- Chuẩn bị câu **#0000 — How many singers do we have?**, mức **Dễ**.
- Mở thử phiên lịch sử **`e84db07f97fe`**: đã chạy đủ DIN-SQL, MAC-SQL, DAIL-SQL và Codex MCP SQL, cả bốn đều trả **6**. Kiểm tra phiên còn truy cập được; tải JSON dự phòng.
- Ưu tiên dùng phiên đã lưu để chủ động thời gian. Nói rõ đây là trace của một lần chạy thật đã lưu. Nếu buổi trình bày yêu cầu chạy trực tiếp, bấm chạy rồi trình bày phần schema trong lúc chờ; chuyển sang lịch sử nếu API chậm.
- Trước buổi demo, chọn **DIN-SQL → Result → Tính CM / EM / EX / VES** trên phiên dự phòng, kiểm tra SELECT F1=1, EM=1, EX=1 và chụp màn hình kết quả để dự phòng. Không học thuộc số VES vì mỗi lần đo có thể khác. Điểm nằm trong cache trình duyệt, có thể phải tính lại khi quay về sau vài phút hoặc reload.
- Tập trước đường đi: **Lược đồ CSDL → Pipeline explorer → lịch sử → DIN-SQL → MAC-SQL → DAIL-SQL → Codex MCP SQL → DIN-SQL → Result → Tính CM / EM / EX / VES**.
- Không xóa lịch sử dự phòng. Không dành thời gian chạy thêm câu khó trong phần chính.

**Thao tác lặp ở mỗi node:** Chọn node → **Trace** → **Input / prompt** → **Output / SQL / kết quả**. Chỉ vào phần dữ liệu cần nói, không đọc toàn bộ prompt.

## Lịch trình mục tiêu 6 phút 30 giây

| Mốc thời gian | Nội dung | Bằng chứng phải chỉ trên UI |
|---|---|---|
| 0:00–0:40 | Schema và câu hỏi | Bảng `singer`, câu hỏi, database |
| 0:40–3:10 | DIN-SQL: toàn bộ chuỗi chính | Input/output ở từng bước, SQL cuối và kết quả 6 |
| 3:10–3:50 | MAC-SQL | Trạng thái chuyển giao, prompt sinh SQL và Refiner |
| 3:50–4:40 | DAIL-SQL | Ví dụ được chọn, prompt và SQL của hai lượt |
| 4:40–5:30 | Codex MCP SQL | Tham số/kết quả tìm schema và thử SQL |
| 5:30–6:15 | Result và bốn độ đo | CM theo thành phần, EM, EX và VES của DIN-SQL |
| 6:15–6:30 | Kết luận | Điểm khác nhau giữa cách tạo SQL và cách đánh giá |

## 1. Schema và câu hỏi — 40 giây

| Thao tác | Lời nói gợi ý |
|---|---|
| Mở **Lược đồ CSDL**, chọn `concert_singer`, chỉ bảng `singer`. | “Database demo có bốn bảng. Hôm nay em dùng câu hỏi ‘Có bao nhiêu ca sĩ?’. Câu này chỉ cần bảng `singer`; những câu phức tạp hơn có thể JOIN nhiều bảng trong cùng database.” |
| Về **Pipeline explorer** và mở phiên lịch sử đã chuẩn bị. | “Đây là trace của một phiên chạy thật đã lưu, với cùng câu hỏi và database cho bốn phương pháp. Em sẽ chỉ rõ input, output và vai trò từng bước.” |

Nếu đang chạy trực tiếp, thay câu thứ hai bằng:

> “Em gửi cùng câu hỏi và database cho các phương pháp. Khi có kết quả, em sẽ mở từng bước để kiểm tra input và output.”

## 2. DIN-SQL: giải thích đầy đủ chuỗi xử lý — 2 phút 30 giây

Chọn **DIN-SQL**. Với mỗi node, mở input rồi output. Các output cụ thể dưới đây thuộc phiên dự phòng `e84db07f97fe`; lần chạy mới có thể khác.

| Node và thời gian gợi ý | Cần chỉ trên màn hình | Lời nói gợi ý |
|---|---|---|
| **Câu hỏi đầu vào** — 10 giây | Input/output chứa câu hỏi và `db_id: concert_singer`. | “Đầu vào là câu hỏi và database. SQL đáp án không được đưa cho phương pháp để sinh câu trả lời.” |
| **Liên kết schema** — 25 giây | Input: prompt chứa câu hỏi và schema. Output: `Schema_links: [singer.*]`. | “Bước này nối từ ‘singers’ trong câu hỏi với bảng `singer`, để mô hình xác định dữ liệu liên quan.” |
| **Phân loại câu hỏi** — 20 giây | Input: prompt phân loại. Output: `Label: "EASY"`. | “Mô hình nhận định câu này không cần JOIN hay truy vấn lồng, nên chọn nhánh sinh SQL đơn giản.” |
| **Sinh SQL** — 25 giây | Input: prompt của nhánh đã chọn. Output: `SELECT COUNT(*) FROM singer`. | “Prompt dùng thông tin câu hỏi và schema để sinh SQL. `COUNT(*)` đếm số dòng trong bảng ca sĩ; không có điều kiện nên không cần `WHERE`.” |
| **Kiểm tra & sửa SQL** — 20 giây | Input: prompt kiểm tra SQL vừa sinh. Output: vẫn là SQL đếm ca sĩ. | “Bước này rà soát SQL. Trong phiên này SQL được giữ nguyên; kiểm tra không đồng nghĩa với lúc nào cũng phải sửa.” |
| **SQL cuối** — 10 giây | Output: SQL được chọn. Nếu không có input riêng, chỉ thông báo trên UI. | “Đây là SQL cuối runner trả về, không phải một lần gọi mô hình mới. Node này có thể không ghi input riêng.” |
| **Thực thi & đánh giá** — 25 giây | Input: SQL cuối. Output: giá trị **6**, đánh giá `SQLite EX` khớp đáp án. | “SQL chạy trên SQLite thật và trả về sáu ca sĩ. Với câu hỏi mẫu, app so sánh kết quả với SQL tham chiếu.” |
| Chuyển phương pháp — 15 giây | Toàn bộ sơ đồ DIN-SQL. | “Chuỗi chính là xác định schema, chọn nhánh, sinh SQL, rà soát rồi thực thi. Em chuyển sang các phương pháp khác để chỉ ra điểm khác biệt.” |

**Lưu ý khi tập:** Nhãn `EASY` ở DIN-SQL là dự đoán để chọn nhánh. Bộ lọc độ khó Spider dựa trên SQL đáp án và có bốn mức; hai cách phân loại không đồng nhất.

## 3. MAC-SQL: chuyển giao giữa các agent — 40 giây

| Thao tác và dữ liệu cần chỉ | Lời nói gợi ý |
|---|---|
| Bấm **Selector · trạng thái**. Mở input chứa câu hỏi/database, rồi output có `pruned: false`, `send_to: Decomposer`. | “MAC-SQL chuyển trạng thái qua các agent. Với schema này, Selector không cần thu gọn và chuyển sang Decomposer.” |
| Bấm **Decomposer · gọi LLM**. Chỉ prompt input và SQL output. | “Decomposer nhận câu hỏi cùng schema để sinh SQL. Câu đơn giản có thể được giải trực tiếp.” |
| Bấm **Refiner · trạng thái**. Chỉ input có SQL dự đoán, output có `pred`, `fixed: false`, `send_to: System`. | “Refiner kiểm tra SQL bằng thực thi và sửa khi cần. Phiên này không cần sửa nên không phát sinh lần gọi LLM sửa lỗi riêng.” |

Không mở lại các bước Input, SQL cuối và thực thi chung nếu sắp hết thời gian. Nếu cô hỏi thêm, chúng vẫn có trên sơ đồ để kiểm tra.

## 4. DAIL-SQL: chọn ví dụ qua hai lượt — 50 giây

| Thao tác và dữ liệu cần chỉ | Lời nói gợi ý |
|---|---|
| Bấm **Lượt 1 · Chọn ví dụ**, mở output và mở một ví dụ đếm đối tượng. | “DAIL-SQL chọn các ví dụ câu hỏi–SQL để hướng dẫn mô hình. Ví dụ đếm máy bay cũng minh họa cấu trúc `COUNT(*)` như câu đếm ca sĩ.” |
| Bấm **Lượt 1 · Sinh SQL sơ bộ**, mở input/prompt rồi output SQL. | “Đầu vào là prompt ghép từ schema, câu hỏi và ví dụ; đầu ra là SQL sơ bộ.” |
| Bấm **Lượt 2 · Chọn lại ví dụ**, chỉ output ví dụ/prompt; sau đó bấm **Lượt 2 · Sinh SQL cuối**, mở input rồi output. | “Lượt hai sử dụng thêm SQL sơ bộ trong quá trình chọn ví dụ, sau đó sinh SQL cuối từ prompt mới. Với câu này, hai lượt có thể cho cùng SQL.” |

**Nhớ khi giải thích:** Ví dụ từ database khác là ví dụ hướng dẫn trong prompt; SQL cuối vẫn chỉ chạy trên `concert_singer`. Nếu input của node lựa chọn chỉ có script/tham số, nói đúng như bản ghi; prompt đã ghép nằm ở output lựa chọn hoặc node gọi LLM kế tiếp.

## 5. Codex MCP SQL: tìm schema và thử SQL bằng công cụ — 50 giây

| Thao tác và dữ liệu cần chỉ | Lời nói gợi ý |
|---|---|
| Bấm **`search_objects`**, mở input tham số tìm kiếm và output schema bảng/cột. | “Agent dùng công cụ để kiểm tra schema thực tế trước khi viết SQL. Đây là dữ liệu công cụ trả về, không chỉ là mô tả của mô hình.” |
| Bấm **`execute_sql`**, mở input SQL và output bảng kết quả **6**. | “Agent thử SQL qua MCP và nhận kết quả từ SQLite. Phản hồi công cụ giúp agent kiểm tra câu SQL đã tạo.” |
| Bấm **SQL cuối**, chỉ SQL output. | “Sau phiên tương tác, agent trả SQL cuối. App vẫn có bước thực thi và đánh giá chung phía sau.” |

Nếu được hỏi về **Phiên Codex**, giải thích: node đó bao quanh các lần gọi công cụ; input là yêu cầu/cấu hình phiên, output là trạng thái và phản hồi công khai cuối. Không giới thiệu trace là toàn bộ suy luận nội bộ của mô hình.

## 6. Result và bốn độ đo — 45 giây

**Thao tác:** Chuyển lại **DIN-SQL → Result → Tính CM / EM / EX / VES**. Nếu đã có kết quả thì dùng kết quả hiện tại, không cần bấm **Đo lại**. Khi số xuất hiện, chỉ lần lượt bốn thẻ. Mở **Chi tiết CM theo thành phần SQL** nếu cần chỉ rõ hàng SELECT; không đọc hết bảng.

| Độ đo | Chỉ trên UI | Lời giải thích ngắn |
|---|---|---|
| **CM — Component Matching** | Thẻ CM: SELECT F1 **1.00**; WHERE/GROUP BY/ORDER BY không dùng hiện **—**. Bảng mở rộng có Precision, Recall và F1. | “CM kiểm tra từng thành phần SQL. SELECT của câu này khớp nên F1 bằng một; dấu gạch nghĩa là thành phần không xuất hiện ở cả hai truy vấn.” |
| **EM — Exact Matching** | Thẻ EM **1** trên SQL của DIN-SQL trong phiên dự phòng. | “EM xét toàn bộ cấu trúc SQL theo bộ chấm Spider, không so từng ký tự. Ở đây EM bằng một.” |
| **EX — Execution Accuracy** | Thẻ EX **1** và bảng kết quả **6**. | “EX kiểm tra kết quả thực thi có khớp đáp án không. Ở đây EX bằng một và kết quả là sáu ca sĩ.” |
| **VES — Valid Efficiency Score** | Thẻ VES và thời gian SQL dự đoán/đáp án. Không đọc một số đã học thuộc. | “VES đánh giá tốc độ SQL dự đoán so với SQL đáp án khi kết quả hợp lệ, không gồm thời gian mô hình sinh SQL.” |

Lời nối để đọc liền:

> “Em quay lại DIN-SQL và tính bốn độ đo. CM chỉ rõ từng thành phần SQL khớp đến đâu; ở đây SELECT có F1 bằng một, dấu gạch là phần không dùng. EM xét cấu trúc toàn câu theo Spider; EX xét kết quả thực thi, cả hai đang bằng một. VES xét tốc độ SQL so với đáp án khi kết quả hợp lệ, không tính thời gian mô hình. Điểm đang xem là của một câu; số VES có thể thay đổi giữa các lần đo.”

**Giữ đúng cách diễn giải:** CM là bộ điểm thành phần, UI không tạo điểm trung bình CM. EM/EX của một câu là 0 hoặc 1, không phải tỷ lệ toàn tập. VES là điểm số, không phải mili giây hay phần trăm chính xác. Không kết luận phương pháp tốt hơn từ một câu hoặc một lần đo tốc độ.

## 7. Kết luận — 15 giây

> “Bốn phương pháp có thể ra cùng kết quả nhưng đi qua các bước khác nhau. Trace cho phép kiểm tra input và output từng bước; bốn độ đo giúp xem xét thành phần, cấu trúc, kết quả và tốc độ SQL. Dạ, em xin kết thúc phần demo.”

## Điều chỉnh khi chỉ có 5 phút hoặc có đủ 7 phút

### Bản 5 phút

| Nội dung | Thời lượng |
|---|---:|
| Schema/câu hỏi | 30 giây |
| DIN-SQL | 2 phút |
| MAC-SQL | 30 giây |
| DAIL-SQL | 35 giây |
| Codex MCP SQL | 35 giây |
| Bốn độ đo | 40 giây |
| Kết luận | 10 giây |
| **Tổng** | **5 phút** |

Giữ thao tác mở input/output ở các bước được trình bày; rút lời nói, không đọc toàn bộ prompt và không mở thêm câu hỏi. Phần độ đo vẫn nói đủ: **CM từng phần, EM cấu trúc, EX kết quả, VES tốc độ SQL**. Có thể chỉ thẻ CM mà không mở bảng chi tiết. Tính điểm trước buổi demo và giữ ảnh kết quả dự phòng để không mất giờ chờ.

### Bản 7 phút

Dùng lịch trình 6 phút 30 giây và dành tối đa **30 giây** còn lại cho một câu hỏi ngắn hoặc mở bảng **Chi tiết CM**. Không cộng thêm một lượt chạy câu hỏi khó vào lịch trình chính.

Nếu được hỏi ngoài phần chính về JOIN, có thể dùng câu **#0037 — List all singer names in concerts in year 2014.** và chỉ schema:

> “Tên ca sĩ ở singer, năm ở concert, còn singer_in_concert nối ca sĩ với concert. Vì vậy câu này cần ba bảng trong cùng database.”

## Câu trả lời dự phòng — không đọc hết trong phần chính

| Tình huống/câu hỏi | Cách xử lý hoặc trả lời |
|---|---|
| API chậm, lỗi mạng | Mở lịch sử, chọn phiên dự phòng và **Phát lại**. Nói rõ: “Đây là trace của một phiên chạy thật đã lưu; em dùng để trình bày tiếp khi dịch vụ đang chậm.” |
| Node chưa có dữ liệu/input riêng | Chỉ thông báo trên UI: “Bản ghi này chưa có dữ liệu riêng cho bước đó.” Không trình bày dữ liệu dự kiến như kết quả đã ghi nhận. |
| Vì sao Self-correction không đổi SQL? | “Bước kiểm tra có thể giữ nguyên SQL. Chỉ kết luận đã sửa khi output khác input thực tế.” |
| Vì sao không có Selector/Refiner gọi LLM? | “Tùy nhánh thực tế; không cần thu gọn schema hoặc sửa SQL thì có thể chỉ ghi nhận node trạng thái.” |
| Vì sao ví dụ DAIL có database khác? | “Đó là ví dụ hướng dẫn cách viết SQL, không phải database đang được truy vấn cùng.” |
| Vì sao MCP thử SQL rồi app còn thực thi lần nữa? | “Công cụ giúp agent tạo câu trả lời; bước cuối của app dùng để hiển thị và đánh giá nhất quán.” |
| EASY của DIN-SQL có phải mức Dễ của bộ lọc? | “Không hoàn toàn. DIN-SQL dự đoán nhánh `EASY`, `NON-NESTED`, `NESTED`; bộ lọc Spider có bốn mức dựa trên SQL đáp án.” |
| Phân loại đưa lý do sai | “Đây là dự đoán của mô hình, có thể sai. Trace giúp mình kiểm tra tác động đến bước sinh SQL.” |
| SQL chạy được nhưng EX không khớp | “Chạy được xác nhận SQL thực thi thành công; chưa xác nhận kết quả giống đáp án.” |
| Câu hỏi tự nhập không có chấm đúng/sai | “Không có SQL tham chiếu nên app chỉ hiển thị kết quả thực thi, không tự gắn nhãn đúng.” |
| CM khác EM thế nào? | “CM cho biết từng thành phần khớp hay sai; EM xét toàn câu. UI giữ điểm CM theo từng thành phần, không lấy trung bình tùy ý.” |
| CM có dấu — là điểm 0 phải không? | “Không. Cả dự đoán và đáp án đều không có thành phần đó. Nếu đáp án có WHERE mà dự đoán thiếu, WHERE được chấm 0.” |
| Vì sao EM/CM khác EX dù SQL chạy được? | “Hai cách viết có thể khác cấu trúc nhưng cùng trả dữ liệu. Bộ chấm Spider cũng có giới hạn parser; cần mở Chi tiết tính điểm để biết lý do.” |
| Tại sao Codex có thể EX=1 nhưng EM=0? | “Trong phiên đã lưu, alias cột có thể không được parser Spider hỗ trợ. CM/EM chấm dự đoán rỗng theo evaluator gốc và ghi rõ lý do; EX vẫn chạy SQL thực tế.” |
| VES có phải thời gian phản hồi toàn hệ thống? | “Không. Chỉ đo thực thi SQL và lấy dữ liệu, không gồm thời gian sinh SQL hay gọi mô hình.” |
| VES hơn 100 có sai không? | “Không. VES không phải tỷ lệ chính xác bị chặn ở 100. Điểm dựa trên tỷ số thời gian; số cao hơn có thể cho thấy SQL dự đoán nhanh hơn SQL đáp án trong phép đo đó.” |
| VES đang tính theo công thức nào? | “Với kết quả khớp theo bộ chấm VES, đo 10 cặp SQL dự đoán/đáp án, lọc tỷ số ngoại lệ 3σ rồi lấy 100 nhân căn bậc hai trung bình tỷ số thời gian đáp án trên dự đoán. Không khớp hoặc prediction lỗi thì VES=0.” |
| Vì sao EX và điều kiện hợp lệ của VES có thể khác? | “VES dùng so kết quả theo tập hợp của BIRD; EX của dự án có xét dòng trùng, thứ tự khi cần và hoán vị cột. Vì vậy phải đọc đúng quy tắc từng độ đo.” |
| Bấm tính điểm bị chậm hoặc báo N/A | “Đây là phép đánh giá riêng, không gọi lại mô hình. Em dùng ảnh điểm đã đo trước để giải thích tiếp và nói rõ là kết quả lưu trước. N/A là chưa tính được, không đọc thành điểm 0.” |
| Có phải chạy nhiều database không? | “Mỗi câu hỏi demo dùng một database. SQL có thể dùng nhiều bảng bên trong database đó.” |

### Nếu cô hỏi sâu về một phiên không khớp đáp án

Có thể mở phiên **`ae77059e867e`**, câu **#0312** trên `cre_Doc_Template_Mgt` nếu còn thời gian hỏi đáp:

> Return the id and type code of the template that is used for the greatest number of documents.

Dữ liệu có ba template **11, 14, 25**, mỗi template gắn **hai tài liệu**. SQL tham chiếu dùng `ORDER BY COUNT(*) DESC LIMIT 1` nhưng không quy định cách phá hòa.

Trong phiên đã kiểm tra, DIN-SQL trả `(25, 'PP')` và được chấm khớp; MAC-SQL trả cả ba template đồng hạng; DAIL-SQL và Codex trả `(11, 'BK')` và bị chấm không khớp.

Lời giải thích:

> “Trường hợp này cần phân tích dữ liệu đồng hạng và cách chọn một dòng. Chỉ nhìn nhãn không khớp chưa đủ để kết luận nguyên nhân là cú pháp hay hiểu sai câu hỏi.”

Không đưa trường hợp này vào lịch trình chính 5–7 phút và không dùng một ví dụ để kết luận phương pháp nào tốt hơn.

## Checklist tập một mình

- [ ] Mở đúng database/câu hỏi và phiên lịch sử dự phòng mà không tìm lâu.
- [ ] Với mỗi node DIN-SQL, chỉ được input, output và lý do cần bước đó.
- [ ] Với ba phương pháp còn lại, chỉ đúng bước khác biệt và dữ liệu thực tế.
- [ ] Phân biệt Trace/Result, node trạng thái/lần gọi LLM, thực thi thành công/khớp đáp án.
- [ ] Tập chuyển sang lịch sử khi API chậm, nói rõ đang xem lại.
- [ ] Tính thử bốn độ đo trên DIN-SQL; phân biệt CM theo thành phần, EM cấu trúc, EX kết quả và VES tốc độ SQL.
- [ ] Giải thích được dấu —, điểm 0, N/A và VES lớn hơn 100.
- [ ] Chạy đồng hồ một lượt: phút 3:10 rời DIN-SQL; phút 5:30 quay lại DIN-SQL → Result để nói bốn độ đo; phút 6:15 bắt đầu kết luận.
- [ ] Tập bản 5 phút để có thể chủ động rút ngắn khi bị hỏi giữa chừng.

Ở bất kỳ bước nào, tự kiểm tra: **Input ở đâu? Output là gì? Được dùng tiếp thế nào? Bằng chứng nào trên UI hỗ trợ lời giải thích?**
