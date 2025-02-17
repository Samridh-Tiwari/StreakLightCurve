# Streak Light Curve

## Introduction
(*To be added later*)

---

## Initial Setup
To get started with this project, follow the steps below:

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/StreakLightCurve.git
cd StreakLightCurve
```

### 2️⃣ Download the Data
The required dataset for this project can be obtained from the following Google Drive link:

[📂 Download Data from Drive](your_drive_link_here)

Alternatively, if you prefer to generate the data locally, you can run the `TestRunModified1.py` script located in the `ImageStLc` directory. This script will process the `Asteroid.txt` file and create the necessary dataset.

```bash
python ImageStLc/TestRunModified1.py
```

---

## Environment Setup
This project uses **Conda** for managing dependencies. The exact environment configuration is saved in the `StLcEnv.yml` file located in the home directory of the project.

### 1️⃣ Create the Conda Environment
```bash
conda env create -f StLcEnv.yml
```

### 2️⃣ Activate the Environment
```bash
conda activate StLc
```

Now, you're ready to proceed with the project.

---

## Project Structure & Workflow

### 📂 `TimeStLc/` (Initial Code)
This folder contains the initial code used to identify valid asteroids that fit the following criteria:
- **Magnitude < 20** (brighter asteroids)
- **Motion Rate > 10 arcseconds per minute**

(*Further explanation for choosing these filters will be added later.*)

---

### 📂 `ImageStLc/` (Generating Observation Images)
Once the valid asteroid list is generated, we use this folder's scripts to obtain observation images using **MOST (Moving Object Search Tool)**.
- Due to storage limitations, we are currently using a **shorter asteroid list** for processing.

---

### 📂 `FWHMEndPoints/` (Finding Streak Endpoints for Photometry)
This module helps determine the streak's endpoints by:
1. Extrapolating RA/Dec using the initial observation RA/Dec and the calculated **RA/Dec rate**.
2. Placing **square FWHMs along the streak** for performing photometry analysis.

---

## Final Notes
- If any issues arise, ensure the environment is correctly set up and dependencies are installed.
- Data can either be downloaded from the drive or generated locally.
- Further documentation and explanations will be added as required.

---

🚀 **Happy Coding!**

