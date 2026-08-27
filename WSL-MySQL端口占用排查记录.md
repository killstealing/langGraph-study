# WSL2 + MySQL 连接故障排查记录

> 记录时间：2026-08-27
> 环境：Windows 11 + WSL2 + Ubuntu 24.04 + MySQL 8.0.46

---

## 一、问题现象

在 WSL Ubuntu 中执行 `mysql`，报错：

```
ERROR 2002 (HY000): Can't connect to local MySQL server through socket '/var/run/mysqld/mysqld.sock' (2)
```

错误码 `(2)` 表示「文件不存在」，即 `/var/run/mysqld/mysqld.sock` 这个 socket 文件不存在——本质是 **MySQL 服务没有正常运行**。

---

## 二、排查过程

### 1. 发现是崩溃重启死循环

```bash
systemctl status mysql
```

输出显示：

```
Active: activating (start) ...
mysql.service: Scheduled restart job, restart counter is at 1504.
```

MySQL 已经**自动重启了 1500+ 次**，陷入死循环。查看错误日志：

```bash
tail -f /var/log/mysql/error.log
```

每次都报同一个错误：

```
[ERROR] Can't start server: Bind on TCP/IP port: Address already in use
[ERROR] Do you already have another mysqld server running on port: 3306 ?
[ERROR] Aborting
```

**结论：3306 端口被占用，MySQL 无法绑定，systemd 反复拉起 → 反复失败。**

### 2. 追查端口占用者（关键难点）

依次用以下工具排查，**全部查不到占用者**：

```bash
ss -tlnp | grep 3306      # 无结果
ss -tanp | grep 3306      # 无结果（连 TIME_WAIT 都没有）
fuser -v 3306/tcp         # 无进程占用
lsof -i :3306             # 无结果
netstat -ano | grep 3306  # Windows 侧也无结果
Get-NetTCPConnection -LocalPort 3306  # PowerShell 也无结果
```

但直接测试绑定端口，却**确实失败**：

```bash
python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',3306))"
# OSError: [Errno 98] Address already in use
```

四种地址（`0.0.0.0`、`127.0.0.1`、`::`、`::1`）绑定 3306 全部失败，但 `ss` 看不到任何 socket。

这就是典型的 **「幽灵端口」**：端口被占用了，但常规工具查不到。

### 3. 定位触发点

对比时间线：

| 时间 | 事件 |
|---|---|
| 16:09 | 手动执行 `sudo nohup dockerd` 启动 Docker 守护进程 |
| 16:11 | MySQL 首次报 3306 绑定失败，开始死循环 |

**两者高度吻合**，判定是 Docker 网络层（手动启动的 dockerd / Docker 相关）造成了端口占用。

### 4. 弯路：改端口无效

尝试把 MySQL 端口从 3306 改为 3307，但仍连不上。原因有二：

1. MySQL 服务此前为停循环已被 `disable`，改端口后**根本没启动**；
2. 3307 同样落在 Hyper-V 保留端口区间附近。

---

## 三、根本原因

- **直接原因**：3306 端口被 Docker 网络层（手动 `dockerd`）以「幽灵占用」方式占住，MySQL 无法绑定，陷入崩溃重启死循环。
- **深层原因**：WSL2 共享内核/网络栈 + 手动启动 Docker 守护进程，产生了一个 `ss`/`netstat` 都看不到的端口占用。
- **重启 WSL 后**（`wsl --shutdown`），幽灵端口释放，3306 恢复空闲。

---

## 四、最终解决方案

### 1. 停掉死循环

```bash
systemctl stop mysql
systemctl disable mysql   # 临时禁用，防止继续空耗资源
```

### 2. 重启 WSL 网络栈（清除幽灵端口）

在 **Windows 命令行** 执行：

```powershell
wsl --shutdown
```

然后重新打开 Ubuntu 终端。

### 3. 端口改回 3306

编辑 `/etc/mysql/mysql.conf.d/mysqld.cnf`，确保：

```ini
[mysqld]
port = 3306
bind-address = 127.0.0.1
mysqlx-bind-address = 127.0.0.1
```

> 应用 `.env` 中连接串使用 `localhost:3306`，改回 3306 可避免改动应用配置。

### 4. 启动并恢复自启

```bash
systemctl start mysql
systemctl enable mysql
```

---

## 五、验证结果

```bash
# socket 连接（root）
mysql -e 'SELECT VERSION(), @@port;'
# → 8.0.46-0ubuntu0.24.04.3 | 3306 ✓

# TCP 连接（应用账号）
mysql -h 127.0.0.1 -P 3306 -u deepseek -pdeepseek langgraph -e 'SELECT DATABASE();'
# → langgraph ✓

# 端口存活
mysqladmin -h 127.0.0.1 -P 3306 -u deepseek -pdeepseek ping
# → mysqld is alive ✓
```

---

## 六、预防措施

1. **优先用系统服务方式运行 Docker**，而非 `sudo nohup dockerd` 手动启动：
   ```bash
   systemctl start docker
   # 或直接使用 Docker Desktop
   ```

2. **再遇到「端口被占但查不到」时**，先重启 WSL 网络栈：
   ```powershell
   wsl --shutdown
   ```

3. **WSL2 小知识**：默认发行版可能不是 Ubuntu（本机默认是 `docker-desktop`），执行命令需指定发行版：
   ```powershell
   wsl -d Ubuntu
   ```

---

## 七、常用排查命令速查

| 目的 | 命令 |
|---|---|
| 查看 MySQL 服务状态 | `systemctl status mysql` |
| 查看错误日志 | `tail -n 50 /var/log/mysql/error.log` |
| 查看端口占用（Linux） | `ss -tlnp \| grep 3306` |
| 查看端口占用（进程） | `fuser -v 3306/tcp` |
| 查看端口占用（Windows） | `netstat -ano \| findstr 3306` |
| 测试端口能否绑定 | `python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',3306))"` |
| 查看 mysqld 实际读取的配置 | `mysqld --print-defaults` |
| 重启 WSL | `wsl --shutdown`（Windows 侧执行） |
| 查看 Hyper-V 保留端口 | `netsh interface ipv4 show excludedportrange protocol=tcp` |
