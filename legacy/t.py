# 피보나치 수열 계산 프로그램

def fibonacci_iterative(n):
    """반복문을 사용한 피보나치 수열 계산"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_recursive(n, memo={}):
    """메모이제이션을 사용한 재귀 피보나치 수열 계산"""
    if n in memo:
        return memo[n]
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    memo[n] = fibonacci_recursive(n - 1, memo) + fibonacci_recursive(n - 2, memo)
    return memo[n]


def fibonacci_generator(max_n):
    """피보나치 수열 제너레이터"""
    a, b = 0, 1
    for _ in range(max_n):
        yield a
        a, b = b, a + b


def get_fibonacci_sequence(n):
    """처음부터 n번째까지의 피보나치 수열 리스트 반환"""
    return list(fibonacci_generator(n + 1))


# 메인 실행 부분
if __name__ == "__main__":
    print("=== 피보나치 수열 계산기 ===\n")
    
    # 예시: 0부터 10까지의 피보나치 수열
    n = 10
    print(f"처음 {n+1}개의 피보나치 수열:")
    sequence = get_fibonacci_sequence(n)
    print(f"F(0) ~ F({n}): {sequence}\n")
    
    # 특정 값 계산
    test_numbers = [5, 10, 15, 20]
    print("특정 항의 피보나치 수:")
    for num in test_numbers:
        result = fibonacci_iterative(num)
        print(f"F({num}) = {result}")
    
    # 사용자 입력 받기
    print("\n" + "=" * 30)
    try:
        user_input = int(input("계산할 피보나치 수열 항의 번호를 입력하세요 (0~30): "))
        if 0 <= user_input <= 30:
            result = fibonacci_iterative(user_input)
            print(f"F({user_input}) = {result}")
        else:
            print("0에서 30 사이의 숫자를 입력해주세요.")
    except ValueError:
        print("올바른 숫자를 입력해주세요.")
