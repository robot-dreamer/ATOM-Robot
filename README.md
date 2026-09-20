# ATOM Robot

<p align="center">
  <img src="Pictures/ATOM%20Robot.png" alt="ATOM omnidirectional multi-robot platform" width="800">
</p>

ATOM is a compact, low-cost omnidirectional robot designed for physical multi-robot research. Each robot combines three-wheel holonomic motion, onboard absolute pose sensing, local computation, and direct robot-to-robot communication in a 63 mm-diameter platform.

The platform is intended to reduce the hardware and deployment overhead of tabletop experiments in trajectory tracking, collision avoidance, formation control, target assignment, and cooperative transport.

## Highlights

- **Omnidirectional motion:** three independently driven omni wheels provide two translational degrees of freedom and one rotational degree of freedom.
- **Onboard absolute localization:** a downward-facing Optical Identification (OID) sensor reads dot patterns on a compatible printable coded surface without an overhead camera or motion-capture system.
- **Onboard closed-loop control:** pose feedback, motion control, and task programs run on the robot.
- **Direct multi-robot communication:** ESP-NOW supports state exchange and task coordination without requiring a wireless access point.
- **Accessible programming:** robot behaviors are developed in the [MicroBlocks](https://microblocks.fun/) graphical programming environment and can run independently after deployment.
- **Low-cost construction:** the bill of materials is approximately USD 35 per robot based on small-batch procurement in August 2026.

## Specifications

| Item | Specification |
|---|---|
| Dimensions | 63 mm diameter, 48 mm height |
| Mass | 120 g |
| Drive | Three N20 geared motors and three omni wheels |
| Wheel radius | 12 mm |
| Center-to-wheel distance | 23 mm |
| Maximum translational speed | Approximately 250 mm/s |
| Maximum angular speed | Approximately 8.1 rad/s |
| Controller | M5Stack StampS3A with ESP32-S3 |
| Localization | Downward-facing OID sensor on a printable coded surface |
| Wireless communication | ESP-NOW, Wi-Fi, and BLE |
| Battery | 2S, 500 mAh lithium-ion battery |
| Typical operating time | Approximately 2 h |
| Approximate BOM cost | USD 35 |

## Repository Contents

```text
ATOM-Robot/
├── Experiment/          # Final experimental programs, data, and analysis scripts
├── Hardware/
│   ├── CAD/             # Mechanical model and assembly references
│   └── PCB/             # Schematic, Gerber files, PCB image, and BOM
├── Pictures/            # Platform photographs
├── Software/            # MicroBlocks robot library
└── Videos/              # Multi-robot demonstration videos
```

Important files:

- [ATOM mechanical model](Hardware/CAD/ATOM.step)
- [PCB schematic](Hardware/PCB/Schematic.pdf)
- [Gerber files](Hardware/PCB/Gerber_PCB.zip)
- [Bill of materials](Hardware/PCB/BOM_ATOM.xlsx)
- [ATOM MicroBlocks library](Software/ATOM.ubl)
- [Experimental programs and data](Experiment/README.md)

## Getting Started

1. Review the BOM, schematic, PCB files, and mechanical model in the `Hardware` directory.
2. Manufacture the PCB and mechanical parts, then assemble the motors, omni wheels, controller, OID sensor, display, and battery.
3. Install [MicroBlocks](https://microblocks.fun/) and connect to the StampS3A controller.
4. Import `Software/ATOM.ubl` into MicroBlocks.
5. Place the robot on a compatible printed OID surface and verify that position and heading data are available.
6. Build task programs using the library's pose, wheel-control, and target-tracking blocks.

The map coordinate convention used by the library is positive X to the right and positive Y downward.

## Demonstrations

- [ATOM ICRA 2027 demonstration](Videos/ATOM%20ICRA%202027.mp4)

The video files are stored using Git LFS. Install [Git LFS](https://git-lfs.com/) before cloning if you need the original video files:

```bash
git lfs install
git clone https://github.com/robot-dreamer/ATOM-Robot.git
```

## Citation

If you use ATOM in academic work, please cite the associated paper. Citation information will be added after publication.

## License

This repository is released under the terms in [LICENSE](LICENSE). Third-party hardware, software, and services remain subject to their respective licenses and terms.
