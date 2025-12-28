import socket

# 测试后端服务的端口8000是否开放
def test_backend_port():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex(('localhost', 8000))
        if result == 0:
            print("✅ 后端服务端口8000已开放")
        else:
            print("❌ 后端服务端口8000未开放")
        s.close()
        return result == 0
    except Exception as e:
        print(f"❌ 测试端口时出错: {e}")
        return False

if __name__ == "__main__":
    test_backend_port()