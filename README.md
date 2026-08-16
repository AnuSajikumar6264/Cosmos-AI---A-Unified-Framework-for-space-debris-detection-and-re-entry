# Satellite-Digital-Twin-for-Anomaly-Detection-and-Heath-Monitoring-System
A highly advanced, interactive satellite anomaly detection and digital twin dashboard built in Streamlit. This dashboard visually breaks down complex aerospace ML architectures like Convolutional Neural Networks (CNNs), Generative Adversarial Networks (GANs), and Recurrent Neural Networks (RNN/LSTM/GRU) into real-time interactive diagnostics.
<img width="1168" height="657" alt="image" src="https://github.com/user-attachments/assets/2502ab54-f01e-4da8-a6bb-143cf5143ce6" />
## Key Features
- **Dynamic 3D Orbital Trajectories**: Real-time Plotly 3D visualizers that physically adapt Low Earth Orbit (LEO) vs Geostationary (GEO) trajectories based on your active Model architecture choice.
- **Topographical Mathematics Engine**: Procedurally generates synthetic topological geometries—such as Volcanic landscapes, Cities with winding rivers, and Agricultural maps—dynamically mirroring physical satellite lenses.
- **Dynamic Modular Framework Mapping**: Adapts interactive Graphviz system architecture diagrams in real-time, mapping exact node pipelines based on whether your selected model uses spatial extraction or temporal bounds checking.
- **Live Diagnostics & Telemetry**: Monitor real-time telemetry (Attitude, Power, Temperature) alongside integrated automated disaster recovery pathways when structural injections fail.

## ☄️ Review 4 — Debris Detection & Re-entry Impact Prediction

The twin now answers a second question: **if this satellite comes apart, or this rocket sheds a
stage, where does the hardware land and who is at risk?**

- 🔧 **[`DEBRIS.md`](DEBRIS.md)** — engineering notes and the complete measured-results tables.
- 📦 **[`debris/`](debris/)** — a 16-module physics package. The core is **numpy-only**.
- 🖥️ Eight new dashboard pages appear under **DEBRIS & GROUND RISK** in the sidebar.

**What it does**

| | |
|---|---|
| **Re-entry propagator** | 3-DOF integration in rotating ECEF with J2 gravity, Mach- and Knudsen-dependent drag, winds, and a coupled aerothermal demise model so objects that burn up never produce an impact point |
| **Debris detection** | Frame-differencing detection on sensor imagery, converting pixels into a *ballistic coefficient* the propagator can use — classical (numpy) and CNN (optional torch) |
| **Breakup modelling** | Full NASA Standard Breakup Model, plus parent-remnant mass accounting |
| **Conformal impact zones** | Distribution-free prediction regions with **guaranteed coverage** — the standard Gaussian ellipse was measured to under-cover on fragment clouds |
| **Ground risk** | Expected-casualty estimate against the regulatory 1-in-10 000 threshold |
| **Anomaly → debris coupling** | Subsystem health drives the breakup *physics*, joining this to Reviews 1–3 |
| **Orbital consequence** | Two-species Kessler cascade / criticality engine, and debris-years sustainability accounting |

**Headline validated results**

- Two independently written propagator implementations agree to **0.15 m** on impact point.
- US Standard Atmosphere 1976 reproduced to **< 0.002 %** at every layer boundary.
- Six objects from one entry state land **2500 km apart** — governed only by ballistic coefficient.
- Conformal density zone: **0.9928 coverage at nominal 0.99 in 19 % *less* area** than the
  χ² ellipse, which itself delivers only 0.971.
- Debris detection F1 **0.06 → 0.70** once framed as a two-frame problem.

##  Running Locally

1. Ensure **Python 3.9+** is installed on your system.
2. Clone or download this repository locally.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```
   *The application will boot locally on `http://localhost:8501`.*

## ☁️ Deploying to GitHub and Streamlit Cloud

Yes, **this code will run perfectly after downloading and pushing to GitHub.** The repository is fully structured for instant public hosting via Streamlit Cloud.

### Step-by-Step GitHub Push Details
1. Create a new empty repository on [GitHub](https://github.com/new).
2. Open your terminal in this project's folder and run:
   ```bash
   git init
   git add .
   git commit -m "Initial launch of Digital Satellite Twin"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```
3. Sign into [Streamlit Community Cloud](https://share.streamlit.io/) with your GitHub account.
4. Click **New App**, select your newly created GitHub repository, use `main` as the branch, and set `app.py` as the Main file path.
5. Click **Deploy!** It will automatically read the `requirements.txt` and launch your dashboard worldwide.


##### My Streamlit App is Deployed in ' https://satellitewithspace.streamlit.app/ '
