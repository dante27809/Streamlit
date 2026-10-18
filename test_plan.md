# Kế hoạch kiểm thử ứng dụng Thu Vàng (mùa thu)

## Cách chạy

| Cách | Lệnh | Dùng cho |
|---|---|---|
| Tự động | `python -m unittest -v test_app` (trong thư mục có `app.py`) | Ca 01–17 (và Ca 21 nếu máy đã cài Streamlit) |
| Thủ công | `pip install -r requirements.txt` rồi `streamlit run app.py` | Ca 18–20 và việc xem bằng mắt các ca khác |

## Đọc kỹ trước khi kiểm thử

1. **Thanh trượt thật không thể vượt giới hạn.** Giá trị lớn nhất của mỗi thanh trượt chính là giới hạn của giáo viên, và tổng giới hạn của cả 7 nguyên liệu chỉ là 20%. Vì vậy Ca 06 (vượt giới hạn) và Ca 07 (tổng hương > 100%, dung môi âm) **không thể làm bằng cách kéo thanh trượt**. Phải kiểm thử bằng cách gọi hàm `calculate_formula` hoặc dùng `FakeSt` trong `test_app.py` (bản mẫu bỏ qua điều này nên học sinh dễ tưởng app lỗi khi không tạo được lỗi).
2. **`FakeSt` là "Streamlit giả"**, chỉ ghi lại những gì app hiển thị để kiểm tra logic giao diện. Nó **không thay thế** việc chạy thật `streamlit run app.py` (Ca 18–20).
3. **Cột "Kết quả thực tế" của Ca 01–17 là kết quả của lần chạy tự động** khi soạn gói này (09/10/2026; Python 3.12; pandas 3.0.2; **máy soạn không cài được Streamlit nên giao diện được thử bằng `FakeSt`**). Nhóm thật phải tự chạy lại và ghi kết quả của mình; các ca thủ công bên dưới để trống.

## Bảng ca kiểm thử

| Ca | Nội dung thử | Cách thử | Kết quả mong đợi | Kết quả thực tế | Đạt |
|---|---|---|---|---|---|
| 01 | Giá trị mặc định B2, thể tích 10 mL | Tự động | Bảng 8 dòng (7 nguyên liệu + dung môi); tổng 100%; tổng 10 mL; có nút tải CSV | 8 dòng; hương 14.40%; dung môi 85.60%; tổng 100.000%; 10.000 mL; nút tải `THU-B2_10mL.csv` | Đạt |
| 02 | Thể tích 5 mL | Tự động | Mọi mL bằng một nửa so với 10 mL | 8/8 dòng đúng một nửa (Cam ngọt 0.105 mL; dung môi 4.280 mL); tổng 5.000 mL | Đạt |
| 03 | Thể tích 20 mL | Tự động | Mọi mL gấp đôi | 8/8 dòng gấp đôi (Cam ngọt 0.420 mL; dung môi 17.120 mL); tổng 20.000 mL | Đạt |
| 04 | Tất cả thành phần hương bằng 0 | Tự động | Dung môi 100%; hợp lệ; vẫn có cảnh báo giáo viên; mô tả nói "chưa có hương" | Dung môi 100.0%; hợp lệ; cảnh báo hiển thị; mô tả "Chưa có thành phần hương để tạo mô tả."; không vẽ biểu đồ | Đạt |
| 05 | Mỗi thành phần đúng bằng giới hạn | Tự động | Không báo vượt, kể cả khi số thực lệch nhẹ (3.0000000000000013) | Cả 7 nguyên liệu tại giới hạn: hợp lệ, tổng hương 20.0%; các giá trị cộng dồn có nhiễu số thực không bị báo sai | Đạt |
| 06 | Một thành phần vượt giới hạn (VA = 1.5%) | Hàm và `FakeSt` (không kéo được) | Báo lỗi; trạng thái "Chưa hợp lệ"; không có nút tải CSV | "Vanilla accord: 1.50% vượt giới hạn dự án 1.00%."; không có nút tải | Đạt |
| 07 | Tổng hương > 100% (7 × 20% = 140%) | Hàm và `FakeSt` (không kéo được) | Dung môi âm; báo lỗi **một lần**; không có nút tải CSV | "Dung môi âm (-40.00%): tổng các thành phần hương đang vượt 100%."; một thông báo; không có nút tải | Đạt |
| 08 | Xuất CSV khi công thức hợp lệ | Tự động | UTF-8 có BOM; giữ tiếng Việt; cột khớp sheet CONG_THUC của Excel; tổng mL bằng thể tích mẻ; ghi rõ chưa duyệt an toàn | 8 dòng × 11 cột; tổng mL 10.000; tổng % 100.000; có "Cuối", "Cam ngọt (Sweet orange)"; cột Trạng thái = "Chưa GV duyệt an toàn"; cộng tay các dòng đã làm tròn lệch tối đa 0.002 mL trên cả 39 thể tích hợp lệ (giới hạn lý thuyết 0.004 mL), còn tổng chưa làm tròn đúng tuyệt đối | Đạt |
| 09 | Đổi mùa | Tự động | Concept đổi theo mùa; mùa chưa có bảng của GV thì báo rõ và không hiện thanh trượt | Thu: "Dịu, ấm, trầm nhẹ" và nhóm hương Fruity – Floral – Woody; Xuân, Hạ, Đông: báo "Chưa có bảng nguyên liệu…", 0 thanh trượt, vẫn có cảnh báo GV | Đạt |
| 10 | Mô tả theo tầng | Tự động | Đổi theo tầng lớn nhất; hai tầng gần nhau thì "cân bằng"; đúng ở biên 5 điểm | B2: "cân bằng giữa tầng Giữa (38.9%) và tầng Cuối (34.7%)"; B (đúng chênh 5.0): "thiên về tầng Giữa (40.0%)"; nặng tầng đầu: "thiên về tầng Đầu (90.9%)"; nặng tầng cuối: "thiên về tầng Cuối (90.9%)" | Đạt |
| 11 | Bảng nguyên liệu của GV sai | Tự động | Thông báo cụ thể, app không sập, không hiện thanh trượt | Báo đúng các lỗi: thiếu file, thiếu cột, giới hạn không phải số/âm/vô cực, tầng hoặc mùa sai, mã trùng, mã `SO` bị dành riêng; báo đủ 3 dòng lỗi trong một lần | Đạt |
| 12 | Bảng GV lưu từ Excel tiếng Việt | Tự động | Đọc đúng dấu `;`, số thập phân dấu phẩy, mã hóa cp1258, tên tầng không dấu, dòng trống, cột thừa | Cả 5 trường hợp đọc đúng giá trị (ví dụ "3,0" thành 3.0; "dau/giua/cuoi" thành Đầu/Giữa/Cuối) | Đạt |
| 13 | Nhãn dữ liệu và việc GV đổi giới hạn | Tự động | "MÔ PHỎNG" hiện cho đến khi GV ghi đúng "ĐÃ DUYỆT"; GV hạ giới hạn thấp hơn mặc định hoặc đặt 0 thì app không sập | Bảng hiện tại hiện "MÔ PHỎNG"; chỉ "ĐÃ DUYỆT", "đã duyệt", "DA_DUYET" được coi là duyệt (còn "duyệt", "CHƯA DUYỆT" thì không); giới hạn BG hạ xuống 1.5 thì thanh trượt tự đặt 1.5 và có thông báo; giới hạn CE = 0 thì không có thanh trượt CE | Đạt |
| 14 | Kiểm chứng đề xuất của AI (mục 6b) | Tự động | P1 và P2 đạt; P3 bị loại; đổi 4 thành phần, đổi quá 0.5, tổng sai, dung môi âm, số âm, thiếu số liệu đều bị loại; áp dụng đúng hai tham số nhóm đặt | P1 7/7; P2 7/7 (đúng ở biên ±0.50); P3 bị loại: "VA 1.20% > 1.00%"; AI quên bù dung môi thì báo "tổng 100.30%" (app không tự sửa); B2 trên thanh trượt trùng P1 | Đạt |
| 15 | Soạn prompt (mục 6a) | Tự động | Đủ 4 phần; số liệu và giới hạn khớp bảng; ràng buộc theo tham số nhóm; không có khóa API | 7 dòng nguyên liệu + dung môi khớp bảng; đổi tham số (2 thành phần, ±1) thì prompt đổi theo; có "Không kết luận công thức là an toàn"; không có api key hay token | Đạt |
| 16 | Không có câu nào khẳng định "an toàn" | Tự động | Quét mọi chữ hiển thị ở 9 tình huống; cảnh báo GV luôn hiện | Không có câu nào khẳng định an toàn ở cả 9 tình huống; câu thành công ghi rõ "chưa có nghĩa là an toàn" | Đạt |
| 17 | App và Excel cùng kết luận | Tự động, 2000 tổ hợp ngẫu nhiên | `valid`, dung môi và tổng mL khớp phép tính Decimal chính xác tuyệt đối | 2000/2000 tổ hợp khớp, gồm cả giá trị âm và vượt giới hạn | Đạt |
| 18 | **Chạy thật** `streamlit run app.py` | Thủ công | Mở được trang; không có khung lỗi đỏ của Python; kéo thanh trượt, đổi mùa, đổi thể tích đều cập nhật; bảng và biểu đồ hiển thị đúng thứ tự Đầu – Giữa – Cuối | | ☐ |
| 19 | Mở CSV đã tải trong Excel hoặc Google Sheets | Thủ công | Tiếng Việt đúng; đủ cột; số đúng | | ☐ |
| 20 | Làm mới trang (F5) | Thủ công | Trở về giá trị mặc định B2 | | ☐ |
| 21 | Công cụ `AppTest` của Streamlit | Tự động, **cần cài Streamlit** | Chạy lần đầu không có exception; kéo một thanh trượt và đổi mùa vẫn không lỗi | Máy soạn gói chưa chạy ca này (không cài được Streamlit): **cần chạy** | ☐ |

## Tiêu chí chấp nhận

- Không có lỗi Python khi chạy app (Ca 18, 21).
- Mọi phép tính % và mL đúng (Ca 01–03, 17).
- Không xuất CSV khi công thức không hợp lệ (Ca 06, 07).
- Cảnh báo giáo viên luôn hiển thị, kể cả khi bảng nguyên liệu lỗi hoặc mùa chưa có dữ liệu (Ca 04, 09, 11, 16).
- Không gọi công thức là "an toàn" (Ca 16).
- Nhãn "MÔ PHỎNG" hiển thị cho đến khi giáo viên đánh dấu "ĐÃ DUYỆT" (Ca 13).
- Mọi đề xuất của AI đều được kiểm chứng bằng app hoặc Excel trước khi dùng (Ca 14).

## Kết quả lần chạy tự động gần nhất (khi soạn gói này)

`python -m unittest -v test_app` → **89 ca chạy, OK; 2 ca bỏ qua** (lớp `TestAppTest` cần cài Streamlit).

Bộ kiểm thử đã được thử độ nhạy bằng cách cố ý làm hỏng app theo 12 cách: đổi `>` thành `>=` ở giới hạn; bỏ dung sai số thực; bỏ xử lý toàn số 0 trong mô tả; đổi dấu ngưỡng cân bằng; bỏ kiểm tra giới hạn của AI; để app tự sửa tổng của AI; tính dung môi sai; cho tải CSV khi không hợp lệ; dùng khung đỏ cho cột thanh trượt; chấp nhận giới hạn âm trong bảng của giáo viên; xóa cảnh báo giáo viên; đổi câu thông báo thành "công thức an toàn". Cả 12 lần đều có ít nhất một ca báo lỗi.
