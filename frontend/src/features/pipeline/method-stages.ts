export const methodStages: Record<
  string,
  Record<string, { purpose: string; output: string }>
> = {
  codex_mcp: {
    Input: {
      purpose:
        "Nhận câu hỏi và database. Phiên Codex chỉ nhận hai thông tin này; gold SQL chỉ dùng để chấm ở bước cuối.",
      output: "Câu hỏi và database chuyển cho agent Codex",
    },
    "Codex turn": {
      purpose:
        "Một phiên agent gồm prompt người dùng, instructions và các lần gọi MCP để khám phá schema, thử SQL, xử lý lỗi rồi trả SQL. Hai tool nằm trong khung phiên: agent gửi yêu cầu và nhận schema / kết quả / lỗi để chọn bước tiếp theo. Các lần gọi được đánh số theo thứ tự trong trace. Prompt và SQL cuối nằm trong node điều phối. Runner chỉ chấp nhận SQL cuối sau khi xác nhận đã khám phá schema thành công và SQL khớp một truy vấn MCP đã chạy thành công. Xác nhận này chưa so sánh gold SQL.",
      output: "SQL cuối và xác nhận của runner trong cùng phiên agent",
    },
    search_objects: {
      purpose:
        "Agent gọi MCP để tìm bảng, view hoặc index theo tên đối tượng hay tên cột. Công cụ trả DDL, cột, khóa ngoại và index; hỗ trợ phân trang. Đây là lời gọi công cụ với tham số do agent chọn, không có prompt LLM riêng.",
      output: "Schema tìm thấy để agent chọn bước tiếp theo",
    },
    execute_sql: {
      purpose:
        "Agent gọi MCP chạy thử một câu SQL chỉ đọc trên database được giao. Kết quả hoặc lỗi được trả lại cho agent để tiếp tục sửa hay khám phá schema. Chạy thành công chưa có nghĩa là đúng đáp án; bước này không có gold SQL.",
      output: "Kết quả chạy thử hoặc lỗi trả lại cho agent",
    },
    "SQLite execution": {
      purpose:
        "Hệ thống thực thi lại SQL đã được runner chấp nhận và so toàn bộ kết quả với gold SQL bằng SQLite EX nếu có đáp án tham chiếu. Đây là bước chấm cuối, khác với các lần agent chạy thử qua MCP.",
      output: "Kết quả truy vấn và đánh giá SQLite EX",
    },
  },
  din_sql: {
    Input: {
      purpose:
        "Nhận câu hỏi và database. Gold SQL chỉ dùng ở bước đánh giá, không gửi vào các prompt sinh SQL.",
      output: "Câu hỏi và database chuyển sang liên kết schema",
    },
    "Schema linking": {
      purpose:
        "LLM liên kết từ trong câu hỏi với bảng, cột, quan hệ và giá trị dựa trên schema, khóa ngoại và ví dụ trong prompt.",
      output: "Liên kết schema dùng cho bước phân loại và sinh SQL",
    },
    Classification: {
      purpose:
        "LLM phân loại câu hỏi và chọn nhánh prompt sinh SQL: EASY không cần JOIN hoặc truy vấn lồng; NON-NESTED cần JOIN nhưng không lồng; NESTED cần truy vấn lồng. Kết quả phân loại và chọn nhánh nằm trong cùng node.",
      output: "Nhãn phân loại và câu hỏi con",
    },
    "SQL generation": {
      purpose:
        "Ghép prompt theo nhánh EASY / NON-NESTED / NESTED, dùng câu hỏi, schema links và câu hỏi con khi cần. LLM trả về SQL ứng viên; chưa thực thi SQLite.",
      output: "SQL ứng viên chuyển sang tự kiểm tra",
    },
    "Self-correction": {
      purpose:
        "LLM tự kiểm tra SQL ứng viên một lần với câu hỏi, bảng, cột và khóa. Có thể sửa hoặc giữ nguyên SQL; không chạy SQLite giữa các bước, không có vòng thực thi lỗi → sửa → chạy lại. Chỉ thử lại cùng prompt khi lời gọi LLM phát sinh lỗi, tối đa 3 lần gọi.",
      output: "SQL sau tự kiểm tra, chuyển sang thực thi và đánh giá",
    },
    "SQLite execution": {
      purpose:
        "Chạy SQL sau tự kiểm tra trên SQLite và so kết quả với gold SQL bằng SQLite EX nếu có đáp án tham chiếu.",
      output: "Kết quả truy vấn và đánh giá SQLite EX",
    },
  },
  dail_sql: {
    Input: {
      purpose:
        "Nhận câu hỏi và database. Gold SQL của câu hỏi đích không dùng để chọn ví dụ hoặc sinh SQL.",
      output: "Câu hỏi và database chuyển sang tiền xử lý",
    },
    Preprocessing: {
      purpose:
        "Tokenize và liên kết schema cho câu hỏi đích; chuẩn bị dữ liệu Spider train + train_others để truy xuất ví dụ. Có thể tái sử dụng cache dữ liệu train, nhưng vẫn xử lý câu hỏi mới. Không gọi LLM sinh SQL ở bước này.",
      output: "Thông tin tiền xử lý và cache tập train",
    },
    "Example selection · pass 1": {
      purpose:
        "Chọn ví dụ từ tập train bằng độ tương đồng câu hỏi đã mask (EUCDISQUESTIONMASK), rồi ghép ví dụ và schema vào prompt lượt 1. Đây là bước truy xuất và ghép prompt, chưa gọi LLM sinh SQL.",
      output: "Ví dụ được chọn và prompt đã ghép cho lượt 1",
    },
    "SQL generation · pass 1": {
      purpose:
        "Gửi prompt lượt 1 đến LLM và chuẩn hóa phản hồi thành SQL sơ bộ. Prompt, phản hồi LLM và SQL được gộp trong node này. SQL sơ bộ dùng để chọn lại ví dụ, chưa chạy SQLite.",
      output: "SQL sơ bộ dùng cho lượt chọn ví dụ thứ hai",
    },
    "Example selection · pass 2": {
      purpose:
        "Dùng câu hỏi đã mask và cấu trúc SQL sơ bộ để chọn lại ví dụ (EUCDISMASKPRESKLSIMTHR), rồi ghép prompt lượt 2. Không dùng kết quả thực thi hoặc gold SQL của câu hỏi đích.",
      output: "Ví dụ được chọn lại và prompt đã ghép cho lượt 2",
    },
    "SQL generation · pass 2": {
      purpose:
        "Gửi prompt đã ghép lại đến LLM để sinh SQL cuối. Pipeline dừng sinh sau lượt 2; không có lượt 3 và không có vòng sửa theo lỗi SQLite. Chỉ thử lại lời gọi LLM khi phát sinh lỗi, tối đa 3 lần gọi với cùng prompt. Phản hồi LLM nằm trong cùng node.",
      output: "SQL cuối chuyển sang thực thi và đánh giá",
    },
    "SQLite execution": {
      purpose:
        "Chạy SQL sinh ở lượt 2 trên SQLite và so kết quả với gold SQL bằng SQLite EX nếu có đáp án tham chiếu.",
      output: "Kết quả truy vấn và đánh giá SQLite EX",
    },
  },
}

export const flowSemantics: Record<string, { title: string; flow: string }> = {
  mac_sql: {
    title: "Tổng quan luồng MAC-SQL",
    flow: "Selector chọn schema liên quan → Decomposer phân rã câu hỏi và sinh SQL → Refiner chạy thử, sửa khi lỗi và chạy lại → đánh giá SQL với gold SQL.",
  },
  codex_mcp: {
    title: "Tổng quan luồng Codex MCP SQL",
    flow: "Codex nhận câu hỏi và database → khám phá schema qua search_objects → sinh và chạy thử SQL qua execute_sql → nhận kết quả hoặc lỗi để tiếp tục khám phá, sửa và chạy lại → runner xác nhận SQL cuối đã chạy thành công → đánh giá SQL với gold SQL.",
  },
  din_sql: {
    title: "Luồng một chiều · tự kiểm tra bằng LLM một lần",
    flow: "Liên kết schema → phân loại → sinh SQL → LLM tự kiểm tra → thực thi và chấm gold. Kết quả hoặc lỗi SQLite ở bước cuối không quay về tự sửa SQL.",
  },
  dail_sql: {
    title: "Hai lượt cố định · SQL sơ bộ dùng để chọn lại ví dụ",
    flow: "Tiền xử lý → chọn ví dụ & sinh SQL lượt 1 → dùng SQL sơ bộ chọn lại ví dụ → sinh SQL lượt 2 → thực thi và chấm gold. Không chạy SQLite giữa hai lượt, không có lượt 3 hoặc vòng sửa lỗi thực thi.",
  },
}

export function describeStep(step: { id: string; stage: string }) {
  return methodStages[step.id.split("-")[0]]?.[step.stage]
}
