# ALF-ROS — Oprogramowanie Komunikacyjne ROS2 dla Unitree G1 EDU

> **Język opisów:** Polski  
> **Język kodu:** Angielski

Kompletne oprogramowanie komunikacyjne **ROS2** z graficznym interfejsem użytkownika (GUI)
dla humanoidalnego robota **Unitree G1 EDU**. System działa zarówno na laptopie, jak i
bezpośrednio na robocie.

---

## 📋 Spis treści

1. [Opis projektu](#opis-projektu)
2. [Architektura systemu](#architektura-systemu)
3. [Wymagania systemowe](#wymagania-systemowe)
4. [Instalacja na laptopie](#instalacja-na-laptopie)
5. [Instalacja na Unitree G1 EDU](#instalacja-na-unitree-g1-edu)
6. [Użycie — uruchamianie GUI](#użycie--uruchamianie-gui)
7. [Użycie — RViz2](#użycie--rviz2)
8. [Użycie — monitor CLI](#użycie--monitor-cli)
9. [Topiki, węzły, akcje, serwisy](#topiki-węzły-akcje-serwisy)
10. [Konfiguracja](#konfiguracja)
11. [Testowanie](#testowanie)
12. [Rozwiązywanie problemów](#rozwiązywanie-problemów)
13. [Wkład w projekt](#wkład-w-projekt)
14. [Licencja](#licencja)

---

## Opis projektu

ALF-ROS to pełne oprogramowanie komunikacyjne ROS2 dla robota **Unitree G1 EDU**.
Dostarcza:

- **GUI (PyQt5)** z zakładkami do zarządzania węzłami, topikami, akcjami i statusem robota,
- **monitor CLI** z kolorowym wyjściem terminalowym,
- **wizualizację RViz2** ze skonfigurowanym widokiem robota,
- **niestandardowe wiadomości ROS2** (`RobotStatus`, `GUICommand`),
- **serwis** (`SetMode`) i **akcję** (`MoveToGoal`),
- bezpieczny **stop awaryjny** dostępny z GUI i przez topik.

---

## Architektura systemu

```
alf_ros/                          ← Pakiet ROS2
├── alf_ros/                      ← Moduł Python
│   ├── gui/
│   │   └── main_window.py        ← Główne okno PyQt5
│   ├── nodes/
│   │   ├── gui_node.py           ← Węzeł ROS2 hostujący GUI
│   │   ├── robot_controller_node.py  ← Węzeł sterowania robotem
│   │   └── status_monitor_node.py    ← Monitor CLI
│   └── cli/
│       └── feedback.py           ← Narzędzia CLI (kolory, format)
├── msg/
│   ├── RobotStatus.msg
│   └── GUICommand.msg
├── srv/
│   └── SetMode.srv
├── action/
│   └── MoveToGoal.action
├── launch/
│   ├── alf_ros.launch.py         ← Główny plik uruchomienia
│   └── rviz.launch.py            ← Uruchomienie samego RViz2
├── rviz/
│   └── alf_ros.rviz              ← Konfiguracja RViz2
└── config/
    └── params.yaml               ← Parametry węzłów
```

### Węzły ROS2

| Węzeł               | Wykonywalny        | Opis                                |
|---------------------|--------------------|-------------------------------------|
| `alf_ros_gui`       | `gui_node`         | GUI PyQt5 + komunikacja ROS2        |
| `alf_ros_controller`| `robot_controller` | Wysokopoziomowe sterowanie robotem  |
| `alf_ros_monitor`   | `status_monitor`   | Monitor statusu w terminalu (CLI)   |

### Topiki

| Topik                        | Typ wiadomości             | Kierunek    | Opis                         |
|------------------------------|----------------------------|-------------|------------------------------|
| `/alf_ros/command`           | `std_msgs/String`          | GUI → ctrl  | Komendy wysokiego poziomu    |
| `/alf_ros/emergency_stop`    | `std_msgs/Bool`            | GUI → ctrl  | Stop awaryjny                |
| `/alf_ros/status`            | `std_msgs/String`          | ctrl → GUI  | Aktualny tryb robota         |
| `/joint_states`              | `sensor_msgs/JointState`   | robot → GUI | Stany stawów                 |
| `/joint_commands`            | `sensor_msgs/JointState`   | ctrl → robot| Komendy stawów               |
| `/cmd_vel`                   | `geometry_msgs/Twist`      | ctrl → robot| Prędkość jazdy               |
| `/battery_state/percentage`  | `std_msgs/Float32`         | robot → GUI | Poziom baterii               |

### Serwisy

| Serwis          | Typ              | Opis                        |
|-----------------|------------------|-----------------------------|
| *(własny)*      | `SetMode.srv`    | Ustawienie trybu operacyjnego|

### Akcje

| Akcja           | Typ               | Opis                        |
|-----------------|-------------------|-----------------------------|
| `/move_to_goal` | `MoveToGoal.action` | Przemieszczenie do pozycji |

---

## Wymagania systemowe

| Wymaganie         | Wersja               |
|-------------------|----------------------|
| Ubuntu            | 22.04 LTS            |
| ROS2              | Humble Hawksbill     |
| Python            | 3.10+                |
| PyQt5             | ≥ 5.15.0             |
| numpy             | ≥ 1.24.0             |

---

## Instalacja na laptopie

### 1. Zainstaluj ROS2 Humble

```bash
# Dodaj repozytorium ROS2
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install ros-humble-desktop ros-humble-rviz2 -y
```

### 2. Zainstaluj zależności Python

```bash
sudo apt install python3-pyqt5 python3-colcon-common-extensions -y
pip install numpy>=1.24.0
```

### 3. Zbuduj pakiet ALF-ROS

```bash
# Przejdź do katalogu workspace (lub utwórz nowy)
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# Skopiuj (lub sklonuj) repozytorium
cp -r /ścieżka/do/alf-ros/alf_ros .

# Zbuduj
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select alf_ros
source install/setup.bash
```

---

## Instalacja na Unitree G1 EDU

Unitree G1 EDU działa na Ubuntu 22.04 z ROS2 Humble (weryfikacja: `ros2 --version`).

### 1. Skopiuj pakiet na robota

```bash
# Z laptopa (zastąp IP adresem robota)
scp -r ./alf_ros unitree@192.168.123.2:~/ros2_ws/src/
```

### 2. Zbuduj na robocie

```bash
ssh unitree@192.168.123.2
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select alf_ros
source install/setup.bash
```

### 3. Uruchom z przestrzenią nazw `g1`

```bash
ros2 launch alf_ros alf_ros.launch.py robot_namespace:=g1 use_gui:=false
```

---

## Użycie — uruchamianie GUI

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# Uruchom wszystkie węzły z GUI (laptop)
ros2 launch alf_ros alf_ros.launch.py

# Tylko węzeł GUI
ros2 run alf_ros gui_node

# Z parametrami
ros2 run alf_ros gui_node --ros-args -p robot_namespace:=g1
```

GUI zawiera cztery zakładki:

| Zakładka         | Opis                                                     |
|------------------|----------------------------------------------------------|
| 🤖 Status robota | Stany stawów, bateria, tryb, przyciski sterowania        |
| 🔵 Węzły         | Lista aktywnych węzłów ROS2, odświeżanie                 |
| 📡 Topiki        | Lista topików, echo, publikowanie wiadomości             |
| 🎯 Akcje         | Wysyłanie celów (goal), feedback, anulowanie             |

**Przyciski sterowania robotem:**

| Przycisk           | Komenda           | Opis                          |
|--------------------|-------------------|-------------------------------|
| 🧍 Stój            | `stand`           | Postawa stojąca               |
| 🛌 Leż             | `lie_down`        | Postawa leżąca                |
| 🏠 Pozycja domyślna| `home_position`   | Wszystkie stawy = 0 rad       |
| 🛑 STOP AWARYJNY   | emergency_stop    | Natychmiastowe zatrzymanie    |

---

## Użycie — RViz2

```bash
# Uruchom samodzielnie
ros2 launch alf_ros rviz.launch.py

# Razem z głównymi węzłami
ros2 launch alf_ros alf_ros.launch.py use_rviz:=true

# Z własną konfiguracją
ros2 launch alf_ros rviz.launch.py rviz_config:=/ścieżka/do/config.rviz
```

Domyślna konfiguracja RViz2 wyświetla:
- **Siatkę** podłoża,
- **Model robota** (`/robot_description`),
- **Drzewko TF** (osie układów współrzędnych),
- **Stany stawów** (`/joint_states`),
- **Markery celu** (`/alf_ros/goal_marker`).

---

## Użycie — monitor CLI

```bash
# Uruchom monitor statusu w terminalu
ros2 run alf_ros status_monitor

# Z przestrzenią nazw
ros2 run alf_ros status_monitor --ros-args -p robot_namespace:=g1
```

Monitor wyświetla kolorowo-sformatowane logi:
- `[STATUS]` — aktualny tryb robota (zielony/czerwony),
- `[BATERIA]` — poziom naładowania (zielony/żółty/czerwony),
- `[STAWY]` — pozycje stawów w radianach,
- `[!!!] STOP AWARYJNY` — czerwony komunikat alarmowy.

---

## Konfiguracja

Parametry węzłów znajdują się w `alf_ros/config/params.yaml`:

```yaml
alf_ros_controller:
  ros__parameters:
    robot_namespace: ""
    publish_rate_hz: 50.0
    max_linear_vel: 0.5      # m/s
    max_angular_vel: 1.0     # rad/s
```

Przekazanie pliku konfiguracyjnego przy uruchomieniu:

```bash
ros2 launch alf_ros alf_ros.launch.py \
  --ros-args --params-file ~/ros2_ws/src/alf_ros/config/params.yaml
```

### Konfiguracja dla Unitree G1 EDU

Odkomentuj sekcję w `params.yaml`:

```yaml
alf_ros_controller:
  ros__parameters:
    robot_namespace: "g1"
    max_linear_vel: 0.3    # bezpieczniejszy limit dla G1
    max_angular_vel: 0.8
```

---

## Testowanie

```bash
# Zainstaluj zależności testowe
pip install pytest pytest-cov

# Uruchom testy jednostkowe (bez ROS2)
pytest tests/test_cli_feedback.py -v

# Testy GUI (wymaga PyQt5)
pytest tests/test_gui_panels.py -v

# Wszystkie testy z pokryciem
pytest tests/ --cov=alf_ros/alf_ros --cov-report=term-missing
```

---

## Rozwiązywanie problemów

### GUI nie uruchamia się

```bash
# Sprawdź czy PyQt5 jest zainstalowane
python3 -c "from PyQt5.QtWidgets import QApplication; print('OK')"

# Zainstaluj jeśli brak
sudo apt install python3-pyqt5
# lub
pip install PyQt5>=5.15.0
```

### Węzły nie widzą się nawzajem

```bash
# Sprawdź zmienną ROS_DOMAIN_ID (musi być taka sama na wszystkich maszynach)
echo $ROS_DOMAIN_ID
export ROS_DOMAIN_ID=0

# Sprawdź połączenie sieciowe
ros2 node list
ros2 topic list
```

### Robot nie odpowiada na komendy

```bash
# Sprawdź czy controller jest aktywny
ros2 node info /alf_ros_controller

# Wyślij komendę ręcznie
ros2 topic pub /alf_ros/command std_msgs/String "{data: 'stand'}" --once

# Sprawdź stop awaryjny
ros2 topic echo /alf_ros/emergency_stop
ros2 topic pub /alf_ros/emergency_stop std_msgs/Bool "{data: false}" --once
```

### Brak danych o stawach

```bash
# Sprawdź czy robot publikuje joint_states
ros2 topic echo /joint_states --no-arr

# Sprawdź częstotliwość
ros2 topic hz /joint_states
```

---

## Styl kodu i narzędzia jakości

| Narzędzie    | Zastosowanie                    |
|--------------|---------------------------------|
| `ruff`       | Lintowanie i formatowanie kodu  |
| `mypy`       | Statyczna analiza typów         |
| `pytest`     | Testy jednostkowe               |
| `pre-commit` | Weryfikacja przed commitem      |

```bash
ruff check alf_ros/ tests/
ruff format alf_ros/ tests/
mypy alf_ros/alf_ros/
pytest tests/ --cov=alf_ros/alf_ros
```

---

## Wkład w projekt

1. Utwórz branch: `feature/<nazwa>` lub `fix/<nazwa>`.
2. Postępuj zgodnie z zasadami z `AGENTS.md` / `CLAUDE.md`.
3. Uruchom testy i linter przed wystawieniem PR.
4. Wypełnij szablon Pull Request (`.github/PULL_REQUEST_TEMPLATE.md`).

---

## Licencja

Projekt objęty licencją **Apache 2.0** — szczegóły w pliku [LICENSE](LICENSE).
