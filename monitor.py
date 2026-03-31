import time
import os
import sys

def get_cpu_times():
    """/proc/stat에서 CPU 시간을 읽어옵니다. (우분투/리눅스 전용)"""
    try:
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith('cpu '):
                parts = list(map(int, line.split()[1:]))
                # 리눅스 cpu stat: user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
                # idle 시간 = idle + iowait
                idleall = parts[3] + parts[4]
                # 총 시간 = 모든 항목의 합
                totalall = sum(parts)
                return totalall, idleall
    except Exception as e:
        return 0, 0
    return 0, 0

def get_memory_info():
    """/proc/meminfo에서 메모리 정보를 읽어옵니다. (단위: kB)"""
    meminfo = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = int(parts[1].split()[0])
                    meminfo[key] = val
    except Exception as e:
        pass
        
    total = meminfo.get('MemTotal', 0)
    available = meminfo.get('MemAvailable', 0)
    free = meminfo.get('MemFree', 0)
    buffers = meminfo.get('Buffers', 0)
    cached = meminfo.get('Cached', 0)
    
    # 리눅스에서 실사용 중인 메모리 계산
    if available > 0:
        used = total - available
    else:
        used = total - free - buffers - cached
        
    return total, used

def draw_bar(percent, width=40, color_code="\033[92m"):
    """진행률 바를 문자열로 생성합니다."""
    # 소수점 이하 버림으로 바 길이 계산
    filled = int((width * percent) // 100)
    empty = width - filled
    
    # 유니코드 블록 문자(█)를 사용하여 더 예쁜 바 생성
    bar = "█" * filled + "▒" * empty
    return f"{color_code}[{bar}]\033[0m"

def main():
    print("\033[93m시스템 정보를 불러오는 중...\033[0m")
    
    prev_total, prev_idle = get_cpu_times()
    
    # 커서 숨기기 (깨끗한 출력을 위해)
    sys.stdout.write("\033[?25l")
    
    try:
        while True:
            # 1초마다 갱신
            time.sleep(1)
            
            curr_total, curr_idle = get_cpu_times()
            
            total_diff = curr_total - prev_total
            idle_diff = curr_idle - prev_idle
            
            if total_diff == 0:
                cpu_percent = 0.0
            else:
                cpu_percent = 100.0 * (total_diff - idle_diff) / total_diff
                
            # 다음 주기를 위해 값 저장
            prev_total, prev_idle = curr_total, curr_idle
            
            # 메모리 정보 갱신
            mem_total, mem_used = get_memory_info()
            mem_percent = 100.0 * mem_used / mem_total if mem_total > 0 else 0.0
            
            # 화면 지우기 및 커서를 맨 위로 이동 (ANSI escape code)
            sys.stdout.write("\033[2J\033[H")
            
            # === 터미널 UI 그리기 ===
            print("\033[1;96m" + "━" * 60)
            print(" " * 15 + "🚀 Ubuntu System Monitor 🚀" + " " * 15)
            print("━" * 60 + "\033[0m\n")
            
            # 사용량에 따른 색상 변화 지정
            # CPU 색상 설정
            cpu_color = "\033[1;92m" # Green
            if cpu_percent > 85:
                cpu_color = "\033[1;91m" # Red
            elif cpu_percent > 60:
                cpu_color = "\033[1;93m" # Yellow
                
            # Memory 색상 설정
            mem_color = "\033[1;94m" # Blue
            if mem_percent > 85:
                mem_color = "\033[1;91m" # Red
            elif mem_percent > 70:
                mem_color = "\033[1;93m" # Yellow
                
            # CPU/RAM 상태 출력
            print(f" \033[1mCPU 사용량\033[0m:    {cpu_percent:5.1f}% {draw_bar(cpu_percent, 35, cpu_color)}")
            print(f" \033[1m메모리 사용량\033[0m: {mem_percent:5.1f}% {draw_bar(mem_percent, 35, mem_color)}")
            
            # kB 단위를 GB 단위로 변환해 메모리 상세 출력
            mem_used_gb = mem_used / 1024 / 1024
            mem_total_gb = mem_total / 1024 / 1024
            print(f"                  ({mem_used_gb:.2f} GB / {mem_total_gb:.2f} GB)\n")
            
            print("\033[1;90m 종료하려면 [Ctrl+C]를 누르세요...\033[0m")
            sys.stdout.flush()
            
    except KeyboardInterrupt:
        # 강제 종료시 터미널 정상화 (커서 다시 표시 및 화면 위치 정리)
        sys.stdout.write("\033[?25h")
        sys.stdout.write("\n\033[1;92m모니터링이 종료되었습니다.\033[0m\n")

if __name__ == "__main__":
    main()
