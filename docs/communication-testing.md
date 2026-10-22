# SpectrumSentry AI — Real Communication Testing Guide (Phase 5)

## 1. Overview
This document specifies how to execute, verify, and evaluate real communication monitoring between SpectrumSentry AI endpoints across three real-world deployment topologies:
1. **Local Loopback Test** (`127.0.0.1`)
2. **Local Area Network (LAN) Test** (Wi-Fi router / Ethernet)
3. **Mobile Phone Hotspot Test** (Portable wireless testbed)

---

## 2. Test Execution Topologies

### Topology 1: Local Loopback Test (Single Device)
- **Monitoring Server**: `http://127.0.0.1:8000`
- **Execution Command**:
  ```bash
  python scripts/communication_client.py --host 127.0.0.1 --port 8000 --interval 0.25 --duration 30
  ```

### Topology 2: Wi-Fi LAN Test (Two Real Devices)
- **Monitoring Server (Device A)**:
  - Connect Laptop A to the local Wi-Fi router.
  - Determine local IP address (e.g. `192.168.1.100` via `ifconfig` or `ipconfig`).
  - Run server bound to all interfaces:
    ```bash
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    ```
- **Test Client (Device B — Phone or Second Laptop)**:
  - Connect Device B to the same Wi-Fi router.
  - Execute test client:
    ```bash
    python scripts/communication_client.py --host 192.168.1.100 --port 8000 --interval 0.25 --duration 60
    ```
  - *Note*: Ensure the host OS firewall permits inbound TCP connections on port 8000.

### Topology 3: Mobile Hotspot Test (Isolated Portable Network)
- **Setup**:
  - Enable Mobile Hotspot on a smartphone.
  - Connect Laptop A (server) and Laptop B (client) to the hotspot.
  - Obtain Laptop A's hotspot IP address (e.g. `172.20.10.2`).
- **Run Server**:
  ```bash
  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
  ```
- **Run Client**:
  ```bash
  python scripts/communication_client.py --host 172.20.10.2 --port 8000 --interval 0.2 --duration 60
  ```

---

## 3. Controlled Interruption & Recovery Verification

To deterministically test interruption detection and recovery without interfering with third-party networks, use the `--pause-after` and `--pause-duration` CLI flags:

```bash
python scripts/communication_client.py \
    --host 127.0.0.1 \
    --port 8000 \
    --interval 0.2 \
    --duration 10.0 \
    --pause-after 10 \
    --pause-duration 3.5
```

### Expected State Transitions:
```
Packets #1–10  : CONNECTED   (RTT ~2–4 ms, Health: 100.0)
Pause 3.5s     : INTERRUPTED (Server timeout threshold 2.0s exceeded)
Packet #11     : RECOVERING  (Resuming packet arrives; calculates 3.5s silence)
Packets #12–N  : CONNECTED   (Link restabilized; Health: 95.0 after history penalty)
```

---

## 4. Benchmark & Validation Results (Actual Run)

### Test Run 1: Normal Continuous Communication
- **Interval**: $0.200\text{ s}$ ($5.0\text{ pkt/s}$)
- **Payload Size**: $1,024\text{ bytes}$
- **Elapsed Duration**: $5.01\text{ s}$
- **Packets Sent**: $24$
- **Packets Acknowledged**: $24$
- **Packet Loss Rate**: **$0.00\%$**
- **RTT Latency**:
  - Minimum: $1.38\text{ ms}$
  - Average: $3.91\text{ ms}$
  - Maximum: $8.73\text{ ms}$
- **Server Metrics**:
  - Average Latency: $3.77\text{ ms}$
  - Jitter: $1.32\text{ ms}$
  - Application Throughput: $40.99\text{ kbps}$
  - Health Score: **$100.0 / 100.0$**
  - Interruptions: $0$

### Test Run 2: Controlled Interruption Simulation
- **Interval**: $0.200\text{ s}$
- **Payload Size**: $1,024\text{ bytes}$
- **Pause Parameter**: $3.0\text{ s}$ pause after packet #8
- **Elapsed Duration**: $7.18\text{ s}$
- **Packets Sent**: $20$
- **Packets Acknowledged**: $20$
- **Packet Loss Rate**: **$0.00\%$**
- **Server Detection**:
  - Interruption Detected: **Yes** ($1$ interruption)
  - Interruption Duration: **$3,211.72\text{ ms}$** ($\approx 3.21\text{ s}$)
  - Recoveries Recorded: **$1$**
  - Final Health Score: **$95.0 / 100.0$** (reflecting historical interruption penalty)

---

## 5. Critical Distinction: Network vs. RF Limitations

Application-layer telemetry measures the performance of standard IP sockets, but does not provide physical-layer radio measurements:

- **Packet Loss $\ne$ Jamming**:
  Packet loss can be caused by Wi-Fi contention, bufferbloat, router CPU saturation, OS scheduling, or physical interference. Application monitoring alone cannot pinpoint the root cause.
- **Latency & Jitter $\ne$ Multipath Fading**:
  Variations in RTT are dominated by OS network stack buffers and TCP/IP scheduling rather than high-frequency RF channel coherence time.
- **Communication Health $\ne$ Spectrum Clear Channel**:
  A health score of $100\%$ indicates clean application-layer packet delivery, not an absence of background RF noise or co-channel signals.

SpectrumSentry AI maintains strict architectural isolation between the **Phase 4 DSP/AI Engine** (physical-layer I/Q features and modulation classification) and the **Phase 5 Communication Monitor** (network-layer packet metrics). These domains will be correlated in **Phase 6: Decision Engine**.
