import os
import subprocess
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Deque, Generator, List, Optional, Tuple

import cv2
import gradio
from tqdm import tqdm

from facefusion import ffmpeg_builder, logger, state_manager, wording
from facefusion.audio import create_empty_audio_frame
from facefusion.common_helper import is_windows
from facefusion.content_analyser import analyse_stream
from facefusion.face_analyser import get_average_face, get_many_faces
from facefusion.ffmpeg import open_ffmpeg
from facefusion.filesystem import filter_image_paths, is_directory
from facefusion.processors.core import get_processors_modules
from facefusion.types import Face, Fps, VisionFrame
from facefusion.uis.core import get_ui_component
from facefusion.vision import normalize_frame_color, read_static_images, unpack_resolution

# 全局变量
VIDEO_CAPTURE: Optional[cv2.VideoCapture] = None
WEBCAM_IMAGE: Optional[gradio.Image] = None
WEBCAM_START_BUTTON: Optional[gradio.Button] = None
WEBCAM_STOP_BUTTON: Optional[gradio.Button] = None


def render() -> None:
	"""
	渲染webcam组件的主视图。
	"""
	global WEBCAM_IMAGE, WEBCAM_START_BUTTON, WEBCAM_STOP_BUTTON
	WEBCAM_IMAGE = gradio.Image(label=wording.get('uis.webcam_image'), interactive=False)
	WEBCAM_START_BUTTON = gradio.Button(value=wording.get('uis.start_button'), variant='primary', size='sm')
	WEBCAM_STOP_BUTTON = gradio.Button(value=wording.get('uis.stop_button'), size='sm')


def listen() -> None:
	"""
	为webcam组件设置事件监听。
	"""
	# 通过 get_ui_component 获取所有需要的组件
	webcam_input_type_radio = get_ui_component('webcam_input_type_radio')
	webcam_device_id_dropdown = get_ui_component('webcam_device_id_dropdown')
	webcam_stream_url_textbox = get_ui_component('webcam_stream_url_textbox')
	webcam_resolution_dropdown = get_ui_component('webcam_resolution_dropdown')
	webcam_fps_slider = get_ui_component('webcam_fps_slider')
	source_image = get_ui_component('source_image')

	# 为输入类型单选框绑定事件
	if webcam_input_type_radio:
		webcam_input_type_radio.change(
			fn=update_visibility,
			inputs=[webcam_input_type_radio],
			outputs=[webcam_device_id_dropdown, webcam_stream_url_textbox]
		)

	# 为开始/停止按钮绑定事件
	start_event = WEBCAM_START_BUTTON.click(
		fn=start,
		inputs=[
			webcam_input_type_radio,
			webcam_device_id_dropdown,
			webcam_stream_url_textbox,
			webcam_resolution_dropdown,
			webcam_fps_slider
		],
		outputs=WEBCAM_IMAGE
	)
	WEBCAM_STOP_BUTTON.click(stop, cancels=start_event, outputs=WEBCAM_IMAGE)

	# 当源图片变化时，自动重启视频流
	if source_image:
		source_image.change(
			fn=start,
			inputs=[
				webcam_input_type_radio,
				webcam_device_id_dropdown,
				webcam_stream_url_textbox,
				webcam_resolution_dropdown,
				webcam_fps_slider
			],
			outputs=WEBCAM_IMAGE,
			cancels=start_event
		)

	# 【新增】当人脸替换模型变化时，自动重启视频流
	if face_swapper_model_dropdown:
		face_swapper_model_dropdown.change(
			fn=start,
			inputs=[
				webcam_input_type_radio,
				webcam_device_id_dropdown,
				webcam_stream_url_textbox,
				webcam_resolution_dropdown,
				webcam_fps_slider
			],
			outputs=WEBCAM_IMAGE,
			cancels=start_event
		)


def update_visibility(input_type: str) -> Tuple[dict, dict]:
	"""
	根据选择的输入类型，更新设备ID下拉框和URL输入框的可见性。
	"""
	if input_type == "USB摄像头":
		return gradio.update(visible=True), gradio.update(visible=False)
	else:
		return gradio.update(visible=False), gradio.update(visible=True)


# ---------------------------------------------------
# 以下是核心的视频处理逻辑，与之前保持一致
# ---------------------------------------------------

def get_video_capture(input_type: str, device_id: str, stream_url: str) -> Optional[cv2.VideoCapture]:
	global VIDEO_CAPTURE
	if VIDEO_CAPTURE is None:
		source = None
		if input_type == "USB摄像头":
			if device_id and device_id != 'none':
				try:
					source = int(device_id)
				except (ValueError, TypeError):
					return None
			else:
				return None
		elif input_type in ["UDP视频流", "HTTP视频流"]:
			source = stream_url if stream_url else None

		if source is not None:
			capture_api = cv2.CAP_DSHOW if is_windows() and isinstance(source, int) else cv2.CAP_ANY
			VIDEO_CAPTURE = cv2.VideoCapture(source, capture_api)
	return VIDEO_CAPTURE


def clear_video_capture() -> None:
	global VIDEO_CAPTURE
	if VIDEO_CAPTURE:
		VIDEO_CAPTURE.release()
	VIDEO_CAPTURE = None


def start(input_type: str, device_id: str, stream_url: str, resolution: str, fps: Fps) -> Generator[
	Optional[VisionFrame], None, None]:
	state_manager.set_item('face_selector_mode', 'one')
	source_paths = filter_image_paths(state_manager.get_item('source_paths'))
	if not source_paths:
		logger.error("请先选择一张源图片", __name__)
		return

	source_frames = read_static_images(source_paths)
	source_face = get_average_face(get_many_faces(source_frames))

	video_capture = get_video_capture(input_type, device_id, stream_url)
	if not (video_capture and video_capture.isOpened()):
		clear_video_capture()
		logger.error(f"无法打开视频源", __name__)
		return

	width, height = unpack_resolution(resolution)
	video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
	video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
	video_capture.set(cv2.CAP_PROP_FPS, fps)

	for capture_frame in multi_process_capture(source_face, video_capture, fps):
		if capture_frame is not None:
			yield normalize_frame_color(capture_frame)


def multi_process_capture(source_face: Face, video_capture: cv2.VideoCapture, fps: Fps) -> Generator[
	Optional[VisionFrame], None, None]:
	deque_capture_frames: Deque[VisionFrame] = deque()
	with tqdm(desc=wording.get('streaming'), unit='frame',
			  disable=state_manager.get_item('log_level') in ['warn', 'error']) as progress:
		with ThreadPoolExecutor(max_workers=state_manager.get_item('execution_thread_count')) as executor:
			futures = []
			while video_capture and video_capture.isOpened():
				ret, capture_frame = video_capture.read()
				if not ret:
					break

				future = executor.submit(process_stream_frame, source_face, capture_frame)
				futures.append(future)

				for future_done in [f for f in futures if f.done()]:
					processed_frame = future_done.result()
					deque_capture_frames.append(processed_frame)
					futures.remove(future_done)

				while deque_capture_frames:
					progress.update()
					yield deque_capture_frames.popleft()


def stop() -> gradio.Image:
	clear_video_capture()
	return gradio.Image(value=None)


def process_stream_frame(source_face: Face, target_vision_frame: VisionFrame) -> VisionFrame:
	source_audio_frame = create_empty_audio_frame()
	for processor_module in get_processors_modules(state_manager.get_item('processors')):
		logger.disable()
		if processor_module.pre_process('stream'):
			target_vision_frame = processor_module.process_frame({
				'source_face': source_face,
				'source_audio_frame': source_audio_frame,
				'target_vision_frame': target_vision_frame
			})
		logger.enable()
	return target_vision_frame


def get_available_webcam_ids(start_id: int, end_id: int) -> List[str]:
	available_ids = []
	for i in range(start_id, end_id):
		cap = cv2.VideoCapture(i)
		if cap.isOpened():
			available_ids.append(str(i))
			cap.release()
	return available_ids
