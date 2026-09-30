# camera_capture

通过 OpenCV 调用本机摄像头，拍一张照片，或按指定目标帧率拍摄指定张数。照片以 JPG 格式保存；默认目录是本工具文件夹下的 `output/`，也可指定其他目录。

来源：直接在本工具盒中创建，以本目录为维护位置。

## 准备

需要可访问的摄像头。按以下步骤创建 `toolkit-camera` conda 环境（Python 3.11）并安装依赖：

```bash
conda create -n toolkit-camera python=3.11 pip -y
conda activate toolkit-camera
python -m pip install -r camera_capture/requirements.txt
```

## 傻瓜式启动

在终端运行：

```bash
bash camera_capture/start.sh
```

脚本会先激活 `toolkit-camera` 环境，再提示输入摄像头编号（通常是 `0`）、选择拍一张或拍多张、输入张数、帧率和保存目录。直接回车可使用提示中的默认值。

## 命令行使用

```bash
# 拍一张，保存到默认目录（先激活环境）
conda run -n toolkit-camera python camera_capture/capture_camera.py

# 用 2 帧/秒拍 10 张，保存到指定目录
conda run -n toolkit-camera python camera_capture/capture_camera.py --camera 0 --count 10 --fps 2 --output /tmp/camera_photos
```

`--camera` 默认 `0`，`--count` 默认 `1`，`--fps` 默认 `1`。输出文件名包含本次运行的时间和序号。指定目录不存在时会自动创建。

## 局限

- 帧率是采集目标间隔；摄像头读取和写入较慢时，实际帧率可能更低。按成功保存的张数计数，不保证视频流每一帧都被保存。
- 使用摄像头设备编号，不提供实时预览、定时延迟、分辨率设置或视频录制。
- 摄像头打不开、某帧读取失败或图片写入失败时会报错退出；此前保存成功的照片会保留。
- 使用环境需要允许当前进程访问摄像头。无摄像头或缺少 `cv2` 时无法实际拍摄。
