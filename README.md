# Satware Simulations

Satware Simulations is an advanced desktop environment designed for real-time modeling, analysis, and simulation of space missions. The software enables orbit design, physical and hardware satellite configuration, and full 6-DOF (translational and rotational) attitude dynamics simulations featuring active ADCS algorithms and LEO environmental disturbance models.

---

## Key Features

### 1. Orbit Designer
* **Orbit Generation:** Define custom trajectories using classical Keplerian orbital elements.
* **3D Visualization:** Render Earth mesh, orbital and equatorial planes, alongside ECI and ECEF reference frame coordinate vectors.
* **Characteristics & Classification:** Analyze trajectory geometry, energy dynamics, and orbit classification (LEO, MEO, HEO, Sun-Synchronous, Molniya) alongside $J_2$ perturbation properties.
* **Pre-defined Profiles:** Load saved custom JSON files or pre-configured orbits (e.g., ISS, Molniya).

### 2. Satellite Configurator
* **Mechanical Modeling:** Define mass, rectangular dimensions, inertia tensors and magnetic dipole parameters.
* **Actuator Setup:** Configure Reaction Wheel assemblies and magnetorquer parameters.
* **Profile Management:** Save and load full satellite hardware configurations using JSON files.

### 3. Simulation Engine
* **6-DOF Dynamics:** Perform numerical integration of equations of motion with customizable integration time steps.
* **Disturbance Models:**
  * $J_2$ gravitational perturbations.
  * Gravity Gradient torque.
  * Atmospheric Drag using NRLMSISE-00 with dynamic CoP/CoM offset and Earth rotation effects.
* **ADCS Algorithms:** Active attitude control testing, including B-dot detumbling and Reaction Wheel momentum management.
* **Real-time Telemetry & Plots:** Real-time 3D motion playback (with pause/speed controls) and customizable plotting interface (up to 3 simultaneous plots).

---

## Prerequisites & Installation

### System Requirements
* **Python:** 3.12.6 
* **Operating System:** Windows / Linux (mainly tested on Windows)

### 1. Clone the Repository
```
git clone https://github.com/Luki10011/SatwareSimulations.git
```

### 2. Create virtual environment
```[bash]
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install required dependecies
```
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Running the Application
```
python -m main
```

---

## User Manual

