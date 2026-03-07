# -*-coding: Utf-8 -*-
# @File : OSC-single decice.py
# author: Gion Hua
# Time：2025/8/31
import threading
import logging
import time
import keyboard
import queue
import sys
import argparse
import csv
from pythonosc import dispatcher, osc_server

class OSCServer:
    def __init__(self, data_buffer, exit_event, server_ip, server_port):
        self.data_buffer = data_buffer
        self.exit_event = exit_event
        self.server_ip = server_ip
        self.server_port = server_port

    def handle_all_signals(self, signal_path, *args):
        """同时获取信号路径和字段数据"""
        self.data_buffer.put((signal_path, args))

    def start(self):
        disp = dispatcher.Dispatcher()
        disp.map("*", self.handle_all_signals)  # 匹配所有路径
        server = osc_server.ThreadingOSCUDPServer(
            (self.server_ip, self.server_port),
            disp
        )
        logging.info(f"开始监听 {self.server_ip}:{self.server_port} 的所有OSC数据...")
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        while not self.exit_event.is_set():
            time.sleep(0.1)

        server.shutdown()
        server_thread.join()
        logging.info("OSC服务器已停止")

def listen_for_exit(exit_event, exit_key):
    while True:
        if keyboard.is_pressed(exit_key):
            logging.info(f"检测到退出键 '{exit_key}'，正在停止程序...")
            exit_event.set()
            break
        time.sleep(0.1)

def process_data(data_buffer, exit_event, csv_file):
    # 写入CSV文件头
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['时间戳', '数据名称', '数据'])

    while not exit_event.is_set():
        try:
            signal_path, data = data_buffer.get(timeout=0.0001)
            signal_type = signal_path.split("/")[-1]
            # 获取当前时间戳
            timestamp = time.time()
            # 打印到控制台
            print(f"信号类型: {signal_type} | 数据字段: {list(data)}")
            # 写入CSV文件
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, signal_type, list(data)])
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"处理数据出错: {e}")

    logging.info(f"数据已保存到 {csv_file}")

def main():
    parser = argparse.ArgumentParser(description='接收OSC数据并输出信号类型和字段，同时保存到CSV文件')
    parser.add_argument('--server-ip', default='127.0.0.1', help='监听的IP地址 (默认: 127.0.0.1)')
    parser.add_argument('--server-port', type=int, default=7000, help='监听的端口 (默认: 7000)')
    parser.add_argument('--exit-key', default='q', help='退出按键 (默认: q)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    parser.add_argument('--csv-file', default='osc_data.csv', help='CSV文件保存路径 (默认: osc_data.csv)')
    args = parser.parse_args()

    # 日志设置
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    data_buffer = queue.Queue()
    exit_event = threading.Event()

    try:
        server = OSCServer(data_buffer, exit_event, args.server_ip, args.server_port)
        exit_thread = threading.Thread(target=listen_for_exit, args=(exit_event, args.exit_key))
        server_thread = threading.Thread(target=server.start)
        # 传递CSV文件路径给处理线程
        process_thread = threading.Thread(target=process_data, args=(data_buffer, exit_event, args.csv_file))

        for t in [exit_thread, server_thread, process_thread]:
            t.daemon = True
            t.start()

        server_thread.join()
        process_thread.join()
    except Exception as e:
        logging.error(f"程序出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
