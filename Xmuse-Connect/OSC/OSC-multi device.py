# -*-coding: Utf-8 -*-
# @File : OSC-multi device.py
# author: Gion Hua
# Time：2025/9/8
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
        """同时获取信号路径、字段数据和端口信息"""
        # 新增端口信息到队列，方便区分设备来源
        self.data_buffer.put((signal_path, args, self.server_port))

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
        logging.info(f"{self.server_ip}:{self.server_port} OSC服务器已停止")

def listen_for_exit(exit_event, exit_key):
    while True:
        if keyboard.is_pressed(exit_key):
            logging.info(f"检测到退出键 '{exit_key}'，正在停止程序...")
            exit_event.set()
            break
        time.sleep(0.1)

def process_data(data_buffer, exit_event, csv_file):
    # 写入CSV文件头（新增端口列）
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['时间戳', '端口', '数据名称', '数据'])

    while not exit_event.is_set():
        try:
            # 从缓冲区获取数据（包含端口信息）
            signal_path, data, port = data_buffer.get(timeout=0.0001)
            signal_type = signal_path.split("/")[-1]
            timestamp = time.time()

            # 打印到控制台（显示端口信息）
            print(f"端口: {port} | 信号类型: {signal_type} | 数据字段: {list(data)}")

            # 写入CSV文件
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, port, signal_type, list(data)])

        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"处理数据出错: {e}")

    logging.info(f"端口数据已保存到 {csv_file}")

def main():
    parser = argparse.ArgumentParser(description='接收多个端口的OSC数据并分别保存到CSV文件')
    # 第一个设备配置
    parser.add_argument('--server-ip1', default='127.0.0.1', help='第一个监听的IP地址 (默认: 127.0.0.1)')
    parser.add_argument('--server-port1', type=int, default=7000, help='第一个监听的端口 (默认: 7000)')
    parser.add_argument('--csv-file1', default='osc_data1.csv', help='第一个CSV文件保存路径 (默认: osc_data1.csv)')

    # 第二个设备配置
    parser.add_argument('--server-ip2', default='127.0.0.1', help='第二个监听的IP地址 (默认: 127.0.0.1)')
    parser.add_argument('--server-port2', type=int, default=8001, help='第二个监听的端口 (默认: 8001)')
    parser.add_argument('--csv-file2', default='osc_data2.csv', help='第二个CSV文件保存路径 (默认: osc_data2.csv)')

    # 公共配置
    parser.add_argument('--exit-key', default='q', help='退出按键 (默认: q)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    args = parser.parse_args()

    # 日志设置
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    # 为两个设备创建独立的数据缓冲区
    data_buffer1 = queue.Queue()
    data_buffer2 = queue.Queue()
    exit_event = threading.Event()

    try:
        # 创建两个OSC服务器实例
        server1 = OSCServer(data_buffer1, exit_event, args.server_ip1, args.server_port1)
        server2 = OSCServer(data_buffer2, exit_event, args.server_ip2, args.server_port2)

        # 创建退出监听线程
        exit_thread = threading.Thread(target=listen_for_exit, args=(exit_event, args.exit_key))

        # 创建服务器线程
        server_thread1 = threading.Thread(target=server1.start)
        server_thread2 = threading.Thread(target=server2.start)

        # 创建数据处理线程（分别对应两个缓冲区和CSV文件）
        process_thread1 = threading.Thread(target=process_data, args=(data_buffer1, exit_event, args.csv_file1))
        process_thread2 = threading.Thread(target=process_data, args=(data_buffer2, exit_event, args.csv_file2))

        # 启动所有线程
        for t in [exit_thread, server_thread1, server_thread2, process_thread1, process_thread2]:
            t.daemon = True
            t.start()

        # 等待线程结束
        server_thread1.join()
        server_thread2.join()
        process_thread1.join()
        process_thread2.join()
        exit_thread.join()

    except Exception as e:
        logging.error(f"程序出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()