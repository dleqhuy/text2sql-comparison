# Lời thoại demo bốn phương pháp Text-to-SQL

**Một người vừa nói vừa thao tác · Bản chính khoảng 7 phút · Cập nhật 22/11/2026.**

Chỉ đọc các đoạn **Lời nói**. Phần **Thao tác** dùng để tập bấm giao diện. Thời gian là mốc tập nói; cần bấm thử và bấm giờ trước buổi trình bày.

## Chuẩn bị trước demo

- Chọn câu mẫu 0000: “How many singers do we have?”, database `concert_singer`. Nghĩa là “Có bao nhiêu ca sĩ?”. Gold SQL là `SELECT COUNT(*) FROM singer`.
- Mở một phiên chạy thật đã lưu, kiểm tra đủ bốn phương pháp và output trước khi tập. Ví dụ chuẩn bị dưới đây dùng trường hợp SQL đếm ca sĩ trả về 6; chỉ đọc số này khi phiên đang mở có kết quả tương ứng.
- Ưu tiên trace mới có bản ghi chạy thử Refiner và xác nhận runner của Codex. Phiên dự phòng trước đây là `e84db07f97fe`, nhưng trace này thiếu hai loại bằng chứng đó; dùng lời thay thế ở cuối tài liệu nếu vẫn chọn phiên này.
- Ở DIN-SQL → Result, tính trước CM / EM / EX / VES; chụp ảnh dự phòng. Không học thuộc VES vì mỗi lần đo có thể khác nhau.
- Bắt đầu ở Lược đồ CSDL. Khi mở node, chọn Trace rồi xem Input / prompt và Output / SQL / kết quả. Chỉ đoạn cần giải thích, không đọc hết prompt.
- Nếu muốn minh họa một lần sửa lỗi, chuẩn bị thêm trace thực sự có lỗi → sửa → chạy lại. Câu đếm ca sĩ có thể thành công ngay nên không bảo đảm xuất hiện nhánh sửa.

## 0:00–0:45 · Giới thiệu câu hỏi và dữ liệu

**Thao tác:** Mở Lược đồ CSDL của `concert_singer`, chỉ bảng `singer`. Sau đó về Pipeline explorer và mở phiên đã chuẩn bị.

**Lời nói:**

> Dạ, em chào cô. Sau đây em xin demo bốn phương pháp chuyển câu hỏi ngôn ngữ tự nhiên thành SQL: DIN-SQL, MAC-SQL, DAIL-SQL và Codex MCP SQL.
>
> Em dùng cùng câu hỏi “Có bao nhiêu ca sĩ?” trên database concert_singer của Spider. Dataset đã cung cấp database tương ứng qua db_id, nên phần demo này tập trung vào hiểu câu hỏi, tìm bảng và sinh SQL trong database đó.
>
> Schema ở đây là cấu trúc bảng, cột và các quan hệ. Câu hỏi này chỉ cần bảng singer. Em mở trace của một lần chạy thật đã lưu để trình bày lần lượt input, output và luồng xử lý.

## 0:45–1:45 · DIN-SQL: luồng một chiều, tự kiểm tra một lần

**Thao tác:** Chọn DIN-SQL. Lần lượt mở Liên kết schema → Phân loại & chọn nhánh → Sinh SQL → LLM tự kiểm tra · 1 lần. Ở mỗi node, chỉ input/prompt và output tương ứng; không mở toàn bộ dữ liệu thô.

**Lời nói:**

> Đầu tiên là DIN-SQL. Phương pháp này chia việc tạo SQL thành bốn bước.
>
> Bước liên kết schema nhận prompt chứa câu hỏi và cấu trúc database. Output chỉ ra bảng singer liên quan đến yêu cầu đếm ca sĩ.
>
> Tiếp theo, bước phân loại nhận câu hỏi cùng thông tin schema để chọn nhánh sinh SQL. Trong phiên này, output là EASY vì mô hình nhận định không cần JOIN hoặc truy vấn lồng. Nhãn này quyết định mẫu prompt của bước tiếp theo.
>
> Bước sinh SQL nhận prompt đã ghép theo nhánh đó và trả về SELECT COUNT(*) FROM singer.
>
> Cuối cùng, LLM nhận SQL ứng viên để tự kiểm tra một lần. Trong ví dụ này, SQL được giữ nguyên. Đây là luồng một chiều: kết quả SQLite ở bước đánh giá cuối không quay ngược lại để mô hình sửa SQL.

## 1:45–3:00 · MAC-SQL: chọn schema, sinh SQL, lặp Refiner

**Thao tác:** Chọn MAC-SQL, chỉ dòng tổng quan trên sơ đồ. Mở Selector · Chọn schema rồi Decomposer · Sinh SQL. Trong khung Refiner, bấm lần chạy thử có bản ghi; nếu có nhánh sửa thực tế, mở thêm LLM sửa SQL rồi lần chạy thử kế tiếp.

**Lời nói:**

> MAC-SQL chia công việc cho ba agent và chuyển tiếp bằng trạng thái. Trạng thái chứa câu hỏi, database, schema, SQL hiện tại và thông tin agent tiếp theo.
>
> Selector nhận câu hỏi và schema để chuẩn bị phần cấu trúc liên quan. Với schema lớn, agent có thể gọi LLM để chọn bảng, cột; với schema nhỏ, nó có thể giữ nguyên. Output là schema đã chuẩn bị và trạng thái chuyển sang Decomposer. Em đối chiếu chế độ thực tế ở đây để biết có gọi LLM hay không.
>
> Decomposer nhận câu hỏi và schema đó, ghép prompt để phân rã bài toán và sinh SQL. Output gồm phần giải thích hoặc câu hỏi con khi cần, cùng SQL được trích xuất. Prompt và phản hồi nằm trong cùng node; đây là một bước xử lý.
>
> Refiner nhận SQL và chạy thử trên SQLite. Nếu thực thi báo lỗi, lỗi cùng SQL được đưa vào prompt để LLM sửa; SQL đã sửa quay lại bước chạy thử. Các nhánh trên sơ đồ thể hiện vòng này theo trace thực tế.
>
> Cấu hình hiện tại giới hạn ba lượt Refiner. Chỉ SQL đã được xác nhận chạy thành công mới chuyển sang đánh giá bổ sung. Chạy thành công nghĩa là câu lệnh thực thi được; việc có trả lời đúng câu hỏi hay không sẽ được đối chiếu với gold SQL ở bước sau.

**Khi SQL thành công ngay:** Chỉ lần chạy thành công và nói thêm: “Phiên này thành công ngay, nên không có lời gọi LLM sửa SQL.” Không đọc nhánh dự kiến như một bước đã chạy.

## 3:00–4:00 · DAIL-SQL: hai lượt chọn ví dụ và sinh SQL

**Thao tác:** Chọn DAIL-SQL. Chỉ Tiền xử lý, rồi mở Lượt 1 · Chọn ví dụ & ghép prompt → Lượt 1 · Sinh SQL sơ bộ → Lượt 2 · Chọn lại ví dụ & ghép prompt → Lượt 2 · Sinh SQL cuối. Ở lượt hai, chỉ SQL sơ bộ trong input.

**Lời nói:**

> DAIL-SQL tập trung vào cách chọn ví dụ câu hỏi–SQL cho prompt. Sau tiền xử lý, lượt đầu dùng câu hỏi đã che các thông tin đặc thù để tìm ví dụ tương tự trong tập train. Output của bước lựa chọn là các ví dụ và prompt đã ghép.
>
> Prompt này được gửi cho LLM để sinh SQL sơ bộ. SQL sơ bộ chưa được chạy SQLite, mà được dùng thêm ở lượt chọn ví dụ thứ hai.
>
> Lượt hai sử dụng cả thông tin câu hỏi và cấu trúc SQL sơ bộ để chọn lại ví dụ, ghép prompt mới, rồi gọi LLM sinh SQL cuối.
>
> Đây là hai lượt cố định. Không có phản hồi lỗi thực thi giữa hai lượt và không có vòng sửa SQL như Refiner. Trong ví dụ đếm ca sĩ, hai lượt có thể cho cùng SQL. Ví dụ lấy từ database khác chỉ hỗ trợ prompt; câu SQL đầu ra vẫn chạy trên database được giao.

## 4:00–5:15 · Codex MCP SQL: agent điều phối hai công cụ

**Thao tác:** Chọn Codex MCP SQL, chỉ tổng quan và khung PHIÊN CODEX MCP SQL. Mở Codex · Điều phối & SQL để xem request/instructions. Mở lần gọi Khám phá schema và Chạy thử SQL có bản ghi, chỉ mũi tên phản hồi quay về agent. Cuối cùng trở lại node điều phối để xem SQL và trạng thái runner.

**Lời nói:**

> Với Codex MCP SQL, một agent điều phối hai công cụ bên trong cùng phiên. Input của agent là câu hỏi, database và hướng dẫn dùng công cụ; không có gold SQL.
>
> Công cụ search_objects nhận tham số tìm kiếm do agent chọn. Output là schema thực tế như bảng, cột, DDL và khóa ngoại. Thông tin này quay về agent để nó quyết định viết SQL hoặc khám phá thêm.
>
> Công cụ execute_sql nhận câu SQL do agent tạo và chạy thử trên database. Output là dữ liệu hoặc lỗi, cũng quay lại agent. Nếu có lỗi hoặc cần kiểm tra thêm, agent có thể sửa SQL, tìm thêm schema và gọi công cụ tiếp. Các lần gọi được đánh số theo thứ tự thực tế.
>
> Vì vậy, hai công cụ nằm trong khung phiên, còn các mũi tên quay về agent thể hiện vòng tương tác. Không phải phiên nào cũng phải sửa lỗi hay gọi mỗi công cụ đúng một lần.
>
> Khi agent kết thúc, runner xác nhận đã khám phá schema thành công và SQL cuối khớp một câu SQL đã chạy thành công qua công cụ. SQL cuối nằm trong output của node điều phối. Sau đó hệ thống mới chuyển nó ra ngoài phiên để đánh giá với gold SQL.

## 5:15–6:00 · Khung đánh giá bổ sung dùng chung

**Thao tác:** Mở node Đánh giá SQL (bổ sung) trong khung HỆ THỐNG ĐÁNH GIÁ BỔ SUNG. Chỉ SQL dự đoán và gold SQL ở input; ở output chỉ bảng dữ liệu và SQLite EX.

**Lời nói:**

> Cả bốn phương pháp đều có một khung riêng mang tên HỆ THỐNG ĐÁNH GIÁ BỔ SUNG. Đây là bước do hệ thống thực nghiệm thêm để chấm đầu ra theo cùng cách.
>
> Input gồm SQL phương pháp đã sinh và gold SQL của câu mẫu. Hệ thống thực thi trên cùng database rồi so sánh toàn bộ kết quả, không chỉ các dòng preview đang hiển thị. Output là dữ liệu truy vấn và điểm SQLite EX.
>
> Với câu đếm ca sĩ, nếu cả hai trả cùng kết quả sáu thì EX bằng một. Gold SQL chỉ được dùng để chấm sau khi phương pháp trả SQL. Nếu tự nhập câu hỏi mới không có gold, hệ thống vẫn có thể chạy truy vấn nhưng không kết luận đúng đáp án.

## 6:00–6:45 · Đọc CM, EM, EX và VES

**Thao tác:** Chọn DIN-SQL → Result. Chỉ các thẻ điểm đã tính. Chỉ đọc giá trị có trên màn hình; nếu chưa tính được, dùng lời giải thích ý nghĩa mà không đọc điểm dự kiến.

**Lời nói:**

> Trên Result, em xem kết quả theo bốn góc độ. CM chấm từng thành phần SQL như SELECT, WHERE; thành phần cả hai câu không dùng sẽ hiện dấu gạch. EM chấm cấu trúc toàn câu theo evaluator Spider, không phải so sánh nguyên chuỗi SQL.
>
> EX kiểm tra kết quả thực thi có khớp đáp án. VES xem thêm hiệu suất thực thi SQL khi kết quả hợp lệ; không tính thời gian LLM sinh SQL. VES có thể dao động và vượt một trăm.
>
> Các điểm ở đây thuộc một câu demo. Chúng giúp giải thích đầu ra, còn kết luận so sánh các phương pháp phải dựa trên toàn bộ tập đánh giá.

## 6:45–7:00 · Kết thúc

**Thao tác:** Giữ màn hình Result.

**Lời nói:**

> Qua demo, DIN-SQL chia bước và tự kiểm tra một lần; MAC-SQL có vòng Refiner; DAIL-SQL chọn ví dụ qua hai lượt; Codex tương tác với công cụ. Trace giúp theo dõi từng bước, còn khung đánh giá bổ sung giúp đối chiếu đầu ra theo cùng tiêu chí. Dạ, em xin kết thúc.

## Nếu cần rút còn khoảng 5 phút

Giữ 30 giây mở đầu, 45 giây mỗi phương pháp, 60 giây cho đánh giá và độ đo, 15 giây kết thúc. Tổng phần nói là 4 phút 45 giây, còn khoảng 15 giây chuyển màn hình. Dùng lời mở đầu và kết thúc rút gọn, vẫn nói rõ đây là trace đã lưu và database đã được cung cấp.

**DIN-SQL:**

> DIN-SQL nhận câu hỏi và schema, liên kết với bảng singer, rồi phân loại để chọn prompt sinh SQL. Output là SQL đếm ca sĩ. LLM tự kiểm tra SQL một lần trước khi chuyển sang đánh giá. Không có phản hồi SQLite quay lại sửa SQL.

**MAC-SQL:**

> Selector chuẩn bị schema và chuyển trạng thái cho Decomposer. Decomposer nhận prompt và sinh SQL. Refiner chạy thử; có lỗi thì dùng lỗi để gọi LLM sửa rồi chạy lại, tối đa ba lượt. SQL đã chạy thành công mới được chuyển sang đánh giá bổ sung với gold. Nhánh sửa chỉ được diễn giải là đã chạy khi có bản ghi thực tế.

**DAIL-SQL:**

> Lượt đầu chọn ví dụ train, ghép prompt và sinh SQL sơ bộ. Lượt hai dùng thêm cấu trúc SQL sơ bộ để chọn lại ví dụ và sinh SQL cuối. Đây là hai lượt cố định, không thực thi SQLite ở giữa để sửa lỗi.

**Codex MCP SQL:**

> Agent nhận câu hỏi và database. search_objects trả schema; execute_sql trả kết quả hoặc lỗi. Các phản hồi quay về agent để quyết định khám phá thêm, sửa hoặc chạy lại. Runner xác nhận SQL cuối đã được chạy thành công trước khi chuyển sang khung đánh giá bổ sung.

**Đánh giá và độ đo:**

> Khung HỆ THỐNG ĐÁNH GIÁ BỔ SUNG thuộc hệ thống thực nghiệm, dùng chung cho bốn phương pháp. Input là SQL dự đoán và gold SQL; output là dữ liệu cùng SQLite EX khi có gold. Gold không được gửi cho mô hình. Trên Result, CM chấm thành phần, EM chấm cấu trúc, EX chấm kết quả, VES xét hiệu suất SQL hợp lệ. Đây là điểm một câu, chưa đủ để xếp hạng phương pháp.

## Trả lời ngắn khi được hỏi thêm

**Vì sao phải biết database?**

> Trong thí nghiệm này, mỗi câu Spider đã có db_id xác định database đích. Các phương pháp xử lý câu hỏi trong database được giao. Tự chọn database giữa nhiều nguồn là một bài toán mở rộng chưa được chấm ở đây.

**Dataset này chỉ có một schema phải không?**

> Spider dev đang dùng có nhiều database. Mỗi database là một file SQLite có tập bảng và quan hệ riêng. Từ schema trong demo nói đến cấu trúc đó, không phải một namespace có tên như schema của PostgreSQL. Trong PostgreSQL, một database có thể chứa nhiều schema, mỗi schema chứa nhiều bảng; hệ thống cần được cấp quyền truy cập phạm vi phù hợp.

**PostgreSQL của app có phải nơi chạy SQL demo không?**

> PostgreSQL lưu lịch sử và metadata của ứng dụng. Các SQL Spider trong demo chạy trên file SQLite tương ứng với db_id.

**Vì sao Decomposer chỉ còn một node?**

> Node trạng thái và lời gọi LLM trước đây mô tả các phần của cùng một bước. Giao diện gộp chúng để xem input, prompt, phản hồi và trạng thái đầu ra trong một nơi. Refiner vẫn tách các lần chạy thử và sửa để thấy được vòng lặp.

**DIN-SQL và DAIL-SQL có vòng sửa theo lỗi SQL không?**

> Không trong cấu hình hiện tại. DIN-SQL tự kiểm tra bằng LLM một lần; DAIL-SQL đi qua hai lượt cố định. Cả hai không dùng kết quả thực thi cuối để quay lại sửa SQL.

**Refiner có sửa khi kết quả rỗng không?**

> Với cấu hình Spider hiện tại, Refiner sửa khi thực thi SQL báo lỗi. Kết quả rỗng hoặc NULL không tự kích hoạt sửa. Chạy được vẫn có thể sai ý nghĩa, nên cần bước chấm với gold.

**MAC-SQL hết lượt mà vẫn lỗi thì sao?**

> Adapter hiện tại dừng và báo lỗi nếu SQL trả về chưa được xác nhận chạy thành công. SQL vừa sửa mà chưa chạy lại thành công không được chuyển sang chấm gold.

**Tại sao Codex chạy thử rồi vẫn cần đánh giá?**

> Chạy thử chứng minh câu lệnh thực thi được và cung cấp dữ liệu cho agent. Xác nhận runner kiểm tra quy trình dùng công cụ và SQL cuối đã được thử. Chỉ bước đánh giá bổ sung mới đối chiếu kết quả với gold SQL.

**EX bằng một có chứng minh đúng trong mọi trường hợp không?**

> EX ở đây cho biết hai SQL khớp kết quả trên database hiện có. Đây không phải chứng minh tương đương trên mọi dữ liệu, cũng không phải test-suite accuracy.

**VES có phải phần trăm câu đúng không?**

> Không. VES xét tỷ lệ hiệu suất khi kết quả hợp lệ, có thể vượt một trăm và thay đổi theo tải máy. Thời gian sinh SQL và gọi mô hình không nằm trong phép đo này.

## Lời thay thế khi trace thiếu dữ liệu hoặc demo gặp sự cố

**MAC-SQL trace cũ thiếu bản ghi chạy thử riêng:**

> Trace này ghi trạng thái Refiner giữ nguyên SQL và trả về hệ thống, nhưng chưa có bản ghi riêng của lần chạy thử. Em chỉ kết quả sáu tại bước đánh giá bổ sung; không dùng trạng thái này để khẳng định một lần chạy thử đã được ghi nhận.

**Codex trace cũ thiếu xác nhận audit của runner:**

> Trace này có lời gọi công cụ và phản hồi cuối của agent, nhưng chưa ghi xác nhận audit riêng của runner. Em đối chiếu SQL agent trả về và kết quả đánh giá bổ sung đang hiển thị.

**Chạy live chậm:**

> Dịch vụ đang phản hồi chậm. Em chuyển sang trace một phiên chạy thật đã lưu để tiếp tục xem input và output.

**Điểm N/A hoặc chưa có kết quả:**

> Hiện tại chưa tính được điểm này. Em giải thích theo trạng thái hiển thị; N/A không có nghĩa là điểm không.

Nếu dùng ảnh dự phòng, nói rõ đó là ảnh đo trước trên cùng phiên. Nếu output khác bản đã tập, đọc dữ liệu thực tế. Node chưa chạy hoặc chưa có bản ghi không được trình bày như bước đã hoàn tất.
