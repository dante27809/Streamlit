# Thu Vàng – Phần Lập trình & AI (sản phẩm mẫu mùa thu)

Gói mẫu cho vai trò **Lập trình – AI** của Tổ 3 (mùa thu), làm theo mục 8 và nhiệm vụ 6–7 (mục 5) của kế hoạch dự án.
Cấu trúc giống gói "Sớm Mai" (mùa xuân) nhưng đã sửa những chỗ dễ làm học sinh nhầm (xem mục 4). Mùa thu có **3 tầng, 7 nguyên liệu** (thêm Sandalwood accord so với 6 nguyên liệu của mùa xuân); app đọc danh sách từ file CSV nên số nguyên liệu thay đổi được.

> **Toàn bộ số liệu trong gói là dữ liệu mô phỏng** (giới hạn nguyên liệu, điểm cảm quan, "phản hồi của AI") để app và nhật ký chạy được ngay.
> Chúng **không phải giới hạn an toàn**. Giáo viên phải thay bằng bảng đã duyệt trước khi dùng thật.

## 1. Chạy ứng dụng

```bash
pip install -r requirements.txt
streamlit run app.py
```

Cần Python 3.9 trở lên. **`app.py` và `nguyen_lieu_thu.csv` phải nằm cùng một thư mục.**

## 2. Các tệp trong gói

| Tệp | Vai trò | Ai sửa |
|---|---|---|
| `app.py` | Ứng dụng Streamlit: thanh trượt, kiểm tra, bảng mL, hồ sơ mùi, xuất CSV, soạn prompt, kiểm chứng đề xuất AI | Nhóm lập trình |
| `nguyen_lieu_thu.csv` | Bảng nguyên liệu và **giới hạn do giáo viên cung cấp** | **Giáo viên** |
| `requirements.txt` | Thư viện cần cài | – |
| `prompt_log.md` | Nhật ký prompt AI (mẫu đã điền, dữ liệu mô phỏng) | Nhóm |
| `test_plan.md` | Kế hoạch và kết quả kiểm thử | Nhóm |
| `test_app.py` | Kiểm thử tự động (không cần cài thêm thư viện) | Tùy chọn |
| `.streamlit/config.toml` | Giao diện màu thu | Tùy chọn (xóa đi app vẫn chạy) |

Đối chiếu với danh mục nộp (mục 17.3 báo cáo mẫu): `03_app.py` = `app.py` **kèm `nguyen_lieu_thu.csv`**; `04_requirements.txt` = `requirements.txt`; `07_Nhat_ky_prompt_AI.pdf` = in/xuất từ `prompt_log.md`.
**Gói này chưa có "ảnh/video chạy thử"** (sản phẩm nộp của nhiệm vụ 7): nhóm tự chụp hoặc quay sau khi chạy thật app.

### Đọc mã nguồn từ đâu

`app.py` dài khoảng 770 dòng (gồm cả chú thích và dữ liệu cấu hình) nhưng chia thành 5 phần theo thứ tự đọc; không cần hiểu hết cùng lúc.

| Phần | Gồm | Số dòng hàm | Bắt buộc? |
|---|---|---|---|
| Mức tối thiểu (kế hoạch 8.1) | `calculate_formula`, `tier_shares`, `dominant_tier_description`, `build_csv`; `render_sliders`, `render_validation`, `render_profile`, `render_export` | khoảng 210 | **Có** (ngang cỡ bản mùa xuân) |
| Đọc bảng của giáo viên | `doc_bang_nguyen_lieu` và các hàm phụ | khoảng 90 | Có |
| AI có kiểm soát (kế hoạch 8.3) | `build_prompt`, `check_proposal`, `render_ai`, `render_notes` | khoảng 240 | Mở rộng cho nhóm khá |

Nhóm chưa đủ thời gian có thể xóa hai dòng `render_ai(...)` và `render_notes(...)` trong `main()`: app vẫn chạy đầy đủ phần tối thiểu (đã kiểm tra). Nhưng **nhật ký prompt AI (`prompt_log.md`) vẫn bắt buộc** vì nằm trong tiêu chí "Sử dụng AI có trách nhiệm".

## 3. Bảng nguyên liệu của giáo viên (`nguyen_lieu_thu.csv`)

App đọc giới hạn từ file này (không viết cứng trong mã) để giáo viên thay dữ liệu mà không động vào chương trình.

| Cột | Ý nghĩa | Ví dụ |
|---|---|---|
| `ma` | Mã ngắn, không trùng trong cùng mùa, không dùng `SO` (dành cho dung môi) | `SW` |
| `mua` | Xuân, Hạ, Thu hoặc Đông | `Thu` |
| `ten` | Tên hiển thị | `Cam ngọt (Sweet orange)` |
| `tang` | Đầu, Giữa hoặc Cuối | `Đầu` |
| `vai_tro` | Vai trò cảm quan, hiện ở dấu `?` cạnh thanh trượt | `Ngọt dịu – gợi trái cây chín` |
| `gioi_han_pct` | Giới hạn tối đa, % thể tích trong cả chai | `3.0` |
| `trang_thai` | Ghi đúng `ĐÃ DUYỆT` khi giáo viên đã duyệt. Giá trị khác (hoặc bỏ cột) được coi là chưa duyệt | `MÔ PHỎNG (chưa duyệt)` |

- Giới hạn đặt **theo từng nguyên liệu**; tổng hương tối đa chính là tổng các giới hạn (bảng mẫu: 3.0 + 2.0 + 4.0 + 4.0 + 3.5 + 2.5 + 1.0 = 20.0%). Muốn giới hạn tổng hương thấp hơn, hạ giới hạn của từng nguyên liệu.
- Cột thừa (nhà cung cấp, số lô, link SDS…) được bỏ qua, nên giáo viên có thể thêm.
- Lưu từ Excel bằng **CSV UTF-8**. App vẫn đọc được dấu `;`, số thập phân dạng `3,0` và mã hóa cp1258 của Excel tiếng Việt đời cũ. Nếu bảng sai, app báo từng dòng lỗi thay vì sập.
- Khi mọi dòng của mùa ghi `ĐÃ DUYỆT`, khung "MÔ PHỎNG" đổi thành thông báo đã duyệt và CSV xuất ra ghi nguồn tương ứng. **Đây là nhắc nhở chứ không phải cơ chế bảo mật**: học sinh vẫn có thể tự sửa file, nên giáo viên cần giữ bản gốc và đối chiếu khi nhận bài.

## 4. Những chỗ học sinh dễ nhầm

| # | Dễ nhầm | Hiểu đúng | Xem ở |
|---|---|---|---|
| 1 | "Tổng 100% và không vượt giới hạn nghĩa là công thức an toàn." | Đó chỉ là kiểm tra toán học: "đủ điều kiện gửi giáo viên xem xét". An toàn phụ thuộc nhãn, SDS, giới hạn của nhà cung cấp/IFRA và quyết định của giáo viên. App không bao giờ nói "an toàn". | Cảnh báo đầu trang; Ca 16 |
| 2 | "Giới hạn trong app là giới hạn thật." | Đây là **dữ liệu mô phỏng**. Giáo viên nhập giới hạn thật vào `nguyen_lieu_thu.csv` rồi ghi `ĐÃ DUYỆT`. Nhóm không tự đặt giới hạn. | Mục 3; khung "MÔ PHỎNG" |
| 3 | "Bảng tham khảo ghi Cam ngọt = 15 thì nhập 15%." | Bảng tham khảo ghi **số phần trên 100 phần hỗn hợp hương**. App dùng **% thể tích trong cả chai**. % trong chai = số phần × tổng hương (%) ÷ 100. Ví dụ: 15 × 14.4 ÷ 100 = 2.16%, tức 0.216 mL cho mẻ 10 mL. Cột "Số phần / 100 phần hương" trong bảng của app giúp quy đổi ngược để so sánh. | Mục 1 và 3 của app |
| 4 | "Tỉ lệ tầng 25 : 40 : 35 là quy tắc phải đạt." | Chỉ là **hướng tham khảo của mùa**, app không dùng nó để quyết định hợp lệ. Nhóm tự đề xuất công thức trước; chỉ bật phần so sánh (tùy chọn ở mục 4 của app) sau khi nhóm xong, rồi giải thích điểm khác biệt. | Mục 4 của app |
| 5 | "Không kéo thanh trượt ra lỗi được, vậy ca kiểm thử 'vượt giới hạn' bị lỗi hoặc không làm được." | Thanh trượt bị chặn đúng ở giới hạn nên **không thể** tạo lỗi này. Kiểm thử bằng cách gọi hàm `calculate_formula` hoặc dùng `FakeSt`. | `test_plan.md`, Ca 06–07 |
| 6 | "Nộp mỗi `app.py` là đủ." | App đọc `nguyen_lieu_thu.csv`; thiếu file thì báo lỗi. Nộp kèm cả hai file và `requirements.txt`. | Mục 2 |
| 7 | "AI đã được báo giới hạn thì chắc chắn đúng giới hạn." | AI vẫn có thể vượt giới hạn, tính tổng sai hoặc **tự thêm nguyên liệu**. Trong bản mẫu, P3 đề xuất vanilla 1.20% (giới hạn 1.00%) và bản nháp giới thiệu nhắc "quế". Mọi con số phải nhập vào mục 6b hoặc Excel; app không tự sửa số của AI. | Mục 6b; `prompt_log.md` mục 4.3 và 6 |
| 8 | "Đạt 7/7 điều kiện thì chọn luôn" và "dự đoán mùi của AI là kết quả". | Đạt kiểm tra chỉ là **đủ điều kiện để xem xét** (bản mẫu: P2 đạt 7/7 nhưng bị loại vì sai concept). Dự đoán của AI chỉ là giả thuyết vì AI không ngửi được lô nguyên liệu thật; phải kiểm chứng bằng thực nghiệm (B so với B2) sau khi giáo viên duyệt. | `prompt_log.md` mục 4.4 và 4.5 |
| 9 | "Prompt ngắn là đủ; số liệu gõ tay cho nhanh." | Prompt cần 4 phần: dữ liệu – mục tiêu – ràng buộc – định dạng đầu ra. Dùng mục 6a để app điền số liệu và ràng buộc (tránh gõ nhầm). Không đưa tên học sinh, ảnh, liên hệ hay API key vào prompt. | Mục 6a |
| 10 | "Hỏi AI một lần là đủ, không cần ghi lại." | Phải lưu nguyên văn prompt, phản hồi, ngày giờ, quyết định và lý do. AI trả lời khác nhau mỗi lần nên hỏi lại ở phiên mới để so sánh. Khai báo mọi phần có AI hỗ trợ. | `prompt_log.md` mục 5 và 7 |
| 11 | "App và Excel ra số khác nhau thì một trong hai sai." | Excel của báo cáo mẫu làm tròn từng dòng bằng `ROUND(…,3)`, còn app cộng trên số chưa làm tròn, nên cộng tay các dòng có thể lệch vài phần nghìn mL (tối đa 0.004). Kết luận hợp lệ vẫn giống nhau. | Mục 3 của app; Ca 08, 17 |
| 12 | "Mở CSV thấy dồn một cột hoặc chữ lỗi nghĩa là app xuất sai." | Excel tiếng Việt thường dùng dấu `;`. Mở bằng **Dữ liệu → Từ văn bản/CSV**, chọn UTF-8 và dấu phẩy; hoặc dùng Google Sheets (Tệp → Nhập). | Mục 5 của app; Ca 19 |

## 5. Dùng cho mùa hoặc nhóm khác

1. Thêm các dòng của mùa vào `nguyen_lieu_thu.csv` (cột `mua` = Xuân, Hạ hoặc Đông). Mùa chưa có dòng nào thì app báo rõ và không hiện thanh trượt.
2. Trong `app.py`: đổi `TEN_SAN_PHAM`, `MUA_MAC_DINH`, `MA_MAU_MAC_DINH`; thêm công thức của nhóm vào `CONG_THUC_NHOM["<mùa>"]` với khóa `"B"` (gốc, đã gửi AI) và `"B2"` (mặc định của thanh trượt). Chưa có thì thanh trượt bắt đầu ở 0.
3. Thể tích mẻ cho phép 1–20 mL theo báo cáo mẫu (mã khung trong kế hoạch ghi 1–50 mL): đổi `THE_TICH_MIN`, `THE_TICH_MAX` nếu cần.
4. Tùy chọn: thêm `VI_DU_PROMPT` và `DE_XUAT_AI_MAU` cho mùa đó. Nếu không, mục 6 chỉ có chế độ "làm với công thức của nhóm" và các ô prompt để trống.
5. Ghi kết quả vào `prompt_log.md` và `test_plan.md` của nhóm.

## 6. Kiểm thử

```bash
python -m unittest -v test_app
```

Kết quả khi soạn gói này: 89 ca chạy, OK; 2 ca bỏ qua vì máy soạn không cài được Streamlit. Giao diện được thử bằng `FakeSt` (Streamlit giả). **Cần chạy thật `streamlit run app.py` một lần và tick Ca 18–21 trong `test_plan.md` trước khi dùng trong lớp.**

## 7. Phạm vi

- Mô hình giáo dục: đánh giá mùi trên giấy thử, không dùng trên cơ thể, không bán. Quyết định cuối cùng thuộc nhóm và giáo viên.
- App **không gọi API AI nào** nên không có API key. Nhóm khá muốn kết nối API do giáo viên quản lý thì đọc khóa từ `st.secrets` hoặc biến môi trường, tuyệt đối không ghi vào mã, prompt hay kho mã nguồn.
