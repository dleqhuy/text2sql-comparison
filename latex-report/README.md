# Báo cáo cuối kỳ Nhóm 11 — LaTeX

Chuyển từ `Team11_Final Report_v4.docx.md`; lấy logo và 5 hình gốc có độ phân giải cao từ `Team11_Final Report_v4.docx`. Giữ nội dung tiếng Việt, bảng số liệu và 14 tài liệu tham khảo của bản nguồn.

## Cấu trúc

```text
latex-report/
├── main.tex                       # Điểm vào duy nhất
├── config/preamble.tex            # Font, khổ giấy, định dạng, gói LaTeX
├── frontmatter/                   # Bìa, nhận xét, cảm ơn, thuật ngữ
├── chapters/                      # 5 chương, mỗi chương một file
├── figures/                       # Logo và 5 hình từ Word
├── bibliography/references.tex    # 14 bibitem, trích dẫn bằng \cite{refN}
├── Makefile
└── build/                         # PDF và file tạm khi build (được gitignore)
```

## Biên dịch

Dùng **XeLaTeX**, hỗ trợ UTF-8 và tiếng Việt. Cần TeX Live với XeTeX, bộ tiếng Việt, các gói LaTeX trong `config/preamble.tex`, font TeX Gyre Termes, TeX Gyre Heros, DejaVu Sans Mono và `latexmk`. Trên Ubuntu/Debian có thể cài:

```bash
sudo apt-get install texlive-xetex texlive-lang-other texlive-latex-extra texlive-fonts-recommended fonts-dejavu-core latexmk
```

Chạy ngay trong thư mục `latex-report`:

```bash
make
# hoặc
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```

PDF đầu ra: `build/main.pdf`. Nếu dùng XeLaTeX trực tiếp, chạy 2–3 lần để cập nhật mục lục và trích dẫn. Không cần BibTeX/Biber vì các mục tham khảo được khai báo bằng `thebibliography`.

Trên Overleaf: tải toàn bộ thư mục lên, chọn `main.tex` làm Main document và XeLaTeX làm Compiler.

## Quy ước chỉnh sửa

- Sửa nội dung tại `chapters/`; chỉnh định dạng chung tại `config/preamble.tex`.
- Hình, bảng, chương và mục được đánh số tự động. Bảng dài dùng `longtable`, có lặp lại tiêu đề khi sang trang.
- Mục lục và danh mục hình/bảng được sinh tự động, thay cho các số trang cố định trong Markdown.
- Công thức được viết lại bằng toán LaTeX. Ở công thức SFT (5), bỏ chữ `log` lặp trong bản Markdown (`log log Pr`), dùng một `\log\Pr` cho cross-entropy; các số liệu thực nghiệm được giữ nguyên.
- Bố cục A4, cỡ chữ 12pt, mỗi chương bắt đầu trang mới. Không ép số trang về bố cục Word; câu “7 trang nội dung chính” trong lời cảm ơn vẫn được giữ theo nguồn và cần cập nhật nếu yêu cầu nộp bài thay đổi.
