import os
from typing import List, Optional

import gradio

from facefusion import wording, logger, state_manager
from facefusion.filesystem import is_image, resolve_file_pattern
from facefusion.uis.core import register_ui_component

# 全局变量，用于存储DFM模型文件和其对应图标的路径
DFM_MODEL_PATHS: List[str] = []
DFM_ICON_PATHS: List[str] = []

# 新的UI组件，使用Gallery来展示模型图标
DFM_MODEL_GALLERY: Optional[gradio.Gallery] = None


def render() -> None:
	"""
	渲染DFM模型选择画廊。
	此函数在UI加载时执行，负责扫描模型和图标目录并进行展示。
	"""
	global DFM_MODEL_GALLERY, DFM_MODEL_PATHS, DFM_ICON_PATHS

	# --- 在这里指定您的DFM模型和图标目录 ---
	# 假设模型和图标存放在以下路径
	dfm_models_directory = '/home/cam1/tools/facefusion/.assets/models/custom'  # DFM模型文件 (.onnx, .pth, etc.) 存放目录
	dfm_icons_directory = '/home/cam1/tools/facefusion/.assets/models/custom_icons'  # DFM模型对应的图标 (.png, .jpg) 存放目录

	# 确保目录存在
	if not os.path.isdir(dfm_models_directory):
		os.makedirs(dfm_models_directory, exist_ok=True)
		logger.warn(f"DFM模型目录 '{dfm_models_directory}' 不存在，已自动创建。请将模型文件放入该目录。", __name__)
	if not os.path.isdir(dfm_icons_directory):
		os.makedirs(dfm_icons_directory, exist_ok=True)
		logger.warn(f"DFM图标目录 '{dfm_icons_directory}' 不存在，已自动创建。请将模型图标放入该目录。", __name__)

	# 扫描模型目录并获取所有模型文件的路径
	# 这里我们假设模型文件可以是任何类型，所以不过滤扩展名
	all_model_files = sorted(os.listdir(dfm_models_directory))

	# 清空旧的路径列表
	DFM_MODEL_PATHS.clear()
	DFM_ICON_PATHS.clear()

	# 匹配模型和图标
	for model_filename in all_model_files:
		model_name, _ = os.path.splitext(model_filename)
		# 假设图标文件名与模型名相同，但扩展名为.png
		icon_path = os.path.join(dfm_icons_directory, f"{model_name}.png")

		# 只有当对应的图标存在时，我们才将其添加到列表中
		if os.path.isfile(icon_path):
			DFM_MODEL_PATHS.append(os.path.join(dfm_models_directory, model_filename))
			DFM_ICON_PATHS.append(icon_path)
		else:
			logger.warn(f"未找到模型 '{model_filename}' 对应的图标 '{model_name}.png'，该模型将不会显示。", __name__)

	# 如果没有可显示的图标，记录一条警告
	if not DFM_ICON_PATHS:
		logger.warn(f"在目录 '{dfm_icons_directory}' 中没有找到任何与模型匹配的图标文件。", __name__)

	# 创建Gallery组件来展示图标
	DFM_MODEL_GALLERY = gradio.Gallery(
		label=wording.get('uis.dfm_model_gallery_label'),
		value=DFM_ICON_PATHS,  # Gallery显示的是图标
		columns=5,  # 每行显示5个图标
		height='auto',
		preview=True
	)

	# 注册组件
	register_ui_component('dfm_model_gallery', DFM_MODEL_GALLERY)


def listen() -> None:
	"""
	为模型画廊组件设置事件监听。
	当用户在画廊中选择一个图标时，会触发 select_dfm_model 函数。
	"""
	DFM_MODEL_GALLERY.select(select_dfm_model, outputs=[])


def select_dfm_model(evt: gradio.SelectData) -> None:
	"""
	当用户在画廊中点击并选择一个模型图标时，此函数被调用。

	Args:
		evt (gradio.SelectData): Gradio传递的事件数据，包含了被选中项的索引 (evt.index)。
	"""
	selected_index = evt.index

	# 确保索引在有效范围内
	if DFM_MODEL_PATHS and 0 <= selected_index < len(DFM_MODEL_PATHS):
		# 根据索引从模型路径列表中获取对应的模型文件路径
		selected_model_path = DFM_MODEL_PATHS[selected_index]

		# 将选中的模型路径设置到facefusion的核心状态管理器中
		# 这里我们使用 'dfm_model_path' 作为键名，您可以根据实际情况修改
		state_manager.set_item('dfm_model_path', selected_model_path)

		# 在后台打印日志，确认模型选择成功
		logger.info(f"{wording.get('uis.dfm_model_selected')}: {os.path.basename(selected_model_path)}", __name__)

