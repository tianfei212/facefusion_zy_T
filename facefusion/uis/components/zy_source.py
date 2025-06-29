import os
from typing import List, Optional

import gradio
from PIL import Image

from facefusion import wording, logger, state_manager
from facefusion.filesystem import is_image, resolve_file_pattern
from facefusion.uis.core import register_ui_component

# 全局变量，用于存储从指定目录加载的图片路径
# 这样就不需要在每次点击时都重新扫描硬盘
IMAGE_PATHS: List[str] = []

# 新的UI组件，使用Gallery来展示图片列表
SOURCE_GALLERY: Optional[gradio.Gallery] = None


def render() -> None:
	"""
	渲染源图片画廊。
	此函数在UI加载时执行，负责扫描指定目录并显示所有图片。
	"""
	global SOURCE_GALLERY, IMAGE_PATHS

	# --- 在这里指定您的高清图片目录 ---
	# 已更新为您提供的路径
	image_directory = '/home/cam1/tools/hig_images'  # 您可以修改为任何有效路径

	# 确保目录存在，如果不存在则创建一个
	if not os.path.isdir(image_directory):
		os.makedirs(image_directory, exist_ok=True)
		logger.warn(f"指定的图片目录 '{image_directory}' 不存在，已自动创建。请将图片放入该目录。", __name__)

	# 扫描目录下的所有图片并更新全局路径列表
	IMAGE_PATHS = sorted([path for path in resolve_file_pattern(os.path.join(image_directory, '*')) if is_image(path)])

	# 如果目录为空，记录一条警告
	if not IMAGE_PATHS:
		logger.warn(f"在目录 '{image_directory}' 中没有找到任何图片文件。", __name__)

	# 创建Gallery组件来展示图片
	# value=IMAGE_PATHS 会让Gradio自动加载并显示这些路径下的图片
	SOURCE_GALLERY = gradio.Gallery(
		label=wording.get('uis.source_gallery_label'),
		value=IMAGE_PATHS,
		columns=4,  # 每行显示4张图片
		height='auto',
		preview=True  # 允许点击放大预览
	)

	# 注册组件，以便其他模块可以访问
	register_ui_component('source_gallery', SOURCE_GALLERY)


def listen() -> None:
	"""
	为画廊组件设置事件监听。
	当用户在画廊中选择一张图片时，会触发 select_source 函数。
	"""
	SOURCE_GALLERY.select(select_source, outputs=[])


def select_source(evt: gradio.SelectData) -> None:
	"""
	当用户在画廊中点击并选择一张图片时，此函数被调用。

	Args:
		evt (gradio.SelectData): Gradio传递的事件数据，包含了被选中项的索引 (evt.index)。
	"""
	# evt.index 是被点击图片在列表中的索引
	selected_index = evt.index

	# 确保索引有效
	if IMAGE_PATHS and 0 <= selected_index < len(IMAGE_PATHS):
		# 根据索引从全局路径列表中获取完整路径
		selected_path = IMAGE_PATHS[selected_index]

		# 将选中的图片路径设置到facefusion的核心状态管理器中
		# 其他模块会从这里读取当前的源文件路径
		state_manager.set_item('source_paths', [selected_path])

		# 在后台打印日志，确认选择成功
		logger.info(f"{wording.get('uis.source_image_selected')}: {os.path.basename(selected_path)}", __name__)

