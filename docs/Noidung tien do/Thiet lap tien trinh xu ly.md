Thiết lập tiến trình xử lý _vtrack
Tuyệt vời, tôi đã xem xét các nguồn bạn cung cấp về hệ thống xử lý tệp video, bao gồm các mô tả chi tiết về program.py, batch_scheduler.py, file_lister.py, và các tương tác với Front-End (FE), cũng như phân tích tính nhất quán về thời gian. Dưới đây là bản tóm tắt chi tiết (briefing doc) về các chủ đề chính, ý tưởng quan trọng và sự tương tác giữa các thành phần.
Tóm tắt Chi tiết Hệ thống Quản lý và Lên Lịch Chương Trình Xử Lý Tệp Video
Briefing này tổng hợp thông tin từ các nguồn được cung cấp, mô tả chức năng, tương tác và logic hoạt động của hệ thống xử lý tệp video, tập trung vào ba tệp chính: program.py, batch_scheduler.py, và file_lister.py, cùng với tương tác với Front-End và xử lý thời gian.
1. program.py: Quản lý Chương trình và API
•
Vai trò chính: program.py đóng vai trò là bộ điều khiển chính của hệ thống, cung cấp các API cho Front-End để quản lý trạng thái chạy của chương trình, khởi động/dừng các chế độ xử lý (Lần đầu, Mặc định, Chỉ định), xác nhận quét tệp, theo dõi tiến độ và truy vấn cấu hình.
•
Chức năng chi tiết:
◦
Khởi tạo và Cấu hình: * Tạo Blueprint program_bp cho Flask. * Thiết lập các đường dẫn quan trọng (BASE_DIR, DB_PATH, LOG_DIR). * Cấu hình logging vào program.log. * Khởi tạo khóa đọc/ghi cơ sở dữ liệu (db_rwlock) và trạng thái chạy toàn cục (running_state). * Khởi tạo đối tượng BatchScheduler (scheduler).
◦
init_default_program: Kiểm tra trạng thái first_run_completed trong cơ sở dữ liệu. Nếu chương trình đã chạy "Lần đầu" trước đó và scheduler chưa hoạt động, nó sẽ tự động khởi động scheduler để tiếp tục xử lý ở chế độ "Mặc định".
◦
API Endpoint: * /program (POST): Xử lý yêu cầu chạy hoặc dừng chương trình. * Chạy "Lần đầu": * Yêu cầu tham số days. * Kiểm tra first_run_completed. Nếu đã chạy, trả về lỗi. * Cập nhật running_state (current_running="Lần đầu", days=<số ngày>). * Khởi động scheduler nếu chưa chạy. * Cập nhật first_run_completed thành true trong cơ sở dữ liệu. * Chạy "Chỉ định": * Yêu cầu tham số custom_path. * Kiểm tra sự tồn tại của đường dẫn. * Tạm dừng scheduler nếu đang chạy (scheduler.pause()). * Cập nhật running_state (current_running="Chỉ định", custom_path=<đường dẫn>). * Gọi run_file_scan với scan_action="custom". * Theo dõi trạng thái xử lý tệp cụ thể, khởi động các luồng xử lý (start_frame_sampler_thread, start_event_detector_thread). * Tiếp tục scheduler sau khi xử lý hoàn tất (scheduler.resume()). * Chạy "Mặc định": * Không yêu cầu tham số bổ sung. * Cập nhật running_state (current_running="Mặc định"). * Khởi động scheduler nếu chưa chạy. * Dừng: Xóa trạng thái trong running_state, dừng scheduler (scheduler.stop()). * /program (GET): Trả về trạng thái chạy hiện tại (current_running, days, custom_path). * /confirm-run (POST): Xác nhận và kích hoạt quá trình quét tệp ban đầu cho các chế độ (Lần đầu, Mặc định, Chỉ định) bằng cách gọi run_file_scan. * /program-progress (GET): Lấy danh sách các tệp chưa xử lý (is_processed = 0) từ bảng file_list để FE hiển thị tiến độ. * /check-first-run (GET): Kiểm tra trạng thái first_run_completed. * /get-cameras (GET): Lấy danh sách camera đã chọn từ processing_config. * /get-camera-folders (GET): Lấy danh sách thư mục con trong đường dẫn video gốc.
•
Tương tác với FE: FE gửi các yêu cầu HTTP (POST/GET) và nhận phản hồi JSON để điều khiển và cập nhật giao diện dựa trên trạng thái chương trình, tiến độ xử lý, và cấu hình.
•
Logic Thời gian (Sau cập nhật): Sử dụng datetime.now(VIETNAM_TZ) để chuẩn hóa thời gian hiện tại, đảm bảo tính nhất quán với file_lister.py.
Trích dẫn cập nhật: now = datetime.now(VIETNAM_TZ) được sử dụng ở một số nơi thay cho datetime.now().
2. batch_scheduler.py: Lên Lịch và Xử lý Hàng loạt
•
Vai trò chính: batch_scheduler.py quản lý việc lên lịch và thực hiện xử lý tệp video theo hàng loạt (batches) trong nền, tối ưu hóa việc sử dụng tài nguyên hệ thống.
•
Chức năng chi tiết:
◦
SystemMonitor: Theo dõi tải CPU để điều chỉnh batch_size động.
◦
BatchScheduler: * Khởi tạo: Thiết lập batch_size ban đầu (2), scan_interval (15 phút), timeout_seconds (900 giây), queue_limit (100). * start(): Khởi động các luồng nền: scan_thread (quét tệp định kỳ) và batch_thread (xử lý hàng loạt). * pause() / resume(): Sử dụng pause_event để tạm dừng hoặc tiếp tục hoạt động của các luồng. Chế độ "Chỉ định" sử dụng tính năng này. * scan_files (Luồng quét): Định kỳ (mỗi scan_interval) kiểm tra hàng đợi pending. Nếu hàng đợi dưới queue_limit, gọi run_file_scan("default") để thêm tệp mới vào file_list. * run_batch (Luồng xử lý): * Kiểm tra pause_event. * Điều chỉnh batch_size dựa trên CPU. * Khởi động batch_size luồng frame_sampler và một luồng event_detector. * Lấy tối đa queue_limit tệp có trạng thái 'pending' từ file_list. * Kích hoạt các sự kiện (ví dụ: frame_sampler_event) để báo hiệu cho các luồng xử lý bắt đầu. * Kiểm tra timeout cho các tệp đang xử lý. * stop(): Dừng các luồng và sự kiện.
•
Tương tác với program.py: program.py khởi động (start), tạm dừng (pause), tiếp tục (resume), và dừng (stop) scheduler dựa trên yêu cầu từ FE. program.py cũng kích hoạt quét ban đầu thông qua run_file_scan.
•
Tương tác với file_lister.py: batch_scheduler.py gọi run_file_scan (từ file_lister.py) trong luồng quét định kỳ để bổ sung tệp vào hàng đợi.
•
Logic Thời gian (Sau cập nhật): Sử dụng datetime.now(VIETNAM_TZ) khi cần thời gian hiện tại và khi so sánh thời gian timeout với created_at trong cơ sở dữ liệu.
Trích dẫn cập nhật: now = datetime.now(VIETNAM_TZ) được sử dụng. Truy vấn timeout được sửa để so sánh thời gian đã được chuẩn hóa.
3. file_lister.py: Quét và Liệt Kê Tệp
•
Vai trò chính: file_lister.py có trách nhiệm quét hệ thống tệp để tìm các tệp video phù hợp dựa trên cấu hình và chế độ chạy, sau đó lưu thông tin các tệp này vào cơ sở dữ liệu. Đây là nơi duy nhất xử lý và chuẩn hóa múi giờ Việt Nam cho thời gian tạo tệp.
•
Chức năng chi tiết:
◦
get_file_creation_time: Sử dụng FFprobe để lấy thời gian tạo tệp video (creation_time). Quan trọng là nó chuẩn hóa thời gian này sang múi giờ Việt Nam (Asia/Ho_Chi_Minh). Có cơ chế dự phòng sử dụng thời gian hệ thống nếu FFprobe thất bại.
◦
scan_files: Duyệt các thư mục (thường là input_path từ processing_config) để tìm tệp video theo các định dạng được hỗ trợ.
◦
Lọc tệp: Áp dụng nhiều tiêu chí lọc: * selected_cameras: Chỉ tệp từ camera đã chọn. * time_threshold: Giới hạn thời gian tạo (cho chế độ "first"). * max_created_at: Bỏ qua các tệp đã quét (cho chế độ "default" quét định kỳ). * restrict_to_current_date: Chỉ quét trong ngày hiện tại (cho "default" quét định kỳ). * working_days, from_time, to_time: Lọc theo ngày làm việc và khung giờ cấu hình.
◦
save_files_to_db: Chèn thông tin các tệp tìm thấy vào bảng file_list, bao gồm file_path, created_at (ở VIETNAM_TZ), ctime (ở VIETNAM_TZ), status ('pending'), program_type, priority (ưu tiên 1 cho "custom").
◦
list_files: Tải cấu hình (input_path, selected_cameras, working_days, etc.) và điều phối quá trình quét dựa trên scan_action (custom, first, default).
◦
run_file_scan: Hàm chính được gọi từ bên ngoài, lấy video_root và gọi list_files.
•
Tương tác với program.py: program.py gọi run_file_scan để bắt đầu quá trình quét tệp cho các chế độ chạy khác nhau.
•
Tương tác với batch_scheduler.py: batch_scheduler.py gọi run_file_scan để thực hiện quét tệp định kỳ và bổ sung tệp vào hàng đợi xử lý.
•
Logic Thời gian: file_lister.py là nơi đảm bảo tất cả các mốc thời gian liên quan đến tệp (thời gian tạo) và thời gian quét (time_threshold, max_created_at) đều được quy đổi và xử lý trong múi giờ Việt Nam. Điều này rất quan trọng để đảm bảo tính nhất quán khi so sánh thời gian trong batch_scheduler.py và program.py.
4. Tương tác Giữa các Thành phần và Luồng Hoạt động (Ví dụ: Chạy "Lần đầu", "Mặc định", "Chỉ định")
•
Chạy "Lần đầu":
◦
FE gửi POST /program (card="Lần đầu", action="run", days=<số ngày>).
◦
program.py kiểm tra first_run_completed, cập nhật running_state, khởi động scheduler (nếu chưa chạy), và cập nhật first_run_completed = true.
◦
FE gửi POST /confirm-run (card="Lần đầu").
◦
program.py gọi run_file_scan ("first", days=<số ngày>) trong file_lister.py.
◦
file_lister.py quét tệp video trong khoảng thời gian days, chuẩn hóa thời gian tạo sang VIETNAM_TZ, và lưu vào file_list.
◦
batch_scheduler.py's run_batch luồng xử lý các tệp 'pending' mới được thêm vào file_list theo hàng loạt, điều chỉnh batch_size động.
◦
FE định kỳ GET /program-progress để hiển thị tiến độ xử lý tệp.
◦
Chương trình chạy cho đến khi bị dừng hoặc ứng dụng tắt.
•
Chạy "Mặc định":
◦
FE gửi POST /program (card="Mặc định", action="run").
◦
program.py cập nhật running_state, khởi động scheduler (nếu chưa chạy).
◦
FE gửi POST /confirm-run (card="Mặc định").
◦
program.py gọi run_file_scan ("default") trong file_lister.py.
◦
file_lister.py quét tệp theo cấu hình mặc định (thường là thư mục video root), chuẩn hóa thời gian và lưu vào file_list.
◦
batch_scheduler.py's run_batch xử lý các tệp. scan_files luồng định kỳ (mỗi 15 phút) gọi run_file_scan ("default") để quét thêm tệp nếu hàng đợi chưa đầy.
◦
FE định kỳ GET /program-progress.
◦
Chương trình chạy liên tục cho đến khi bị dừng hoặc ứng dụng tắt.
•
Chạy "Chỉ định":
◦
FE gửi POST /program (card="Chỉ định", action="run", custom_path=<đường dẫn>).
◦
program.py kiểm tra custom_path.
◦
program.py gọi scheduler.pause() để tạm dừng xử lý nền.
◦
program.py cập nhật running_state.
◦
program.py gọi run_file_scan ("custom", custom_path=<đường dẫn>) trong file_lister.py. file_lister.py quét tệp tại đường dẫn cụ thể, chuẩn hóa thời gian, lưu vào file_list với priority=1.
◦
program.py kiểm tra và khởi động luồng xử lý cho tệp 'pending' có priority=1. Theo dõi trạng thái xử lý tệp này cho đến khi xong.
◦
program.py gọi scheduler.resume() để tiếp tục xử lý nền.
◦
FE định kỳ GET /program-progress.
◦
Chương trình chạy cho đến khi bị dừng hoặc ứng dụng tắt.
•
Khởi động lại ứng dụng:
◦
Ứng dụng khởi tạo lại môi trường và running_state.
◦
init_default_program kiểm tra first_run_completed trong cơ sở dữ liệu.
◦
Nếu first_run_completed là true và scheduler chưa chạy, init_default_program gọi scheduler.start(). Điều này làm cho scheduler tiếp tục chạy ở chế độ "Mặc định", xử lý các tệp 'pending' còn lại từ lần chạy trước.
◦
FE có thể kiểm tra trạng thái qua GET /program (ban đầu là null) và GET /check-first-run để điều chỉnh giao diện.
◦
FE tiếp tục theo dõi tiến độ qua GET /program-progress.
5. Tính Nhất Quán và Logic Thời Gian (Sau cập nhật)
•
file_lister.py: Đảm bảo tính nhất quán về múi giờ bằng cách chuẩn hóa tất cả thời gian tạo tệp sang múi giờ Việt Nam (Asia/Ho_Chi_Minh) trước khi lưu vào cơ sở dữ liệu hoặc sử dụng trong các so sánh thời gian quét (time_threshold, max_created_at). Đây là điểm mạnh quan trọng để tránh sai lệch.
•
batch_scheduler.py & program.py (Sau cập nhật): Các cập nhật đảm bảo rằng các thành phần này cũng sử dụng datetime.now(VIETNAM_TZ) khi cần lấy thời gian hiện tại và so sánh với dữ liệu thời gian từ file_lister.py (ví dụ: kiểm tra timeout). Điều này khắc phục rủi ro lệch múi giờ nếu hệ thống chạy ở múi giờ khác.
•
Cơ sở dữ liệu (file_list): Dữ liệu thời gian (created_at, ctime) được lưu bởi file_lister.py là ở VIETNAM_TZ, đảm bảo tính nhất quán trong dữ liệu lưu trữ. Các truy vấn từ các tệp khác sử dụng dữ liệu này một cách chính xác nếu thời gian hiện tại được so sánh cũng ở cùng múi giờ.
•
Kiểm tra tính thống nhất: Sau cập nhật, hệ thống đạt được tính thống nhất cao hơn về xử lý thời gian. Tất cả các thành phần chính đều hoạt động dựa trên giả định thời gian hiện tại và thời gian trong cơ sở dữ liệu đều liên quan đến múi giờ Việt Nam, giảm đáng kể nguy cơ sai lệch trong logic quét và xử lý tệp.
6. Hạn chế và Điểm cần cải thiện (Từ phân tích):
•
Hiệu suất FFprobe: Việc gọi FFprobe cho mỗi tệp trong file_lister.py vẫn là một điểm tiềm năng gây chậm trễ, đặc biệt với số lượng tệp lớn. Cần xem xét cơ chế cache hoặc xử lý song song cho việc này.
•
Xử lý lỗi: Mặc dù có ghi log lỗi, cơ chế thử lại cho các thao tác như gọi FFprobe hoặc truy vấn DB khi thất bại còn hạn chế.
•
Kiểm tra cấu hình: Cần thêm kiểm tra chặt chẽ hơn đối với các cấu hình bắt buộc (video_root, selected_cameras) trong file_lister.py trước khi tiến hành quét.
Tóm lại, hệ thống được thiết kế với kiến trúc rõ ràng, phân chia trách nhiệm giữa các tệp: program.py quản lý trạng thái và API, batch_scheduler.py xử lý việc lên lịch và hàng loạt, và file_lister.py thực hiện quét tệp và quản lý dữ liệu thời gian. Tương tác với FE được thực hiện qua các API RESTful. Việc chuẩn hóa múi giờ Việt Nam trong file_lister.py là một điểm mạnh quan trọng, và các cập nhật ở program.py và batch_scheduler.py đã cải thiện tính nhất quán trong toàn bộ hệ thống.
Đây là bản tóm tắt chi tiết dựa trên thông tin bạn cung cấp. Hy vọng nó hữu ích!