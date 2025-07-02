import gradio as gr


def greet(name):
	# 一个简单的后台函数
	if not name:
		return "Please enter a name!"
	return "Hello, " + name + "!"


# 创建一个最基础的UI界面
with gr.Blocks() as demo:
	gr.Markdown("这是一个用于诊断Gradio环境的最小测试程序。")

	with gr.Row():
		name_textbox = gr.Textbox(label="输入您的名字")
		greet_button = gr.Button("问候")

	output_textbox = gr.Textbox(label="输出结果")

	# 为按钮绑定点击事件
	greet_button.click(
		fn=greet,
		inputs=name_textbox,
		outputs=output_textbox
	)

# 使用和facefusion相同的参数启动
print("正在启动Gradio诊断程序...")
demo.launch(server_name="0.0.0.0", server_port=7860)

