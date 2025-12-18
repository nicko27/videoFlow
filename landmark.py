#!/usr/bin/env python3
import argparse
import subprocess
import sys
import numpy as np

try:
    from scipy.signal import stft
    from scipy.ndimage import maximum_filter
except ImportError:
    print("Il manque scipy. Installe: pip install numpy scipy", file=sys.stderr)
    sys.exit(1)


def ffmpeg_audio_to_pcm(video_path: str, sr: int) -> np.ndarray:
    """
    Extrait l'audio en PCM float32 mono à sr Hz via ffmpeg (pipe stdout).
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", str(sr),
        "-f", "f32le",
        "pipe:1",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg a échoué sur {video_path}:\n{p.stderr.decode('utf-8', errors='replace')}")
    audio = np.frombuffer(p.stdout, dtype=np.float32)
    if audio.size == 0:
        raise RuntimeError(f"Aucun échantillon audio extrait depuis {video_path}.")
    # clamp / nettoyage simple
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    # normalisation légère
    m = np.max(np.abs(audio)) + 1e-9
    audio = audio / m
    return audio


def compute_spectrogram(audio: np.ndarray, sr: int, n_fft: int, hop: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    STFT -> spectrogramme amplitude en dB approx (log).
    Retourne (freqs, times, S_log)
    """
    f, t, Z = stft(audio, fs=sr, nperseg=n_fft, noverlap=(n_fft - hop), boundary=None, padded=False)
    S = np.abs(Z)
    S_log = np.log1p(S)  # log compress
    return f, t, S_log


def pick_peaks(S_log: np.ndarray, f: np.ndarray, t: np.ndarray,
               freq_max_hz: float,
               neighborhood_time: int,
               neighborhood_freq: int,
               amp_percentile: float,
               max_peaks_per_second: int) -> np.ndarray:
    """
    Détecte des pics locaux (f_bin, t_bin) sur une carte temps-fréquence.
    Retourne un tableau Nx2: [t_idx, f_idx]
    """
    # Limite en fréquence (on coupe au-dessus pour réduire bruit/inutilité)
    max_f_bin = np.searchsorted(f, freq_max_hz)
    max_f_bin = max(1, min(max_f_bin, S_log.shape[0]))
    S = S_log[:max_f_bin, :]

    # Filtre de maximum local
    footprint = (2 * neighborhood_freq + 1, 2 * neighborhood_time + 1)
    local_max = maximum_filter(S, size=footprint, mode="constant")
    peaks_mask = (S == local_max)

    # Seuil amplitude global (percentile)
    thresh = np.percentile(S[S > 0], amp_percentile) if np.any(S > 0) else 0.0
    peaks_mask &= (S >= thresh)

    # Récupère indices
    f_idx, t_idx = np.where(peaks_mask)

    if t_idx.size == 0:
        return np.zeros((0, 2), dtype=np.int32)

    # Limite densité: max_peaks_per_second
    # On convertit t_idx -> secondes via t[]
    # Stratégie: pour chaque "seconde" (bucket), garder les meilleurs pics par amplitude
    times_sec = t[t_idx]
    sec_bucket = np.floor(times_sec).astype(np.int32)

    # amplitude des pics pour trier
    amp = S[f_idx, t_idx]

    # Trie par bucket puis amplitude décroissante
    order = np.lexsort((-amp, sec_bucket))
    sec_bucket = sec_bucket[order]
    t_idx = t_idx[order]
    f_idx = f_idx[order]
    amp = amp[order]

    kept_t = []
    kept_f = []
    counts = {}

    for sb, ti, fi in zip(sec_bucket, t_idx, f_idx):
        c = counts.get(sb, 0)
        if c < max_peaks_per_second:
            kept_t.append(ti)
            kept_f.append(fi)
            counts[sb] = c + 1

    peaks = np.stack([np.array(kept_t, dtype=np.int32), np.array(kept_f, dtype=np.int32)], axis=1)
    # peaks = [t_idx, f_idx]
    return peaks


def build_landmark_hashes(peaks: np.ndarray, times: np.ndarray,
                          fanout: int,
                          dt_min: float,
                          dt_max: float,
                          freq_bin_quant: int,
                          time_quant: int) -> dict[int, list[int]]:
    """
    Fabrique des hashes de paires de pics.
    Retourne dict: hash -> liste de temps (quantifiés) du pic ancre.
    - peaks: Nx2 [t_idx, f_idx]
    """
    if peaks.shape[0] == 0:
        return {}

    # Trie par temps
    peaks = peaks[np.argsort(peaks[:, 0])]
    t_idx = peaks[:, 0]
    f_idx = peaks[:, 1]

    # Convertit index temps -> secondes
    t_sec = times[t_idx]

    # Quantification (pour stabilité)
    # On quantifie f_idx et dt et t_anchor
    hashes: dict[int, list[int]] = {}

    n = peaks.shape[0]
    for i in range(n):
        t1 = t_sec[i]
        f1 = f_idx[i]
        # associe avec les 'fanout' pics suivants (dans la fenêtre dt)
        paired = 0
        j = i + 1
        while j < n and paired < fanout:
            dt = t_sec[j] - t1
            if dt < dt_min:
                j += 1
                continue
            if dt > dt_max:
                break
            f2 = f_idx[j]

            # Quantifie
            f1q = int(f1 // freq_bin_quant)
            f2q = int(f2 // freq_bin_quant)
            dtq = int(round(dt * 1000.0 / time_quant))  # dt en ms/time_quant

            # Hash compact (int)
            # On met des bornes raisonnables pour éviter débordement :
            # f bins typiques < 2048, dtq < ~2000
            h = (f1q & 0x3FF) | ((f2q & 0x3FF) << 10) | ((dtq & 0xFFF) << 20)

            t_anchor_q = int(round(t1 * 1000.0 / time_quant))  # ms/time_quant
            hashes.setdefault(h, []).append(t_anchor_q)

            paired += 1
            j += 1

    return hashes


def match_hashes(h1: dict[int, list[int]], h2: dict[int, list[int]],
                 max_offsets_to_report: int = 5) -> tuple[int, list[tuple[int, int]]]:
    """
    Compare 2 dicts de hashes.
    Retourne (best_offset, top_offsets)
    - offset en unités "time_quant" (ms/time_quant)
    - top_offsets: liste (offset, votes) triée
    """
    # Vote histogram: offset -> votes
    votes = {}

    # Itère sur le plus petit dict pour réduire coût
    if len(h1) > len(h2):
        h1, h2 = h2, h1
        swap = True
    else:
        swap = False

    for h, tlist1 in h1.items():
        tlist2 = h2.get(h)
        if not tlist2:
            continue
        # Pour chaque t1, t2 : offset = t2 - t1
        # Attention: peut exploser si listes longues.
        # On limite: si trop, échantillonne.
        if len(tlist1) * len(tlist2) > 2000:
            # échantillonnage léger
            tlist1_s = tlist1[: min(len(tlist1), 50)]
            tlist2_s = tlist2[: min(len(tlist2), 50)]
        else:
            tlist1_s = tlist1
            tlist2_s = tlist2

        for t1 in tlist1_s:
            for t2 in tlist2_s:
                off = (t2 - t1)
                votes[off] = votes.get(off, 0) + 1

    if not votes:
        return 0, []

    # Top offsets
    top = sorted(votes.items(), key=lambda x: x[1], reverse=True)[:max_offsets_to_report]
    best_offset, best_votes = top[0]

    # Si on a swap, l'offset est inversé conceptuellement, mais pour l'utilisateur :
    # on affiche toujours "video2 ≈ video1 + offset".
    # Ici on a potentiellement inversé les rôles, mais on garde la convention plus bas
    # en recalculant proprement dans main (sans swap). On renvoie juste top.

    return best_offset, top


def extract_fingerprints(video_path: str,
                         sr: int,
                         n_fft: int,
                         hop: int,
                         freq_max_hz: float,
                         neighborhood_time: int,
                         neighborhood_freq: int,
                         amp_percentile: float,
                         max_peaks_per_second: int,
                         fanout: int,
                         dt_min: float,
                         dt_max: float,
                         freq_bin_quant: int,
                         time_quant: int) -> dict[int, list[int]]:
    audio = ffmpeg_audio_to_pcm(video_path, sr=sr)
    f, tt, S_log = compute_spectrogram(audio, sr=sr, n_fft=n_fft, hop=hop)
    peaks = pick_peaks(
        S_log=S_log, f=f, t=tt,
        freq_max_hz=freq_max_hz,
        neighborhood_time=neighborhood_time,
        neighborhood_freq=neighborhood_freq,
        amp_percentile=amp_percentile,
        max_peaks_per_second=max_peaks_per_second
    )
    hashes = build_landmark_hashes(
        peaks=peaks, times=tt,
        fanout=fanout, dt_min=dt_min, dt_max=dt_max,
        freq_bin_quant=freq_bin_quant,
        time_quant=time_quant
    )
    return hashes


def seconds_from_offset(offset_units: int, time_quant: int) -> float:
    # offset_units = ms/time_quant
    return (offset_units * time_quant) / 1000.0


def main():
    ap = argparse.ArgumentParser(description="Match 2 vidéos via audio landmarks (style Shazam).")
    ap.add_argument("video1", help="Chemin vers la vidéo 1 (extrait ou complète).")
    ap.add_argument("video2", help="Chemin vers la vidéo 2 (souvent la longue).")

    # Paramètres raisonnables par défaut
    ap.add_argument("--sr", type=int, default=11025)
    ap.add_argument("--n_fft", type=int, default=4096)
    ap.add_argument("--hop", type=int, default=512)
    ap.add_argument("--freq_max_hz", type=float, default=5000.0)

    ap.add_argument("--neigh_t", type=int, default=12, help="Voisinage temps (bins STFT) pour max local.")
    ap.add_argument("--neigh_f", type=int, default=8, help="Voisinage fréquence (bins STFT) pour max local.")
    ap.add_argument("--amp_pct", type=float, default=75.0, help="Percentile amplitude pour seuil pics (plus haut => moins de pics).")
    ap.add_argument("--max_peaks_per_sec", type=int, default=25)

    ap.add_argument("--fanout", type=int, default=8, help="Nombre de paires par pic ancre.")
    ap.add_argument("--dt_min", type=float, default=0.5)
    ap.add_argument("--dt_max", type=float, default=3.0)

    ap.add_argument("--freq_bin_quant", type=int, default=2, help="Quantification des bins fréquence (stabilité).")
    ap.add_argument("--time_quant", type=int, default=20, help="Quantification temps en ms (ex: 20ms).")

    ap.add_argument("--top", type=int, default=5, help="Nombre d'offsets top à afficher.")
    ap.add_argument("--min_votes", type=int, default=200, help="Seuil simple pour dire 'match probable'.")

    args = ap.parse_args()

    print("Indexing vidéo 1...")
    h1 = extract_fingerprints(
        video_path=args.video1,
        sr=args.sr, n_fft=args.n_fft, hop=args.hop, freq_max_hz=args.freq_max_hz,
        neighborhood_time=args.neigh_t, neighborhood_freq=args.neigh_f,
        amp_percentile=args.amp_pct, max_peaks_per_second=args.max_peaks_per_sec,
        fanout=args.fanout, dt_min=args.dt_min, dt_max=args.dt_max,
        freq_bin_quant=args.freq_bin_quant, time_quant=args.time_quant
    )
    print(f"  hashes vidéo1: {len(h1):,}")

    print("Indexing vidéo 2...")
    h2 = extract_fingerprints(
        video_path=args.video2,
        sr=args.sr, n_fft=args.n_fft, hop=args.hop, freq_max_hz=args.freq_max_hz,
        neighborhood_time=args.neigh_t, neighborhood_freq=args.neigh_f,
        amp_percentile=args.amp_pct, max_peaks_per_second=args.max_peaks_per_sec,
        fanout=args.fanout, dt_min=args.dt_min, dt_max=args.dt_max,
        freq_bin_quant=args.freq_bin_quant, time_quant=args.time_quant
    )
    print(f"  hashes vidéo2: {len(h2):,}")

    print("Matching...")
    # On calcule les votes d'offset en convention: video2 ≈ video1 + offset
    votes = {}
    # Itère sur les hashes communs
    for h, tlist1 in h1.items():
        tlist2 = h2.get(h)
        if not tlist2:
            continue
        # limites anti explosion
        if len(tlist1) * len(tlist2) > 2000:
            tlist1_s = tlist1[: min(len(tlist1), 50)]
            tlist2_s = tlist2[: min(len(tlist2), 50)]
        else:
            tlist1_s = tlist1
            tlist2_s = tlist2

        for t1 in tlist1_s:
            for t2 in tlist2_s:
                off = (t2 - t1)
                votes[off] = votes.get(off, 0) + 1

    if not votes:
        print("Aucune correspondance significative trouvée.")
        sys.exit(2)

    top = sorted(votes.items(), key=lambda x: x[1], reverse=True)[:args.top]
    best_off, best_votes = top[0]
    best_sec = seconds_from_offset(best_off, args.time_quant)

    print("\nTop offsets (video2 ≈ video1 + offset):")
    for off, v in top:
        sec = seconds_from_offset(off, args.time_quant)
        print(f"  offset={sec:10.3f}s   votes={v}")

    print("\nConclusion:")
    if best_votes >= args.min_votes:
        print(f"  MATCH probable. Meilleur alignement: offset ≈ {best_sec:.3f}s (votes={best_votes})")
        print("  Interprétation: le contenu de video1 apparaît dans video2 vers ce décalage.")
    else:
        print(f"  Match faible/incertain: offset ≈ {best_sec:.3f}s (votes={best_votes})")
        print("  Augmente la robustesse en baissant --amp_pct ou en augmentant --min_votes selon ton corpus.")


if __name__ == "__main__":
    main()
