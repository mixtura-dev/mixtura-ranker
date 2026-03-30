import math
from openskill.models import ThurstoneMostellerFull

class RatingSystem:
    def __init__(
        self,
        R_min: float = 0.0,
        R_max: float = 5000.0,
        g: float = 0.5,
        mu_open: float = 2400.0,
        d: float = 6.0,
        sigma_init: float = 6.25,
    ):
        """
        Инициализация системы рейтингов по математической спецификации.
        
        Параметры (доступны пользователю):
            R_min, R_max — границы открытого рейтинга
            g — гравитация оценки игрока
            mu_open — математическое ожидание открытой системы
            d — крутизна гейт-функции (экспериментально фиксировано)
            sigma_init — начальная неопределённость (экспериментально 2.5, чтобы s_closed = 10)
        """
        self.R_min = float(R_min)
        self.R_max = float(R_max)
        self.Delta_open = self.R_max - self.R_min
        self.g = float(g)
        self.mu_open = float(mu_open)
        self.d = float(d)
        self.sigma_init = float(sigma_init)
        self.s_closed = 4.0 * self.sigma_init          # согласно 2.2
        self.Delta_translate = (self.R_min + self.R_max) / 2.0 - self.mu_open

        self.model = ThurstoneMostellerFull()

    def sigmoid(self, x: float) -> float:
        """Стандартная логистическая сигмоида σ_sig(x)"""
        return 1.0 / (1.0 + math.exp(-x))

    def ordinal(self, mu: float, sigma: float) -> float:
        """Ординал скрытого рейтинга o(μ, σ)"""
        return mu / (1.0 + self.g * sigma / self.sigma_init)

    def f(self, o: float) -> float:
        """Прямое отображение: скрытый ординал → открытый рейтинг (формула 2.3)"""
        return (
            self.R_min
            + self.Delta_open * self.sigmoid(o / self.s_closed)
            - self.Delta_translate
        )

    def f_inv(self, R: float) -> float:
        """Обратное отображение (logit) — формула 2.4"""
        numerator = R + self.Delta_translate - self.R_min
        denominator = self.R_max - (R + self.Delta_translate)
        # Защита от выхода за границы
        arg =  numerator / denominator
        return self.s_closed * math.log(arg)

    def gate(self, Delta: float) -> float:
        """Гейт-функция коррекции G(Δ) — формула 5.1"""
        abs_norm = abs(Delta) / self.Delta_open
        return self.sigmoid(2.0 * self.d * abs_norm - self.d)

    def create_player(self, name: str, R_expert: float) -> dict:
        """
        Создание нового игрока по экспертной оценке (раздел 4).
        Возвращает словарь-игрока для удобства тестирования.
        """
        R = max(self.R_min, min(self.R_max, float(R_expert)))
        mu_init = self.f_inv(R)
        sigma = self.sigma_init
        hidden = ThurstoneMostellerFull.create_rating([mu_init, sigma])

        return {
            "name": name,
            "hidden": hidden,      # объект openskill Rating (μ, σ)
            "R": R,                # открытый рейтинг
        }

    def compute_ordinal(self, player: dict) -> float:
        """Текущий ординал игрока"""
        return self.ordinal(player["hidden"].mu, player["hidden"].sigma)

    def compute_delta(self, player: dict) -> float:
        """Δ = f(o) - R (для эффективного рейтинга и коррекции)"""
        o = self.compute_ordinal(player)
        return self.f(o) - player["R"]

    def compute_R_eff(self, player: dict) -> float:
        """Эффективный рейтинг для матчмейкинга (раздел 6)"""
        Delta = self.compute_delta(player)
        G = self.gate(Delta)
        Delta_eff = G * Delta
        R_eff = max(self.R_min, min(self.R_max, player["R"] + Delta_eff))
        return R_eff

    def update_after_match(self, teams: list[list[dict]], ranks: list[float]):
        """
        Обновление после матча (раздел 7).
        
        teams  — список команд, каждая команда — список игроков (dict)
        ranks  — список рангов команд (меньше = лучше, обычно [0, 1] для двух команд)
        """
        # 1. Фиксируем состояние ДО матча
        pre_states = []
        for team in teams:
            team_pre = []
            for p in team:
                team_pre.append({
                    "player": p,
                    "o_pre": self.compute_ordinal(p),
                    "R_pre": p["R"],
                })
            pre_states.append(team_pre)

        # 2. Подготавливаем данные для OpenSkill
        rating_groups = [[p["hidden"] for p in team] for team in teams]

        # 3. Обновляем скрытый рейтинг через Thurstone–Mosteller Full
        updated_groups = self.model.rate(rating_groups, ranks=ranks)

        # 4. Присваиваем новые скрытые рейтинги обратно игрокам
        for team_idx, updated_team in enumerate(updated_groups):
            for p_idx, new_hidden in enumerate(updated_team):
                teams[team_idx][p_idx]["hidden"] = new_hidden

        # 5. Обновляем открытый рейтинг по формуле 7.3
        for team_idx, team_pre in enumerate(pre_states):
            for p_pre in team_pre:
                player = p_pre["player"]
                o_pre = p_pre["o_pre"]
                R_pre = p_pre["R_pre"]

                o_post = self.compute_ordinal(player)
                f_o_post = self.f(o_post)
                f_o_pre = self.f(o_pre)

                Delta_post = f_o_pre - R_pre
                Delta_match = f_o_post - f_o_pre

                if abs(Delta_match) < 1e-9:
                    sig_factor = 0.0
                else:
                    arg = (
                        2.0
                        * Delta_post
                        * math.copysign(1.0, Delta_match)
                        / self.Delta_open
                    )
                    sig_factor = self.sigmoid(arg)

                delta_R = 2 * Delta_match * sig_factor
                R_new = max(self.R_min, min(self.R_max, R_pre + delta_R))
                player["R"] = R_new

    def expert_correct(self, player: dict, new_R: float):
        """Экспертная коррекция открытого рейтинга (раздел 8)"""
        player["R"] = max(self.R_min, min(self.R_max, float(new_R)))


# ======================== ПРИМЕР ТЕСТИРОВАНИЯ ========================
if __name__ == "__main__":
    print("=== Тест рейтинговой системы ===\n")

    # Создаём систему (можно менять гиперпараметры)
    system = RatingSystem(
        R_min=0.0,
        R_max=5000.0,
        g=0.5,
        mu_open=2400.0,
        d=4.0,
        sigma_init=6.25,
    )

    # Создаём игроков по экспертным оценкам
    p1 = system.create_player("Игрок1", 2400.0)
    p2 = system.create_player("Игрок2", 2500.0)
    p3 = system.create_player("Игрок3", 2300.0)
    p4 = system.create_player("Игрок4", 2600.0)

    players = [p1, p2, p3, p4]
    original_diffs = []

    print("ИСХОДНЫЕ РЕЙТИНГИ:")
    for p in players:
        o = system.compute_ordinal(p)
        R_eff = system.compute_R_eff(p)
        original_diffs.append(p['R']-system.f(o))
        print(
            f"{p['name']:>8} | "
            f"R_open = {p['R']:6.1f} | "
            f"μ = {p['hidden'].mu:6.1f} | "
            f"σ = {p['hidden'].sigma:5.2f} | "
            f"o = {o:6.1f} | "
            f"f(o) = {system.f(o):6.1f} | "
            f"R_eff = {R_eff:6.1f}"
        )

    # Симулируем матч: команда А (Игрок1 + Игрок2) побеждает команду Б (Игрок3 + Игрок4)
    teams = [[p1, p2], [p3, p4]]
    ranks = [0.0, 1.0]                     # 0 — победа, 1 — поражение

    print("\nПроводим матч (команда А побеждает)...")
    system.update_after_match(teams, ranks)

    diffs_after = []
    print("РЕЙТИНГИ ПОСЛЕ МАТЧА:")
    for p in players:
        o = system.compute_ordinal(p)
        R_eff = system.compute_R_eff(p)
        diffs_after.append(p['R']-system.f(o))
        print(
            f"{p['name']:>8} | "
            f"R_open = {p['R']:6.1f} | "
            f"μ = {p['hidden'].mu:6.1f} | "
            f"σ = {p['hidden'].sigma:5.2f} | "
            f"o = {o:6.1f} | "
            f"f(o) = {system.f(o):6.1f} | "
            f"R_eff = {R_eff:6.1f}"
        )

    # Демонстрация экспертной коррекции
    print("\nЭкспертная коррекция Игрок1 → 2700")
    system.expert_correct(p1, 2700.0)
    print("\nЭкспертная коррекция Игрок2 → 1000")
    system.expert_correct(p2, 1000.0)

    print("ПОСЛЕ ЭКСПЕРТНОЙ КОРРЕКЦИИ:")
    for p in [p1,p2]:
        o = system.compute_ordinal(p)
        R_eff = system.compute_R_eff(p)
        print(
            f"{p['name']:>8} | "
            f"R_open = {p['R']:6.1f} | "
            f"μ = {p['hidden'].mu:6.1f} | "
            f"σ = {p['hidden'].sigma:5.2f} | "
            f"o = {o:6.1f} | "
            f"f(o) = {system.f(o):6.1f} | "
            f"R_eff = {R_eff:6.1f}"
        )

    print("Схождение рейтингов к скрытым параметрам (R - f(o)):")
    for i, (diff_orig, diff_after) in enumerate(zip(original_diffs, diffs_after)):
        print(f"Игрок {i+1}: {diff_orig:.1f} → {diff_after:.1f}: {'Сближение' if abs(diff_after) < abs(diff_orig) else 'Расхождение'}")
