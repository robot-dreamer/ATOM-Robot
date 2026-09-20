from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


MESSAGE_BYTES = np.array([10, 50, 100, 150, 200, 250])
MEAN_RTT_MS = np.array([4.563, 5.667, 6.068, 7.311, 8.034, 8.915])
STD_RTT_MS = np.array([0.293, 0.535, 0.148, 0.209, 0.136, 0.270])
SUCCESS_RATE = np.array([96.0, 96.4, 93.2, 92.8, 88.8, 88.0])


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 7.5,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax_rtt = plt.subplots(figsize=(3.35, 1.80))
    ax_success = ax_rtt.twinx()

    rtt_plot = ax_rtt.errorbar(
        MESSAGE_BYTES,
        MEAN_RTT_MS,
        yerr=STD_RTT_MS,
        color="#2066A8",
        marker="o",
        markersize=3.5,
        linewidth=1.25,
        elinewidth=0.8,
        capsize=2,
        label="Mean RTT",
        zorder=3,
    )
    success_plot = ax_success.plot(
        MESSAGE_BYTES,
        SUCCESS_RATE,
        color="#D04A35",
        marker="s",
        markersize=3.2,
        linewidth=1.15,
        linestyle="--",
        label="Round-trip success",
        zorder=2,
    )[0]

    ax_rtt.set_xlabel("Message length (bytes)")
    ax_rtt.set_ylabel("Mean RTT (ms)", color="#2066A8")
    ax_success.set_ylabel("Success rate (%)", color="#D04A35")
    ax_rtt.tick_params(axis="y", colors="#2066A8")
    ax_success.tick_params(axis="y", colors="#D04A35")

    ax_rtt.set_xlim(0, 260)
    ax_rtt.set_xticks([10, 50, 100, 150, 200, 250])
    ax_rtt.set_ylim(4.0, 9.5)
    ax_success.set_ylim(84, 100)
    ax_success.set_yticks([84, 88, 92, 96, 100])
    ax_rtt.grid(axis="y", color="0.86", linewidth=0.55, linestyle="--")

    ax_rtt.legend(
        [rtt_plot, success_plot],
        ["Mean RTT", "Round-trip success"],
        loc="upper left",
        frameon=False,
        ncol=2,
        columnspacing=0.9,
        handlelength=2.0,
    )

    fig.tight_layout(pad=0.45)
    output_dir = Path(__file__).resolve().parent.parent / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "espnow_latency.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "espnow_latency.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
