# Layered Graph Security Games Generators

This repository contains Python scripts for generating three types of security games played on layered graphs (and their conversion to normal form), as introduced in our paper. Each script can operate on synthetic grid worlds or real-world maps generated using the `osmnx` library. The games described include Pursuit-Evasion (PE), Anti-Terrorism (AT), and Logistical Interdiction (LI)/Persistent Threats (PT) games. Below is a description of the games and their respective generators.

## Games

### 1. **Pursuit-Evasion (PE)**
The simplest of the implemented games, the Pursuit-Evasion (PE) game models a finite-horizon scenario where a defender (pursuer) attempts to capture an attacker (evader) within a graph. Players start at specific vertices, and at each timestep, they select an edge to traverse (loops are allowed). The game ends if both players share the same vertex simultaneously. 
Key features:
- Attacker aims to evade capture.
- Defender aims to intercept the attacker by sharing the same vertex.
- The interdiction function can vary, such as interdiction occurring on the same edge or based on physical proximity.

### 2. **Anti-Terrorism (AT)**
An extension of PE games, the Anti-Terrorism (AT) game introduces the concept of a terrorist (attacker) aiming to plant an explosive device at a target node. The attacker must stay at the target vertex for a set time to successfully detonate the explosive, all while evading capture by the defender. The interdiction rules are similar to PE but involve additional complexity due to waiting times and setup phases.
Key features:
- The attacker must complete a setup phase to plant an explosive at a target node.
- The game uses layered graphs to model the attacker's waiting time and movement.
- If the attacker is captured or fails to plant the explosive, they receive no reward.

### 3. **Logistical Interdiction (LI) & Persistent Threats (PT)**
This game type modifies PE games by introducing exit vertices that allow the attacker to end the game. A `delay factor` (`γ`) is introduced to represent the time cost or benefit of staying in the game:
- **Logistical Interdiction (LI)**: When `γ < 1`, the attacker aims to exit the game as quickly as possible, representing real-world scenarios such as protecting supply lines where delays cause damage.
- **Persistent Threats (PT)**: When `γ > 1`, the attacker aims to remain in the game for as long as possible, modeling situations like advanced persistent threats (APTs) in cybersecurity where attackers seek to extract information or cause damage over time.

## Generators

- **`generate_pursuit_game.py`**: Generates the Pursuit-Evasion (PE) game. This script can simulate the pursuit-evasion game on either synthetic grid worlds or real-world maps.
  
- **`generate_antiterrorism_game.py`**: Generates the Anti-Terrorism (AT) game. The attacker aims to plant an explosive at a target node, while the defender attempts to prevent this.

- **`generate_interdiction_game.py`**: Generates the Logistical Interdiction (LI) and Persistent Threats (PT) games. These games model scenarios where the attacker seeks to either exit the graph quickly or stay and cause more damage over time.

## Real-World Map Support

Each generator supports the use of real-world maps via the `osmnx` library. This feature allows users to simulate the games on real urban environments. The maps are converted into graph representations, where nodes represent intersections or important locations, and edges represent roads or pathways.

## Dependencies

- Python 3.x
- `osmnx`: For generating real-world map data. Install via:
  ```bash
  pip install osmnx
  ```
- `numpy`: For numerical computations. Install via:
  ```bash
  pip install numpy
  ```

## Citation

If you use this repository, please cite our paper:

Jakub Cerny, Chun Kai Ling, Christian Kroer and Garud Iyengar. "Layered Graph Security Games." *IJCAI'24* and *arXiv preprint arXiv:2405.03070* (2024).

```bibtex
@inproceedings{cerny2024lgsg,
  title     = {Layered Graph Security Games},
  author    = {Cerny, Jakub and Ling, Chun Kai and Kroer, Christian and Iyengar, Garud},
  booktitle = {Proceedings of the Thirty-Third International Joint Conference on
               Artificial Intelligence, {IJCAI-24}},
  publisher = {International Joint Conferences on Artificial Intelligence Organization},
  editor    = {Kate Larson},
  pages     = {2695--2703},
  year      = {2024},
  month     = {8},
  note      = {Main Track},
  doi       = {10.24963/ijcai.2024/298},
  url       = {https://doi.org/10.24963/ijcai.2024/298},
}

```