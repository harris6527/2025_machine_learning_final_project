# ---------------------------------------------------------------------------
# Prototype note:
# 本原型目前使用 Regex 進行語法層面 (Syntactic) 的偵測；在 2045 年的願景中，
# 這部分將被 Lean/Coq 自動定理證明器的語意驗證 (Semantic Verification) 取代。
# ---------------------------------------------------------------------------
"""
Diagnostic Tutor Prototype
--------------------------
This script simulates a minimal AI tutor brain that inspects math expressions,
emits pedagogical hints instead of direct answers, and records interaction
state to modulate feedback intensity. It focuses on two common misconceptions:
1) Missing coefficients when differentiating powers (e.g., d/dx(x^2) = x).
2) The "Freshman's Dream" expansion mistake (e.g., (a+b)^2 = a^2 + b^2).
The loop at the bottom lets users enter expressions repeatedly for testing.
"""

from __future__ import annotations

import re
from typing import Callable, Optional, Sequence, Tuple

try:
    # Sympy is optional; used for light algebraic checks to ensure
    # mathematical equivalence (基本等價性檢查).
    import sympy as sp

    SYMPY_AVAILABLE = True
except Exception:
    SYMPY_AVAILABLE = False


class InteractionLog:
    """
    Minimal cognitive state simulation:
    tracks consecutive occurrences of the same misconception to escalate hints.
    """

    def __init__(self) -> None:
        self.last_rule: Optional[str] = None
        self.streak: int = 0

    def record(self, rule_id: str) -> int:
        """
        Update streak for a detected rule and return the current streak length.
        """
        if rule_id == self.last_rule:
            self.streak += 1
        else:
            self.last_rule = rule_id
            self.streak = 1
        return self.streak

    def reset(self) -> None:
        """Reset streak when no misconception is detected."""
        self.last_rule = None
        self.streak = 0


def normalize(expr: str) -> str:
    """Lowercase and strip spaces for pattern checks."""
    return expr.replace(" ", "").lower()


def hint_power_rule(expr: str) -> Optional[Tuple[str, str, str]]:
    """
    Detect missing coefficient in derivatives like d/dx(x^n) = x^(n-1).
    Returns (rule_id, base_hint, escalated_hint) if detected.
    """
    compact = normalize(expr)
    # Directly match the provided scenario: d/dx(x^2) = x
    if re.fullmatch(r"d/dx\(?x\^?2\)?=x", compact):
        return (
            "power_rule_missing_coefficient",
            "你似乎忘了冪次前的係數，回想一下 d/dx(x^n) 的前導常數應該是多少？",
            "你持續遺漏冪次求導的前導係數，請完整寫出 d/dx(x^n)=n·x^(n-1) 並檢查每一步。",
        )

    # Generalized pattern: d/dx(x^k) = x^(k-1) without leading coefficient k
    match = re.fullmatch(r"d/dx\(?x\^?(\d+)\)?=x\^?(\d+)", compact)
    if match:
        n_left = int(match.group(1))
        n_right = int(match.group(2))
        if n_left - 1 == n_right and n_left != 1:
            return (
                "power_rule_missing_coefficient",
                "冪次下降時需要把原本的指數乘到前面，確認一下前導係數是否遺漏。",
                "連續遺漏前導係數：請寫出一般公式並逐步帶入 n，確認計算與符號都未省略。",
            )
    return None


def hint_freshman_dream(expr: str) -> Optional[Tuple[str, str, str]]:
    """
    Detect the Freshman's Dream error: (a+b)^2 = a^2 + b^2 (missing 2ab term).
    Returns (rule_id, base_hint, escalated_hint) if detected.
    """
    compact = normalize(expr)
    # Quick direct match for the classic form with a and b.
    if re.fullmatch(r"\(a\+b\)\^2=a\^2\+b\^2", compact):
        return (
            "freshman_dream",
            "請回想二項式展開公式：(a+b)^2 應該包含哪個混合項？",
            "你連續遺漏了二項式的交叉項 2ab，請完整展開並標示每一項係數後再合併。",
        )

    # More general regex: (u+v)^2 = u^2 + v^2
    general = re.fullmatch(
        r"\(([a-z]+)\+([a-z]+)\)\^2=([a-z]+)\^2\+([a-z]+)\^2", compact
    )
    if general:
        left_a, left_b, right_a, right_b = general.groups()
        # Ensure variables align (order-insensitive check).
        same_vars = sorted([left_a, left_b]) == sorted([right_a, right_b])
        if same_vars:
            return (
                "freshman_dream",
                "展開平方時中間的 2ab 被拿掉了，再檢查一次完整的二項式定理。",
                "持續出現 Freshman's Dream：請寫出 (u+v)^2 = u^2 + 2uv + v^2 並檢驗各項次。",
            )

    # Sympy-based fallback for variants like (x+y)^2 = x^2 + y^2
    if SYMPY_AVAILABLE and "=" in expr:
        left_raw, right_raw = expr.split("=", 1)
        try:
            left = sp.expand(sp.sympify(left_raw))
            right = sp.expand(sp.sympify(right_raw))
            if left != right:
                diff = sp.expand(left - right)
                symbols = list(diff.free_symbols)
                if len(symbols) >= 2 and diff.is_polynomial():
                    terms = diff.as_ordered_terms()
                    for term in terms:
                        coeff = term.as_coeff_mul()[0]
                        vars_in_term = term.as_poly().gens if term.is_polynomial() else ()
                        if coeff == 2 and len(vars_in_term) >= 2:
                            return (
                                "freshman_dream",
                                "好像少了混合項 2ab，試著完整展開後檢查每一項。",
                                "多次缺少混合項：請逐步展開並明確寫出 2·(第一項)·(第二項) 的來源。",
                            )
        except Exception:
            pass
    return None


# 教學圖譜節點（規則引擎的入口）
PEDAGOGICAL_GRAPH_NODES: Sequence[
    Callable[[str], Optional[Tuple[str, str, str]]]
] = (hint_power_rule, hint_freshman_dream)


def analyze_expression(expr: str, log: InteractionLog) -> str:
    """
    Analyze the given math expression string and return a pedagogical hint.
    If no known misconception is detected, return a neutral message.
    """
    for detector in PEDAGOGICAL_GRAPH_NODES:
        result = detector(expr)
        if result:
            rule_id, base_hint, escalated_hint = result
            streak = log.record(rule_id)
            return escalated_hint if streak >= 2 else base_hint

    # Reset streak if no misconception matched.
    log.reset()

    # If sympy is available, lightly sanity-check equality for mathematical equivalence.
    if SYMPY_AVAILABLE and "=" in expr:
        left_raw, right_raw = expr.split("=", 1)
        try:
            left = sp.simplify(left_raw)
            right = sp.simplify(right_raw)
            if not sp.Eq(left, right):
                return "等式兩側似乎不相等，嘗試重新推導並檢查是否有省略或符號錯置。"
        except Exception:
            # Parsing failed; fall through to neutral feedback.
            pass

    return "目前未偵測到特定迷思，請繼續嘗試或提供更多步驟。"


def main() -> None:
    """
    Simple REPL loop to query the diagnostic tutor.
    Type 'exit' or press Enter on an empty line to quit.
    """
    log = InteractionLog()
    print("=== Diagnostic Tutor Prototype ===")
    print("輸入一條數學算式讓導師診斷，輸入 'exit' 以離開。")
    while True:
        user_input = input("\n算式> ").strip()
        if user_input == "" or user_input.lower() == "exit":
            print("結束對話，再見。")
            break
        hint = analyze_expression(user_input, log)
        print(f"導師提示：{hint}")


if __name__ == "__main__":
    main()
