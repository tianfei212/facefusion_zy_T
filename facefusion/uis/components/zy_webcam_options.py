from typing import Optional, Tuple
import gradio

from facefusion import wording
from facefusion.common_helper import get_first
# 确保从正确的模块导入函数。如果 webcam.py 中有该函数，则导入正确
from facefusion.uis.components.zy_webcam import get_available_webcam_ids
from facefusion.uis.core import get_ui_component, register_ui_component

# 声明所有UI组件
WEBCAM_INPUT_TYPE_RADIO: Optional[gradio.Radio] = None
WEBCAM_DEVICE_ID_DROPDOWN: Optional[gradio.Dropdown] = None
WEBCAM_STREAM_URL_TEXTBOX: Optional[gradio.Textbox] = None
WEBCAM_RESOLUTION_DROPDOWN: Optional[gradio.Dropdown] = None
WEBCAM_FPS_SLIDER: Optional[gradio.Slider] = None


def render() -> None:
	"""
	渲染摄像头及视频流的全部设置选项。
	"""
	global WEBCAM_INPUT_TYPE_RADIO, WEBCAM_DEVICE_ID_DROPDOWN, WEBCAM_STREAM_URL_TEXTBOX, WEBCAM_RESOLUTION_DROPDOWN, WEBCAM_FPS_SLIDER

	# 创建输入源类型选择器
	WEBCAM_INPUT_TYPE_RADIO = gradio.Radio(
		label=wording.get('uis.webcam_input_type_radio'),
		choices=["USB摄像头", "UDP视频流", "HTTP视频流"],
		value="USB摄像头"
	)

	# 扫描可用的USB摄像头
	available_webcam_ids = get_available_webcam_ids(0, 10) or ['none']
	WEBCAM_DEVICE_ID_DROPDOWN = gradio.Dropdown(
		label=wording.get('uis.webcam_device_id_dropdown'),
		choices=available_webcam_ids,
		value=get_first(available_webcam_ids),
		visible=True  # 默认显示
	)

	# 创建视频流URL输入框
	WEBCAM_STREAM_URL_TEXTBOX = gradio.Textbox(
		label=wording.get('uis.webcam_stream_url_textbox'),
		placeholder="例如: udp://127.0.0.1:1234 或 http://192.168.1.10:8080/video",
		visible=False,  # 默认隐藏
		max_lines=1
	)

	# 分辨率和FPS设置
	WEBCAM_RESOLUTION_DROPDOWN = gradio.Dropdown(
		label=wording.get('uis.webcam_resolution_dropdown'),
		choices=['640x480', '1280x720', '1920x1080'],
		value='1280x720'
	)
	WEBCAM_FPS_SLIDER = gradio.Slider(
		label=wording.get('uis.webcam_fps_slider'),
		value=30,
		step=1,
		minimum=1,
		maximum=60
	)

	# 注册所有组件
	register_ui_component('webcam_input_type_radio', WEBCAM_INPUT_TYPE_RADIO)
	register_ui_component('webcam_device_id_dropdown', WEBCAM_DEVICE_ID_DROPDOWN)
	register_ui_component('webcam_stream_url_textbox', WEBCAM_STREAM_URL_TEXTBOX)
	register_ui_component('webcam_resolution_dropdown', WEBCAM_RESOLUTION_DROPDOWN)
	register_ui_component('webcam_fps_slider', WEBCAM_FPS_SLIDER)

